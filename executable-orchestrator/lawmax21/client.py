"""DeepSeek client. Real HTTP, real usage accounting, honest identity for every request.

v2.0 keyed its cache on (role, ticket, context_hash) — so a different question with the
same ticket was served a stale answer, and the dry-run advertised that as a passing
"replay test". Here the logical id covers the ENTIRE request: protocol version, endpoint,
model, system-prompt hash, context-package hash, role, ticket and the canonical request
body. Two requests share an id only when they are byte-identical in every dimension that
could change the answer.

Order is fixed and load-bearing:
    reserve budget -> write raw request -> send -> write raw response -> parse
                   -> validate against the caller's schema -> settle budget
A crash anywhere leaves the raw bytes on disk, so `--resume` can always see exactly what
was asked and what came back.
"""
import json
import os
import time
import urllib.error
import urllib.request

from .canonical import (PROTOCOL_VERSION, atomic_write_json, canonical_bytes, read_json,
                        sha256_bytes, sha256_obj, utc)


class ApiError(Exception):
    pass


class StructuredOutputRejected(Exception):
    pass


# EUR per 1M tokens. Owner decision D-01 freezes the values actually used for a run.
DEFAULT_PRICES = {"input_eur_per_mtok": 0.55, "output_eur_per_mtok": 2.19}


class HttpTransport:
    """The only transport used by --launch. It cannot be swapped at runtime by a flag:
    orchestrator.py constructs it from frozen config, and the mock server is reached by
    pointing `endpoint` at localhost — same code path, same parsing, same accounting."""

    def __init__(self, endpoint, model, api_key_env="DEEPSEEK_API_KEY", timeout=180):
        self.endpoint, self.model, self.key_env, self.timeout = endpoint, model, api_key_env, timeout

    def describe(self):
        return {"endpoint": self.endpoint, "model": self.model, "key_env": self.key_env}

    def send(self, body):
        key = os.environ.get(self.key_env)
        if not key:
            raise ApiError(f"{self.key_env} is not set — refusing to attempt a call")
        data = canonical_bytes(body)
        req = urllib.request.Request(
            self.endpoint, data=data,
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                     "User-Agent": f"LAWMAX/{PROTOCOL_VERSION}"},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read().decode("utf-8")
                return r.status, raw
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except urllib.error.URLError as e:
            raise ApiError(f"transport failure: {e.reason}") from e


def extract_content(response_obj):
    """Pull the assistant message out of a real chat-completion envelope.
    v2.0 never did this: it handed the whole envelope to a brace-scanner."""
    try:
        choice = response_obj["choices"][0]
    except (KeyError, IndexError, TypeError):
        raise ApiError("response has no choices[0]")
    msg = choice.get("message") or {}
    content = msg.get("content")
    if content is None:
        content = choice.get("text")
    if not isinstance(content, str):
        raise ApiError("response contains no textual assistant content")
    if choice.get("finish_reason") == "length":
        raise ApiError("response was truncated by the output limit (finish_reason=length)")
    return content


def extract_json_object(text):
    """Exactly one JSON object is expected. Fenced blocks are tolerated; ambiguity is not."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    dec, found, i = json.JSONDecoder(), [], 0
    while i < len(s):
        j = s.find("{", i)
        if j < 0:
            break
        try:
            obj, k = dec.raw_decode(s, j)
            found.append(obj)
            i = k
        except ValueError:
            i = j + 1
    if not found:
        raise StructuredOutputRejected("no JSON object in the model's reply")
    if len(found) > 1:
        raise StructuredOutputRejected(f"{len(found)} JSON objects in the reply — ambiguous")
    return found[0]


def extract_usage(response_obj, prices):
    u = response_obj.get("usage") or {}
    pt = u.get("prompt_tokens")
    ct = u.get("completion_tokens")
    if pt is None or ct is None:
        raise ApiError("response carries no usage.prompt_tokens/completion_tokens — "
                       "cost cannot be accounted, so the call is not admissible")
    eur = (pt / 1e6) * prices["input_eur_per_mtok"] + (ct / 1e6) * prices["output_eur_per_mtok"]
    return {"prompt_tokens": pt, "completion_tokens": ct,
            "total_tokens": u.get("total_tokens", pt + ct),
            "cached_tokens": (u.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
            "eur": round(eur, 6)}


class Client:
    def __init__(self, transport, raw_dir, ledger, log, system_prompt, prices=None,
                 max_technical_retries=5, estimate_tokens_per_char=0.34):
        self.t = transport
        self.raw = os.path.abspath(raw_dir)
        self.ledger = ledger
        self.log = log
        self.system_prompt = system_prompt
        self.system_sha = sha256_bytes(system_prompt.encode("utf-8"))
        self.prices = dict(prices or DEFAULT_PRICES)
        self.max_technical_retries = max_technical_retries
        self.tpc = estimate_tokens_per_char
        os.makedirs(os.path.join(self.raw, "requests"), exist_ok=True)
        os.makedirs(os.path.join(self.raw, "responses"), exist_ok=True)
        os.makedirs(os.path.join(self.raw, "meta"), exist_ok=True)

    # ------------------------------------------------------------- identity
    def identity(self, role, ticket, context_package_sha, request_body):
        return {
            "protocol_version": PROTOCOL_VERSION,
            "endpoint": self.t.endpoint,
            "model": self.t.model,
            "system_prompt_sha256": self.system_sha,
            "context_package_sha256": context_package_sha,
            "role": role,
            "ticket": ticket,
            "request": request_body,
        }

    @staticmethod
    def logical_id(identity):
        return sha256_obj(identity)

    def _paths(self, lid):
        return (os.path.join(self.raw, "meta", lid + ".json"),
                os.path.join(self.raw, "requests", lid + ".request.json"),
                os.path.join(self.raw, "responses", lid + ".response.json"))

    def _estimate(self, identity):
        chars = len(canonical_bytes(identity)) + len(self.system_prompt)
        est_in = int(chars * self.tpc)
        est_out = 4096
        eur = (est_in / 1e6) * self.prices["input_eur_per_mtok"] + \
              (est_out / 1e6) * self.prices["output_eur_per_mtok"]
        return est_in + est_out, round(eur, 6)

    # ----------------------------------------------------------------- call
    def call(self, role, ticket, context_package_sha, messages, response_schema=None,
             temperature=0.0, max_tokens=8192, line="main"):
        """Returns (logical_id, parsed_object_or_text, replayed: bool, usage)."""
        body = {"model": self.t.model, "temperature": temperature, "max_tokens": max_tokens,
                "messages": [{"role": "system", "content": self.system_prompt}] + messages}
        identity = self.identity(role, ticket, context_package_sha, body)
        lid = self.logical_id(identity)
        meta_p, req_p, resp_p = self._paths(lid)

        if os.path.exists(meta_p) and os.path.exists(resp_p):
            meta = read_json(meta_p)
            parsed = self._parse(read_json(resp_p), response_schema, role)
            return lid, parsed, True, meta["usage"]

        est_tokens, est_eur = self._estimate(identity)
        self.ledger.reserve(lid, role, est_tokens, est_eur, line=line)

        # raw request on disk BEFORE a single byte leaves the machine
        atomic_write_json(req_p, {"logical_id": lid, "utc": utc(), "identity": identity})

        try:
            status, raw_text = self._send_with_retries(body)
            try:
                response_obj = json.loads(raw_text)
            except json.JSONDecodeError:
                response_obj = {"_non_json_body": raw_text}
            atomic_write_json(resp_p, response_obj)  # raw response BEFORE parsing
            if status != 200:
                raise ApiError(f"HTTP {status}: {json.dumps(response_obj)[:400]}")
            usage = extract_usage(response_obj, self.prices)
        except BaseException:
            self.ledger.release(lid)
            raise

        parsed = self._parse(response_obj, response_schema, role)
        atomic_write_json(meta_p, {"logical_id": lid, "role": role, "ticket": ticket,
                                   "utc": utc(), "status": status, "usage": usage,
                                   "identity_sha256": sha256_obj(identity)})
        self.ledger.settle(lid, usage["total_tokens"], usage["eur"], usage=usage)
        if self.log is not None:
            self.log.append("api-call", "deepseek-client",
                            {"logical_id": lid, "role": role, "ticket": ticket,
                             "model": self.t.model, "endpoint": self.t.endpoint,
                             "usage": usage},
                            reason="paid call settled", subject_sha256=lid)
        return lid, parsed, False, usage

    def _send_with_retries(self, body):
        last = None
        for attempt in range(1, self.max_technical_retries + 1):
            try:
                status, raw = self.t.send(body)
                if status in (429, 500, 502, 503, 504) and attempt < self.max_technical_retries:
                    last = f"HTTP {status}"
                    time.sleep(min(2 ** attempt, 30))
                    continue
                return status, raw
            except ApiError as e:
                last = str(e)
                if attempt == self.max_technical_retries:
                    break
                time.sleep(min(2 ** attempt, 30))
        raise ApiError(f"transport failed after {self.max_technical_retries} technical retries: {last}")

    def _parse(self, response_obj, response_schema, role):
        content = extract_content(response_obj)
        if response_schema is None:
            return content
        obj = extract_json_object(content)
        from .schema import ValidationError, validate
        try:
            validate(obj, response_schema)
        except ValidationError as e:
            raise StructuredOutputRejected(f"{role}: reply does not satisfy its schema: {e}")
        return obj
