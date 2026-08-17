"""Protocol-centralized National Legal Observatory launcher."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess

from . import decisions as dec
from . import handlers as base_handlers
from . import (observatory_audit, observatory_blueprint_overlay,
               observatory_crown_overlay, observatory_handlers,
               observatory_preflight, observatory_protocol,
               observatory_roles, observatory_supremacy_overlay,
               profiles, roles, states as states_module)
from .budget import BudgetLedger
from .client import Client, HttpTransport
from .eventlog import EventLog, LogTampered
from .observatory_escalation import install_state_semantics
from .observatory_runtime import ObservatoryContext
from .signing import generate_private, load_private, load_public

ORCH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(ORCH)
OFFICIAL_ENDPOINT = "https://api.deepseek.com/chat/completions"
PRODUCTION_MODEL = "deepseek-v4-pro"
PROFILE = profiles.resolve("national-observatory")
_ORIGINAL_COMMITTED_SEMANTIC = install_state_semantics(states_module)
REQUEST_DEFAULTS = {"thinking": {"type": "enabled"}, "reasoning_effort": "max"}
DEFAULT_MAX_TOKENS = 384000
HTTP_TIMEOUT_SECONDS = 1800
TECHNICAL_RETRIES = 1
PRODUCTION_MAX_ROUNDS = 0  # zero is the shared orchestrator's explicit unbounded policy


def _load_base_orchestrator():
    path = os.path.join(ORCH, "orchestrator.py")
    spec = importlib.util.spec_from_file_location("lawmax_shared_orchestrator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = _load_base_orchestrator()


def _is_local(endpoint):
    endpoint = (endpoint or "").lower()
    return any(endpoint.startswith(prefix) for prefix in (
        "http://127.0.0.1:", "http://localhost:",
        "https://127.0.0.1:", "https://localhost:"))


def _git(*args):
    result = subprocess.run(["git", "-C", ROOT, *args],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise observatory_preflight.PreflightFailed(
            f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def paths(root, runtime):
    return {"runtime": runtime,
            "secrets": os.path.join(root, "private-evaluator", "owner-held-secrets"),
            "evaluator": os.path.join(root, "private-evaluator", "evaluator"),
            "bank": os.path.join(root, "private-evaluator", "observatory-hidden-bank"),
            "suite": os.path.join(root, "benchmark", "observatory-visible-suite.json"),
            "owner_pub": os.path.join(root, "immutable-package", "OWNER-PUBLIC-KEY.hex"),
            "decisions": os.path.join(root, "OWNER-DECISIONS.signed.json")}


def validate_provider_budget(decisions, model):
    budget = decisions.budget
    if budget.get("currency") != "USD" or "amount" not in budget:
        raise observatory_preflight.PreflightFailed(
            "Observatory D01 must use a currency-explicit USD hard ceiling")
    schedule = budget.get("price_schedule") or {}
    if schedule.get("model") != model or schedule.get("currency") != "USD":
        raise observatory_preflight.PreflightFailed(
            "signed provider price schedule does not match production model/currency")
    if schedule.get("require_cache_split") is not True:
        raise observatory_preflight.PreflightFailed(
            "provider accounting must require cache hit/miss split")
    return schedule


def validate_mission(decisions):
    mission = decisions.d.get("D09_ROW0_TARGET")
    if not isinstance(mission, dict):
        raise observatory_preflight.PreflightFailed(
            "Observatory D09 must contain the structured signed mission")
    try:
        return observatory_protocol.validate_mission(ROOT, mission, _git)
    except RuntimeError as exc:
        raise observatory_preflight.PreflightFailed(str(exc)) from exc


def build_context(root, runtime, run_id, mode, endpoint, model, key_env, backend,
                  canonical_repo, corpus_root, run_key_path):
    p = paths(root, runtime)
    owner_public = load_public(p["owner_pub"])
    decisions = dec.load(p["decisions"], owner_public, run_id)
    schedule = validate_provider_budget(decisions, model)
    validate_mission(decisions)
    run_key = (load_private(run_key_path) if os.path.exists(run_key_path)
               else generate_private(run_key_path))
    log = EventLog(os.path.join(runtime, "state", "events.jsonl"), signer=run_key)
    ledger = BudgetLedger(os.path.join(runtime, "budget", "ledger.json"),
                          dict(decisions.budget))
    transport = HttpTransport(endpoint, model, api_key_env=key_env,
                              timeout=HTTP_TIMEOUT_SECONDS)
    system_prompt = open(PROFILE.master_system_path(root), encoding="utf-8").read()
    client = Client(transport, os.path.join(runtime, "raw-api"), ledger, log,
                    system_prompt, prices=schedule,
                    max_technical_retries=TECHNICAL_RETRIES,
                    request_defaults=REQUEST_DEFAULTS,
                    default_max_tokens=DEFAULT_MAX_TOKENS)
    cp1 = os.environ.get("OBSERVATORY_CP1_EVIDENCE")
    prior = os.environ.get("OBSERVATORY_PRIOR_CP2")
    if not cp1 or not prior:
        raise observatory_preflight.PreflightFailed(
            "OBSERVATORY_CP1_EVIDENCE and OBSERVATORY_PRIOR_CP2 are required")
    ctx = ObservatoryContext(
        root, runtime, run_id, client, ledger, log, decisions, owner_public,
        p["evaluator"], p["bank"],
        os.path.join(p["secrets"], "OBSERVATORY-HIDDEN.key"),
        canonical_repo, p["suite"], backend, mode, corpus_root, PROFILE, cp1, prior)
    handlers = observatory_handlers.build_observatory_handlers(
        ctx, base_handlers.build_handlers(ctx))
    handlers = observatory_blueprint_overlay.install(ctx, handlers)
    handlers = observatory_supremacy_overlay.install(ctx, handlers)
    handlers = observatory_crown_overlay.install(ctx, handlers)
    handlers = observatory_audit.install(ctx, handlers)
    machine = states_module.Machine(runtime, log, owner_public, run_id, handlers)
    machine.profile_id = PROFILE.id
    return ctx, machine, log, ledger, decisions


def install_overlay():
    base._paths = paths
    base.build_context = build_context
    base.preflight.run = observatory_preflight.run
    roles.PROPOSAL_SCHEMA = observatory_roles.PROPOSAL_SCHEMA
    roles.BUILD_SCHEMA = observatory_roles.BUILD_SCHEMA
    roles.CEILING_SCHEMA = observatory_roles.CEILING_SCHEMA
    roles.SYNTHESIS_SCHEMA = observatory_roles.SYNTHESIS_SCHEMA
    roles.MIGRATION_SCHEMA = observatory_roles.MIGRATION_SCHEMA
    roles.AUDIT_SCHEMA = observatory_roles.AUDIT_SCHEMA


def main(argv=None):
    install_overlay()
    parser = argparse.ArgumentParser(
        description="National Legal Observatory Ω architecture tournament")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--resume", action="store_true")
    parser.add_argument("--runtime", default=os.environ.get(
        "OBSERVATORY_RUNTIME", os.path.join(ROOT, "runtime-observatory")))
    parser.add_argument("--run-id", default=os.environ.get(
        "OBSERVATORY_RUN_ID", "OBS-RUN-0001"))
    parser.add_argument("--endpoint", default=os.environ.get(
        "DEEPSEEK_ENDPOINT", OFFICIAL_ENDPOINT))
    parser.add_argument("--model", default=os.environ.get(
        "DEEPSEEK_MODEL", PRODUCTION_MODEL))
    parser.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--backend", choices=("subprocess", "container"),
                        default="container")
    parser.add_argument("--canonical-repo", default=os.environ.get(
        "OBSERVATORY_CANONICAL_REPO"))
    parser.add_argument("--cp1-evidence", default=os.environ.get(
        "OBSERVATORY_CP1_EVIDENCE"))
    parser.add_argument("--prior-cp2", default=os.environ.get(
        "OBSERVATORY_PRIOR_CP2"))
    parser.add_argument(
        "--max-rounds", type=int, default=PRODUCTION_MAX_ROUNDS,
        help=("0 means unbounded and is mandatory for the real production provider; "
              "a positive value is available only to bounded local proof/rehearsal runs"))
    parser.add_argument("--crash-after", type=int, default=None)
    args = parser.parse_args(argv)

    if args.max_rounds < 0:
        print("launch refused: --max-rounds must be zero or a positive integer")
        return base.EXIT_PREFLIGHT

    local = _is_local(args.endpoint)
    if not local:
        if observatory_protocol.proof_mode():
            print("production launch refused: zero-cost proof workload is active")
            return base.EXIT_PREFLIGHT
        if args.endpoint.rstrip("/") != OFFICIAL_ENDPOINT:
            print("production launch refused: endpoint must be official DeepSeek ChatCompletions")
            return base.EXIT_PREFLIGHT
        if args.model != PRODUCTION_MODEL:
            print(f"production launch refused: model must be {PRODUCTION_MODEL}")
            return base.EXIT_PREFLIGHT
        if args.backend != "container":
            print("production launch refused: container isolation is mandatory")
            return base.EXIT_PREFLIGHT
        if args.max_rounds != PRODUCTION_MAX_ROUNDS:
            print(
                "production launch refused: a finite round cap can stop before design-space "
                "saturation; use --max-rounds 0")
            return base.EXIT_PREFLIGHT

    os.environ["OBSERVATORY_BACKEND"] = args.backend
    for env_name, value in (("OBSERVATORY_CANONICAL_REPO", args.canonical_repo),
                            ("OBSERVATORY_CP1_EVIDENCE", args.cp1_evidence),
                            ("OBSERVATORY_PRIOR_CP2", args.prior_cp2)):
        if value:
            os.environ[env_name] = os.path.abspath(value)
    p = paths(ROOT, args.runtime)

    if args.preflight:
        try:
            if not os.path.exists(p["owner_pub"]):
                raise observatory_preflight.PreflightFailed(
                    "owner public key missing; run setup_observatory.py")
            owner_public = load_public(p["owner_pub"])
            decisions = dec.load(p["decisions"], owner_public, args.run_id)
            schedule = validate_provider_budget(decisions, args.model)
            mission = validate_mission(decisions)
            report = observatory_preflight.run(
                ROOT, ORCH, args.runtime, require_vault=True,
                owner_public=owner_public, backend=args.backend)
            report["signed_provider_budget"] = {
                "currency": decisions.budget["currency"],
                "amount": decisions.budget["amount"], "model": schedule["model"],
                "price_schedule": schedule, "decisions_sha256": decisions.sha256()}
            report["signed_mission"] = mission
            report["protocol_version"] = observatory_protocol.PROTOCOL_VERSION
            report["proof_mode"] = observatory_protocol.proof_mode()
            report["round_policy"] = {
                "max_rounds": args.max_rounds,
                "unbounded": args.max_rounds == 0,
                "finite_cap_allowed_for_real_provider": False}
        except (observatory_preflight.PreflightFailed, dec.DecisionsRejected) as exc:
            print(str(exc)); return base.EXIT_PREFLIGHT
        print(json.dumps(report, ensure_ascii=False, indent=1)); return base.EXIT_OK

    missing = [name for name, value in (
        ("--canonical-repo", args.canonical_repo),
        ("--cp1-evidence", args.cp1_evidence),
        ("--prior-cp2", args.prior_cp2)) if not value]
    if missing:
        print("launch refused: missing " + ", ".join(missing))
        return base.EXIT_PREFLIGHT
    if not local and not os.environ.get(args.key_env):
        print(f"production launch refused: {args.key_env} is not set")
        return base.EXIT_PREFLIGHT
    try:
        return base.run(ROOT, args.runtime, args.run_id, "LAUNCH",
                        args.endpoint, args.model, args.key_env, args.backend,
                        os.path.abspath(args.canonical_repo),
                        PROFILE.master_system_path(ROOT), args.max_rounds,
                        args.crash_after, skip_preflight_vault=False)
    except observatory_preflight.PreflightFailed as exc:
        print(str(exc)); return base.EXIT_PREFLIGHT
    except dec.DecisionsRejected as exc:
        print(f"owner decisions rejected: {exc}"); return base.EXIT_PREFLIGHT
    except LogTampered as exc:
        print(f"REFUSING TO RUN — {exc}"); return base.EXIT_FAIL
