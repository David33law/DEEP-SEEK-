"""Strict JSON Schema validator (Draft-07 subset), dependency-free and deterministic.

Why not a library: the trusted path must not depend on network-installed packages whose
absence degrades validation to a no-op. Unsupported keywords are a HARD ERROR, never a
silent skip — a schema this validator cannot fully enforce must not be usable at all.
"""
import re

SUPPORTED = {
    "$schema", "$id", "$comment", "title", "description", "definitions", "$ref",
    "type", "enum", "const",
    "properties", "required", "additionalProperties", "patternProperties", "propertyNames",
    "minProperties", "maxProperties",
    "items", "minItems", "maxItems", "uniqueItems", "contains",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf",
    "minLength", "maxLength", "pattern",
    "allOf", "anyOf", "oneOf", "not",
}

TYPES = {
    "object": dict, "array": list, "string": str, "boolean": bool,
    "null": type(None), "number": (int, float), "integer": int,
}


class SchemaError(Exception):
    """The schema itself is unusable. Never downgraded to a warning."""


class ValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors[:12]) + ("" if len(errors) <= 12 else f" (+{len(errors)-12} more)"))


def _assert_supported(schema, where="#"):
    if isinstance(schema, bool):
        return
    if not isinstance(schema, dict):
        raise SchemaError(f"{where}: schema must be an object or boolean")
    unknown = set(schema) - SUPPORTED
    if unknown:
        raise SchemaError(f"{where}: unsupported schema keywords {sorted(unknown)} — refusing to validate")
    for k in ("properties", "patternProperties", "definitions"):
        for name, sub in (schema.get(k) or {}).items():
            _assert_supported(sub, f"{where}/{k}/{name}")
    for k in ("items", "not", "contains", "propertyNames"):
        if k in schema:
            v = schema[k]
            if isinstance(v, list):
                for i, sub in enumerate(v):
                    _assert_supported(sub, f"{where}/{k}/{i}")
            else:
                _assert_supported(v, f"{where}/{k}")
    for k in ("allOf", "anyOf", "oneOf"):
        for i, sub in enumerate(schema.get(k) or []):
            _assert_supported(sub, f"{where}/{k}/{i}")
    if "additionalProperties" in schema:
        _assert_supported(schema["additionalProperties"], f"{where}/additionalProperties")


def _typecheck(value, t):
    if t == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if t == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if t == "boolean":
        return isinstance(value, bool)
    py = TYPES.get(t)
    if py is None:
        raise SchemaError(f"unknown type {t!r}")
    return isinstance(value, py)


class Validator:
    def __init__(self, schema):
        _assert_supported(schema)
        self.root = schema

    def _resolve(self, ref, path):
        if not ref.startswith("#/"):
            raise SchemaError(f"{path}: only local $ref supported, got {ref!r}")
        node = self.root
        for part in ref[2:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            if not isinstance(node, dict) or part not in node:
                raise SchemaError(f"{path}: unresolvable $ref {ref!r}")
            node = node[part]
        return node

    def validate(self, instance):
        errs = []
        self._v(instance, self.root, "$", errs)
        if errs:
            raise ValidationError(errs)
        return True

    def _v(self, x, s, p, errs):
        if s is True or s == {}:
            return
        if s is False:
            errs.append(f"{p}: schema forbids any value")
            return
        if "$ref" in s:
            self._v(x, self._resolve(s["$ref"], p), p, errs)
            return

        if "type" in s:
            types = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(_typecheck(x, t) for t in types):
                errs.append(f"{p}: expected type {s['type']}, got {type(x).__name__}")
                return
        if "enum" in s and x not in s["enum"]:
            errs.append(f"{p}: {x!r} not in enum")
        if "const" in s and x != s["const"]:
            errs.append(f"{p}: expected const {s['const']!r}")

        if isinstance(x, str):
            if "minLength" in s and len(x) < s["minLength"]:
                errs.append(f"{p}: shorter than minLength {s['minLength']}")
            if "maxLength" in s and len(x) > s["maxLength"]:
                errs.append(f"{p}: longer than maxLength {s['maxLength']}")
            if "pattern" in s and not re.search(s["pattern"], x):
                errs.append(f"{p}: does not match pattern {s['pattern']!r}")

        if isinstance(x, (int, float)) and not isinstance(x, bool):
            for kw, ok, msg in (
                ("minimum", lambda v: x >= v, "below minimum"),
                ("maximum", lambda v: x <= v, "above maximum"),
                ("exclusiveMinimum", lambda v: x > v, "not above exclusiveMinimum"),
                ("exclusiveMaximum", lambda v: x < v, "not below exclusiveMaximum"),
            ):
                if kw in s and not ok(s[kw]):
                    errs.append(f"{p}: {msg} {s[kw]}")
            if "multipleOf" in s and s["multipleOf"] and (x % s["multipleOf"]) != 0:
                errs.append(f"{p}: not a multiple of {s['multipleOf']}")

        if isinstance(x, list):
            if "minItems" in s and len(x) < s["minItems"]:
                errs.append(f"{p}: fewer than minItems {s['minItems']}")
            if "maxItems" in s and len(x) > s["maxItems"]:
                errs.append(f"{p}: more than maxItems {s['maxItems']}")
            if s.get("uniqueItems"):
                seen = []
                for it in x:
                    if it in seen:
                        errs.append(f"{p}: duplicate item {it!r}")
                        break
                    seen.append(it)
            if "items" in s:
                if isinstance(s["items"], list):
                    for i, sub in enumerate(s["items"]):
                        if i < len(x):
                            self._v(x[i], sub, f"{p}[{i}]", errs)
                else:
                    for i, it in enumerate(x):
                        self._v(it, s["items"], f"{p}[{i}]", errs)
            if "contains" in s:
                if not any(self._ok(it, s["contains"]) for it in x):
                    errs.append(f"{p}: no item matches 'contains'")

        if isinstance(x, dict):
            for r in s.get("required", []):
                if r not in x:
                    errs.append(f"{p}: missing required property {r!r}")
            if "minProperties" in s and len(x) < s["minProperties"]:
                errs.append(f"{p}: fewer than minProperties {s['minProperties']}")
            if "maxProperties" in s and len(x) > s["maxProperties"]:
                errs.append(f"{p}: more than maxProperties {s['maxProperties']}")
            props = s.get("properties", {})
            pats = s.get("patternProperties", {})
            for k, v in x.items():
                matched = False
                if k in props:
                    self._v(v, props[k], f"{p}.{k}", errs)
                    matched = True
                for pat, sub in pats.items():
                    if re.search(pat, k):
                        self._v(v, sub, f"{p}.{k}", errs)
                        matched = True
                if "propertyNames" in s:
                    self._v(k, s["propertyNames"], f"{p}.<key {k!r}>", errs)
                if not matched and "additionalProperties" in s:
                    ap = s["additionalProperties"]
                    if ap is False:
                        errs.append(f"{p}: additional property {k!r} not allowed")
                    elif ap is not True:
                        self._v(v, ap, f"{p}.{k}", errs)

        for kw in ("allOf",):
            for i, sub in enumerate(s.get(kw, [])):
                self._v(x, sub, f"{p}/allOf[{i}]", errs)
        if "anyOf" in s and not any(self._ok(x, sub) for sub in s["anyOf"]):
            errs.append(f"{p}: matches none of anyOf")
        if "oneOf" in s:
            n = sum(1 for sub in s["oneOf"] if self._ok(x, sub))
            if n != 1:
                errs.append(f"{p}: matches {n} of oneOf (must be exactly 1)")
        if "not" in s and self._ok(x, s["not"]):
            errs.append(f"{p}: matches 'not' schema")

    def _ok(self, x, s):
        e = []
        self._v(x, s, "$", e)
        return not e


def validate(instance, schema):
    return Validator(schema).validate(instance)
