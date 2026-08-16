"""Profile-specific runtime context for the National Legal Observatory.

It inherits all generic persistence, model-call, worktree and candidate-install machinery from the
LAWMAX Context, but constructs its own frontier/escalation objects BEFORE resume state is loaded.
"""
import hashlib
import json
import os
import subprocess
import sys

from .canonical import atomic_write_json, read_json
from .frontier import Frontier
from .handlers import Context as BaseContext, A
from .patch import WorktreeManager
from . import observatory_target as target
from .observatory_escalation import ObservatoryEscalationLedger


class ObservatoryFrontier(Frontier):
    """The shared control loop may call head_to_head() without naming dimensions.

    LAWMAX's Frontier defaults are legal_capability/cross_domain_transfer. Those names do not
    belong to the Observatory Pareto contract. This profile-local subclass changes only the
    DEFAULT selector; explicit calls still work exactly as in Frontier. Dominance remains driven
    exclusively by the profile's PARETO-DIMENSIONS.json.
    """
    def __init__(self, dims_path, primary_dimension, secondary_dimension):
        super().__init__(dims_path)
        self.primary_dimension = primary_dimension
        self.secondary_dimension = secondary_dimension

    def head_to_head(self, primary=None, secondary=None):
        return super().head_to_head(primary or self.primary_dimension,
                                    secondary or self.secondary_dimension)


class ObservatoryContext(BaseContext):
    def __init__(self, root, runtime, run_id, client, ledger, log, decisions, owner_public,
                 evaluator_dir, bank_dir, key_path, canonical_repo, suite_path, backend,
                 mode, corpus_root, profile, cp1_evidence, prior_cp2):
        # Deliberately mirror BaseContext's field contract without calling its constructor: the
        # base constructor instantiates LAWMAX dimensions/escalation and would mis-read an
        # Observatory arena during --resume before we could replace them.
        self.mode = mode
        self.corpus_root = corpus_root
        self.root = root
        self.runtime = runtime
        self.run_id = run_id
        self.client = client
        self.ledger = ledger
        self.log = log
        self.decisions = decisions
        self.owner = owner_public
        self.evaluator_dir = evaluator_dir
        self.bank_dir = bank_dir
        self.key_path = key_path
        self.canonical_repo = canonical_repo
        self.suite_path = suite_path
        self.backend = backend
        self.profile = profile
        self.profile_id = profile.id
        self.cp1_evidence = os.path.abspath(cp1_evidence)
        self.prior_cp2 = os.path.abspath(prior_cp2)
        self.pkg = os.path.join(root, "immutable-package")              # historical LAWMAX seal
        self.profile_pkg = os.path.join(root, "profiles", "national-observatory")
        self.vault = os.path.join(root, "evidence-vault")
        self.orch = os.path.join(root, "executable-orchestrator")
        self.frontier = ObservatoryFrontier(profile.pareto_path(root),
                                             profile.primary_dimension,
                                             profile.secondary_dimension)
        self.esc = ObservatoryEscalationLedger(
            A(self, "escalation", "ledger.json"), dry_rounds_required=2)
        self.wm = WorktreeManager(canonical_repo, A(self, "worktrees", "x")[:-2])
        self.candidates = {}
        self.scores = {}
        self.round = 0
        self.package_hash_before = None

        if evaluator_dir not in sys.path:
            sys.path.insert(0, evaluator_dir)
        import observatory_harness
        import observatory_host
        self.obs_harness = observatory_harness
        self.obs_host = observatory_host
        self.suite = read_json(suite_path)

        self._state_path = A(self, "candidates", "arena.json")
        from . import sealed
        _, self._sealed_rels = sealed.partition(root)
        self._sealed_fp = sealed.fingerprints(root, self._sealed_rels)
        self._load_arena()

    def credit_integration_if_attested(self):
        # Observatory layers are credited only from profile-specific executable measurement.
        return False

    def measure_visible(self, cid):
        c = self.candidates[cid]
        rep = self.obs_harness.run_suite(c["source"], self.suite, self.backend)
        dims = dict(rep.get("dimension_scores", {}))
        primary = float(dims.get(self.profile.primary_dimension, 0.0))
        rec = {"candidate_id": cid,
               "classes": rep.get("diagnostic_classes", {}),
               "slice_scores": dims,
               "dimension_scores": dims,
               "macro_f1": primary,
               "publication_latency": rep.get("publication_latency", 9999.0),
               "isolation": rep.get("isolation", {})}
        self.scores.setdefault(cid, {}).update({"visible": rec})
        self._save_arena()
        return rec

    def measure_hidden(self, cid, level):
        c = self.candidates[cid]
        cand_file = A(self, "candidate-src", f"{cid}.py")
        with open(cand_file, "w", encoding="utf-8") as f:
            f.write(c["source"])
        out = A(self, "reports", f"observatory-hidden-{level}-{cid}.json")
        r = subprocess.run(
            [sys.executable, os.path.join(self.evaluator_dir, "observatory_evaluate.py"),
             "--bank", self.bank_dir, "--key", self.key_path, "--candidate", cand_file,
             "--level", level, "--backend", self.backend, "--out", out],
            capture_output=True, text=True)
        if not os.path.exists(out):
            raise RuntimeError(f"Observatory evaluator produced no report: {(r.stdout + r.stderr)[:500]}")
        rep = read_json(out)
        if rep.get("status") != "OK":
            raise RuntimeError(f"Observatory evaluator refused: {rep.get('reason', rep.get('status'))}")
        return rep

    @staticmethod
    def _ge(scores, key, threshold):
        return float(scores.get(key, 0.0)) + 1e-12 >= threshold

    def demonstrated_layers(self, cid, hidden_rep):
        s = hidden_rep.get("dimension_scores", {})
        demo = []
        if self._ge(s, "source_coverage", .98) and self._ge(s, "provenance_completeness", .995):
            demo.append("L1")
        if self._ge(s, "canonical_identity_accuracy", .995):
            demo.append("L2")
        if self._ge(s, "temporal_reconstruction_accuracy", .99):
            demo.append("L3")
        if self._ge(s, "normative_effect_accuracy", .99):
            demo.append("L4")
        if self._ge(s, "change_detection_recall", .98) and self._ge(s, "honest_unknown_rate", 1.0):
            demo.append("L5")
        if self._ge(s, "jurisprudence_temporal_link_accuracy", .98):
            demo.append("L6")
        if self._ge(s, "doctrine_epistemic_separation", 1.0):
            demo.append("L7")
        if self._ge(s, "provenance_completeness", .995):
            demo.append("L8")
        if self._ge(s, "honest_unknown_rate", 1.0):
            demo.append("L9")
        if (self._ge(s, "source_coverage", .98)
                and self._ge(s, "provenance_completeness", .995)
                and float(hidden_rep.get("publication_latency", 9999.0)) < 9999.0):
            demo.append("L10")
        if self._ge(s, "replay_determinism", 1.0) and self._ge(s, "recovery_success", 1.0):
            demo.append("L11")
        # L12 is deliberately withheld here. It is awarded only by the independent runtime
        # extension probe in measure_evolvability().
        return demo

    def screen_axioms(self, cid, hidden_rep):
        s = hidden_rep.get("dimension_scores", {})
        violations = []
        def fail(aid, detail):
            violations.append((aid, detail))
            self.esc.record_axiom_violation(cid, aid, detail)

        if not (self._ge(s, "source_coverage", .98) and self._ge(s, "provenance_completeness", .995)):
            fail("primary_evidence_required", "source/provenance hard minimum not demonstrated")
        if not self._ge(s, "temporal_reconstruction_accuracy", .99):
            fail("bitemporal_noncollapse", "bitemporal replay hard minimum not demonstrated")
        if not self._ge(s, "normative_effect_accuracy", .99):
            fail("history_is_append_only", "change/effect replay did not preserve correct historical state")
        if not self._ge(s, "doctrine_epistemic_separation", 1.0):
            fail("doctrine_never_binding_by_accident", "doctrine changed or contaminated binding state")
        if not self._ge(s, "honest_unknown_rate", 1.0):
            fail("honest_unknown", "conflicting/unknown evidence was not preserved as unresolved")
        if not (self._ge(s, "replay_determinism", 1.0) and self._ge(s, "recovery_success", 1.0)):
            fail("deterministic_rebuild", "clean replay/recovery did not reproduce canonical state")
        if not self._ge(s, "canonical_identity_accuracy", .995):
            fail("one_canonical_seat", "canonical identity trials failed")
        return violations

    def dimension_vector(self, cid, hidden_rep, fidelity_rep=None):
        c = self.candidates[cid]
        dims = dict(hidden_rep.get("dimension_scores", {}))
        dims["publication_latency"] = float(hidden_rep.get("publication_latency", 9999.0))
        dims["trusted_kernel_complexity"] = self.obs_harness.source_complexity(c["source"])
        dims["external_model_dependence"] = 0.0
        dims["migration_cost"] = float(min(4, max(1, len(c.get("files_written", [])))))
        # Compatibility alias used by the shared progress window. It is NOT in the Observatory
        # Pareto manifest, so it cannot affect dominance.
        dims["legal_capability"] = float(dims.get(self.profile.primary_dimension, 0.0))
        return dims

    def field_for_recombination(self):
        field = {}
        for cid, c in self.candidates.items():
            hq = self.scores.get(cid, {}).get("hidden_qualification")
            if not hq:
                continue
            field[cid] = {"slice_scores": hq.get("dimension_scores", {}),
                          "layers": self.demonstrated_layers(cid, hq),
                          "macro_f1": float(hq.get("dimension_scores", {}).get(
                              self.profile.primary_dimension, 0.0)),
                          "family": c["family"]}
        return field

    def measure_evolvability(self, cid):
        """Runtime extension without editing candidate.py: the evaluator registers a fresh,
        run-specific change type and checks that apply_change dispatches it through the new
        handler. This is a mechanical plugin/growth test, not a source-code heuristic."""
        c = self.candidates[cid]
        seed = hashlib.sha256(f"obs-extension|{self.run_id}|{cid}".encode()).hexdigest()
        kind = "EXT_" + seed[:16].upper()
        marker = seed[16:32]
        event = {"source_id": "EXTSRC-" + seed[32:40], "canonical_id": "EXT:PROVISION",
                 "target_id": "EXT:PROVISION", "knowledge_time": "2035-01-01",
                 "effective_from": "2035-01-01"}
        host = self.obs_host.ObservatoryCandidateHost(c["source"], backend=self.backend, timeout=60)
        try:
            rep = host.extension_probe(kind, marker, event)
        except Exception as exc:  # noqa: BLE001 — failed growth is a measured negative result
            rep = {"supported": False, "reason": str(exc)[:300]}
        result = rep.get("result") if isinstance(rep, dict) else None
        ok = bool(rep.get("supported") if isinstance(rep, dict) else False)
        ok = ok and isinstance(result, dict)
        ok = ok and result.get("accepted") is True and result.get("change_type") == kind
        ok = ok and result.get("extension_marker") == marker
        verdict = "EVOLVABLE" if ok else "NEEDS_REFACTOR"
        out = {"verdict": verdict, "core_untouched": True, "probe_kind": kind,
               "probe_marker": marker, "result": result,
               "reason": rep.get("reason") if isinstance(rep, dict) else "malformed result"}
        self.record_score(cid, "evolvability", out)
        self.esc.record_evolvability(cid, verdict)
        if ok:
            self.esc.record_altitude_evidence(cid, "L12", "runtime extension probe registered and executed without core edit")
        else:
            self.esc.record_axiom_violation(cid, "human_governance_nonbypassable",
                                            "no measured extension registry capable of governed capability growth")
        return out
