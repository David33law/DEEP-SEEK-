#!/usr/bin/env python3
"""National Legal Observatory launcher over the shared LAWMAX v2.3 control plane.

This file does not implement a second state machine. It injects the Observatory profile-specific
paths/context/handlers/schema and calls executable-orchestrator/orchestrator.py's existing run loop.
"""
import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.join(ROOT, "executable-orchestrator")
sys.path.insert(0, ORCH)


def _load_base_orchestrator():
    p = os.path.join(ORCH, "orchestrator.py")
    spec = importlib.util.spec_from_file_location("lawmax_shared_orchestrator", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = _load_base_orchestrator()
from lawmax21 import decisions as dec  # noqa: E402
from lawmax21 import handlers as base_handlers  # noqa: E402
from lawmax21 import observatory_handlers, observatory_preflight, observatory_roles, profiles, roles  # noqa: E402
from lawmax21.observatory_escalation import install_state_semantics  # noqa: E402
from lawmax21.observatory_runtime import ObservatoryContext  # noqa: E402
from lawmax21.budget import BudgetLedger  # noqa: E402
from lawmax21.client import Client, HttpTransport  # noqa: E402
from lawmax21.eventlog import EventLog, LogTampered  # noqa: E402
from lawmax21.signing import generate_private, load_private, load_public  # noqa: E402
from lawmax21 import states as states_module  # noqa: E402

PROFILE = profiles.resolve("national-observatory")
_ORIGINAL_COMMITTED_SEMANTIC = install_state_semantics(states_module)

# Provider policy for the real Observatory experiment. The shared Client records these fields
# inside the logical request identity, so a crash/resume/cache replay can never silently reuse a
# response produced under a weaker reasoning policy.
OBSERVATORY_REQUEST_DEFAULTS = {
    "thinking": {"type": "enabled"},
    "reasoning_effort": "max",
}
OBSERVATORY_DEFAULT_MAX_TOKENS = 65536


def observatory_paths(root, runtime):
    return {
        "runtime": runtime,
        "secrets": os.path.join(root, "private-evaluator", "owner-held-secrets"),
        "evaluator": os.path.join(root, "private-evaluator", "evaluator"),
        "bank": os.path.join(root, "private-evaluator", "observatory-hidden-bank"),
        "suite": os.path.join(root, "benchmark", "observatory-visible-suite.json"),
        "owner_pub": os.path.join(root, "immutable-package", "OWNER-PUBLIC-KEY.hex"),
        "decisions": os.path.join(root, "OWNER-DECISIONS.signed.json"),
    }


def observatory_build_context(root, runtime, run_id, mode, endpoint, model, key_env, backend,
                              canonical_repo, corpus_root, run_key_path):
    P = observatory_paths(root, runtime)
    owner_pub = load_public(P["owner_pub"])
    D = dec.load(P["decisions"], owner_pub, run_id)
    run_key = load_private(run_key_path) if os.path.exists(run_key_path) else generate_private(run_key_path)
    log = EventLog(os.path.join(runtime, "state", "events.jsonl"), signer=run_key)
    ledger = BudgetLedger(os.path.join(runtime, "budget", "ledger.json"), dict(D.budget))
    transport = HttpTransport(endpoint, model, api_key_env=key_env)
    system_prompt = open(PROFILE.master_system_path(root), encoding="utf-8").read()
    client = Client(
        transport, os.path.join(runtime, "raw-api"), ledger, log, system_prompt,
        request_defaults=OBSERVATORY_REQUEST_DEFAULTS,
        default_max_tokens=OBSERVATORY_DEFAULT_MAX_TOKENS,
    )

    cp1 = os.environ.get("OBSERVATORY_CP1_EVIDENCE")
    prior = os.environ.get("OBSERVATORY_PRIOR_CP2")
    if not cp1 or not prior:
        raise observatory_preflight.PreflightFailed(
            "OBSERVATORY_CP1_EVIDENCE and OBSERVATORY_PRIOR_CP2 must be set before context construction")

    ctx = ObservatoryContext(
        root, runtime, run_id, client, ledger, log, D, owner_pub,
        P["evaluator"], P["bank"], os.path.join(P["secrets"], "OBSERVATORY-HIDDEN.key"),
        canonical_repo, P["suite"], backend, mode, corpus_root, PROFILE, cp1, prior)
    handlers = observatory_handlers.build_observatory_handlers(ctx, base_handlers.build_handlers(ctx))
    machine = states_module.Machine(runtime, log, owner_pub, run_id, handlers)
    machine.profile_id = PROFILE.id
    return ctx, machine, log, ledger, D


def install_overlay():
    # Shared run() resolves these names from its module globals at execution time.
    base._paths = observatory_paths
    base.build_context = observatory_build_context
    base.preflight.run = observatory_preflight.run
    # Whole-system Observatory proposals use architecture mechanism names; LAWMAX's historical
    # micro-mechanism object schema remains untouched in ordinary runs/processes.
    roles.PROPOSAL_SCHEMA = observatory_roles.PROPOSAL_SCHEMA


def main(argv=None):
    install_overlay()
    ap = argparse.ArgumentParser(description="National Legal Observatory Ω architecture tournament")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--resume", action="store_true")
    ap.add_argument("--runtime", default=os.environ.get("OBSERVATORY_RUNTIME",
                                                        os.path.join(ROOT, "runtime-observatory")))
    ap.add_argument("--run-id", default=os.environ.get("OBSERVATORY_RUN_ID", "OBS-RUN-0001"))
    ap.add_argument("--endpoint", default=os.environ.get("DEEPSEEK_ENDPOINT",
                                                         "https://api.deepseek.com/chat/completions"))
    ap.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-pro"))
    ap.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--backend", choices=("subprocess", "container"), default="container",
                    help="real untrusted-model runs should use container; subprocess is for proof/development")
    ap.add_argument("--canonical-repo", default=os.environ.get("OBSERVATORY_CANONICAL_REPO"))
    ap.add_argument("--cp1-evidence", default=os.environ.get("OBSERVATORY_CP1_EVIDENCE"))
    ap.add_argument("--prior-cp2", default=os.environ.get("OBSERVATORY_PRIOR_CP2"))
    ap.add_argument("--max-rounds", type=int, default=6)
    ap.add_argument("--crash-after", type=int, default=None)
    a = ap.parse_args(argv)

    if a.canonical_repo:
        os.environ["OBSERVATORY_CANONICAL_REPO"] = os.path.abspath(a.canonical_repo)
    if a.cp1_evidence:
        os.environ["OBSERVATORY_CP1_EVIDENCE"] = os.path.abspath(a.cp1_evidence)
    if a.prior_cp2:
        os.environ["OBSERVATORY_PRIOR_CP2"] = os.path.abspath(a.prior_cp2)

    P = observatory_paths(ROOT, a.runtime)
    if a.preflight:
        try:
            pub_path = P["owner_pub"]
            pub = load_public(pub_path) if os.path.exists(pub_path) else None
            report = observatory_preflight.run(ROOT, ORCH, a.runtime, require_vault=True,
                                               owner_public=pub)
        except observatory_preflight.PreflightFailed as exc:
            print(str(exc))
            return base.EXIT_PREFLIGHT
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return base.EXIT_OK

    missing = [name for name, value in (("--canonical-repo", a.canonical_repo),
                                        ("--cp1-evidence", a.cp1_evidence),
                                        ("--prior-cp2", a.prior_cp2)) if not value]
    if missing:
        print("launch refused: missing " + ", ".join(missing))
        return base.EXIT_PREFLIGHT

    try:
        # --resume and --launch both enter the same idempotent shared run loop; signed-log replay
        # determines which transitions are already complete.
        return base.run(
            ROOT, a.runtime, a.run_id, "LAUNCH", a.endpoint, a.model, a.key_env,
            a.backend, os.path.abspath(a.canonical_repo), PROFILE.master_system_path(ROOT),
            a.max_rounds, a.crash_after, skip_preflight_vault=False)
    except observatory_preflight.PreflightFailed as exc:
        print(str(exc)); return base.EXIT_PREFLIGHT
    except dec.DecisionsRejected as exc:
        print(f"owner decisions rejected: {exc}"); return base.EXIT_PREFLIGHT
    except LogTampered as exc:
        print(f"REFUSING TO RUN — {exc}"); return base.EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
