"""Child-side bootstrap. Runs the candidate. Holds NO ground truth, by construction.

What this process is given:
  * its own source code, over stdin (never a path to the bank, never a key)
  * one label-free {case, draft} per request, over stdin
Nothing else. argv carries no secrets, the environment is scrubbed, the working
directory is an empty scratch dir, and RLIMIT_FSIZE=0 makes the kernel itself refuse
every write. A CPython audit hook — which cannot be uninstalled once installed — then
denies the capabilities by which bytes could be read from, or sent to, anywhere.

The defence is ACTION-based, not import-based. Classic sandbox escapes that reach the
`os` module through object graphs still cannot open a file: `os.open` raises the same
audit event as `builtins.open`. Reads are permitted only for the interpreter's own
standard library, and only read-only, so lazy stdlib imports keep working while the
hidden bank stays unreachable no matter how it is addressed.

ISOLATION MODEL — read this honestly. The audit hook is a Python-level guard, and
Python is a reflective language: the hook is (necessarily) an object on the heap, and
reassigning a function's __code__ fires no audit event. So a candidate that can REACH
the hook object could neuter it in place. This bootstrap closes the known route — the
heap-enumeration primitives (gc.get_objects / get_referrers / get_referents and the
inspect / tracemalloc enumerators) are denied AND severed, so the hook closure has no
Python-level referrer and cannot be located — which defeats every demonstrated escape.
But an in-process guard in a reflective runtime is DEFENCE-IN-DEPTH, not a proof of
containment. The STRUCTURAL isolation guarantee is the container backend
(`CandidateHost(backend="container")`: --network=none --read-only --cap-drop=ALL
--no-new-privileges), where the escape's payload — network egress, filesystem writes,
subprocess execution — is impossible at the kernel level even if the in-process hook
were defeated. A real launch that runs an UNTRUSTED (e.g. externally-generated)
candidate MUST use the container backend; the subprocess backend is for trusted or
development use, hardened but best-effort.
"""
import builtins
import json
import os
import sys
import sysconfig

DENIED_IMPORTS = {
    "subprocess", "socket", "ctypes", "shutil", "tempfile", "pathlib", "multiprocessing",
    "asyncio", "urllib", "http", "ftplib", "smtplib", "telnetlib", "sqlite3", "ssl",
    "pickle", "shelve", "dbm", "runpy", "site", "pty", "mmap", "fcntl", "select",
    "resource", "signal", "getpass", "pwd", "grp", "webbrowser", "importlib",
    "cryptography", "nacl", "Crypto", "requests", "httpx",
    # Object-graph introspection (audit v2.3 round 3, CRITICAL): the audit hook is an ordinary
    # closure, and setting a function's __code__ fires NO audit event — so a candidate that can
    # REACH the hook object can neuter it in place, then import socket / read files / spawn a
    # subprocess. The only Python-level way to reach that closure is whole-heap enumeration, so
    # the enumeration modules are denied AND gc's enumeration primitives are severed below.
    "gc", "inspect", "tracemalloc",
}

DENIED_EVENTS = {
    "os.listdir", "os.scandir", "os.walk", "os.mkdir", "os.rmdir", "os.remove",
    "os.rename", "os.chmod", "os.chown", "os.link", "os.symlink", "os.truncate",
    "os.system", "os.exec", "os.spawn", "os.fork", "os.forkpty", "os.posix_spawn",
    "os.putenv", "os.unsetenv", "os.startfile", "os.add_dll_directory", "os.chdir",
    "subprocess.Popen", "shutil.copyfile", "shutil.move", "shutil.rmtree",
    "urllib.Request", "ftplib.connect", "smtplib.connect", "sqlite3.connect",
    "cpython.run_file", "pty.spawn", "mmap.__new__", "resource.setrlimit",
    "os.getxattr", "os.setxattr", "os.listxattr", "os.removexattr",
}

WRITE_FLAGS = 0
for _n in ("O_WRONLY", "O_RDWR", "O_CREAT", "O_APPEND", "O_TRUNC", "O_EXCL"):
    WRITE_FLAGS |= getattr(os, _n, 0)

PREIMPORT = (
    "json", "math", "re", "itertools", "functools", "collections", "collections.abc",
    "dataclasses", "typing", "decimal", "fractions", "statistics", "string", "enum",
    "abc", "copy", "heapq", "bisect", "operator", "textwrap", "unicodedata", "difflib",
    "hashlib", "datetime", "random", "types", "numbers", "contextlib", "warnings",
    "traceback", "codecs", "encodings.utf_8", "struct", "binascii", "copyreg", "time",
)


class SandboxViolation(Exception):
    """A candidate reached for a capability it must not have. Fatal, never logged-and-continued."""


def _make_severed(name, msg):
    """A stand-in for a heap-enumeration primitive that raises instead of handing out object
    references (audit v2.3 round 3): with these severed, the audit-hook closure is unreachable."""
    def _severed(*_a, **_k):
        raise RuntimeError(f"{name}: {msg}")
    return _severed


def _stdlib_prefixes():
    out = set()
    for k in ("stdlib", "platstdlib", "purelib", "platlib"):
        p = sysconfig.get_paths().get(k)
        if p:
            out.add(os.path.realpath(p))
    out.add(os.path.realpath(os.path.dirname(os.__file__)))
    return tuple(sorted(out))


def _harden_posix():
    """Kernel-level limits, applied before any candidate byte is executed."""
    try:
        import resource
    except ImportError:
        return ["resource module unavailable (non-POSIX): audit hook + process isolation only"]
    notes = []
    for name, limit, label in (
        ("RLIMIT_FSIZE", (0, 0), "kernel refuses every file write, at every path"),
        ("RLIMIT_NPROC", (0, 0), "no new processes"),
        ("RLIMIT_CPU", (60, 60), "cpu seconds"),
        ("RLIMIT_AS", (2 * 1024 * 1024 * 1024, 2 * 1024 * 1024 * 1024), "address space"),
    ):
        r = getattr(resource, name, None)
        if r is None:
            continue
        try:
            resource.setrlimit(r, limit)
            notes.append(f"{name}={limit[0]} ({label})")
        except (ValueError, OSError) as e:
            notes.append(f"{name} NOT APPLIED ({e})")
    return notes


def _install_audit_hook(stdlib_prefixes):
    # Close over FROZEN copies of the policy (audit v2.3 round 4, HIGH): the hook must NOT read the
    # module globals DENIED_IMPORTS / DENIED_EVENTS / WRITE_FLAGS at call time. A candidate can walk
    # the call stack (sys._getframe, or a frame off an exception traceback — unpreventable in a
    # reflective runtime) to the bootstrap module frame and clear those globals; if the hook read
    # them live, that would neuter it without ever touching the closure. Reading immutable locals
    # instead makes the globals-mutation escape inert: clearing them changes nothing the hook sees.
    denied_imports = frozenset(DENIED_IMPORTS)
    denied_events = frozenset(DENIED_EVENTS)
    write_flags = int(WRITE_FLAGS)
    prefixes = tuple(stdlib_prefixes)

    def hook(event, args):
        if event == "import":
            name = (args[0] or "") if args else ""
            root = name.split(".")[0]
            if root in denied_imports:
                raise SandboxViolation(f"candidate attempted to import {name!r}")
            return
        if event == "open":
            path, mode, flags = (list(args) + [None, None, 0])[:3]
            if isinstance(flags, int) and (flags & write_flags):
                raise SandboxViolation("candidate attempted to open a file for writing")
            if mode and any(c in str(mode) for c in "wxa+"):
                raise SandboxViolation("candidate attempted to open a file for writing")
            try:
                real = os.path.realpath(os.fspath(path))
            except (TypeError, ValueError):
                raise SandboxViolation("candidate attempted to open a non-path object")
            if not real.startswith(prefixes):
                raise SandboxViolation(f"candidate attempted to read {real!r} (outside the standard library)")
            return
        if event in denied_events or event.startswith(("socket.", "ctypes.", "subprocess.", "ssl.")):
            raise SandboxViolation(f"candidate attempted {event}")

    sys.addaudithook(hook)  # irreversible for the lifetime of this process


def main():
    stdin, stdout = sys.stdin, sys.stdout
    header = json.loads(stdin.readline())
    source = header["candidate_source"]

    limits = _harden_posix()
    prefixes = _stdlib_prefixes()
    for m in PREIMPORT:
        try:
            __import__(m)
        except ImportError:
            pass
    # Sever the heap-enumeration primitives on the already-loaded gc module (audit v2.3 round 3,
    # CRITICAL). Denying `import gc` alone is not enough — gc is loaded at interpreter start, so a
    # candidate could reach it via sys.modules without an import event. With get_objects /
    # get_referrers / get_referents severed, the audit-hook closure (the only thing standing
    # between the candidate and the network/filesystem) cannot be located, so its __code__ cannot
    # be swapped out. gc.collect and friends remain, so legitimate stdlib is unaffected.
    _severed = "disabled in sandbox"
    for _modname in ("gc", "inspect", "tracemalloc"):
        _mod = sys.modules.get(_modname)
        if _mod is None:
            continue
        for _fn in ("get_objects", "get_referrers", "get_referents", "getclosurevars",
                    "getmembers", "stack", "_getframe", "currentframe", "snapshot"):
            if hasattr(_mod, _fn):
                try:
                    setattr(_mod, _fn, _make_severed(_fn, _severed))
                except (AttributeError, TypeError):
                    pass
    stdout.write(json.dumps({"ready": True, "limits": limits, "read_scope": list(prefixes)}) + "\n")
    stdout.flush()

    _install_audit_hook(prefixes)

    ns = {"__name__": "candidate", "__builtins__": builtins}
    try:
        exec(compile(source, "<candidate>", "exec"), ns)
        detect = ns.get("detect")
        if not callable(detect):
            raise RuntimeError("candidate does not define a callable detect(case, draft)")
    except BaseException as e:
        stdout.write(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}", "phase": "load"}) + "\n")
        stdout.flush()
        return 1

    # The contract is `detect`, plus OPTIONAL higher-layer capabilities. A candidate that
    # defines them can be measured on layers 5, 9, 12; one that does not simply returns null
    # for those ops and is honestly uncredited on those layers.
    # training_proposal is intentionally ABSENT here: it is an institution method, dispatched only
    # via institution_session / _call_institution (audit v2.3 round 3 — it had two dispatch seats).
    OPTIONAL = {"counterfactual", "known_gaps", "identity", "capabilities", "ingest_proposal"}

    # Institution methods (layers L1,L2,L7,L8,L10 + consciousness dims 1,2,8,9). These require
    # STATE across operations — a ledger you record into and later reconstruct from cannot be
    # exercised one-shot. So they run inside a single-process SESSION (below), where module
    # globals persist across the steps of ONE script but are discarded when the process exits.
    # Isolation is unchanged: same audit hook, same RLIMIT_FSIZE=0, no network, no filesystem —
    # the institution's state lives only in this process's memory and nowhere else.
    INSTITUTION = {"ledger_record", "ledger_reconstruct", "ledger_root", "bitemporal_query",
                   "simulate_forward", "governed_intake", "constitutional_compile",
                   "self_model", "capability_registry", "training_proposal"}

    def _call_institution(method, a):
        fn = ns.get(method)
        if not callable(fn):
            return None
        if method == "ledger_record":        return fn(a["act"])
        if method == "ledger_reconstruct":   return fn(a["act_id"])
        if method == "ledger_root":          return fn()
        if method == "bitemporal_query":     return fn(a["fact"], a["law_time"], a["knowledge_time"])
        if method == "simulate_forward":     return fn(a["matter"])
        if method == "governed_intake":      return fn(a["pack"])
        if method == "constitutional_compile": return fn(a["request"])
        if method == "self_model":           return fn()
        if method == "capability_registry":  return fn()
        if method == "training_proposal":    return fn(a["gap"])
        return None

    def dispatch(op, req):
        if op == "detect":
            return detect(req["case"], req["draft"])
        if op == "institution_session":
            # Run a scripted sequence against ONE institution instance, in THIS process, so
            # the ledger (and any other institution state) is real across the steps. A method
            # the candidate does not implement yields {"r": null}; a step that raises is
            # captured, never crashing the whole session — an honest partial institution is
            # measured on what it actually does.
            out = []
            for step in req.get("script", []):
                m = step.get("m")
                if m not in INSTITUTION:
                    out.append({"m": m, "error": "unknown institution method"})
                    continue
                try:
                    out.append({"m": m, "r": _call_institution(m, step.get("a", {}))})
                except BaseException as e:  # noqa: BLE001 — a failed step is data, not a crash
                    out.append({"m": m, "error": f"{type(e).__name__}: {e}"})
            return out
        if op in OPTIONAL:
            fn = ns.get(op)
            if not callable(fn):
                return None
            if op == "counterfactual":
                return fn(req["case"], req["draft"], req["change"])
            if op == "known_gaps":
                return fn(req["case"])
            if op == "identity":
                return fn()
            if op == "capabilities":
                return fn()
            if op == "ingest_proposal":
                return fn(req["proposal"])
        return None

    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue
        op = req.get("op")
        if op == "quit":
            break
        try:
            result = dispatch(op, req)
            json.dumps(result)  # must be plain JSON — no exotic objects smuggled back
            stdout.write(json.dumps({"ok": True, "op": op, "result": result}) + "\n")
        except BaseException as e:
            stdout.write(json.dumps({"ok": False, "op": op,
                                     "error": f"{type(e).__name__}: {e}", "phase": op}) + "\n")
        stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
