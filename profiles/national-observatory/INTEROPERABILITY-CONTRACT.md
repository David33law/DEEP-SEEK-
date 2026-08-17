# National Legal Observatory — Legal Interoperability Contract v1

## 1. Purpose

One canonical legal truth is useful nationally only if humans, public bodies, European systems and AI consumers can receive faithful, independently verifiable projections. A channel name or generic JSON object is not interoperability evidence.

Every surviving architecture must provide an `interoperability_candidate.py` implementing deterministic projections for a bounded machine-checkable profile derived from ELI, ELI impact, ECLI, Akoma Ntoso, LegalRuleML, PROV-O and the Observatory's one-root publication invariant.

The profile does not claim complete validation against every external standard rule. It proves the exact tested subset and exposes the remaining conformance boundary.

## 2. Candidate interface

`interoperability_candidate.py` exports:

```python
def project(canonical_bundle: dict) -> dict: ...
def interoperability_manifest() -> dict: ...
```

`project` is pure and deterministic. It receives one canonical bundle containing stable work, expression, manifestation, provision-version, normative-impact, decision/ECLI, provenance and canonical-root fields.

It returns exactly:

- `human` — structured human projection;
- `api` — canonical JSON API projection;
- `linked_data` — JSON-LD projection;
- `eli` — ELI/ELI-impact JSON-LD profile;
- `akoma_ntoso` — UTF-8 XML string;
- `legalruleml` — UTF-8 XML string;
- `public_sector` — bulk/public-administration package;
- `ai` — machine-consumption package;
- `provenance` — PROV-style derivation object.

## 3. One-root invariant

Every channel must expose the exact input `canonical_root`, stable work identity, expression/version identity, status and legal/effective interval. No channel may become a writable or independently resolved truth seat.

Projection-specific identifiers may be added only as deterministic mappings from canonical identity.

## 4. ELI profile

The ELI projection must distinguish:

- legal resource/work;
- legal expression/version and language;
- manifestation/format;
- provision identity;
- normative impacts with effect type, target and legal effective time.

It must preserve deterministic mappings to the canonical Observatory identifiers and must not collapse work, expression and manifestation identity.

## 5. ECLI profile

A judicial decision must preserve a stable ECLI and link to the exact applicable provision-version identifier and legal-time cut. A link merely to the current statute or unversioned article fails.

## 6. Akoma Ntoso profile

The XML projection uses the Akoma Ntoso 3.0 namespace and includes:

- FRBRWork, FRBRExpression and FRBRManifestation identity;
- deterministic `eId` values for amendable provisions;
- the legal text/version represented by the canonical bundle;
- modification metadata sufficient to recover the supplied normative impacts.

## 7. LegalRuleML profile

The XML projection uses the LegalRuleML 1.0 namespace and includes:

- legal source references;
- rule/statement identity;
- temporal/effective metadata;
- authority/status metadata;
- provenance link to canonical evidence;
- explicit normative effect type and target.

The exchange representation remains a projection; it is not the trusted legal-effect interpreter.

## 8. Provenance profile

The provenance projection exposes entities, activities and derivation relationships sufficient to trace every public assertion to input evidence and the versioned projection activity. It must preserve source hashes and the canonical root.

## 9. Machine-checked trials

The evaluator uses hidden randomized Greek-law-shaped bundles and checks:

1. deterministic byte-equivalent output;
2. one-root and identity consistency across all channels;
3. work/expression/manifestation non-collapse;
4. ELI impact completeness and exact target/effect/time;
5. ECLI to exact provision-version linkage;
6. Akoma Ntoso namespace, FRBR and `eId` structure;
7. LegalRuleML namespace, source, temporal, authority and effect structure;
8. PROV-style evidence/activity/derivation completeness;
9. UTF-8 and XML parseability;
10. no doctrine or AI-generated proposition promoted to binding status;
11. explicit unknown/conflict preservation;
12. projection replay determinism under reordered input maps.

## 10. Independent implementations

Two independently prompted interoperability implementations are required. Both must pass hidden conformance and agree on the evaluator-normalized legal identity/effect digest. Source bytes must be distinct.

One architecture-preserving revision per implementation may use aggregate conformance failures. Hidden bundles and expected output bytes are not disclosed.

## 11. Terminal consequence

`legal_interoperability_passed`, `interoperability_implementations_agree`, `interoperability_replication_passed` and `interoperability_crown_passed` are explicit supremacy conditions.

A missing standard profile, identity collapse, projection divergence, parse failure or unresolved conformance gap blocks `COMMITTED`. Resource exhaustion yields only `BEST_DISCOVERED_SO_FAR`.