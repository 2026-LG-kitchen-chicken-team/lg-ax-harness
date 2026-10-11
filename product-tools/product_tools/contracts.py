"""Strict shared contracts; references/claims still need semantic review."""
import hashlib
import json
import re

CONTRACT_VERSION = "product-contract-v1"
DEFAULT_DATA_PATH = "data/business/lg-kitchen-v4"
MAX_BYTES = 65536
MAX_PLANNING_BYTES = 12288
MAX_RESULT_BYTES = 32768

class ToolError(ValueError):
    def __init__(self, code, message):
        super().__init__(message[:512])
        self.code = code

def fail(code, message):
    raise ToolError(code, message)

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def fingerprint(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()

def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                fail("invalid_json", f"Duplicate JSON key: {key}")
            result[key] = value
        return result
    def nonfinite(value):
        fail("invalid_json", f"Non-finite number: {value}")
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (json.JSONDecodeError, RecursionError) as exc:
        fail("invalid_json", str(exc))

def decode_json_bytes(raw):
    """Accept explicit Windows Unicode BOMs, never guess an ANSI encoding."""
    if len(raw) > MAX_BYTES:
        fail("input_limit", "Input exceeds 64 KiB")
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    try:
        value = raw.decode(encoding)
    except UnicodeError as exc:
        fail("invalid_json", "Expected UTF-8 or BOM-marked UTF-16 JSON: " + str(exc))
    if len(value.encode("utf-8")) > MAX_BYTES:
        fail("input_limit", "Decoded input exceeds 64 KiB")
    return value

def obj(value, required, optional=()):
    if not isinstance(value, dict):
        fail("invalid_input", "Expected JSON object")
    missing, extra = set(required) - value.keys(), value.keys() - set(required) - set(optional)
    if missing or extra:
        fail("invalid_input", f"Missing fields: {sorted(missing)}; unknown fields: {sorted(extra)}")
    return value

def text(value, name, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        fail("invalid_input", f"{name} must be a nonempty string <= {maximum} characters")
    return value

def identifier(value, name):
    text(value, name, 96)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", value):
        fail("invalid_input", f"Invalid {name}")
    return value

def integer(value, name, low=0, high=1000000000):
    if type(value) is not int or not low <= value <= high:
        fail("invalid_input", f"{name} must be integer in [{low}, {high}]")
    return value

def items(value, name, maximum=20):
    if not isinstance(value, list) or len(value) > maximum:
        fail("invalid_input", f"{name} must be an array with <= {maximum} items")
    return value

SCOPE_FIELDS = ("model_id", "model_version", "document_version")
PRODUCT_FAMILIES = ("refrigerator", "microwave", "dishwasher")

def scope(value):
    obj(value, SCOPE_FIELDS)
    for field in SCOPE_FIELDS:
        identifier(value[field], field)
    return value

def planning_input(value):
    obj(value, ("session_id", "request_key", "question", "product_family", "model_scope", "target_customer", "context",
                "constraints", "data_version", "runtime", "workflow"), ("scope_mode",))
    for field in ("session_id", "request_key", "data_version"):
        identifier(value[field], field)
    for field in ("question", "target_customer", "context"):
        text(value[field], field)
    if value["product_family"] not in PRODUCT_FAMILIES:
        fail("unsupported_family", "Supported families: refrigerator, microwave, dishwasher")
    scopes = items(value["model_scope"], "model_scope", 5)
    if not scopes:
        fail("needs_input", "At least one exact model/version/document scope is required")
    for model in scopes:
        scope(model)
    if len({canonical(s) for s in scopes}) != len(scopes):
        fail("invalid_input", "Duplicate model scope")
    if value.get("scope_mode", "exact_model") not in ("exact_model", "family_catalog"):
        fail("invalid_input", "scope_mode must be exact_model or family_catalog")
    if value.get("scope_mode") == "exact_model" and len(scopes) != 1:
        fail("invalid_input", "An exact-model request selects one snapshot")
    constraints = obj(value["constraints"], ("max_concepts", "hardware_allowed", "exclude_pains"))
    integer(constraints["max_concepts"], "max_concepts", 1, 3)
    if type(constraints["hardware_allowed"]) is not bool:
        fail("invalid_input", "hardware_allowed must be boolean")
    for pain in items(constraints["exclude_pains"], "exclude_pains"):
        text(pain, "excluded pain", 200)
    runtime = obj(value["runtime"], ("engine", "engine_version", "model_id", "settings_fingerprint"))
    if runtime["engine"] not in (None, "codex", "claude", "fixture"):
        fail("invalid_input", "Unknown runtime engine")
    for key in ("engine_version", "model_id", "settings_fingerprint"):
        if runtime[key] is not None:
            text(runtime[key], key, 200)
    workflow = obj(value["workflow"], ("rules_version", "skill_fingerprint", "prompt_fingerprint"))
    identifier(workflow["rules_version"], "rules_version")
    for key in ("skill_fingerprint", "prompt_fingerprint"):
        if workflow[key] is not None:
            text(workflow[key], key, 200)
    if len(canonical(value).encode("utf-8")) > MAX_PLANNING_BYTES:
        fail("input_limit", "Planning input exceeds 12 KiB")
    return value

REF_FIELDS = ("source_id", *SCOPE_FIELDS, "data_version", "location", "sha256", "synthetic", "quote", "origin")

def origin(value, synthetic):
    from datetime import date
    obj(value, ("source_url", "retrieved_date", "published_date", "representation", "model_matching", "purchase_verified", "sponsorship"), ("commercial_disclosure",))
    if value.get("commercial_disclosure") is not None:
        text(value["commercial_disclosure"], "commercial_disclosure", 500)
    for key in ("retrieved_date", "published_date"):
        if value[key] is not None and (not isinstance(value[key], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value[key])):
            fail("invalid_input", "Source dates must be ISO dates or null")
        if value[key] is not None:
            try:
                date.fromisoformat(value[key])
            except ValueError:
                fail("invalid_input", "Invalid calendar date")
    if value["retrieved_date"] is None:
        fail("invalid_input", "Source observation date is required")
    for key in ("purchase_verified", "sponsorship"):
        if value[key] is not None and type(value[key]) is not bool:
            fail("invalid_input", f"{key} must be boolean or null")
    if synthetic:
        if value["source_url"] is not None or value["representation"] != "synthetic" or value["model_matching"] != "fictional":
            fail("invalid_input", "Synthetic origin must be explicit")
    else:
        from urllib.parse import urlparse
        if not isinstance(value["source_url"], str) or len(value["source_url"]) > 2000:
            fail("invalid_input", "Real source needs a URL")
        url = urlparse(value["source_url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            fail("invalid_input", "Real source must have a public HTTPS URL without credentials")
        if value["representation"] not in ("excerpt", "factual_summary") or value["model_matching"] not in ("product_page_association", "explicit_model_verified"):
            fail("invalid_input", "Real source representation/model matching must be explicit")
    return value

def evidence_ref(value):
    obj(value, REF_FIELDS)
    for key in ("source_id", *SCOPE_FIELDS, "data_version"):
        identifier(value[key], key)
    text(value["location"], "location", 200)
    text(value["quote"], "quote", 4000)
    if not isinstance(value["sha256"], str) or not re.fullmatch(r"[a-f0-9]{64}", value["sha256"]):
        fail("invalid_input", "sha256 must be 64 lowercase hex characters")
    if type(value["synthetic"]) is not bool:
        fail("invalid_input", "synthetic must be boolean")
    origin(value["origin"], value["synthetic"])
    return value

def claim(value, concept=False):
    obj(value, ("id", "text", "source_ids") + (("requirements", "requires_hardware", "assumptions") if concept else ()),
        ("implementation_steps", "validation_plan") if concept else ())
    identifier(value["id"], "claim id")
    text(value["text"], "claim text")
    refs = items(value["source_ids"], "source_ids")
    for ref in refs:
        identifier(ref, "source_id")
    if not refs or len(set(refs)) != len(refs):
        fail("invalid_input", "Each claim needs unique nonempty source_ids")
    if concept:
        if type(value["requires_hardware"]) is not bool:
            fail("invalid_input", "requires_hardware must be boolean")
        for key in ("requirements", "assumptions"):
            for item in items(value[key], key, 10):
                text(item, key, 1000)
        if not value["requirements"]:
            fail("invalid_input", "A concept needs at least one requirement")
        if "implementation_steps" in value:
            steps = items(value["implementation_steps"], "implementation_steps", 8)
            if not steps:
                fail("invalid_input", "Implementation steps cannot be empty")
            for step in steps:
                text(step, "implementation step", 1000)
        if "validation_plan" in value:
            plan = obj(value["validation_plan"], ("metric", "baseline", "method", "success_criterion", "business_value", "status"))
            for key in ("metric", "baseline", "method", "success_criterion", "business_value"):
                text(plan[key], key, 1000)
            if plan["status"] != "planned_not_measured":
                fail("invalid_input", "Model-authored validation plans cannot certify measured effects")

def product_result(value, planning):
    obj(value, ("status", "pains", "existing_features", "remaining_pains", "concepts", "assumptions", "evidence_refs", "validation_findings", "revisions", "usage_summary"))
    if value["status"] not in ("completed", "needs_input", "held", "failed", "cancelled"):
        fail("invalid_input", "Unknown result status")
    integer(value["revisions"], "revisions", 0, 2)
    ids = []
    for key in ("pains", "existing_features", "remaining_pains", "concepts"):
        for record in items(value[key], key, planning["constraints"]["max_concepts"] if key == "concepts" else 20):
            claim(record, concept=key == "concepts")
            ids.append(record["id"])
    if len(set(ids)) != len(ids):
        fail("invalid_input", "Claim IDs must be unique across result sections")
    if value["status"] == "completed" and not value["concepts"]:
        fail("invalid_input", "Completed proposal requires at least one concept")
    for key in ("assumptions", "validation_findings"):
        for item in items(value[key], key):
            text(item, key)
    if value["status"] != "completed" and not value["validation_findings"]:
        fail("invalid_input", "Non-completed result requires reasons")
    for ref in items(value["evidence_refs"], "evidence_refs", 40):
        evidence_ref(ref)
    if not planning["constraints"]["hardware_allowed"] and any(c["requires_hardware"] for c in value["concepts"]):
        fail("constraint_violation", "Hardware is excluded by planning input")
    summary = obj(value["usage_summary"], ("status",))
    if summary["status"] != "unknown":
        fail("invalid_input", "Result must not self-certify usage; record observed calls separately")
    if len(canonical(value).encode("utf-8")) > MAX_RESULT_BYTES:
        fail("input_limit", "Result exceeds 32 KiB")
    return value
