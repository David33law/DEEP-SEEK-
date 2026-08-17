#!/usr/bin/env python3
"""Negative proof that every signed Observatory terminal condition is load-bearing.

Builds the exact production context without a provider call, validates the real COMMITTED artifact
against the dynamically extended schema, then mutates and deletes every required condition and
supremacy boolean. Every mutation must be rejected by the actual semantic guard or schema validator.
"""
import argparse
import copy
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ORCH = os.path.dirname(HERE)
ROOT = os.path.dirname(ORCH)
sys.path.insert(0, ORCH)

from lawmax21 import observatory_launcher, schema, states
from lawmax21.canonical import atomic_write_json, read_json


def _expect_guard_failure(guard, artifact, label):
    class Runtime:
        profile_id = "national-observatory"
    try:
        guard(Runtime(), artifact)
    except states.GuardFailed:
        return {"label": label, "rejected": True}
    raise RuntimeError(label + ": semantic guard accepted a disabled terminal obligation")


def _expect_schema_failure(validator, artifact, label):
    try:
        validator.validate(artifact)
    except schema.ValidationError:
        return {"label": label, "rejected": True}
    raise RuntimeError(label + ": schema accepted a missing required terminal obligation")


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--canonical-repo", required=True)
    parser.add_argument("--cp1-evidence", required=True)
    parser.add_argument("--prior-cp2", required=True)
    parser.add_argument("--endpoint", default="http://127.0.0.1:9/chat/completions")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    os.environ["OBSERVATORY_ZERO_COST_PROOF"] = "1"
    os.environ["OBSERVATORY_CANONICAL_REPO"] = os.path.abspath(args.canonical_repo)
    os.environ["OBSERVATORY_CP1_EVIDENCE"] = os.path.abspath(args.cp1_evidence)
    os.environ["OBSERVATORY_PRIOR_CP2"] = os.path.abspath(args.prior_cp2)
    os.environ["DEEPSEEK_API_KEY"] = "terminal-proof-local-placeholder"

    result = {"proof": "observatory-terminal-condition-closure-v1",
              "provider_calls": 0, "status": "FAIL"}
    try:
        observatory_launcher.install_overlay()
        run_key = os.path.join(ROOT, "private-evaluator", "owner-held-secrets",
                               f"RUN-{args.run_id}.key")
        observatory_launcher.build_context(
            ROOT, os.path.abspath(args.runtime), args.run_id, "LAUNCH",
            args.endpoint, "deepseek-v4-pro", "DEEPSEEK_API_KEY", "subprocess",
            os.path.abspath(args.canonical_repo),
            observatory_launcher.PROFILE.master_system_path(ROOT), run_key)

        summary = read_json(os.path.join(args.runtime, "reports", "run_summary.json"))
        artifact = summary["escalation"]
        committed_schema = states.SCHEMAS["COMMITTED"]
        validator = schema.Validator(committed_schema)
        validator.validate(artifact)
        guard = states.SEMANTIC["COMMITTED"]
        class Runtime:
            profile_id = "national-observatory"
        guard(Runtime(), artifact)

        conditions_required = list(
            committed_schema["properties"]["conditions"]["required"])
        supremacy_required = list(
            committed_schema["properties"]["supremacy"]["required"])
        condition_mutations = []
        for key in conditions_required:
            if not isinstance(artifact["conditions"].get(key), bool):
                continue
            mutated = copy.deepcopy(artifact); mutated["conditions"][key] = False
            condition_mutations.append(_expect_guard_failure(
                guard, mutated, "condition-false:" + key))
            missing = copy.deepcopy(artifact); del missing["conditions"][key]
            condition_mutations.append(_expect_schema_failure(
                validator, missing, "condition-missing:" + key))

        supremacy_mutations = []
        for key in supremacy_required:
            if not isinstance(artifact["supremacy"].get(key), bool):
                continue
            mutated = copy.deepcopy(artifact); mutated["supremacy"][key] = False
            supremacy_mutations.append(_expect_guard_failure(
                guard, mutated, "supremacy-false:" + key))
            missing = copy.deepcopy(artifact); del missing["supremacy"][key]
            supremacy_mutations.append(_expect_schema_failure(
                validator, missing, "supremacy-missing:" + key))

        structural = []
        for label, mutate in (
            ("ceiling-false", lambda x: x.__setitem__("ceiling_proven", False)),
            ("terminal-not-committed", lambda x: x.__setitem__(
                "terminal_state", "BEST_DISCOVERED_SO_FAR")),
            ("untried-family", lambda x: x.__setitem__(
                "untried_families", ["NEGATIVE-WITNESS"])),
            ("unreached-layer", lambda x: x.__setitem__(
                "layers_unreached", ["L12"])),
            ("axiom-false", lambda x: x.__setitem__("axioms_upheld", False)),
            ("evolvability-false", lambda x: x.__setitem__(
                "evolvability", "NEEDS_REFACTOR"))):
            mutated = copy.deepcopy(artifact); mutate(mutated)
            structural.append(_expect_guard_failure(guard, mutated, label))

        result.update({
            "status": "PASS",
            "schema_required_conditions": conditions_required,
            "schema_required_supremacy": supremacy_required,
            "condition_negative_witnesses": condition_mutations,
            "supremacy_negative_witnesses": supremacy_mutations,
            "structural_negative_witnesses": structural,
            "all_required_fields_fail_closed": True,
        })
    except Exception as exc:
        result["reason"] = str(exc)
    finally:
        os.environ.pop("DEEPSEEK_API_KEY", None)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        atomic_write_json(args.out, result)
        print(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
