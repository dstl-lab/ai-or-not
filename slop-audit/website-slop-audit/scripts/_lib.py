"""Shared helpers for the website-slop-audit scripts. Standard library only.

The scripts must run in hosts that cannot install packages (some skill
sandboxes have no network), so this module includes a small JSON Schema
validator covering exactly the keywords the bundled schemas use.
SUPPORTED_KEYWORDS lists them; tests check that every schema stays inside
that subset and that results agree with the reference `jsonschema` package.
"""

import hashlib
import json
import re
import struct
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = SKILL_ROOT / "schemas"
ASSET_DIR = SKILL_ROOT / "assets"

SUPPORTED_KEYWORDS = {
    "$schema", "$id", "$defs", "$ref", "title", "description", "$comment",
    "type", "properties", "required", "additionalProperties", "enum", "const",
    "items", "minItems", "maxItems", "uniqueItems", "minimum", "maximum",
    "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength", "pattern", "anyOf",
}

LEVEL_ORDER = {"none": 0, "weak": 1, "moderate": 2, "strong": 3}


class UsageError(Exception):
    """Bad input files or arguments; the message says what to fix."""


# --- files and hashing -------------------------------------------------------

def load_json(path):
    path = Path(path)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise UsageError(f"{path}: file not found") from None
    except json.JSONDecodeError as err:
        raise UsageError(f"{path}: not valid JSON ({err})") from None


def canonical_json(obj):
    """Deterministic bytes for hashing: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def image_size(path):
    """(width, height) of a PNG or JPEG file, read from its header."""
    data = Path(path).read_bytes()
    if data[:8] == b"\x89PNG\r\n\x1a\n" and data[12:16] == b"IHDR":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                height, width = struct.unpack(">HH", data[i + 5:i + 9])
                return width, height
            i += 2 + length
    raise UsageError(f"{path}: not a readable PNG or JPEG image")


# --- schema validation (subset) ---------------------------------------------

_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _resolve(ref, root):
    if not ref.startswith("#/"):
        raise UsageError(f"unsupported $ref {ref!r} (only local #/ refs)")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def schema_errors(instance, schema, root=None, path="$"):
    """List of 'path: message' strings; empty when the instance is valid."""
    root = root if root is not None else schema
    errors = []
    if "$ref" in schema:
        errors += schema_errors(instance, _resolve(schema["$ref"], root), root, path)
    if "anyOf" in schema:
        branches = [schema_errors(instance, s, root, path) for s in schema["anyOf"]]
        if all(branches):
            errors.append(f"{path}: does not match any allowed form ({branches[0][0]})")
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPE_CHECKS[t](instance) for t in types):
            return errors + [f"{path}: expected {'/'.join(types)}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} is not one of {schema['enum']}")
    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than {schema['minLength']} characters")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: longer than {schema['maxLength']} characters")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']}")
    if _TYPE_CHECKS["number"](instance):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: must be greater than {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and instance >= schema["exclusiveMaximum"]:
            errors.append(f"{path}: must be less than {schema['exclusiveMaximum']}")
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: needs at least {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: allows at most {schema['maxItems']} items")
        if schema.get("uniqueItems"):
            seen = [canonical_json(x) for x in instance]
            if len(set(seen)) != len(seen):
                errors.append(f"{path}: items must be unique")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors += schema_errors(item, schema["items"], root, f"{path}[{i}]")
    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required field {key!r}")
        for key, value in instance.items():
            if key in props:
                errors += schema_errors(value, props[key], root, f"{path}.{key}")
            elif "additionalProperties" in schema:
                extra = schema["additionalProperties"]
                if extra is False:
                    errors.append(f"{path}: unexpected field {key!r}")
                elif isinstance(extra, dict):
                    errors += schema_errors(value, extra, root, f"{path}.{key}")
    return errors


def unsupported_keywords(schema, path="$"):
    """Keywords outside SUPPORTED_KEYWORDS (property names are not keywords)."""
    found = []
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key not in SUPPORTED_KEYWORDS:
                found.append(f"{path}.{key}")
            if key in ("properties", "$defs"):
                for name, sub in value.items():
                    found += unsupported_keywords(sub, f"{path}.{key}.{name}")
            elif key in ("items", "additionalProperties") and isinstance(value, dict):
                found += unsupported_keywords(value, f"{path}.{key}")
            elif key == "anyOf":
                for i, sub in enumerate(value):
                    found += unsupported_keywords(sub, f"{path}.anyOf[{i}]")
    return found


def load_schema(name):
    return load_json(SCHEMA_DIR / name)


# --- codebook, profiles, bundles ---------------------------------------------

def load_codebook():
    return load_json(ASSET_DIR / "codebook.json")


def load_profiles():
    return load_json(ASSET_DIR / "profiles.json")


def features_by_id(codebook=None):
    codebook = codebook or load_codebook()
    return {f["id"]: f for f in codebook["features"]}


def profile(profile_id, profiles=None):
    profiles = profiles or load_profiles()
    try:
        return profiles["analysis_profiles"][profile_id]
    except KeyError:
        known = ", ".join(sorted(profiles["analysis_profiles"]))
        raise UsageError(f"unknown analysis profile {profile_id!r}; choose one of: {known}") from None


def profile_features(profile_id, codebook=None):
    """Codebook features that belong to the profile's modules, in codebook order."""
    modules = set(profile(profile_id)["modules"])
    codebook = codebook or load_codebook()
    return [f for f in codebook["features"] if f["module"] in modules]


def available_modalities(manifest, profile_id):
    """Modalities the auditor may use: present in the bundle AND allowed by the profile."""
    present = {m for m, on in manifest["modalities"].items() if on}
    if profile(profile_id)["capability"] == "text_only":
        present.discard("screenshot")
    return present


def feature_assessable(feature, modalities):
    """True if at least one of the feature's modality sets is fully available."""
    return any(set(s) <= modalities for s in feature["modality_sets"])


def bundle_hash(manifest):
    """Hash of the canonical manifest. Asset files are covered through their listed sha256."""
    return sha256_bytes(canonical_json(manifest))


class Bundle:
    """A capture bundle on disk with lookup tables by id."""

    def __init__(self, directory):
        self.dir = Path(directory)
        if self.dir.is_file():
            self.dir = self.dir.parent
        self.manifest = load_json(self.dir / "manifest.json")
        m = self.manifest
        self.assets = {a["asset_id"]: a for a in m.get("assets", [])}
        self.states = {s["state_id"]: s for s in m.get("states", [])}
        self.regions = {r["region_id"]: r for r in m.get("regions", [])}
        self.spans = {t["span_id"]: t for t in m.get("text_spans", [])}
        self.elements = {e["element_id"]: e for e in m.get("dom_elements", [])}
        self.events = {e["event_id"]: e for e in m.get("interactions", [])}
        self.excerpts = {x["excerpt_id"]: x for x in m.get("source_excerpts", [])}
        self.viewports = {v["viewport_id"]: v for v in m.get("viewports", [])}

    @property
    def bundle_id(self):
        return self.manifest.get("bundle_id")

    @property
    def hash(self):
        return bundle_hash(self.manifest)

    def selectors(self, state_id=None):
        return {e["selector"] for e in self.elements.values() if state_id in (None, e["state_id"])}


# --- reporting -------------------------------------------------------------

class Report:
    """Collects coded errors and warnings so scorers can count error kinds."""

    def __init__(self, label):
        self.label = label
        self.errors = []    # (code, message)
        self.warnings = []

    def error(self, code, message):
        self.errors.append((code, message))

    def warn(self, code, message):
        self.warnings.append((code, message))

    @property
    def ok(self):
        return not self.errors

    def as_dict(self):
        return {
            "target": self.label,
            "valid": self.ok,
            "errors": [{"code": c, "message": m} for c, m in self.errors],
            "warnings": [{"code": c, "message": m} for c, m in self.warnings],
        }

    def print(self, stream=sys.stdout):
        verdict = "VALID" if self.ok else "INVALID"
        print(f"{verdict}: {self.label} ({len(self.errors)} error(s), {len(self.warnings)} warning(s))", file=stream)
        for code, msg in self.errors:
            print(f"  error [{code}] {msg}", file=stream)
        for code, msg in self.warnings:
            print(f"  warning [{code}] {msg}", file=stream)


def normalize_space(text):
    return re.sub(r"\s+", " ", text or "").strip()


def run_main(main):
    """Run a script's main(), turning UsageError into a clean exit code 2."""
    try:
        sys.exit(main())
    except UsageError as err:
        print(f"error: {err}", file=sys.stderr)
        sys.exit(2)
