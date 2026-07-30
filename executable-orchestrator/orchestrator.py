#!/usr/bin/env python3
"""LAWMAX v2.1 orchestrator.

    --preflight   check the machine, the package and the evidence vault; change nothing
    --launch      run the experiment for real, over HTTP, against the configured endpoint
    --resume      continue an interrupted run from the signed event log

There is no --dry-run and no mock handler. The proof suite exercises THIS code path with
the endpoint pointed at a local server that speaks the real API shape, so what is proven
is the same code that runs against DeepSeek.

The escalation loop is the shape of the run: propose, build, measure, attack, and only
stop when a ceiling has been PROVEN. Stopping for budget or time is allowed, and it
produces BEST_DISCOVERED_SO_FAR — never COMMITTED.
"""
import argparse
import json
import os
import sys
import time

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from lawmax21 import decisions as dec  # noqa: E402
from lawmax21 import escalation, preflight  # noqa: E402
from lawmax21.budget import BudgetExhausted, BudgetLedger, StagnationDetected  # noqa: E402
from lawmax21.canonical import atomic_write_json, read_json, utc  # noqa: E402
from lawmax21.client import Client, HttpTransport  # noqa: E402
from lawmax21.eventlog import EventLog, LogTampered  # noqa: E402
from lawmax21.handlers import Context, build_handlers  # noqa: E402
from lawmax21.roles import MASTER_SYSTEM  # noqa: E402
from lawmax21.signing import generate_private, load_private, load_public  # noqa: E402
from lawmax21.states import NEXT, STATES, GuardFailed, Machine, OwnerApprovalRequired, replay  # noqa: E402

LOOP_BODY = ["CEILING_ANALYSIS", "SUCCESSOR_SEARCH", "RADICAL_CHALLENGER_SEARCH",
             "SIMPLIFICATION_CHALLENGE", "FRONTIER_REVIEW", "PRIVATE_REPLICATION",
             "ANTI_SATISFICING_AUDIT"]
PREFIX = STATES[1:STATES.index("PROVISIONAL_FRONTIER_MEMBER") + 1]
TAIL = ["HESA_CANDIDATE", "FINAL_HOLDOUT_EVALUATION", "ARCHITECTURE_EVIDENCE_SYNTHESIS",
        "TARGET_ARCHITECTURE_v1_REVIEWED", "MIGRATION_PLAN_FROZEN", "INDEPENDENT_AUDIT"]

EXIT_OK, EXIT_FAIL, EXIT_AWAITING_OWNER, EXIT_PREFLIGHT = 0, 1, 10, 2


def _paths(root, runtime):
    return {
        "runtime": runtime,
        "secrets": os.path.join(root, "private-evaluator", "owner-held-secrets"),
        "evaluator": os.path.join(root, "private-evaluator", "evaluator"),
        "bank": os.path.join(root, "private-evaluator", "encrypted-hidden-bank"),
        "suite": os.path.join(root, "benchmark", "visible-suite.json"),
        "owner_pub": os.path.join(root, "immutable-package", "OWNER-PUBLIC-KEY.hex"),
        "decisions": os.path.join(root, "OWNER-DECISIONS.signed.json"),
    }


def _owner_gate_instructions(e, root):
    signer = os.path.join(root, "executable-orchestrator", "tools", "owner_sign.py")
    return {
        "awaiting": e.gate_id,
        "run_id": e.run_id,
        "subject": e.subject_path,
        "subject_sha256": e.subject_sha256,
        "approval_expected_at": e.approval_path,
        "rejected_because": e.reason or "no approval present",
        "what_to_do": (
            "Review the subject artifact, then on YOUR machine (where the owner private key "
            "lives, never on the experiment machine) run:\n"
            f"  python3 {signer} --key <owner-private-key> --gate {e.gate_id} "
            f"--run-id {e.run_id} --subject {e.subject_path} --decision APPROVE "
            f"--out {e.approval_path}\n"
            "Then re-run the orchestrator with --resume."),
        "note": "The runner has no code path that can approve this on your behalf.",
    }


def build_context(root, runtime, run_id, mode, endpoint, model, key_env, backend,
                  canonical_repo, corpus_root, run_key_path):
    P = _paths(root, runtime)
    owner_pub = load_public(P["owner_pub"])
    D = dec.load(P["decisions"], owner_pub, run_id)

    run_key = load_private(run_key_path) if os.path.exists(run_key_path) else generate_private(run_key_path)
    log = EventLog(os.path.join(runtime, "state", "events.jsonl"), signer=run_key)

    limits = dict(D.budget)
    ledger = BudgetLedger(os.path.join(runtime, "budget", "ledger.json"), limits)
    transport = HttpTransport(endpoint, model, api_key_env=key_env)
    client = Client(transport, os.path.join(runtime, "raw-api"), ledger, log, MASTER_SYSTEM)

    ctx = Context(root, runtime, run_id, client, ledger, log, D, owner_pub,
                  P["evaluator"], P["bank"], os.path.join(P["secrets"], "HIDDEN.key"),
                  canonical_repo, P["suite"], backend, mode, corpus_root)
    machine = Machine(runtime, log, owner_pub, run_id, build_handlers(ctx))
    return ctx, machine, log, ledger, D


def run(root, runtime, run_id, mode, endpoint, model, key_env, backend, canonical_repo,
        corpus_root, max_rounds, crash_after=None, skip_preflight_vault=False):
    os.makedirs(runtime, exist_ok=True)
    P = _paths(root, runtime)

    pre = preflight.run(root, HERE, runtime, require_vault=not skip_preflight_vault,
                        owner_public=load_public(P["owner_pub"]))
    atomic_write_json(os.path.join(runtime, "reports", "preflight.json"), pre)

    ctx, machine, log, ledger, D = build_context(
        root, runtime, run_id, mode, endpoint, model, key_env, backend,
        canonical_repo, corpus_root, os.path.join(P["secrets"], f"RUN-{run_id}.key"))

    started = time.monotonic()
    deadline = started + D.budget["wall_clock_days"] * 86400
    done = 0
    try:
        _, done = machine.run_linear(PREFIX, crash_after=crash_after, done=done)

        # The escalation loop is cyclic, so resume must READ its position from the signed log,
        # never COUNT (audit: resume-round-drift bricked round-1 resume). The round number is
        # the number of CEILING_ANALYSIS transitions the log records — a durable, authoritative
        # fact. A crash that wrote a ceiling file but did not log its transition simply re-runs
        # that round and overwrites the same file, so there is no double-count.
        def rounds_started():
            return sum(1 for e in log.events()
                       if e["kind"] == "transition" and e["payload"].get("to") == "CEILING_ANALYSIS")

        while STATES.index(machine.state()) < STATES.index("HESA_CANDIDATE"):
            at = machine.state()
            rs = rounds_started()
            if at in ("PROVISIONAL_FRONTIER_MEMBER", "ANTI_SATISFICING_AUDIT"):
                if at == "ANTI_SATISFICING_AUDIT":
                    cont, why = ctx.esc.must_continue()
                    if rs >= 1 and not cont:
                        break                       # ceiling proven → exit to TAIL via HESA
                    if rs >= max_rounds:
                        ctx.esc.stop("round-ceiling")
                        break
                    if time.monotonic() > deadline:
                        ctx.esc.stop("wall-clock")
                        break
                ctx.round = rs + 1                   # about to run CEILING for the next round
            else:
                ctx.round = rs                       # mid-loop: in the round CEILING last opened
            for st in LOOP_BODY:
                cur = machine.state()
                if STATES.index(cur) >= STATES.index(st) and st not in NEXT.get(cur, []):
                    continue                          # already recorded in this cycle
                machine.advance(st)
                done += 1
                if crash_after is not None and done >= crash_after:
                    raise KeyboardInterrupt(f"SIMULATED CRASH after {done} transitions")
            if machine.state() == "ANTI_SATISFICING_AUDIT":
                try:
                    ctx.ledger.close_window(
                        f"round-{ctx.round}",
                        ctx.frontier.members[ctx.frontier.head_to_head()[0]]["dimension_vector"]["legal_capability"]
                        if ctx.frontier.non_dominated() else 0.0,
                        D.thresholds["progress_min_delta"], D.thresholds["max_stagnant_windows"])
                except StagnationDetected as e:
                    ctx.esc.stop(f"stagnation: {e}")
                    break

        _, done = machine.run_linear(TAIL, crash_after=crash_after, done=done)

        # Resuming an already-finished run must be a clean no-op, never a crash: if the signed
        # log already records a terminal state there is nothing left to advance (audit: a resume
        # of a completed run re-advanced the terminal and raised an illegal self-transition).
        if machine.state() not in ("COMMITTED", "BEST_DISCOVERED_SO_FAR", "HALTED"):
            proof = ctx.esc.proof()
            terminal = proof["terminal_state"]
            machine.advance(terminal)

    except BudgetExhausted as e:
        ctx.esc.stop(f"budget: {e}")
        return _finish(machine, ctx, log, ledger, "BEST_DISCOVERED_SO_FAR", str(e))
    except OwnerApprovalRequired as e:
        info = _owner_gate_instructions(e, root)
        atomic_write_json(os.path.join(runtime, "gates", "AWAITING-OWNER.json"), info)
        print(json.dumps(info, ensure_ascii=False, indent=1))
        return EXIT_AWAITING_OWNER

    return _finish(machine, ctx, log, ledger, machine.state(), "")


def _finish(machine, ctx, log, ledger, terminal, note):
    ok, n, why = log.verify()
    summary = {"run_id": ctx.run_id, "final_state": machine.state(), "requested_terminal": terminal,
               "events": n, "log_verified": ok, "log_reason": why,
               "budget": ledger.snapshot(), "escalation": ctx.esc.proof(),
               "note": note, "utc": utc()}
    atomic_write_json(os.path.join(ctx.runtime, "reports", "run_summary.json"), summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return EXIT_OK if ok else EXIT_FAIL


def main(argv=None):
    ap = argparse.ArgumentParser(description="LAWMAX v2.1 experiment runner")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true")
    mode.add_argument("--launch", action="store_true")
    mode.add_argument("--resume", action="store_true")
    ap.add_argument("--runtime", default=os.environ.get("LAWMAX_RUNTIME", os.path.join(ROOT, "runtime")))
    ap.add_argument("--run-id", default=os.environ.get("LAWMAX_RUN_ID", "RUN-0001"))
    ap.add_argument("--endpoint", default=os.environ.get("DEEPSEEK_ENDPOINT",
                                                         "https://api.deepseek.com/chat/completions"))
    ap.add_argument("--model", default=os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"))
    ap.add_argument("--key-env", default="DEEPSEEK_API_KEY")
    ap.add_argument("--backend", choices=("subprocess", "container"), default="subprocess")
    ap.add_argument("--canonical-repo", default=os.environ.get("LAWMAX_REPO",
                                                               os.path.join(ROOT, "evidence-vault", "lawmax-current")))
    ap.add_argument("--corpus-root", default=None,
                    help="what the model must demonstrably read (default: the immutable package)")
    ap.add_argument("--max-rounds", type=int, default=4)
    ap.add_argument("--crash-after", type=int, default=None, help="crash-safety drill")
    ap.add_argument("--allow-incomplete-vault", action="store_true",
                    help="preflight only; recorded in the report and never allowed for a real launch")
    a = ap.parse_args(argv)

    corpus = a.corpus_root or os.path.join(ROOT, "immutable-package")

    if a.preflight:
        try:
            pub_path = _paths(ROOT, a.runtime)["owner_pub"]
            pub = load_public(pub_path) if os.path.exists(pub_path) else None
            if pub is None and not a.allow_incomplete_vault:
                print(f"preflight refused: no owner public key at {pub_path} — "
                      "run tools/owner_sign.py --init on the owner machine first")
                return EXIT_PREFLIGHT
            rep = preflight.run(ROOT, HERE, a.runtime, require_vault=not a.allow_incomplete_vault,
                                owner_public=pub)
        except preflight.PreflightFailed as e:
            print(str(e))
            return EXIT_PREFLIGHT
        print(json.dumps(rep, ensure_ascii=False, indent=1))
        return EXIT_OK

    if a.launch and a.allow_incomplete_vault:
        print("--allow-incomplete-vault is refused for --launch: DeepSeek would be asked to "
              "reason about material it was never given.")
        return EXIT_PREFLIGHT

    try:
        return run(ROOT, a.runtime, a.run_id, "LAUNCH", a.endpoint, a.model, a.key_env,
                   a.backend, a.canonical_repo, corpus, a.max_rounds, a.crash_after,
                   skip_preflight_vault=False)
    except preflight.PreflightFailed as e:
        print(str(e))
        return EXIT_PREFLIGHT
    except dec.DecisionsRejected as e:
        print(f"owner decisions rejected: {e}")
        return EXIT_PREFLIGHT
    except LogTampered as e:
        print(f"REFUSING TO RUN — {e}")
        return EXIT_FAIL


if __name__ == "__main__":
    sys.exit(main())
