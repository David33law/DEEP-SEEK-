"""Parent-side driver for candidate execution. The candidate NEVER runs in this process.

Two backends:
  * "container" — docker/podman, `--network=none --read-only`, nothing mounted. Strongest.
  * "subprocess" — a scrubbed, isolated CPython child (see candidate_bootstrap.py).

The backend is chosen by configuration, not by availability. If the configuration
demands `container` and no container runtime answers, this module REFUSES to evaluate
rather than silently degrading — an evaluation whose isolation is weaker than declared
would be worse than no evaluation at all.
"""
import json
import os
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
BOOTSTRAP = os.path.join(HERE, "candidate_bootstrap.py")
DEFAULT_TIMEOUT_S = 60
# Hard ceiling on bytes a candidate may send back per op. Normal results are a few KB; this only
# stops a stdout flood from OOM-ing the trusted parent (audit v2.3 round 2). Enforced by streaming.
MAX_OUTPUT_BYTES = 8 * 1024 * 1024


class IsolationUnavailable(Exception):
    pass


class CandidateFailure(Exception):
    pass


def container_runtime():
    for exe in ("podman", "docker"):
        try:
            r = subprocess.run([exe, "info"], capture_output=True, timeout=20)
            if r.returncode == 0:
                return exe
        except (OSError, subprocess.TimeoutExpired):
            continue
    return None


class CandidateHost:
    """One short-lived, stateless child per case. No cross-case memory is possible,
    so a candidate cannot accumulate information across the hidden set."""

    def __init__(self, candidate_source, backend="subprocess", image="python:3.11-slim",
                 timeout=DEFAULT_TIMEOUT_S):
        self.source = candidate_source
        self.backend = backend
        self.image = image
        self.timeout = timeout
        self.runtime = None
        if backend == "container":
            self.runtime = container_runtime()
            if not self.runtime:
                raise IsolationUnavailable(
                    "configuration requires container isolation, but no podman/docker runtime "
                    "responded — refusing to evaluate under weaker isolation"
                )
        elif backend != "subprocess":
            raise IsolationUnavailable(f"unknown isolation backend {backend!r}")

    # ------------------------------------------------------------------ argv
    def _argv_and_cwd(self, scratch):
        if self.backend == "container":
            with open(BOOTSTRAP, "r", encoding="utf-8") as f:
                boot = f.read()
            argv = [
                self.runtime, "run", "--rm", "-i",
                "--network=none", "--read-only", "--tmpfs", "/tmp:size=64m",
                "--memory=1g", "--pids-limit=64", "--cap-drop=ALL",
                "--security-opt", "no-new-privileges",
                "-w", "/tmp", self.image, "python3", "-I", "-S", "-B", "-c", boot,
            ]
            return argv, None
        return [sys.executable, "-I", "-S", "-B", BOOTSTRAP], scratch

    @staticmethod
    def _scrubbed_env():
        """No API keys, no LAWMAX_* paths, no HOME to search. Only what CPython needs."""
        env = {"PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8", "LC_ALL": "C.UTF-8"}
        if os.name == "nt":
            for k in ("SYSTEMROOT", "PATHEXT", "COMSPEC"):
                if k in os.environ:
                    env[k] = os.environ[k]
            env["PATH"] = os.environ.get("PATH", "")
        else:
            env["PATH"] = "/usr/bin:/bin"
        return env

    # --------------------------------------------------------------- execute
    def _run_bounded(self, argv, body, cwd):
        """Execute the child with a HARD cap on how many bytes it may send back. `subprocess.run`
        buffers the child's stdout without limit, so a candidate that floods fd 1 (a write the
        audit hook and RLIMIT_FSIZE do not cover — neither guards an already-open pipe) can drive
        the TRUSTED parent to OOM at ~3x the flood (audit v2.3 round 2). Here a reader thread reads
        in chunks and, the instant the cap is crossed, KILLS the child and stops buffering; stderr
        is drained on its own thread (also capped) so it can never fill its pipe and deadlock the
        child. The candidate's isolation guarantee — it cannot send bytes anywhere unbounded — is
        thereby actually enforced, not merely asserted."""
        proc = subprocess.Popen(
            argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=cwd, env=self._scrubbed_env())
        out_state = {"buf": [], "total": 0, "over": False}
        err_state = {"buf": [], "total": 0}

        def read_out():
            while True:
                chunk = proc.stdout.read(65536)
                if not chunk:
                    break
                out_state["total"] += len(chunk)
                if out_state["total"] <= MAX_OUTPUT_BYTES:
                    out_state["buf"].append(chunk)
                else:
                    out_state["over"] = True
                    try:
                        proc.kill()
                    except OSError:
                        pass
                    try:                                   # keep draining so the child never blocks
                        while proc.stdout.read(65536):
                            pass
                    except OSError:
                        pass
                    break

        def read_err():
            while True:
                try:
                    chunk = proc.stderr.read(65536)
                except OSError:
                    break
                if not chunk:
                    break
                err_state["total"] += len(chunk)
                if err_state["total"] <= 65536:           # only the head is ever used, in a message
                    err_state["buf"].append(chunk)

        to = threading.Thread(target=read_out, daemon=True)
        te = threading.Thread(target=read_err, daemon=True)
        to.start()
        te.start()
        try:
            proc.stdin.write(body.encode("utf-8"))
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        try:
            proc.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            to.join(timeout=5)
            te.join(timeout=5)
            raise
        to.join(timeout=5)
        te.join(timeout=5)
        out = b"".join(out_state["buf"]).decode("utf-8", "replace")
        err = b"".join(err_state["buf"]).decode("utf-8", "replace")
        return out, err, out_state["over"]

    def op(self, op_name, payload):
        """Run ONE operation in a fresh isolated process, return its result (or None if the
        candidate does not implement that optional op). A fresh process per op keeps the
        candidate stateless — it cannot accumulate anything across the higher-layer probes."""
        scratch = tempfile.mkdtemp(prefix="cand-scratch-")
        argv, cwd = self._argv_and_cwd(scratch)
        req = {"op": op_name}
        req.update(payload)
        body = (
            json.dumps({"candidate_source": self.source}, ensure_ascii=False) + "\n"
            + json.dumps(req, ensure_ascii=False) + "\n"
            + json.dumps({"op": "quit"}) + "\n"
        )
        try:
            out, err, over = self._run_bounded(argv, body, cwd)
        except subprocess.TimeoutExpired:
            raise CandidateFailure("candidate exceeded its time budget")
        except OSError as e:
            raise IsolationUnavailable(f"could not start isolated candidate process: {e}")

        if over:
            raise CandidateFailure(
                f"candidate exceeded its output budget of {MAX_OUTPUT_BYTES} bytes (stdout flood)")

        result = None
        for ln in out.splitlines():
            if not ln.strip():
                continue
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if "ok" in obj:
                result = obj
        if result is None:
            raise CandidateFailure(f"candidate produced no result line (stderr: {err.strip()[:400]})")
        if not result["ok"]:
            raise CandidateFailure(f"{result.get('phase', '?')}: {result.get('error', 'unknown')}")
        return result.get("result")

    def detect(self, case, draft):
        """Send ONE label-free case. Return the candidate's flags, or raise."""
        flags = self.op("detect", {"case": case, "draft": draft})
        if not isinstance(flags, list):
            raise CandidateFailure("candidate returned a non-list result for detect")
        return flags

    def isolation_report(self):
        return {"backend": self.backend, "runtime": self.runtime, "image": self.image if self.backend == "container" else None,
                "timeout_s": self.timeout,
                "candidate_receives": ["own source code", "one label-free {case, draft} per process"],
                "candidate_never_receives": ["key path", "shard path", "expected outputs",
                                             "private manifest", "evaluator source", "process argv",
                                             "inherited environment", "network"]}
