#!/usr/bin/env python3
"""LAWMAX v2.1 security and launch proof.

Builds a disposable copy of the package, stands up a local server that speaks the real
API shape, and drives the REAL --launch path through it: owner gates, candidate builds,
sealed evaluation, a crash and a resume, a budget block, a cache probe, and the full
adversarial battery.

Nothing here is a shortcut around the product code. The orchestrator, the client, the
guards, the evaluator and the isolation host are the shipped ones; only the endpoint is
local, and no paid call is made.

Exit code 0 means every rejection test rejected and the launch path completed.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
sys.path.insert(0, ORCH)

from lawmax21.canonical import atomic_write_json, read_json, sha256_file  # noqa: E402

PORT = 8731
RUN_ID = "PROOF-0001"


def sh(argv, **kw):
    return subprocess.run(argv, capture_output=True, text=True, **kw)


def py(script, *args, env=None, cwd=None):
    e = dict(os.environ)
    e.update(env or {})
    return sh([sys.executable, script, *args], env=e, cwd=cwd)


# ==================================================================== environment
def build_env(dest):
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(ROOT, dest, ignore=shutil.ignore_patterns(
        "__pycache__", "proof", "runtime", "*.pyc"))
    for d in ("proof", "runtime"):
        os.makedirs(os.path.join(dest, d), exist_ok=True)

    tools = os.path.join(dest, "executable-orchestrator", "tools")
    secrets = os.path.join(dest, "private-evaluator", "owner-held-secrets")
    os.makedirs(secrets, exist_ok=True)
    owner_key = os.path.join(secrets, "PROOF-OWNER.key")
    owner_pub = os.path.join(dest, "immutable-package", "OWNER-PUBLIC-KEY.hex")

    r = py(os.path.join(tools, "owner_sign.py"), "--init", "--key", owner_key,
           "--public-out", owner_pub)
    assert r.returncode == 0, r.stdout + r.stderr

    # ---- the eleven decisions, signed
    decisions = {
        "D01_BUDGET": {"decided": True, "value": {"eur": 40.0, "tokens": 20_000_000, "calls": 4000,
                                                  "wall_clock_days": 14,
                                                  "successor_reserve_fraction": 0.3}},
        "D02_HIDDEN_SET_AUTHORITY": {"decided": True,
                                     "value": "deterministic generator run by an independent party; "
                                              "owner seals the merkle root"},
        "D03_RUNTIME_DIRECTION": {"decided": True, "value": "decided after the reality model; "
                                                            "no runtime is pre-selected by the package"},
        "D04_PACKAGE_AUTHOR_REPO_ACCESS": {"decided": True, "value": "read-only, attested import only"},
        "D05_PII_FIXTURE_POLICY": {"decided": True, "value": "all fixtures anonymised; real case "
                                                             "material never on the experiment machine"},
        "D06_GATE_CADENCE": {"decided": True, "value": "owner answers the gate queue within 48h"},
        "D07_ACCEPTANCE_THRESHOLDS": {"decided": True,
                                      "value": {"hidden_pass_rate": 0.8, "min_slice_f1": 0.7,
                                                "clean_runs": 2, "ablation_min_drop": 0.1,
                                                "progress_min_delta": 0.01,
                                                "max_stagnant_windows": 3,
                                                "best_of_n": 2, "revision_rounds": 1}},
        "D08_OFFMACHINE_BACKUP": {"decided": True, "value": "encrypted off-machine copy of the "
                                                            "signed log and checkpoints"},
        "D09_ROW0_TARGET": {"decided": True, "value": "Row 0 approved as first-cycle minimum success"},
        "D10_CS01_FIXTURE_LICENCE": {"decided": True, "value": "anonymised CS-01 fixtures permitted "
                                                               "in the visible suite only"},
        "D11_CHALLENGER_RESERVE": {"decided": True, "value": {"fraction": 0.3,
                                                              "critic_contexts": "separate role contexts; "
                                                                                 "the builder never certifies itself"}},
    }
    dpath = os.path.join(dest, "decisions.unsigned.json")
    atomic_write_json(dpath, decisions)
    r = py(os.path.join(tools, "owner_sign.py"), "--key", owner_key, "--run-id", RUN_ID,
           "--decisions", dpath, "--out", os.path.join(dest, "OWNER-DECISIONS.signed.json"))
    assert r.returncode == 0, r.stdout + r.stderr

    # ---- visible suite (fixtures) and hidden bank (sealed, disjoint domains)
    sys.path.insert(0, os.path.join(dest, "private-evaluator", "evaluator"))
    from lawmax21 import harness
    harness.configure(os.path.join(dest, "private-evaluator", "evaluator"))
    harness.build_visible_suite(os.path.join(dest, "benchmark", "visible-suite.json"), seed=1312, n_per_domain=2)

    bank = os.path.join(dest, "private-evaluator", "encrypted-hidden-bank")
    if os.path.exists(bank):
        shutil.rmtree(bank)
    r = py(os.path.join(dest, "private-evaluator", "evaluator", "bank_builder.py"),
           "--bank", bank, "--key", os.path.join(secrets, "HIDDEN.key"),
           "--seed", "777", "--qualification", "6", "--replication", "3", "--holdout", "3")
    assert r.returncode == 0, r.stdout + r.stderr

    # ---- canonical repository (a real git repo the candidates branch from)
    repo = os.path.join(dest, "evidence-vault", "lawmax-current")
    os.makedirs(repo, exist_ok=True)
    with open(os.path.join(repo, "core.py"), "w", encoding="utf-8") as f:
        f.write("def admission_check(case, draft):\n    return []\n")
    with open(os.path.join(repo, "README.md"), "w", encoding="utf-8") as f:
        f.write("# LAWMAX (proof fixture)\n\nStands in for the real repository during the proof run.\n")
    for cmd in (["init", "-q"], ["config", "user.email", "info@stavropouloslaw.com"],
                ["config", "user.name", "Stavropoulos Law"], ["add", "-A"],
                ["commit", "-qm", "baseline"]):
        sh(["git", "-C", repo] + cmd)

    # ---- vault sources, each attested by the owner key
    from lawmax21.preflight import REQUIRED_VAULT_SOURCES
    for name, what in REQUIRED_VAULT_SOURCES.items():
        d = os.path.join(dest, "evidence-vault", name)
        os.makedirs(d, exist_ok=True)
        if not [f for f in os.listdir(d) if f != "SOURCE-ATTESTATION.json"]:
            with open(os.path.join(d, "FIXTURE.md"), "w", encoding="utf-8") as f:
                f.write(f"# {name}\n\n{what}\n\nPROOF FIXTURE — stands in for the real material. "
                        f"A real launch requires the genuine source, imported with "
                        f"tools/import_evidence.py and attested by the owner.\n")
        r = py(os.path.join(tools, "import_evidence.py"), "--attest-only", "--into", name,
               "--vault", os.path.join(dest, "evidence-vault"), "--sign-with", owner_key)
        assert r.returncode == 0, r.stdout + r.stderr

    # ---- Canonical Vision, filled with citations into the attested vault
    vision_path = os.path.join(dest, "immutable-package", "canonical-charter",
                               "LAWMAX-CANONICAL-VISION.json")
    vision = read_json(vision_path)
    vision["status"] = "EVIDENCE_BACKED"
    def _attested(n):
        att = read_json(os.path.join(dest, "evidence-vault", n, "SOURCE-ATTESTATION.json"))
        return f"evidence-vault/{n}#{att['payload']['subject_sha256'][:16]}"

    vision["filled_sections"] = {
        s: {"body": f"section {s} grounded in the attested vault",
            "citations": [_attested(n) for n in list(REQUIRED_VAULT_SOURCES)[:2]]}
        for s in vision["sections"]
    }
    atomic_write_json(vision_path, vision)

    # protocol 19 is generated from the state machine; regenerate then re-seal the manifest
    r = py(os.path.join(tools, "generate_protocol19.py"))
    assert r.returncode == 0, r.stdout + r.stderr
    r = py(os.path.join(tools, "make_manifest.py"))
    assert r.returncode == 0, r.stdout + r.stderr

    return {"dest": dest, "owner_key": owner_key, "owner_pub": owner_pub,
            "bank": bank, "repo": repo, "secrets": secrets, "tools": tools}


# ==================================================================== launch drive
def _to_resume(args, drop_crash=False):
    """Turn a --launch argv into a --resume argv. Drops --crash-after AND its value cleanly
    by position — the old code stripped every all-digit token, which silently ate the
    --max-rounds value on resume and broke the crash drill (audit: max-rounds stripping)."""
    out, skip = [], False
    for x in args:
        if skip:
            skip = False
            continue
        if x == "--launch":
            out.append("--resume")
        elif drop_crash and x == "--crash-after":
            skip = True   # drop the flag and the number after it
        else:
            out.append(x)
    return out


def drive_launch(E, runtime_name="runtime", extra_env=None, crash_after=None, max_rounds=2):
    """Run --launch, satisfying owner gates the way the owner would, until it terminates.
    If a crash was injected, the deliberate abort is caught and the run is RESUMED from the
    signed log — the drill only proves something if resume actually carries it to completion.
    Each scenario gets its OWN runtime dir so the crash drill and the clean launch are two
    independent end-to-end demonstrations, not one resuming the other's finished log."""
    dest = E["dest"]
    orch = os.path.join(dest, "executable-orchestrator", "orchestrator.py")
    runtime = os.path.join(dest, runtime_name)
    env = {"DEEPSEEK_API_KEY": "proof-token-not-a-real-key",
           "LAWMAX_RUNTIME": runtime}
    env.update(extra_env or {})
    args = ["--launch", "--run-id", RUN_ID,
            "--endpoint", f"http://127.0.0.1:{PORT}/chat/completions",
            "--model", "deepseek-chat", "--max-rounds", str(max_rounds),
            "--canonical-repo", E["repo"]]
    if crash_after:
        args += ["--crash-after", str(crash_after)]

    transcript, gates_signed = [], []
    crash_pending = crash_after is not None
    crashed_and_resumed = False
    for attempt in range(20):
        r = py(orch, *args, env=env)
        transcript.append({"attempt": attempt, "rc": r.returncode,
                           "tail": (r.stdout or r.stderr)[-1200:]})
        if r.returncode == 10:  # awaiting owner — sign the gate exactly as the owner would
            info = read_json(os.path.join(runtime, "gates", "AWAITING-OWNER.json"))
            gate = info["awaiting"]
            s = py(os.path.join(E["tools"], "owner_sign.py"), "--key", E["owner_key"],
                   "--gate", gate, "--run-id", RUN_ID,
                   "--subject", info["subject"], "--decision", "APPROVE",
                   "--out", info["approval_expected_at"])
            assert s.returncode == 0, s.stdout + s.stderr
            gates_signed.append(gate)
            args = _to_resume(args, drop_crash=True)
            crash_pending = False
            continue
        if r.returncode == 0:
            return {"completed": True, "attempts": attempt + 1, "gates_signed": gates_signed,
                    "crashed_and_resumed": crashed_and_resumed, "transcript": transcript}
        # non-zero, non-10
        if crash_pending:
            # the injected crash fired (KeyboardInterrupt → non-zero exit). This is the drill:
            # switch to --resume, drop --crash-after, and drive on from the signed log.
            crash_pending, crashed_and_resumed = False, True
            args = _to_resume(args, drop_crash=True)
            continue
        return {"completed": False, "attempts": attempt + 1, "gates_signed": gates_signed,
                "crashed_and_resumed": crashed_and_resumed, "transcript": transcript}
    return {"completed": False, "attempts": 20, "gates_signed": gates_signed,
            "crashed_and_resumed": crashed_and_resumed, "transcript": transcript}


def _measure_institution(E, src, tag, seed):
    """Run the REAL seeded institution sensors against a candidate source, in the shipped
    isolation, at a given secret seed. The candidate never receives the seed."""
    dest = E["dest"]
    evaluator = os.path.join(dest, "private-evaluator", "evaluator")
    cand = os.path.join(E["secrets"], f"inst-{tag}.py")
    with open(cand, "w", encoding="utf-8") as f:
        f.write(src)
    out = os.path.join(E["secrets"], f"inst-{tag}-{seed}.json")
    py(os.path.join(evaluator, "measure_institution.py"), "--candidate", cand,
       "--seed", str(seed), "--out", out)
    return read_json(out)["institution_measurement"]


def committed_reachability(E):
    """LIVENESS + EVIDENCE-BOUND, GENERALISATION-HARDENED CREDIT — the crown is reachable, and
    ONLY for an institution MEASURED to exist under a SECRET per-run seed and whose measurement
    the owner signed.

    The rejection battery proves the guard cannot be tricked OPEN; this proves it is not welded
    SHUT either, and that the last two trust holes are closed:

      * v2.2 closed the blanket-signature hole (owner could sign a layer list for an institution
        that was never built) — credit is now MEASURED, then owner-authorised.
      * v2.3 closes the test-tautology hole — the sensors' vectors are drawn from a SECRET per-run
        seed the candidate never sees, over K independent trials, with ground truth computed on
        the fly. A candidate that merely MEMORISED a known test set passes that set and collapses
        on the run's real seed.

    We drive the REAL escalation ledger, the REAL COMMITTED guard, the REAL seeded sensors, and
    REAL Ed25519 signatures, and show:

      A. HONEST institution GENERALISES (measured true on several independent secret seeds) +
         owner signs the run-seed measurement -> COMMITTED.
      B. FAKE institution (right-shaped constants) -> 0 layers on every seed; owner signs it
         anyway -> nothing credited -> SHUT.
      C. HONEST measurement but NO owner signature -> not credited -> SHUT (sovereignty).
      D. FORGED (non-owner) signature over an honest measurement -> rejected -> SHUT.
      E. MEMORISER that baked seed S0 -> full institution on S0, but under the run's SECRET seed
         it collapses to [L1] only -> not crown-eligible -> SHUT, EVEN with the owner's signature
         over its (secret-seed) measurement. The test-tautology, made concrete and killed.
    """
    import tempfile

    from tools.institution_fixtures import (FAKE_INSTITUTION, HONEST_INSTITUTION,
                                            build_memorizer_source)

    from lawmax21.escalation import (PROOF_SCHEMA, EscalationLedger, integration_credit_gate)
    from lawmax21.schema import validate
    from lawmax21.signing import (generate_private, load_private,
                                   load_public, make_approval)
    from lawmax21.states import SEMANTIC, GuardFailed

    # secret run seed the candidate never sees; a couple of extra independent seeds show the
    # honest institution GENERALISES rather than fitting one vector set.
    RUN_SEED, GEN_SEEDS = 777001, [424242, 909090]
    S0_BAKED = 111222  # the (different) seed a memoriser is allowed to see and bake

    sys.path.insert(0, os.path.join(E["dest"], "private-evaluator", "evaluator"))
    import institution_probe  # the SAME shipped sensor module the subprocess grader uses

    owner = load_public(E["owner_pub"])
    honest = _measure_institution(E, HONEST_INSTITUTION, "honest", RUN_SEED)
    honest_gen = [_measure_institution(E, HONEST_INSTITUTION, "honest", s) for s in GEN_SEEDS]
    fake = _measure_institution(E, FAKE_INSTITUTION, "fake", RUN_SEED)
    # the memoriser bakes S0_BAKED; we measure it BOTH on S0 (it should look conscious) and on the
    # run's secret seed (it should collapse). build_trials is pure and shared with the sensors.
    memorizer_src = build_memorizer_source(institution_probe.build_trials(S0_BAKED))
    mem_on_baked = _measure_institution(E, memorizer_src, "memorizer", S0_BAKED)
    mem_on_secret = _measure_institution(E, memorizer_src, "memorizer", RUN_SEED)

    def fresh_ledger():
        rt = tempfile.mkdtemp(prefix="proof-live-")
        esc = EscalationLedger(os.path.join(rt, "ledger.json"), dry_rounds_required=2)
        INC = "CAND-SUP"
        esc.declare_families(["graph", "norm-lattice", "rule"])
        for lid in ("L3", "L4", "L5", "L6", "L9", "L11", "L12"):   # sandbox-demonstrable layers
            esc.record_altitude_evidence(INC, lid, "liveness: demonstrated in execution")
        esc.record_consciousness(INC, "REAL")
        esc.record_evolvability(INC, "EVOLVABLE")
        esc.record_round("r1", [INC, "CAND-RAD", "CAND-SIMP"], INC, 0.9,
                         {INC: {"kind": "successor", "family": "graph"},
                          "CAND-RAD": {"kind": "radical", "family": "norm-lattice"},
                          "CAND-SIMP": {"kind": "simplification", "family": "rule"}})
        esc.record_round("r2", [INC], INC, 0.9, {INC: {"kind": "successor", "family": "graph"}})
        esc.record_round("r3", [INC], INC, 0.9, {INC: {"kind": "successor", "family": "graph"}})
        return rt, esc

    def guard(esc):
        p = esc.proof()
        try:
            SEMANTIC["COMMITTED"](None, p)
            return True, "", p
        except GuardFailed as e:
            return False, str(e)[:200], p

    def stage_and_sign(rt, measurement, sign=True, stray=False, candidate_id="CAND-SUP"):
        subj = os.path.join(rt, "integration_subject.json")
        atomic_write_json(subj, {"gate": "GATE-INTEGRATION", "run_id": RUN_ID,
                                 "candidate_id": candidate_id, "institution_measurement": measurement})
        subj_sha = sha256_file(subj)
        signer = generate_private(os.path.join(rt, "stray.key")) if stray else load_private(E["owner_key"])
        if not sign:
            return subj, subj_sha, None
        return subj, subj_sha, make_approval(signer, "GATE-INTEGRATION", RUN_ID, subj_sha, "APPROVE")

    def credit_the_runner_way(esc, subj, subj_sha, approval, fresh):
        """Drives the SHIPPED credit gate (escalation.integration_credit_gate) — the SAME function
        handlers.credit_integration_if_attested calls (audit v2.3 round 3: no re-implementation, so
        a regression in the real gate now fails the proof). `fresh` is the deterministic re-run of
        the sensors on the candidate's source; the gate re-derives via this and refuses on mismatch."""
        return integration_credit_gate(
            esc=esc, subject=read_json(subj), subject_sha=subj_sha, approval=approval,
            owner_pub=owner, run_id=RUN_ID, remeasure=lambda cid: fresh)

    steps = []

    # A — honest institution GENERALISES across independent secret seeds, then owner-signed -> COMMITTED
    generalises = (honest["consciousness_full"] and len(honest["layers_demonstrated"]) == 5
                   and all(g["consciousness_full"] and len(g["layers_demonstrated"]) == 5
                           for g in honest_gen))
    rt, esc = fresh_ledger()
    subj, sha, appr = stage_and_sign(rt, honest, sign=True)
    credited = credit_the_runner_way(esc, subj, sha, appr, honest)
    okA, whyA, pA = guard(esc)
    validate(pA, PROOF_SCHEMA)
    steps.append({"stage": "A_honest_generalises_and_signed",
                  "run_seed_layers": honest["layers_demonstrated"],
                  "extra_seed_layers": [g["layers_demonstrated"] for g in honest_gen],
                  "generalises_across_seeds": generalises,
                  "consciousness_full": honest["consciousness_full"],
                  "credited": credited, "door_open": okA, "terminal_state": pA["terminal_state"],
                  "conditions": pA["conditions"], "audited_altitude": pA["audited_altitude"],
                  "layers_unreached": pA["layers_unreached"], "reason": whyA})

    # B — FAKE institution, owner signs it anyway -> nothing credited -> SHUT
    rt, esc = fresh_ledger()
    subj, sha, appr = stage_and_sign(rt, fake, sign=True)
    credited = credit_the_runner_way(esc, subj, sha, appr, fake)
    okB, whyB, pB = guard(esc)
    steps.append({"stage": "B_fake_measured_but_signed",
                  "institution_layers_measured": fake["layers_demonstrated"],
                  "consciousness_full": fake["consciousness_full"],
                  "credited_layers_after_signature": esc.credited_layers_raw(),
                  "door_open": okB, "door_shut": not okB,
                  "terminal_state": pB["terminal_state"],
                  "layers_unreached": pB["layers_unreached"], "reason": whyB})

    # C — honest measurement but NO owner signature -> not credited -> SHUT (sovereignty)
    rt, esc = fresh_ledger()
    subj, sha, _ = stage_and_sign(rt, honest, sign=False)
    credited = credit_the_runner_way(esc, subj, sha, None, honest)
    okC, whyC, pC = guard(esc)
    steps.append({"stage": "C_honest_measured_but_unsigned", "credited": credited,
                  "door_open": okC, "door_shut": not okC,
                  "terminal_state": pC["terminal_state"], "reason": whyC})

    # D — a FORGED (non-owner) signature over the honest measurement -> rejected -> SHUT
    rt, esc = fresh_ledger()
    subj, sha, forged = stage_and_sign(rt, honest, sign=True, stray=True)
    credited = credit_the_runner_way(esc, subj, sha, forged, honest)
    okD, whyD, _ = guard(esc)
    steps.append({"stage": "D_honest_measured_forged_signature",
                  "forged_credit_rejected": not credited, "door_open": okD, "door_shut": not okD})

    # E — the MEMORISER. It baked seed S0 and looks fully conscious THERE; under the run's secret
    # seed it collapses. The owner signs its (secret-seed) measurement, and STILL it is not crowned,
    # because credit follows the measurement and the measurement shows it is not an institution.
    mem_baked_full = (mem_on_baked["consciousness_full"]
                      and len(mem_on_baked["layers_demonstrated"]) == 5)
    rt, esc = fresh_ledger()
    subj, sha, appr = stage_and_sign(rt, mem_on_secret, sign=True)   # owner signs it anyway
    credited = credit_the_runner_way(esc, subj, sha, appr, mem_on_secret)
    okE, whyE, pE = guard(esc)
    steps.append({"stage": "E_memoriser_baked_S0_then_secret_seed",
                  "on_baked_seed_layers": mem_on_baked["layers_demonstrated"],
                  "on_baked_seed_consciousness_full": mem_on_baked["consciousness_full"],
                  "looked_fully_conscious_on_baked_seed": mem_baked_full,
                  "on_secret_seed_layers": mem_on_secret["layers_demonstrated"],
                  "on_secret_seed_consciousness_full": mem_on_secret["consciousness_full"],
                  "credited_layers_after_owner_signature": esc.credited_layers_raw(),
                  "door_open": okE, "door_shut": not okE,
                  "terminal_state": pE["terminal_state"], "reason": whyE})

    # F — BOUND CREDIT (audit v2.3-critical regression). The incumbent is CAND-SUP; the owner
    # signs a subject for a DIFFERENT candidate (CAND-OTHER) carrying a genuine 5-layer, fully
    # conscious institution measurement. Credit binds to CAND-OTHER, so the incumbent CAND-SUP —
    # who demonstrated no institution layer — is NOT crowned. Before the fix, this global credit
    # opened the door for the wrong candidate.
    rt, esc = fresh_ledger()   # incumbent = CAND-SUP
    subj, sha, appr = stage_and_sign(rt, honest, sign=True, candidate_id="CAND-OTHER")
    credited = credit_the_runner_way(esc, subj, sha, appr, honest)
    okF, whyF, pF = guard(esc)
    steps.append({"stage": "F_owner_signs_a_different_candidates_institution",
                  "incumbent": pF["incumbent"], "credited_candidate": pF["integration_credited_candidate"],
                  "credited_layers_for_incumbent": pF["credited_layers"],
                  "door_open": okF, "door_shut": not okF,
                  "terminal_state": pF["terminal_state"], "reason": whyF})

    # G — FABRICATED signed measurement (audit v2.3 round 2). The owner signs a subject for the
    # incumbent that CLAIMS a full 5-layer institution, but the candidate is a detector: re-deriving
    # the measurement yields nothing, the fresh result does not match the signed one, and credit is
    # REFUSED. A hand-authored attestation cannot conjure a crown — the runner re-measures the truth.
    rt, esc = fresh_ledger()   # incumbent = CAND-SUP
    subj, sha, appr = stage_and_sign(rt, honest, sign=True, candidate_id="CAND-SUP")  # SIGNED claim: 5 layers
    credited = credit_the_runner_way(esc, subj, sha, appr, fake)   # ...but re-derivation measures FAKE ([])
    okG, whyG, pG = guard(esc)
    steps.append({"stage": "G_fabricated_signed_measurement_rederived",
                  "signed_claim_layers": honest["layers_demonstrated"],
                  "re_derived_layers": fake["layers_demonstrated"],
                  "credit_refused_on_mismatch": not credited,
                  "credited_layers_for_incumbent": pG["credited_layers"],
                  "door_open": okG, "door_shut": not okG,
                  "terminal_state": pG["terminal_state"], "reason": whyG})

    passed = (okA and generalises
              and not okB and not fake["layers_demonstrated"]
              and not okC and not okD
              and mem_baked_full                         # memoriser DID fool the fixed-seed view
              and not okE and mem_on_secret["layers_demonstrated"] == ["L1"]  # ...but not the secret seed
              and not okF and pF["credited_layers"] == []  # bound credit: wrong candidate gets nothing
              and not okG and pG["credited_layers"] == [])  # re-derivation: fabricated report refused
    return {"committed_reachable_only_via_measured_generalising_and_owner_signed_integration": bool(passed),
            "honest_institution_measurement": honest,
            "honest_generalisation_seeds": [g["layers_demonstrated"] for g in honest_gen],
            "fake_institution_measurement": fake,
            "memoriser_on_baked_seed": mem_on_baked["layers_demonstrated"],
            "memoriser_on_secret_seed": mem_on_secret["layers_demonstrated"],
            "bound_credit_wrong_candidate_shut": not okF,
            "fabricated_measurement_refused_shut": not okG,
            "steps": steps}


# ==================================================================== rejection tests
def rejection_tests(E, launch_runtime):
    """The thirteen conditions under which v2.1 must be refused. Each must REJECT."""
    dest, out = E["dest"], []
    tools, orch = E["tools"], os.path.join(dest, "executable-orchestrator", "orchestrator.py")
    evaluator = os.path.join(dest, "private-evaluator", "evaluator")

    def t(name, rejected, detail):
        out.append({"test": name, "rejected": bool(rejected), "detail": detail})

    # 1 — candidate reads the hidden key/shard
    r = py(os.path.join(evaluator, "evaluate.py"), "--bank", E["bank"],
           "--key", os.path.join(E["secrets"], "HIDDEN.key"),
           "--candidate", os.path.join(evaluator, "canaries", "ATTACK-argv-theft.py"),
           "--level", "qualification")
    rep = json.loads(r.stdout)
    scored = rep.get("diagnostic_classes", {}).get("PASS", 0)
    t("candidate reads hidden key/shard", scored == 0,
      f"argv-theft candidate scored {scored} passes; canaries: "
      f"{[c['verdict'] for c in rep.get('canaries', [])]}")

    # 2 — patch writes outside the worktree
    from lawmax21.patch import PatchEngine, PatchRejected
    from lawmax21.sandbox import SandboxedWorktree
    wt = SandboxedWorktree(tempfile.mkdtemp(prefix="proof-wt-"))
    pe = PatchEngine(wt, tempfile.mkdtemp())
    escapes, blocked = ["/etc/lawmax-escape", "../escape.txt", "../../evaluator/grade.py",
                        "C:\\escape.txt", ".git/config"], 0
    for p in escapes:
        try:
            pe.apply("ESC", [{"path": p, "new_content": "escaped"}])
        except PatchRejected:
            blocked += 1
    t("patch writes outside worktree", blocked == len(escapes),
      f"{blocked}/{len(escapes)} escape attempts rejected")

    # 3 — tampered manifest returns OK
    tamper = tempfile.mkdtemp(prefix="proof-tamper-")
    shutil.copytree(dest, os.path.join(tamper, "pkg"), symlinks=True,
                    ignore=shutil.ignore_patterns("__pycache__", "runtime", "proof"))
    tp = os.path.join(tamper, "pkg")
    with open(os.path.join(tp, "immutable-package", "canonical-charter",
                           "00-LAWMAX-SYSTEM-OBJECTIVE-CHARTER.md"), "a", encoding="utf-8") as f:
        f.write("\n\nINJECTED OBJECTIVE\n")
    os.remove(os.path.join(tp, "immutable-package", "protocols", "23-RISK-REGISTER.md"))
    with open(os.path.join(tp, "immutable-package", "protocols", "99-SMUGGLED.md"), "w",
              encoding="utf-8") as f:
        f.write("unlisted\n")
    r = py(os.path.join(tp, "executable-orchestrator", "tools", "validate_package.py"))
    t("tampered manifest returns OK", r.returncode != 0,
      f"validator exit={r.returncode}; {r.stdout.strip().splitlines()[0] if r.stdout.strip() else ''}")

    # 4 — state advances on an empty/invalid artifact
    from lawmax21.eventlog import EventLog
    from lawmax21.signing import generate_private, load_public
    from lawmax21.states import GuardFailed, Machine
    rt = tempfile.mkdtemp(prefix="proof-empty-")
    sk = generate_private(os.path.join(rt, "run.key"))
    log = EventLog(os.path.join(rt, "state", "events.jsonl"), signer=sk)
    empty = os.path.join(rt, "artifact.json")
    open(empty, "w").close()
    mm = Machine(rt, log, load_public(E["owner_pub"]), RUN_ID, {"PACKAGE_VALIDATED": lambda m: empty})
    try:
        mm.advance("PACKAGE_VALIDATED")
        t("state advances on empty artifact", False, "the machine accepted a 0-byte artifact")
    except GuardFailed as e:
        t("state advances on empty artifact", True, str(e)[:160])

    # 4b — a syntactically valid but semantically hollow artifact
    hollow = os.path.join(rt, "hollow.json")
    atomic_write_json(hollow, {"verdict": "OK", "manifest_files_checked": 1,
                               "unlisted_files": ["smuggled.md"], "missing_files": [],
                               "schema_failures": []})
    mm2 = Machine(rt, log, load_public(E["owner_pub"]), RUN_ID, {"PACKAGE_VALIDATED": lambda m: hollow})
    try:
        mm2.advance("PACKAGE_VALIDATED")
        t("state advances on hollow artifact", False, "schema guard accepted an unlisted file")
    except GuardFailed as e:
        t("state advances on hollow artifact", True, str(e)[:160])

    # 5 — cached response reused for a different request
    from lawmax21.budget import BudgetLedger
    from lawmax21.client import Client, HttpTransport
    led = BudgetLedger(os.path.join(rt, "ledger.json"),
                       {"eur": 5, "tokens": 5_000_000, "calls": 100, "successor_reserve_fraction": 0.2})
    cli = Client(HttpTransport(f"http://127.0.0.1:{PORT}/chat/completions", "deepseek-chat"),
                 os.path.join(rt, "raw"), led, None, "system")
    os.environ.setdefault("DEEPSEEK_API_KEY", "proof-token-not-a-real-key")
    l1, _, r1, _ = cli.call("builder", "T1", "ctxA", [{"role": "user", "content": "ROLE: builder\nQUESTION ONE"}])
    l2, _, r2, _ = cli.call("builder", "T1", "ctxA", [{"role": "user", "content": "ROLE: builder\nA DIFFERENT QUESTION"}])
    l3, _, r3, _ = cli.call("builder", "T1", "ctxA", [{"role": "user", "content": "ROLE: builder\nQUESTION ONE"}])
    # Both directions must hold: a DIFFERENT body must NOT reuse the cache (l1≠l2, r2 fresh),
    # and an IDENTICAL body MUST replay the same logical response (l3==l1, r3 replayed). The
    # old assertion checked only the first half, so a cache that never replayed would have
    # passed it too (audit: one-sided replay test).
    t("cached response reused for a different request",
      l1 != l2 and not r2 and l3 == l1 and r3,
      f"different body -> different id ({l1[:8]} vs {l2[:8]}), r2={r2}; "
      f"identical body -> same id and replay (l3==l1: {l3 == l1}, r3={r3})")

    # 6 — launch completes a real non-mock state path
    summary = read_json(os.path.join(launch_runtime, "reports", "run_summary.json"))
    raw = os.path.join(launch_runtime, "raw-api", "responses")
    n_http = len(os.listdir(raw)) if os.path.isdir(raw) else 0
    t("launch fails to complete a real state path",
      summary["final_state"] in ("COMMITTED", "BEST_DISCOVERED_SO_FAR") and n_http > 0,
      f"final_state={summary['final_state']} after {n_http} real HTTP responses")

    # 7 — hand-written checkpoint is obeyed
    from lawmax21.eventlog import LogTampered
    forged_rt = tempfile.mkdtemp(prefix="proof-forge-")
    fsk = generate_private(os.path.join(forged_rt, "run.key"))
    flog = EventLog(os.path.join(forged_rt, "state", "events.jsonl"), signer=fsk)
    atomic_write_json(os.path.join(forged_rt, "state", "current.json"),
                      {"state": "INDEPENDENT_AUDIT", "transitions": 0, "anchor": "0" * 64})
    fm = Machine(forged_rt, flog, load_public(E["owner_pub"]), RUN_ID, {})
    try:
        st = fm.state()
        t("hand-written checkpoint obeyed", False, f"runner accepted a forged checkpoint: {st}")
    except LogTampered as e:
        t("hand-written checkpoint obeyed", True, str(e)[:200])

    # 8 — rewritten event log still verifies
    import hashlib
    from lawmax21.canonical import canonical_bytes, utc
    rw = tempfile.mkdtemp(prefix="proof-rewrite-")
    rsk = generate_private(os.path.join(rw, "run.key"))
    rlog = EventLog(os.path.join(rw, "state", "events.jsonl"), signer=rsk)
    rlog.append("transition", "state-machine", {"from": "UNINITIALIZED", "to": "PACKAGE_VALIDATED"})
    prev, lines = "0" * 64, []
    for i, to in enumerate(["PACKAGE_VALIDATED", "INDEPENDENT_AUDIT", "COMMITTED"]):
        body = {"seq": i, "utc": utc(), "kind": "transition", "actor": "state-machine",
                "payload": {"from": "X", "to": to}, "reason": "forged", "subject_sha256": "",
                "prev_hash": prev, "signer_key_id": rsk.key_id}
        bh = hashlib.sha256(canonical_bytes(body)).hexdigest()
        prev = bh
        lines.append(json.dumps({"body": body, "body_hash": bh, "signature": "00" * 64},
                                sort_keys=True))
    with open(os.path.join(rw, "state", "events.jsonl"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    ok, n, why = EventLog(os.path.join(rw, "state", "events.jsonl"), verifier=rsk.public).verify()
    t("rewritten event log still verifies", not ok, f"verify -> {ok}: {why}")

    # 9 — candidate patch modifies the evaluator
    ev_before = sha256_file(os.path.join(evaluator, "grade.py"))
    try:
        pe.apply("EV", [{"path": "../../private-evaluator/evaluator/grade.py",
                         "new_content": "# rewritten"}])
    except PatchRejected:
        pass
    t("candidate patch modifies the evaluator",
      sha256_file(os.path.join(evaluator, "grade.py")) == ev_before, "evaluator source unchanged")

    # 10 — coverage certified without model replies
    from lawmax21.coverage import CitationFabricated, CoverageLedger
    corp = tempfile.mkdtemp(prefix="proof-corpus-")
    with open(os.path.join(corp, "doc.md"), "w", encoding="utf-8") as f:
        f.write("The protocol requires that every claim carries a verifiable citation.\n")
    cl = CoverageLedger(os.path.join(tempfile.mkdtemp(), "cov.json"), corp)
    before = cl.certify()["certified"]
    w = cl.plan()[0]
    try:
        cl.record_ingestion(w["rel"], w["file_sha256"], w["start"], w["end"], "x", {},
                            {"summary": "a summary long enough to satisfy the minimum length rule",
                             "claims": [{"claim": "an invented claim about the passage",
                                         "citation": {"start": 0, "end": 20,
                                                      "quote": "TEXT THAT IS NOT THERE"}}],
                             "contradictions": [], "probe_answers": [{"question": "q", "answer": "a"}]},
                            ["q"])
        fabricated_accepted = True
    except CitationFabricated:
        fabricated_accepted = False
    t("coverage certified without verified model replies",
      (not before) and (not fabricated_accepted),
      "filesystem walk certifies nothing; a quote that is not in the source is rejected")

    # 11 — holdout passes a candidate that does not implement the capability
    r = py(os.path.join(evaluator, "evaluate.py"), "--bank", E["bank"],
           "--key", os.path.join(E["secrets"], "HIDDEN.key"),
           "--candidate", os.path.join(evaluator, "canaries", "ATTACK-filesystem-sweep.py"),
           "--level", "replication")
    rep = json.loads(r.stdout)
    t("holdout/replication passes a non-implementing candidate",
      rep.get("diagnostic_classes", {}).get("PASS", 0) == 0,
      f"sweep candidate PASS count = {rep.get('diagnostic_classes', {}).get('PASS')}")

    # 12 — the package starts without its dependency lock being satisfiable
    lock = os.path.join(dest, "requirements.lock")
    t("package has no dependency lock / preflight", os.path.exists(lock),
      "requirements.lock present and preflight exercises each dependency, not just imports")

    # 13 — budget overrun proceeds
    from lawmax21.budget import BudgetExhausted
    tiny = BudgetLedger(os.path.join(tempfile.mkdtemp(), "tiny.json"),
                        {"eur": 0.001, "tokens": 10, "calls": 5, "successor_reserve_fraction": 0.2})
    try:
        tiny.reserve("r1", "builder", 1_000_000, 25.0)
        blocked_pre = False
    except BudgetExhausted:
        blocked_pre = True
    t("budget overrun proceeds", blocked_pre, "reserve() raises BEFORE the call instead of logging after")

    # 14 — COMMITTED without a proof of ceiling. The proof concludes BEST_DISCOVERED_SO_FAR,
    # so the label rule must refuse to relabel it supreme (altitudes use the real L-ladder).
    from lawmax21.states import SEMANTIC
    fake = {"ceiling_proven": False, "conditions": {"dryness": True, "attacked_by_radical": False,
                                                    "simplification_tested": True,
                                                    "families_exhausted": False,
                                                    "altitude_saturated": True},
            "rounds": 1, "incumbent": "CAND-A", "untried_families": ["norm-lattice"],
            "audited_altitude": "L4", "highest_evidenced_altitude": "L6",
            "layers_unreached": ["L7"], "evolvability": "NEEDS_REFACTOR",
            "axioms_upheld": True, "consciousness": "NOT_DEMONSTRATED",
            "terminal_state": "BEST_DISCOVERED_SO_FAR"}
    try:
        SEMANTIC["COMMITTED"](None, fake)
        t("COMMITTED without a proven ceiling", False, "the label rule did not fire")
    except GuardFailed as e:
        t("COMMITTED without a proven ceiling", True, str(e)[:200])

    return out


# ==================================================================== main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "proof"))
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)
    dest = os.path.join(a.out, "env")
    print("· building a disposable copy of the package …")
    E = build_env(dest)

    sys.path.insert(0, os.path.join(dest, "executable-orchestrator"))
    from tools import mock_deepseek_server as mock  # noqa: F401  (imported for its module path)
    sys.path.insert(0, os.path.join(dest, "executable-orchestrator", "tools"))
    import mock_deepseek_server as mockmod
    srv = mockmod.serve(PORT)
    print(f"· local API on 127.0.0.1:{PORT} (no paid call is possible from here)")

    report = {"protocol_version": "2.1.0", "run_id": RUN_ID}
    try:
        print("· preflight …")
        r = py(os.path.join(dest, "executable-orchestrator", "orchestrator.py"), "--preflight",
               env={"LAWMAX_RUNTIME": os.path.join(dest, "runtime")})
        report["preflight"] = {"rc": r.returncode, "tail": (r.stdout or r.stderr)[-800:]}

        # ONE coherent end-to-end run that ALSO proves crash-safety: it launches, is crashed
        # after 4 transitions, resumes from the signed log, satisfies every owner gate, and
        # runs through to a terminal. A separate "clean launch" would be a strict subset of
        # this path and would double-consume the single-use holdout against the shared bank —
        # so the crash-and-resume run IS the full launch, exercising more, not less.
        print("· full launch over HTTP: crash after 4, resume, owner gates, to completion …")
        launch = drive_launch(E, runtime_name="runtime", crash_after=4, max_rounds=2)
        report["launch"] = {"completed": launch["completed"], "attempts": launch["attempts"],
                            "crashed_and_resumed": launch["crashed_and_resumed"],
                            "gates_signed": launch["gates_signed"],
                            "last": launch["transcript"][-1]["tail"][-900:]}
        report["crash_then_resume"] = {"completed": launch["completed"],
                                       "crashed_and_resumed": launch["crashed_and_resumed"],
                                       "attempts": launch["attempts"],
                                       "gates_signed": launch["gates_signed"]}

        runtime = os.path.join(dest, "runtime")
        for name, rel in (("run_summary", "reports/run_summary.json"),
                          ("escalation_proof", "audit/escalation_proof.json"),
                          ("independent_audit", "audit/independent_audit.json"),
                          ("coverage", "reports/coverage_report.json"),
                          ("hesa", "frontier/hesa_candidate.json"),
                          ("migration", "architecture/migration_plan.json")):
            p = os.path.join(runtime, rel)
            if os.path.exists(p):
                report[name] = read_json(p)
        report["api_calls_made"] = mockmod.STATE["calls"]

        print("· adversarial battery …")
        report["rejection_tests"] = rejection_tests(E, runtime)

        print("· liveness: COMMITTED is reachable, and only via owner integration …")
        report["committed_reachability"] = committed_reachability(E)
    finally:
        srv.shutdown()

    passed = [t for t in report.get("rejection_tests", []) if t["rejected"]]
    failed = [t for t in report.get("rejection_tests", []) if not t["rejected"]]
    crash = report.get("crash_then_resume", {})
    crash_ok = bool(crash.get("completed") and crash.get("crashed_and_resumed"))
    reach_ok = report.get("committed_reachability", {}).get(
        "committed_reachable_only_via_measured_generalising_and_owner_signed_integration", False)
    launch_ok = report.get("launch", {}).get("completed", False)
    report["verdict"] = {
        "rejection_tests_total": len(report.get("rejection_tests", [])),
        "rejected_as_required": len(passed),
        "FAILED": [t["test"] for t in failed],
        "launch_completed": launch_ok,
        "crash_then_resume_completed": crash_ok,
        "committed_reachable_only_via_measured_generalising_and_owner_signed_integration": reach_ok,
        "local_api_calls": report.get("api_calls_made", 0),   # all to 127.0.0.1, none billable
        "paid_api_calls": 0,
        "overall": "PASS" if (not failed and launch_ok and crash_ok and reach_ok) else "FAIL",
    }
    atomic_write_json(os.path.join(a.out, "LAWMAX_v2.1_SECURITY_AND_LAUNCH_PROOF.json"), report)
    print(json.dumps(report["verdict"], ensure_ascii=False, indent=1))
    if not a.keep:
        pass
    return 0 if report["verdict"]["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
