"""Integrity-checked business/fixture catalogs and exact version-scoped lookup."""
import copy
import hashlib
from .contracts import canonical, fail, identifier, integer, obj, origin, product_family, scope, strict_json, text
from .paths import real_path

MAX_CATALOG_FILE_BYTES = 16 * 1024 * 1024


class Dataset:
    def __init__(self, root):
        self.root = real_path(root)
        raw_manifest = self._read("manifest.json")
        self.manifest = strict_json(raw_manifest.decode("utf-8"))
        obj(self.manifest, ("data_version", "synthetic", "purpose", "created_date", "provenance", "model_count", "scope_count", "review_count", "fact_count", "files"))
        self.version = identifier(self.manifest["data_version"], "data_version")
        if type(self.manifest["synthetic"]) is not bool or self.manifest["purpose"] != ("test_only" if self.manifest["synthetic"] else "business"):
            fail("invalid_dataset", "Synthetic fixtures must be test_only; real sources must be business")
        self.synthetic = self.manifest["synthetic"]
        self.files = {}
        for entry in self.manifest["files"]:
            obj(entry, ("path", "sha256"))
            name = entry["path"]
            if name not in ("models.json", "sources.jsonl") or name in self.files:
                fail("invalid_dataset", "Unexpected or duplicate catalog file")
            content = self._read(name)
            if hashlib.sha256(content).hexdigest() != entry["sha256"]:
                fail("dataset_integrity", f"File fingerprint mismatch: {name}")
            self.files[name] = content
        if set(self.files) != {"models.json", "sources.jsonl"}:
            fail("invalid_dataset", "Both catalog files are required")
        self.fingerprint = hashlib.sha256(raw_manifest + b"\0" + self.files["models.json"] + b"\0" + self.files["sources.jsonl"]).hexdigest()
        self.models = strict_json(self.files["models.json"].decode("utf-8"))
        if not isinstance(self.models, list) or not 0 <= len(self.models) <= 20:
            fail("invalid_dataset", "Invalid model catalog")
        self.scopes = set()
        for model in self.models:
            obj(model, ("model_id", "model_version", "document_version", "name", "product_family", "synthetic"), ("dimensions_mm", "capacity_l", "layout", "spec_source_id", "identity_review"))
            exact = {k: model[k] for k in ("model_id", "model_version", "document_version")}
            scope(exact)
            product_family(model["product_family"])
            if model["synthetic"] is not self.synthetic:
                fail("invalid_dataset", "Invalid model provenance/family")
            text(model["name"], "model name", 200)
            key = canonical(exact)
            if key in self.scopes:
                fail("invalid_dataset", "Duplicate model/version/document scope")
            self.scopes.add(key)
        self.sources = {}
        for number, line in enumerate(self.files["sources.jsonl"].decode("utf-8").splitlines(), 1):
            record = strict_json(line)
            obj(record, ("source_id", "kind", "model_id", "model_version", "document_version", "data_version", "location", "text", "synthetic", "sha256", "origin"), ("feature_key", "availability"))
            identifier(record["source_id"], "source_id")
            if record["source_id"] in self.sources:
                fail("invalid_dataset", "Duplicate source_id")
            self.check_scope({k: record[k] for k in ("model_id", "model_version", "document_version")})
            text(record["text"], "source text", 4000)
            text(record["location"], "source location", 200)
            if record["synthetic"] is not self.synthetic or record["data_version"] != self.version:
                fail("invalid_dataset", "Source provenance/version mismatch")
            origin(record["origin"], self.synthetic)
            if record["kind"] == "review" and not self.synthetic and record["origin"]["representation"] != "excerpt":
                fail("invalid_dataset", "Real customer review needs an observed excerpt, not an AI summary")
            if hashlib.sha256(record["text"].encode("utf-8")).hexdigest() != record["sha256"]:
                fail("dataset_integrity", f"Source text fingerprint mismatch on line {number}")
            if record["kind"] == "product_fact":
                identifier(record.get("feature_key"), "feature_key")
                if record.get("availability") not in ("present", "explicitly_absent"):
                    fail("invalid_dataset", "Invalid explicit feature fact")
            elif record["kind"] != "review" or "feature_key" in record or "availability" in record:
                fail("invalid_dataset", "Invalid source kind/fields")
            self.sources[record["source_id"]] = record
        for model in self.models:
            if "dimensions_mm" in model:
                dimensions = obj(model["dimensions_mm"], ("width", "height", "depth"))
                for key, value in dimensions.items():
                    integer(value, "dimension " + key, 1, 10000)
            if "capacity_l" in model:
                integer(model["capacity_l"], "capacity_l", 1, 10000)
            if "layout" in model:
                layout = obj(model["layout"], ("door_count", "arrangement", "internal_dimensions_mm", "shelf_spacing_mm"))
                integer(layout["door_count"], "door_count", 1, 10)
                text(layout["arrangement"], "arrangement", 200)
                if layout["internal_dimensions_mm"] is not None:
                    for key, value in obj(layout["internal_dimensions_mm"], ("width", "height", "depth")).items():
                        integer(value, "internal " + key, 1, 10000)
                if layout["shelf_spacing_mm"] is not None:
                    from .contracts import items
                    for spacing in items(layout["shelf_spacing_mm"], "shelf spacing", 20):
                        integer(spacing, "shelf spacing", 1, 10000)
            if any(k in model for k in ("dimensions_mm", "capacity_l", "layout", "spec_source_id", "identity_review")):
                source = self.source(model.get("spec_source_id"))
                if source["kind"] != "product_fact" or any(source[k] != model[k] for k in ("model_id", "model_version", "document_version")):
                    fail("invalid_dataset", "Model specification source must match exact scope")
            if "identity_review" in model:
                review = obj(model["identity_review"], ("source_id", "manufacturer", "authority", "rationale"))
                if review["source_id"] != model["spec_source_id"] or review["authority"] != "manufacturer":
                    fail("invalid_dataset", "Identity review must declare its matching manufacturer source")
                text(review["manufacturer"], "manufacturer", 200)
                text(review["rationale"], "identity rationale", 2000)
        counts = {"model_count": len({m["model_id"] for m in self.models}), "scope_count": len(self.models),
                  "review_count": sum(s["kind"] == "review" for s in self.sources.values()),
                  "fact_count": sum(s["kind"] == "product_fact" for s in self.sources.values())}
        for key, count in counts.items():
            integer(self.manifest[key], key, 0, 1000)
            if self.manifest[key] != count:
                fail("invalid_dataset", f"Manifest count mismatch: {key}")

    def _read(self, name):
        path = real_path(self.root / name)
        if not path.is_relative_to(self.root) or not path.is_file():
            fail("invalid_dataset", "Catalog path escapes dataset")
        if path.stat().st_size > MAX_CATALOG_FILE_BYTES:
            fail("dataset_limit", "Catalog file exceeds 16 MiB")
        return path.read_bytes()

    def check_scope(self, exact):
        scope(exact)
        if canonical(exact) not in self.scopes:
            known = {m["model_id"] for m in self.models}
            fail("unknown_model" if exact["model_id"] not in known else "unknown_scope", "Unknown model/version/document combination")
        return exact

    def check_input(self, planning):
        if planning["data_version"] != self.version:
            fail("data_version_mismatch", "Input data version differs from loaded catalog")
        for exact in planning["model_scope"]:
            self.check_scope(exact)
            model = next(m for m in self.models if all(m[k] == exact[k] for k in exact))
            if model["product_family"] != planning["product_family"]:
                fail("family_mismatch", "Planning family differs from the exact catalog model")

    def source(self, source_id):
        identifier(source_id, "source_id")
        if source_id not in self.sources:
            fail("source_not_found", f"Unknown source_id: {source_id}")
        return copy.deepcopy(self.sources[source_id])

    def reference(self, record):
        return {**{key: record[key] for key in ("source_id", "model_id", "model_version", "document_version", "data_version", "location", "sha256", "synthetic", "origin")}, "quote": record["text"]}

    def retrieve(self, kind, exact, query="", limit=12, feature_key=None, offset=0):
        self.check_scope(exact)
        if kind not in ("review", "product_fact"):
            fail("invalid_input", "Unknown retrieval kind")
        integer(limit, "limit", 1, 20)
        integer(offset, "offset", 0, 1000000)
        if not isinstance(query, str) or len(query) > 200:
            fail("invalid_input", "query must be a string <= 200 characters")
        if feature_key is not None:
            identifier(feature_key, "feature_key")
        found = [s for s in self.sources.values() if s["kind"] == kind and all(s[k] == v for k, v in exact.items())
                 and query.casefold() in s["text"].casefold() and (feature_key is None or s.get("feature_key") == feature_key)]
        documented = [s for s in self.sources.values() if s["kind"] == "product_fact" and all(s[k] == v for k, v in exact.items()) and s.get("feature_key") == feature_key]
        presence = {s["availability"] for s in documented}
        return {"data_version": self.version, "dataset_fingerprint": self.fingerprint, "scope": exact,
                "status": "found" if found else "empty", "total": len(found), "truncated": len(found) > offset+limit,
                "offset": offset, "next_offset": offset+limit if len(found) > offset+limit else None,
                "records": [{**copy.deepcopy(s), "content_trust": "untrusted_source_data"} for s in found[offset:offset+limit]],
                "feature_presence": ("conflicting" if len(presence) > 1 else next(iter(presence)) if presence else "not_documented") if kind == "product_fact" and feature_key else None,
                "semantic_status": "unverified", "synthetic": self.synthetic, "purpose": self.manifest["purpose"]}
