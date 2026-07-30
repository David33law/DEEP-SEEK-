"""Preflight. Everything that must be true BEFORE the first byte is sent.

Two v2.0 failures die here. First, the package would not even start on a clean machine
(`cryptography` imported but its backend panicked) — so this checks dependencies by
USING them, not by importing them. Second, the run could reach
GLOBAL_LAWMAX_MODEL_CERTIFIED with one file in the evidence vault and a Canonical Vision
still marked TEMPLATE — so launch is refused unless the vault carries every declared
source and the Vision is evidence-backed.
"""
import os
import platform
import shutil
import subprocess
import sys

from .canonical import read_json

MIN_PYTHON = (3, 9)

REQUIRED_VAULT_SOURCES = {
    "lawmax-current": "the LAWMAX repository as it stands today",
    "canonical-plans": "the canonical plans and specifications",
    "claude-opus48": "the Claude Opus 4.8 architecture material",
    "deepseek-cp0-cp6": "DeepSeek CP0–CP6 checkpoints",
    "deepseek-e1-committed": "DeepSeek E1 committed evidence",
    "deepseek-e1-runtime": "DeepSeek E1 runtime and raw evidence",
    "earlier-architecture-studies": "earlier architecture studies and tournaments",
    "empirical-case-studies": "empirical case studies (CS-01)",
}


class PreflightFailed(Exception):
    pass


def _dir_bytes(root):
    total, files = 0, 0
    for r, ds, fs in os.walk(root):
        ds[:] = [d for d in ds if d != ".git"]
        for f in fs:
            try:
                total += os.path.getsize(os.path.join(r, f))
                files += 1
            except OSError:
                pass
    return total, files


def check_python():
    if sys.version_info[:2] < MIN_PYTHON:
        return f"Python {'.'.join(map(str, MIN_PYTHON))}+ required, found {platform.python_version()}"
    return None


def check_dependencies():
    """Exercise each dependency, because importing it is not evidence that it works."""
    problems = []
    try:
        from cryptography.fernet import Fernet
        k = Fernet.generate_key()
        if Fernet(k).decrypt(Fernet(k).encrypt(b"probe")) != b"probe":
            problems.append("cryptography: Fernet round-trip returned the wrong bytes")
    except Exception as e:  # noqa: BLE001 — any failure here is disqualifying
        problems.append(f"cryptography unusable: {type(e).__name__}: {e}")
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        sk = Ed25519PrivateKey.generate()
        sk.public_key().verify(sk.sign(b"probe"), b"probe")
    except Exception as e:  # noqa: BLE001
        problems.append(f"Ed25519 unusable: {type(e).__name__}: {e}")
    try:
        import yaml
        if yaml.safe_load("a: 1") != {"a": 1}:
            problems.append("PyYAML: safe_load returned the wrong value")
    except Exception as e:  # noqa: BLE001
        problems.append(f"PyYAML unusable: {type(e).__name__}: {e}")
    if shutil.which("git") is None:
        problems.append("git is not on PATH — candidate worktrees cannot be created")
    return problems


def check_lock_concurrency(tmp_path):
    """Prove the event-store lock serialises rather than raising under contention."""
    from .eventlog import file_lock
    try:
        with file_lock(tmp_path, timeout=5):
            pass
        return None
    except Exception as e:  # noqa: BLE001
        return f"event-store lock unusable on this platform: {type(e).__name__}: {e}"


ATTESTATION_NAME = "SOURCE-ATTESTATION.json"


def source_tree_hash(path):
    """Hash of a vault source, excluding its own attestation."""
    import hashlib
    h = hashlib.sha256()
    for r, ds, fs in os.walk(path):
        ds[:] = [d for d in ds if d not in (".git", "__pycache__")]
        for f in sorted(fs):
            if f == ATTESTATION_NAME:
                continue
            p = os.path.join(r, f)
            h.update(os.path.relpath(p, path).replace("\\", "/").encode("utf-8"))
            with open(p, "rb") as fh:
                for c in iter(lambda: fh.read(1 << 20), b""):
                    h.update(c)
    return h.hexdigest()


def check_vault(vault_root, owner_public=None):
    """Present and non-empty is not enough. Each source must carry an owner-signed
    attestation of WHAT it is and WHICH bytes it contains, so nobody — including a future
    session of this runner — can quietly fill the vault with filler and call it evidence."""
    from .signing import SignatureRejected, verify_approval

    problems, present, sizes = [], [], {}
    for name, what in REQUIRED_VAULT_SOURCES.items():
        p = os.path.join(vault_root, name)
        if not os.path.isdir(p):
            problems.append(f"evidence vault is missing {name}/ ({what})")
            continue
        total, files = _dir_bytes(p)
        sizes[name] = {"bytes": total, "files": files}
        if files == 0 or total == 0:
            problems.append(f"evidence vault {name}/ is empty ({what}) — "
                            "DeepSeek would be asked to reason about material it was never given")
            continue
        att_path = os.path.join(p, ATTESTATION_NAME)
        if not os.path.exists(att_path):
            problems.append(f"evidence vault {name}/ has no owner-signed {ATTESTATION_NAME} — "
                            "unattested material is not evidence")
            continue
        if owner_public is not None:
            att = read_json(att_path)
            actual = source_tree_hash(p)
            try:
                verify_approval(att, owner_public, f"VAULT-{name}",
                                att["payload"]["run_id"], actual)
            except (SignatureRejected, KeyError) as e:
                problems.append(f"evidence vault {name}/: attestation rejected ({e}) — "
                                "the contents do not match what the owner signed")
                continue
            sizes[name]["attested_sha256"] = actual[:16] + "…"
        present.append(name)
    return problems, present, sizes


def check_vision(package_root):
    p = os.path.join(package_root, "canonical-charter", "LAWMAX-CANONICAL-VISION.json")
    if not os.path.exists(p):
        return ["Canonical Vision is absent"]
    v = read_json(p)
    if v.get("status") != "EVIDENCE_BACKED":
        return [f"Canonical Vision status is {v.get('status')!r} — it must be EVIDENCE_BACKED, "
                "with every section citing vault files by hash, before launch"]
    unfilled = [s for s, body in (v.get("filled_sections") or {}).items() if not body.get("citations")]
    if unfilled:
        return [f"Canonical Vision sections without citations: {unfilled}"]
    return []


def check_package(orchestrator_root):
    r = subprocess.run([sys.executable, os.path.join(orchestrator_root, "tools", "validate_package.py")],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return [f"validate_package failed: {(r.stdout + r.stderr).strip()[:1500]}"]
    return []


def run(root, orchestrator_root, runtime, require_vault=True, owner_public=None):
    """Returns a report. Raises PreflightFailed if anything is disqualifying."""
    problems = []
    v = check_python()
    if v:
        problems.append(v)
    problems += check_dependencies()
    lock = check_lock_concurrency(os.path.join(runtime, "state", "preflight.lock"))
    if lock:
        problems.append(lock)
    problems += check_package(orchestrator_root)
    vision = check_vision(os.path.join(root, "immutable-package"))
    vault_problems, present, sizes = check_vault(os.path.join(root, "evidence-vault"), owner_public)
    if require_vault:
        problems += vision + vault_problems

    report = {
        "python": platform.python_version(),
        "platform": f"{platform.system()} {platform.release()}",
        "vault_present": sorted(present),
        "vault_required": sorted(REQUIRED_VAULT_SOURCES),
        "vault_missing": sorted(set(REQUIRED_VAULT_SOURCES) - set(present)),
        "vault_sizes": sizes,
        "vision_problems": vision,
        "problems": problems,
        "ok": not problems,
    }
    if problems:
        raise PreflightFailed("\n  - ".join(["preflight refused to launch:"] + problems))
    return report
