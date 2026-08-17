#!/usr/bin/env python3
"""National Legal Observatory launcher over the shared LAWMAX v2.3 control plane.

This file does not implement a second state machine. It injects profile paths, semantics,
provider policy, currency-explicit accounting and Observatory/supremacy/crown/novelty handlers into
the existing signed control loop.
"""
import argparse
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.join(ROOT, "executable-orchestrator")
sys.path.insert(0, ORCH)
OFFICIAL_DEEPSEEK_ENDPOINT = "https://api.deepseek.com/chat/completions"
PRODUCTION_MODEL = "deepseek-v4-pro"

REQUIRED_NOVELTY_METHODS = [
    "G91-assumption-inversion",
    "G92-morphological-gap-search",
    "G93-cross-domain-structural-transfer",
    "G94-surgical-genome-mutation",
    "G95-trusted-boundary-recut",
    "G96-ontology-and-taxonomy-challenge",
]


def _load_base_orchestrator():
    p = os.path.join(ORCH, "orchestrator.py")
    spec = importlib.util.spec_from_file_location("lawmax_shared_orchestrator", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = _load_base_orchestrator()
from lawmax21 import decisions as dec  # noqa: E402
from lawmax21 import handlers as base_handlers  # noqa: E402
from lawmax21 import (observatory_audit, observatory_blueprint_overlay, observatory_crown_overlay,
                      observatory_handlers, observatory_preflight, observatory_roles,
                      observatory_supremacy_overlay, profiles, roles)  # noqa: E402
from lawmax21.observatory_escalation import install_state_semantics  # noqa: E402
from lawmax21.observatory_runtime import ObservatoryContext  # noqa: E402
from lawmax21.budget import BudgetLedger  # noqa: E402
from lawmax21.client import Client, HttpTransport  # noqa: E402
from lawmax21.eventlog import EventLog, LogTampered  # noqa: E402
from lawmax21.signing import generate_private, load_private, load_public  # noqa: E402
from lawmax21.canonical import sha256_file  # noqa: E402
from lawmax21 import states as states_module  # noqa: E402

PROFILE = profiles.resolve("national-observatory")
_ORIGINAL_COMMITTED_SEMANTIC = install_state_semantics(states_module)

OBSERVATORY_REQUEST_DEFAULTS = {
    "thinking": {"type": "enabled"},
    "reasoning_effort": "max",
}
OBSERVATORY_DEFAULT_MAX_TOKENS = 384000
OBSERVATORY_HTTP_TIMEOUT_SECONDS = 1800
OBSERVATORY_TECHNICAL_RETRIES = 1
REQUIRED_PUBLICATION_CHANNELS = {"human", "api", "linked_data", "eli", "public_sector", "ai"}


def _is_local_endpoint(endpoint):
    e = (endpoint or "").lower()
    return (e.startswith("http://127.0.0.1:") or e.startswith("http://localhost:")
            or e.startswith("https://127.0.0.1:") or e.startswith("https://localhost:"))


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


def _validate_signed_provider_budget(D, model):
    b = D.budget
    if b.get("currency") != "USD" or "amount" not in b:
        raise observatory_preflight.PreflightFailed(
            "Observatory D01 must use a USD currency-explicit hard ceiling")
    schedule = b.get("price_schedule") or {}
    if schedule.get("model") != model:
        raise observatory_preflight.PreflightFailed(
            f"signed D01 price schedule is for {schedule.get('model')!r}, not {model!r}")
    if schedule.get("currency") != b.get("currency"):
        raise observatory_preflight.PreflightFailed(
            "signed D01 price schedule currency does not match budget currency")
    if schedule.get("require_cache_split") is not True:
        raise observatory_preflight.PreflightFailed(
            "Observatory V4 billing requires provider-reported cache-hit/cache-miss split")
    return schedule


def _validate_signed_mission(D, root):
    mission = D.d.get("D09_ROW0_TARGET")
    if not isinstance(mission, dict):
        raise observatory_preflight.PreflightFailed(
            "Observatory D09 must be the structured signed mission binding")
    required_true = (
        "all_twelve_layers_required",
        "no_silent_legally_material_loss",
        "supremacy_search_required",
        "no_first_answer_privilege",
        "public_supremacy_case_required",
        "durable_systems_arena_required",
        "active_novelty_saturation_required",
    )
    missing_flags = [k for k in required_true if mission.get(k) is not True]
    if missing_flags:
        raise observatory_preflight.PreflightFailed(
            "signed D09 does not bind the supremacy mission flags: " + ", ".join(missing_flags))
    if int(mission.get("novelty_dry_waves_required", 0)) != 3:
        raise observatory_preflight.PreflightFailed(
            "signed D09 must require exactly three consecutive active novelty dry waves")
    if list(mission.get("novelty_methods") or []) != REQUIRED_NOVELTY_METHODS:
        raise observatory_preflight.PreflightFailed(
            "signed D09 novelty-miner portfolio does not match the production protocol")
    if not REQUIRED_PUBLICATION_CHANNELS.issubset(set(mission.get("publication_channels") or [])):
        raise observatory_preflight.PreflightFailed(
            "signed D09 does not bind all required national publication channels")

    profile = os.path.join(root, "profiles", "national-observatory")
    expected = {
        "charter_sha256": sha256_file(os.path.join(profile, "OBJECTIVE-CHARTER.md")),
        "master_system_sha256": sha256_file(os.path.join(profile, "MASTER-SYSTEM-PROMPT.md")),
        "pareto_sha256": sha256_file(os.path.join(profile, "PARETO-DIMENSIONS.json")),
        "evaluator_contract_sha256": sha256_file(os.path.join(profile, "EVALUATOR-CONTRACT.md")),
        "supremacy_contract_sha256": sha256_file(os.path.join(profile, "SUPREMACY-CONTRACT.md")),
        "systems_contract_sha256": sha256_file(os.path.join(profile, "SYSTEMS-CONTRACT.md")),
        "novelty_search_contract_sha256": sha256_file(
            os.path.join(profile, "NOVELTY-SEARCH-CONTRACT.md")),
    }
    drift = [k for k, v in expected.items() if mission.get(k) != v]
    if drift:
        raise observatory_preflight.PreflightFailed(
            "signed D09 mission contract has drifted from current files: " + ", ".join(drift))
    return mission


def observatory_build_context(root, runtime, run_id, mode, endpoint, model, key_env, backend,
                              canonical_repo, corpus_root, run_key_path):
    P = observatory_paths(root, runtime)
    owner_pub = load_public(P["owner_pub"])
    D = dec.load(P["decisions"], owner_pub, run_id)
    schedule = _validate_signed_provider_budget(D, model)
    _validate_signed_mission(D, root)

    run_key = load_private(run_key_path) if os.path.exists(run_key_path) else generate_private(run_key_path)
    log = EventLog(os.path.join(runtime, "state", "events.jsonl"), signer=run_key)
    ledger = BudgetLedger(os.path.join(runtime, "budget", "ledger.json"), dict(D.budget))
    transport = HttpTransport(
        endpoint, model, api_key_env=key_env, timeout=OBSERVATORY_HTTP_TIMEOUT_SECONDS)
    system_prompt = open(PROFILE.master_system_path(root), encoding="utf-8").read()
    client = Client(
        transport, os.path.join(runtime, "raw-api"), ledger, log, system_prompt,
        prices=schedule,
        max_technical_retries=OBSERVATORY_TECHNICAL_RETRIES,
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
    handlers = observatory_blueprint_overlay.install(ctx, handlers)
    handlers = observatory_supremacy_overlay.install(ctx, handlers)
    handlers = observatory_crown_overlay.install(ctx, handlers)
    handlers = observatory_audit.install(ctx, handlers)
    machine = states_module.Machine(runtime, log, owner_pub, run_id, handlers)
    machine.profile_id = PROFILE.id
    return ctx, machine, log, ledger, D


def install_overlay():
    base._paths = observatory_paths
    base.build_context = observatory_build_context
    base.preflight.run = observatory_preflight.run
    roles.PROPOSAL_SCHEMA = observatory_roles.PROPOSAL_SCHEMA
    roles.BUILD_SCHEMA = observatory_roles.BUILD_SCHEMA
    roles.CEILING_SCHEMA = observatory_roles.CEILING_SCHEMA
    roles.SYNTHESIS_SCHEMA = observatory_roles.SYNTHESIS_SCHEMA
    roles.MIGRATION_SCHEMA = observatory_roles.MIGRATION_SCHEMA
    roles.AUDIT_SCHEMA = observatory_roles.AUDIT_SCHEMA


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
    ap.add_argument("--endpoint", default=os.environ.get("DEEPSEEK_ENDPOINT", OFFICIAL_DEEPSEEK_ENDPOINT))
    ap.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", PRODUCTION_MODEL))
    ap.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--backend", choices=("subprocess", "container"), default="container",
                    help="production requires container; subprocess is accepted only for localhost proof/development")
    ap.add_argument("--canonical-repo", default=os.environ.get("OBSERVATORY_CANONICAL_REPO"))
    ap.add_argument("--cp1-evidence", default=os.environ.get("OBSERVATORY_CP1_EVIDENCE"))
    ap.add_argument("--prior-cp2", default=os.environ.get("OBSERVATORY_PRIOR_CP2"))
    ap.add_argument("--max-rounds", type=int, default=64,
                    help="resource backstop only; reaching it yields BEST_DISCOVERED_SO_FAR, never supremacy")
    ap.add_argument("--crash-after", type=int, default=None)
    a = ap.parse_args(argv)

    local_endpoint = _is_local_endpoint(a.endpoint)
    if not local_endpoint:
        if a.endpoint.rstrip("/") != OFFICIAL_DEEPSEEK_ENDPOINT:
            print("production launch refused: endpoint must be the official DeepSeek ChatCompletions endpoint")
            return base.EXIT_PREFLIGHT
        if a.model != PRODUCTION_MODEL:
            print(f"production launch refused: model must be {PRODUCTION_MODEL}")
            return base.EXIT_PREFLIGHT
        if a.backend != "container":
            print("production launch refused: non-local Observatory runs require container isolation")
            return base.EXIT_PREFLIGHT

    os.environ["OBSERVATORY_BACKEND"] = a.backend
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
            if pub is None:
                raise observatory_preflight.PreflightFailed(
                    "owner public key missing; run setup_observatory.py before production preflight")
            D = dec.load(P["decisions"], pub, a.run_id)
            schedule = _validate_signed_provider_budget(D, a.model)
            mission = _validate_signed_mission(D, ROOT)
            report = observatory_preflight.run(
                ROOT, ORCH, a.runtime, require_vault=True, owner_public=pub, backend=a.backend)
            report["signed_provider_budget"] = {
                "currency": D.budget["currency"],
                "amount": D.budget["amount"],
                "model": schedule["model"],
                "price_schedule": schedule,
                "decisions_sha256": D.sha256(),
            }
            report["signed_mission"] = mission
        except (observatory_preflight.PreflightFailed, dec.DecisionsRejected) as exc:
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
    if not local_endpoint and not os.environ.get(a.key_env):
        print(f"production launch refused: {a.key_env} is not set")
        return base.EXIT_PREFLIGHT

    try:
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
