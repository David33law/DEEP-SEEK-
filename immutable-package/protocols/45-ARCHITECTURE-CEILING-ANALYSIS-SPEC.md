# 45 — ARCHITECTURE CEILING ANALYSIS SPEC (v1.3)
After EVERY successful engineering cycle produce:
CURRENT-ARCHITECTURE-CEILING.md + .json and NEXT-ALTITUDE-HYPOTHESES.yaml.
Required content: capabilities NOW (audited, per ontology) · capabilities NOT attainable at
current altitude (with the blocking reason) · bottlenecks (mechanism-level, with evidence) ·
hidden dependencies discovered (incl. silent external-model reliance) · structural changes
required for the next altitude · next FALSIFIABLE experiments (each phrased so failure is
possible and informative, and each bound to an open architectural question, 32).
NEXT-ALTITUDE-HYPOTHESES.yaml schema: {hypothesis, altitude_from→to, mechanism_change,
predicted_new_capabilities: [ontology ids], falsification_test, cost_class S/M/L/XL}.
These artifacts are inputs to 44 (successor design) and to FRONTIER_EXHAUSTION_REVIEW (40 §3b).
