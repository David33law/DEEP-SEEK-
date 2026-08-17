#!/usr/bin/env python3
"""Hidden bounded conformance arena for Observatory legal projections."""
import argparse
import copy
import hashlib
import json
import os
import random
import subprocess
import sys
import xml.etree.ElementTree as ET

from candidate_host import container_runtime

IMAGE = "python:3.11-slim"
AKN = "http://docs.oasis-open.org/legaldocml/ns/akn/3.0"
LRML = "http://docs.oasis-open.org/legalruleml/ns/v1.0/"
REQUIRED_OUTPUTS = {"human", "api", "linked_data", "eli", "akoma_ntoso",
                    "legalruleml", "public_sector", "ai", "provenance"}
MANIFEST_FIELDS = ("identity_model", "temporal_model", "normative_effect_model",
                   "provenance_proof_model", "publication_topology")
BOOTSTRAP = r'''
import copy,json,sys
req=json.loads(sys.stdin.read()); ns={"__name__":"__candidate__"}
try:
 exec(compile(req["source"],"<interoperability-candidate>","exec"),ns,ns)
 if req["op"]=="manifest": out=ns["interoperability_manifest"]()
 else: out=ns["project"](copy.deepcopy(req["bundle"]))
 print(json.dumps({"ok":True,"result":out},ensure_ascii=False,sort_keys=True))
except BaseException as exc:
 print(json.dumps({"ok":False,"error":type(exc).__name__+": "+str(exc)},ensure_ascii=False))
'''


def _canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


def _digest(value):
    return hashlib.sha256(_canon(value).encode("utf-8")).hexdigest()


def _call(runtime, source, op, bundle=None, timeout=90):
    request = {"source": source, "op": op, "bundle": bundle}
    command = [runtime, "run", "--rm", "-i", "--network=none", "--read-only",
               "--tmpfs", "/tmp:size=64m", "--memory=1g", "--pids-limit=64",
               "--cap-drop=ALL", "--security-opt", "no-new-privileges",
               "-w", "/tmp", IMAGE, "python3", "-I", "-S", "-B", "-c", BOOTSTRAP]
    result = subprocess.run(command, input=json.dumps(request, ensure_ascii=False),
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0 or len(result.stdout.encode("utf-8")) > 8 * 1024 * 1024:
        raise RuntimeError("interoperability candidate container failed or flooded output")
    rows = []
    for line in result.stdout.splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "ok" in obj:
            rows.append(obj)
    if not rows or rows[-1].get("ok") is not True:
        raise RuntimeError((rows[-1].get("error") if rows else result.stderr[-500:])
                           or "candidate produced no result")
    return rows[-1]["result"]


def _bundle(index, seed):
    token = hashlib.sha256(f"{seed}|{index}".encode()).hexdigest()
    year = 1990 + index % 35
    work = f"https://law.example/eli/nomos/{year}/{100+index}"
    expression = work + f"/ell@{year+1}-01-01"
    manifestation = expression + "/html"
    provision = work + f"/article/{1+index%30}"
    version = provision + f"@{year+1}-01-01"
    evidence = [{"id": f"SRC-{token[:12]}-{j}",
                 "sha256": hashlib.sha256(f"e|{token}|{j}".encode()).hexdigest(),
                 "uri": f"https://evidence.example/{token[:16]}/{j}"}
                for j in range(1, 4)]
    effects = ("AMEND", "CORRECT", "REPEAL", "REVIVE")
    impacts = [{"id": f"IMP-{token[12:24]}-{j}", "effect": effects[j % 4],
                "target_version_id": version,
                "effective_from": f"{year+1+j:04d}-0{1+j}-01",
                "source_id": evidence[j % len(evidence)]["id"]}
               for j in range(1, 3)]
    status = "REPEALED" if index % 4 == 0 else "IN_FORCE"
    return {"canonical_root": hashlib.sha256(f"root|{token}".encode()).hexdigest(),
            "work": {"id": work, "title": f"Νόμος {100+index}/{year}",
                     "jurisdiction": "GR"},
            "expression": {"id": expression, "version": f"v{index+1}",
                           "language": "ell", "knowledge_time": f"{year+1}-02-01"},
            "manifestation": {"id": manifestation, "media_type": "text/html"},
            "provision": {"id": provision, "version_id": version,
                          "eid": f"art_{1+index%30}", "number": str(1+index%30),
                          "text": f"Κείμενο {token[24:44]}", "status": status,
                          "valid_from": f"{year+1}-01-01", "valid_to": None},
            "impacts": impacts,
            "decision": {"id": f"DEC-{token[44:56]}",
                         "ecli": f"ECLI:GR:AREIOSPAGOS:{year+2}:{1000+index}",
                         "legal_time": f"{year+2}-03-01",
                         "applicable_provision_version_id": version},
            "evidence": evidence,
            "doctrine": [{"id": f"DOC-{token[56:64]}",
                          "proposition": "ερμηνευτική θέση", "binding": False}],
            "unknowns": ([{"kind": "SOURCE_GAP", "id": f"UNK-{token[:8]}"}]
                         if index % 3 == 0 else [])}


def _common(output, key):
    value = output.get(key)
    if not isinstance(value, dict):
        raise ValueError(key + " must be an object")
    return value


def _validate_xml(xml_text, namespace, local_names):
    if not isinstance(xml_text, str):
        raise ValueError("XML projection is not text")
    root = ET.fromstring(xml_text)
    if not root.tag.startswith("{" + namespace + "}"):
        raise ValueError("wrong XML namespace")
    names = {node.tag.split("}")[-1] for node in root.iter()}
    missing = set(local_names) - names
    if missing:
        raise ValueError("missing XML elements: " + ", ".join(sorted(missing)))
    return root


def _validate(bundle, output):
    if not isinstance(output, dict) or set(output) != REQUIRED_OUTPUTS:
        raise ValueError("projection output keys do not match the contract")
    root = bundle["canonical_root"]; p = bundle["provision"]
    normalized = {"root": root, "work": bundle["work"]["id"],
                  "expression": bundle["expression"]["id"],
                  "manifestation": bundle["manifestation"]["id"],
                  "provision": p["id"], "version": p["version_id"],
                  "status": p["status"],
                  "impacts": sorted((x["id"], x["effect"], x["target_version_id"],
                                     x["effective_from"], x["source_id"])
                                    for x in bundle["impacts"]),
                  "ecli": bundle["decision"]["ecli"]}
    for key in ("human", "api", "public_sector", "ai"):
        value = _common(output, key)
        for field, expected in (("canonical_root", root), ("work_id", normalized["work"]),
                                ("expression_id", normalized["expression"]),
                                ("manifestation_id", normalized["manifestation"]),
                                ("provision_id", normalized["provision"]),
                                ("provision_version_id", normalized["version"]),
                                ("status", normalized["status"])):
            if value.get(field) != expected:
                raise ValueError(f"{key}.{field} diverged")
        if any(x.get("binding") is not False for x in value.get("doctrine", [])):
            raise ValueError("doctrine was promoted to binding authority")
    linked = _common(output, "linked_data")
    if linked.get("canonical_root") != root or not isinstance(linked.get("@graph"), list):
        raise ValueError("linked-data root/graph invalid")
    graph = linked["@graph"]
    ids = {x.get("@id") for x in graph if isinstance(x, dict)}
    if not {normalized["work"], normalized["expression"], normalized["manifestation"],
            normalized["version"], bundle["decision"]["id"]}.issubset(ids):
        raise ValueError("linked-data identities incomplete")
    decisions = [x for x in graph if x.get("obs:ecli") == normalized["ecli"]]
    if len(decisions) != 1 or (decisions[0].get("obs:appliesProvisionVersion") or {}).get("@id") != normalized["version"]:
        raise ValueError("ECLI does not link the exact provision version")
    eli = _common(output, "eli")
    if eli.get("canonical_root") != root:
        raise ValueError("ELI root diverged")
    if (eli.get("legal_resource") or {}).get("@id") != normalized["work"] \
            or (eli.get("legal_expression") or {}).get("@id") != normalized["expression"] \
            or (eli.get("manifestation") or {}).get("@id") != normalized["manifestation"]:
        raise ValueError("ELI work/expression/manifestation collapsed")
    got_impacts = sorted((x.get("id"), x.get("effect"), x.get("target"),
                          x.get("effective_from"), x.get("source_id"))
                         for x in eli.get("impacts", []))
    if got_impacts != normalized["impacts"]:
        raise ValueError("ELI impact semantics incomplete")
    akn = _validate_xml(output["akoma_ntoso"], AKN,
                        ("FRBRWork", "FRBRExpression", "FRBRManifestation",
                         "article", "textualMod"))
    values = {node.attrib.get("value") for node in akn.iter()
              if node.tag.endswith("FRBRthis")}
    if not {normalized["work"], normalized["expression"],
            normalized["manifestation"]}.issubset(values):
        raise ValueError("Akoma Ntoso FRBR identities incomplete")
    articles = [x for x in akn.iter() if x.tag.endswith("article")]
    if len(articles) != 1 or articles[0].attrib.get("eId") != p["eid"]:
        raise ValueError("Akoma Ntoso eId invalid")
    lrml = _validate_xml(output["legalruleml"], LRML,
                         ("LegalRuleML", "LegalSource", "PrescriptiveStatement",
                          "TemporalCharacteristic", "Association"))
    statements = [x for x in lrml.iter() if x.tag.endswith("PrescriptiveStatement")]
    if len(statements) != 1 or statements[0].attrib.get("key") != normalized["version"] \
            or statements[0].attrib.get("canonicalRoot") != root:
        raise ValueError("LegalRuleML statement identity/root invalid")
    provenance = _common(output, "provenance")
    if provenance.get("canonical_root") != root:
        raise ValueError("provenance root diverged")
    evidence = {x["id"]: x["sha256"] for x in bundle["evidence"]}
    entities = {x.get("id"): x.get("sha256") for x in provenance.get("entities", [])}
    if any(entities.get(key) != value for key, value in evidence.items()):
        raise ValueError("provenance evidence hashes incomplete")
    used = {x.get("used") for x in provenance.get("wasDerivedFrom", [])}
    if not set(evidence).issubset(used):
        raise ValueError("provenance derivations incomplete")
    return normalized


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True); parser.add_argument("--out", required=True)
    for field in MANIFEST_FIELDS:
        parser.add_argument("--expected-" + field.replace("_", "-"), required=True)
    parser.add_argument("--seed", type=int, default=9802026)
    parser.add_argument("--cases", type=int, default=24)
    args = parser.parse_args(argv)
    runtime = container_runtime()
    if not runtime:
        raise RuntimeError("interoperability arena requires docker/podman")
    source = open(args.candidate, encoding="utf-8").read()
    expected = {field: getattr(args, "expected_" + field) for field in MANIFEST_FIELDS}
    report = {"status": "FAIL", "passed": False, "backend": "container",
              "runtime": runtime, "image": IMAGE, "cases": args.cases,
              "expected_manifest": expected, "failures": []}
    try:
        manifest = _call(runtime, source, "manifest")
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise RuntimeError(f"manifest mismatch {key}: {manifest.get(key)!r} != {value!r}")
        if manifest.get("projection_only") is not True or not manifest.get("standards_profiles"):
            raise RuntimeError("interoperability manifest is incomplete")
        normalized = []
        total_bytes = 0
        for index in range(args.cases):
            bundle = _bundle(index, args.seed)
            original = _canon(bundle)
            first = _call(runtime, source, "project", bundle)
            second = _call(runtime, source, "project", bundle)
            if _canon(first) != _canon(second):
                raise RuntimeError(f"case {index}: nondeterministic projection")
            if _canon(bundle) != original:
                raise RuntimeError(f"case {index}: caller bundle mutated")
            try:
                normalized.append(_validate(bundle, first))
            except Exception as exc:
                report["failures"].append({"case": index, "reason": str(exc)})
            total_bytes += len(_canon(first).encode("utf-8"))
        digest = _digest(normalized)
        passed = not report["failures"] and len(normalized) == args.cases
        report.update({"status": "PASS" if passed else "FAIL", "passed": passed,
                       "manifest": manifest, "semantic_digest": digest,
                       "cases_passed": len(normalized),
                       "projection_bytes_total": total_bytes,
                       "projection_bytes_per_case": total_bytes / max(args.cases, 1),
                       "proof_boundary": "bounded hidden profile, not full external-standard certification"})
    except Exception as exc:
        report["reason"] = str(exc)
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=1, sort_keys=True)
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0 if report.get("passed") is True else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"status": "FAIL", "passed": False, "reason": str(exc)},
                         ensure_ascii=False, indent=1))
        sys.exit(1)
