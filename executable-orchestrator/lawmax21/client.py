"""DeepSeek client. Real HTTP, real usage accounting, honest identity for every request.

The logical id covers the entire identity-bearing request. Budget is reserved before a byte leaves
the machine and settled only from provider-reported usage. Historical LAWMAX pricing remains
supported without changing its request identity; currency-explicit profiles freeze their price
schedule into the identity so a replay can never silently cross billing contracts.
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


DEFAULT_PRICES = {"input_eur_per_mtok": 0.55, "output_eur_per_mtok": 2.19}


def _is_legacy_price_table(prices):
    p = prices or {}
    return "input_eur_per_mtok" in p or "output_eur_per_mtok" in p


def normalize_prices(prices):
    p = dict(prices or DEFAULT_PRICES)
    if _is_legacy_price_table(p):
        if "input_eur_per_mtok" not in p or "output_eur_per_mtok" not in p:
            raise ValueError("legacy price table requires both input_eur_per_mtok and output_eur_per_mtok")
        return {
            "currency": "EUR",
            "input_cache_hit_per_mtok": float(p["input_eur_per_mtok"]),
            "input_cache_miss_per_mtok": float(p["input_eur_per_mtok"]),
            "output_per_mtok": float(p["output_eur_per_mtok"]),
            "require_cache_split": False,
            "model": p.get("model"),
            "source": p.get("source"),
        }

    required = ("currency", "input_cache_hit_per_mtok",
                "input_cache_miss_per_mtok", "output_per_mtok")
    missing = [k for k in required if k not in p]
    if missing:
        raise ValueError(f"currency-explicit price table missing: {missing}")
    out = {
        "currency": str(p["currency"]).upper(),
        "input_cache_hit_per_mtok": float(p["input_cache_hit_per_mtok"]),
        "input_cache_miss_per_mtok": float(p["input_cache_miss_per_mtok"]),
        "output_per_mtok": float(p["output_per_mtok"]),
        "require_cache_split": bool(p.get("require_cache_split", True)),
        "model": p.get("model"),
        "source": p.get("source"),
        "verified_date": p.get("verified_date"),
    }
    if any(out[k] < 0 for k in ("input_cache_hit_per_mtok",
                                 "input_cache_miss_per_mtok", "output_per_mtok")):
        raise ValueError("price table contains a negative rate")
    return out


class HttpTransport:
    """The only transport used by --launch."""

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
    raw_prices = dict(prices or DEFAULT_PRICES)
    legacy = _is_legacy_price_table(raw_prices)
    p = normalize_prices(raw_prices)
    u = response_obj.get("usage") or {}
    pt = u.get("prompt_tokens")
    ct = u.get("completion_tokens")
    if pt is None or ct is None:
        raise ApiError("response carries no usage.prompt_tokens/completion_tokens — "
                       "cost cannot be accounted, so the call is not admissible")
    pt, ct = int(pt), int(ct)

    hit = u.get("prompt_cache_hit_tokens")
    miss = u.get("prompt_cache_miss_tokens")
    if hit is None or miss is None:
        nested = (u.get("prompt_tokens_details") or {}).get("cached_tokens")
        if p["require_cache_split"]:
            raise ApiError("provider usage omitted prompt_cache_hit_tokens/prompt_cache_miss_tokens — "
                           "currency-explicit cost cannot be settled exactly")
        hit = int(nested or 0)
        miss = pt - hit
    hit, miss = int(hit), int(miss)
    if hit < 0 or miss < 0 or hit + miss != pt:
        raise ApiError(
            f"provider cache accounting inconsistent: hit={hit}, miss={miss}, prompt={pt}")

    amount = ((hit / 1e6) * p["input_cache_hit_per_mtok"]
              + (miss / 1e6) * p["input_cache_miss_per_mtok"]
              + (ct / 1e6) * p["output_per_mtok"])
    usage = {
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": int(u.get("total_tokens", pt + ct)),
        "prompt_cache_hit_tokens": hit,
        "prompt_cache_miss_tokens": miss,
        "cached_tokens": hit,
        "reasoning_tokens": int((u.get("completion_tokens_details") or {}).get("reasoning_tokens", 0) or 0),
        "billing_currency": p["currency"],
        "billing_amount": round(amount, 9),
    }
    if legacy:
        usage["eur"] = usage["billing_amount"]
    return usage


class Client:
    def __init__(self, transport, raw_dir, ledger, log, system_prompt, prices=None,
                 max_technical_retries=5, estimate_tokens_per_char=0.34,
                 request_defaults=None, default_max_tokens=8192):
        self.t = transport
        self.raw = os.path.abspath(raw_dir)
        self.ledger = ledger
        self.log = log
        self.system_prompt = system_prompt
        self.system_sha = sha256_bytes(system_prompt.encode("utf-8"))
        raw_prices = dict(DEFAULT_PRICES if prices is None else prices)
        self.legacy_pricing = _is_legacy_price_table(raw_prices)
        self.prices = normalize_prices(raw_prices)
        self.max_technical_retries = max_technical_retries
        self.tpc = estimate_tokens_per_char
        self.request_defaults = dict(request_defaults or {})
        self.default_max_tokens = int(default_max_tokens)
        if self.default_max_tokens <= 0:
            raise ValueError("default_max_tokens must be positive")
        if getattr(self.ledger, "currency", self.prices["currency"]) != self.prices["currency"]:
            raise ValueError(
                f"budget currency {getattr(self.ledger, 'currency', None)} does not match "
                f"provider price currency {self.prices['currency']}")
        forbidden = {"model", "messages"} & set(self.request_defaults)
        if forbidden:
            raise ValueError(f"request_defaults may not override core request fields: {sorted(forbidden)}")
        os.makedirs(os.path.join(self.raw, "requests"), exist_ok=True)
        os.makedirs(os.path.join(self.raw, "responses"), exist_ok=True)
        os.makedirs(os.path.join(self.raw, "meta"), exist_ok=True)

    def identity(self, role, ticket, context_package_sha, request_body):
        identity = {
            "protocol_version": PROTOCOL_VERSION,
            "endpoint": self.t.endpoint,
            "model": self.t.model,
            "system_prompt_sha256": self.system_sha,
            "context_package_sha256": context_package_sha,
            "role": role,
            "ticket": ticket,
            "request": request_body,
        }
        # Preserve the historical LAWMAX identity byte-shape. New currency-explicit profiles bind
        # their signed price schedule into identity because a billing contract change is material.
        if not self.legacy_pricing:
            identity["price_schedule"] = self.prices
        return identity

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
        est_out = int((identity.get("request") or {}).get("max_tokens") or 4096)
        amount = ((est_in / 1e6) * self.prices["input_cache_miss_per_mtok"]
                  + (est_out / 1e6) * self.prices["output_per_mtok"])
        return est_in + est_out, round(amount, 9)

    def call(self, role, ticket, context_package_sha, messages, response_schema=None,
             temperature=0.0, max_tokens=None, line="main"):
        ceiling = self.default_max_tokens if max_tokens is None else int(max_tokens)
        if ceiling <= 0:
            raise ValueError("max_tokens must be positive")
        body = dict(self.request_defaults)
        body.update({"model": self.t.model, "max_tokens": ceiling,
                     "messages": [{"role": "system", "content": self.system_prompt}] + messages})
        thinking = body.get("thinking")
        if not (isinstance(thinking, dict) and thinking.get("type") == "enabled"):
            body["temperature"] = temperature
        identity = self.identity(role, ticket, context_package_sha, body)
        lid = self.logical_id(identity)
        meta_p, req_p, resp_p = self._paths(lid)

        if os.path.exists(meta_p) and os.path.exists(resp_p):
            meta = read_json(meta_p)
            parsed = self._parse(read_json(resp_p), response_schema, role)
            return lid, parsed, True, meta["usage"]

        est_tokens, est_money = self._estimate(identity)
        self.ledger.reserve(lid, role, est_tokens, est_money, line=line)
        atomic_write_json(req_p, {"logical_id": lid, "utc": utc(), "identity": identity})

        try:
            status, raw_text = self._send_with_retries(body)
            try:
                response_obj = json.loads(raw_text)
            except json.JSONDecodeError:
                response_obj = {"_non_json_body": raw_text}
            atomic_write_json(resp_p, response_obj)
            if status != 200:
                raise ApiError(f"HTTP {status}: {json.dumps(response_obj)[:400]}")
            # Pass the original pricing contract shape for legacy readers; explicit profiles use
            # the normalized signed table directly.
            usage_prices = DEFAULT_PRICES if self.legacy_pricing else self.prices
            usage = extract_usage(response_obj, usage_prices)
        except BaseException:
            self.ledger.release(lid)
            raise

        parsed = self._parse(response_obj, response_schema, role)
        atomic_write_json(meta_p, {"logical_id": lid, "role": role, "ticket": ticket,
                                   "utc": utc(), "status": status, "usage": usage,
                                   "identity_sha256": sha256_obj(identity)})
        self.ledger.settle(lid, usage["total_tokens"], usage["billing_amount"], usage=usage)
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
