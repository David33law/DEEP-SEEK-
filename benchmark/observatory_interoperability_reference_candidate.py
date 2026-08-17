"""Dependency-free calibration candidate for the bounded interoperability arena."""
import copy
import hashlib
import json
import xml.etree.ElementTree as ET

IDENTITY_MODEL = "composite_identity"
TEMPORAL_MODEL = "bitemporal_intervals"
NORMATIVE_EFFECT_MODEL = "typed_directive_interpreter"
PROVENANCE_PROOF_MODEL = "provenance_graph"
PUBLICATION_TOPOLOGY = "compiled_read_only_projections"
PROFILE_VERSION = "OBS-INTEROP-1"
AKN = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
LRML = "http://docs.oasis-open.org/legalruleml/ns/v1.0/"
RULEML = "http://ruleml.org/spec"
ELI = "http://data.europa.eu/eli/ontology#"
PROV = "http://www.w3.org/ns/prov#"
ET.register_namespace("", AKN)
ET.register_namespace("lrml", LRML)
ET.register_namespace("ruleml", RULEML)


def _canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha(x):
    return hashlib.sha256(_canon(x).encode()).hexdigest()


def _common(b):
    p, e, w, m = b["provision"], b["expression"], b["work"], b["manifestation"]
    return {"canonical_root": b["canonical_root"], "work_id": w["id"],
            "expression_id": e["id"], "manifestation_id": m["id"],
            "provision_id": p["id"], "provision_version_id": p["version_id"],
            "status": p["status"], "valid_from": p["valid_from"],
            "valid_to": p.get("valid_to"), "knowledge_time": e["knowledge_time"],
            "language": e["language"],
            "source_hashes": [x["sha256"] for x in b.get("evidence", [])],
            "unknowns": copy.deepcopy(b.get("unknowns", []))}


def _impacts(b):
    return [{"id": x["id"], "effect": x["effect"],
             "target": x["target_version_id"],
             "effective_from": x["effective_from"], "source_id": x["source_id"]}
            for x in b.get("impacts", [])]


def _linked(b, c, impacts):
    g = [{"@id": c["work_id"], "@type": "eli:LegalResource"},
         {"@id": c["expression_id"], "@type": "eli:LegalExpression",
          "eli:realizes": {"@id": c["work_id"]}, "eli:language": c["language"]},
         {"@id": c["manifestation_id"], "@type": "eli:Format",
          "eli:embodies": {"@id": c["expression_id"]}},
         {"@id": c["provision_version_id"],
          "@type": "eli:LegalResourceSubdivision",
          "eli:is_part_of": {"@id": c["expression_id"]},
          "eli:id_local": c["provision_id"], "obs:status": c["status"]}]
    d = b.get("decision") or {}
    if d:
        g.append({"@id": d["id"], "@type": "obs:JudicialDecision",
                  "obs:ecli": d["ecli"],
                  "obs:appliesProvisionVersion": {"@id": d["applicable_provision_version_id"]},
                  "obs:legalTime": d["legal_time"]})
    for x in impacts:
        g.append({"@id": x["id"], "@type": "obs:NormativeImpact",
                  "eli:changes": {"@id": x["target"]},
                  "obs:effectType": x["effect"],
                  "obs:effectiveFrom": x["effective_from"],
                  "prov:wasDerivedFrom": {"@id": x["source_id"]}})
    return {"@context": {"eli": ELI, "prov": PROV,
                          "obs": "https://observatory.example/ns#"},
            "canonical_root": c["canonical_root"], "@graph": g}


def _eli(b, c, impacts):
    return {"@context": {"eli": ELI, "obs": "https://observatory.example/ns#"},
            "canonical_root": c["canonical_root"],
            "legal_resource": {"@id": c["work_id"], "@type": "eli:LegalResource"},
            "legal_expression": {"@id": c["expression_id"],
                                 "@type": "eli:LegalExpression",
                                 "eli:realizes": c["work_id"],
                                 "eli:language": c["language"],
                                 "eli:version": b["expression"]["version"]},
            "manifestation": {"@id": c["manifestation_id"], "@type": "eli:Format",
                              "eli:embodies": c["expression_id"],
                              "eli:format": b["manifestation"]["media_type"]},
            "provision": {"@id": c["provision_version_id"],
                          "stable_id": c["provision_id"],
                          "expression": c["expression_id"], "status": c["status"],
                          "valid_from": c["valid_from"], "valid_to": c["valid_to"]},
            "impacts": copy.deepcopy(impacts)}


def _akn(b, c, impacts):
    q = lambda n: "{" + AKN + "}" + n
    root = ET.Element(q("akomaNtoso")); act = ET.SubElement(root, q("act"))
    meta = ET.SubElement(act, q("meta")); ident = ET.SubElement(meta, q("identification"))
    for kind, value in (("FRBRWork", c["work_id"]),
                        ("FRBRExpression", c["expression_id"]),
                        ("FRBRManifestation", c["manifestation_id"])):
        node = ET.SubElement(ident, q(kind)); ET.SubElement(node, q("FRBRthis"), {"value": value})
        ET.SubElement(node, q("FRBRuri"), {"value": value})
    prop = ET.SubElement(meta, q("proprietary"))
    ET.SubElement(prop, "observatoryCanonicalRoot").text = c["canonical_root"]
    analysis = ET.SubElement(meta, q("analysis")); mods = ET.SubElement(analysis, q("activeModifications"))
    for x in impacts:
        mod = ET.SubElement(mods, q("textualMod"), {"eId": x["id"], "type": x["effect"]})
        ET.SubElement(mod, q("source"), {"href": x["source_id"]})
        ET.SubElement(mod, q("destination"), {"href": x["target"]})
        ET.SubElement(mod, q("efficacy"), {"date": x["effective_from"]})
    body = ET.SubElement(act, q("body")); article = ET.SubElement(body, q("article"),
                                                                 {"eId": b["provision"]["eid"]})
    ET.SubElement(article, q("num")).text = b["provision"]["number"]
    paragraph = ET.SubElement(article, q("paragraph"),
                              {"eId": b["provision"]["eid"] + "__p1"})
    ET.SubElement(ET.SubElement(paragraph, q("content")), q("p")).text = b["provision"]["text"]
    return ET.tostring(root, encoding="unicode")


def _lrml(b, c, impacts):
    q = lambda n: "{" + LRML + "}" + n
    rq = lambda n: "{" + RULEML + "}" + n
    root = ET.Element(q("LegalRuleML")); sources = ET.SubElement(root, q("LegalSources"))
    for e in b.get("evidence", []):
        ET.SubElement(sources, q("LegalSource"),
                      {"key": e["id"], "sameAs": e["uri"], "sha256": e["sha256"]})
    statement = ET.SubElement(ET.SubElement(root, q("Statements")),
                              q("PrescriptiveStatement"),
                              {"key": c["provision_version_id"], "status": c["status"],
                               "canonicalRoot": c["canonical_root"]})
    ET.SubElement(statement, rq("Atom"), {"key": c["provision_id"]})
    ET.SubElement(statement, q("TemporalCharacteristic"),
                  {"effectiveFrom": c["valid_from"],
                   "effectiveTo": c["valid_to"] or "OPEN",
                   "knowledgeTime": c["knowledge_time"]})
    for x in impacts:
        ET.SubElement(root, q("Association"),
                      {"key": x["id"], "type": x["effect"], "target": x["target"],
                       "effectiveFrom": x["effective_from"], "source": x["source_id"]})
    return ET.tostring(root, encoding="unicode")


def _prov(b, c):
    entities, derivations = [], []
    for e in b.get("evidence", []):
        entities.append({"id": e["id"], "type": "prov:Entity",
                         "sha256": e["sha256"], "uri": e["uri"]})
        derivations.append({"generated": c["provision_version_id"], "used": e["id"],
                            "activity": "projection:" + PROFILE_VERSION})
    entities.append({"id": c["provision_version_id"], "type": "prov:Entity",
                     "canonical_root": c["canonical_root"]})
    return {"canonical_root": c["canonical_root"], "entities": entities,
            "activities": [{"id": "projection:" + PROFILE_VERSION,
                            "type": "prov:Activity",
                            "canonical_root": c["canonical_root"]}],
            "wasDerivedFrom": derivations,
            "agents": [{"id": "NationalLegalObservatory", "type": "prov:SoftwareAgent"}]}


def project(canonical_bundle):
    b = copy.deepcopy(canonical_bundle); c = _common(b); impacts = _impacts(b)
    doctrine = copy.deepcopy(b.get("doctrine", []))
    if any(x.get("binding") is not False for x in doctrine):
        raise ValueError("doctrine must remain non-binding")
    base = {**c, "title": b["work"]["title"], "text": b["provision"]["text"],
            "impacts": copy.deepcopy(impacts), "decision": copy.deepcopy(b.get("decision")),
            "doctrine": doctrine, "projection_profile": PROFILE_VERSION}
    return {"human": copy.deepcopy(base), "api": copy.deepcopy(base),
            "linked_data": _linked(b, c, impacts), "eli": _eli(b, c, impacts),
            "akoma_ntoso": _akn(b, c, impacts), "legalruleml": _lrml(b, c, impacts),
            "public_sector": {**copy.deepcopy(base), "bulk_record_sha256": _sha(base)},
            "ai": {**copy.deepcopy(base), "grounding_evidence": copy.deepcopy(b.get("evidence", [])),
                   "binding_assertion": c["status"] in ("IN_FORCE", "REPEALED")},
            "provenance": _prov(b, c)}


def interoperability_manifest():
    return {"profile_version": PROFILE_VERSION, "identity_model": IDENTITY_MODEL,
            "temporal_model": TEMPORAL_MODEL,
            "normative_effect_model": NORMATIVE_EFFECT_MODEL,
            "provenance_proof_model": PROVENANCE_PROOF_MODEL,
            "publication_topology": PUBLICATION_TOPOLOGY,
            "standards_profiles": ["ELI-1.5-bounded", "ELI-Impact-1.0-bounded",
                                   "ECLI-bounded", "Akoma-Ntoso-3.0-bounded",
                                   "LegalRuleML-1.0-bounded", "PROV-O-bounded"],
            "projection_only": True, "canonical_root_field": "canonical_root",
            "proof_boundary": "bounded deterministic exchange profile; not full external conformance"}
