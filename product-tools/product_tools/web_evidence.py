"""Bounded public-page collection and versioned import. No search engine or LLM."""
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import build_opener, HTTPRedirectHandler, ProxyHandler, Request
from .contracts import canonical, fail, fingerprint, identifier, items, obj, strict_json, text
from .dataset import Dataset

ALLOWED_HOSTS = {"www.lge.co.kr", "static.lge.co.kr", "gscs-b2c.lge.com", "gscs-manual.lge.com", "min-inter.co.kr"}
MAX_PAGE_BYTES = 2097152


def check_manual_section(url, content, location=None):
    """Bind explicit section markers; never infer a source URL from text."""
    parsed = urlparse(url)
    if (parsed.hostname != "gscs-manual.lge.com"
            or not re.fullmatch(r"/CNZ/MFL[0-9]+/ko-kr/main\.html", parsed.path)):
        return
    marker = r"(?<![A-Za-z0-9_])topic_[0-9]+(?![A-Za-z0-9_])"
    topics = set(re.findall(marker, content))
    if location is not None:
        text(location, "location", 500)
        located = set(re.findall(marker, location))
        if not parsed.fragment or located != {parsed.fragment}:
            fail("section_mismatch", "Manual location must name only its observed URL topic; capture each section separately")
        topics.update(located)
    if topics and topics != {parsed.fragment}:
        fail("section_mismatch", "Do not combine manual topics under one URL; use separate observed section snapshots")


def public_url(value):
    text(value, "url", 2000)
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        fail("unsupported_url", "Malformed source URL/port")
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS or parsed.username is not None or parsed.password is not None or port not in (None, 443):
        fail("unsupported_url", "Use an approved HTTPS source host without credentials/custom ports")
    return value


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "head", "template"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "head", "template") and self.hidden:
            self.hidden -= 1
        elif not self.hidden:
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


class WebEvidence:
    def __init__(self, db, workspace):
        self.workspace = Path(workspace).resolve()
        self.base = (self.workspace / "runtime-data/web-evidence").resolve()
        if not self.base.is_relative_to(self.workspace / "runtime-data"):
            fail("invalid_path", "Web snapshots must stay in runtime-data")
        self.base.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db, timeout=5)
        self.db.execute("CREATE TABLE IF NOT EXISTS web_pages (research_id TEXT, page_id TEXT, request_hash TEXT, attempts INTEGER, retryable INTEGER, snapshot_id TEXT, PRIMARY KEY(research_id,page_id))")
        self.db.commit()

    def close(self):
        self.db.close()

    def _reserve(self, payload, mode):
        identifier(payload["research_id"], "research_id")
        identifier(payload["page_id"], "page_id")
        public_url(payload["url"])
        key = fingerprint({"mode": mode, **payload})
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT request_hash,attempts,retryable,snapshot_id FROM web_pages WHERE research_id=? AND page_id=?", (payload["research_id"], payload["page_id"])).fetchone()
            if row:
                if row[0] != key:
                    fail("request_conflict", "Same page ID cannot refer to changed content/URL")
                if row[3]:
                    return self._read(row[3]), True
                if row[1] >= 2 or not row[2]:
                    fail("research_limit", "Page exhausted its first attempt and at most one transient retry")
                self.db.execute("UPDATE web_pages SET attempts=attempts+1,retryable=0 WHERE research_id=? AND page_id=?", (payload["research_id"], payload["page_id"]))
            else:
                count = self.db.execute("SELECT COUNT(*) FROM web_pages WHERE research_id=?", (payload["research_id"],)).fetchone()[0]
                if count >= 6:
                    fail("research_limit", "A research ID can collect at most six pages")
                self.db.execute("INSERT INTO web_pages VALUES (?,?,?,1,0,NULL)", (payload["research_id"], payload["page_id"], key))
        return None, False

    def _read(self, snapshot_id):
        identifier(snapshot_id, "snapshot_id")
        path = (self.base / (snapshot_id + ".json")).resolve(strict=True)
        if path.parent != self.base or path.stat().st_size > 262144:
            fail("invalid_path", "Invalid snapshot path/size")
        value = strict_json(path.read_text(encoding="utf-8"))
        if value["snapshot_id"] != snapshot_id or fingerprint({k: v for k, v in value.items() if k != "snapshot_id"}) != snapshot_id:
            fail("snapshot_integrity", "Snapshot fingerprint mismatch")
        return value

    def collect(self, payload, browser=False):
        obj(payload, ("research_id", "page_id", "url") + (("observed_text", "native_tool_name") if browser else ()), ("focus", "preview_chars"))
        preview_chars = payload.get("preview_chars", 4000)
        if type(preview_chars) is not int or not 256 <= preview_chars <= 4000:
            fail("invalid_input", "preview_chars must be an integer from 256 to 4000")
        if "focus" in payload:
            text(payload["focus"], "focus", 200)
        public_url(payload["url"])
        if browser:
            text(payload["observed_text"], "observed_text", 16000)
            text(payload["native_tool_name"], "native_tool_name", 100)
            check_manual_section(payload["url"], payload["observed_text"])
        elif urlparse(payload["url"]).hostname == "gscs-manual.lge.com" and urlparse(payload["url"]).fragment:
            fail("unsupported_content", "HTTP does not select manual hash topics; capture the actual native section body")
        # Presentation size does not change the observed source or page identity.
        collection_payload = {k: v for k, v in payload.items() if k != "preview_chars"}
        cached, reused = self._reserve(collection_payload, "browser" if browser else "http")
        if reused:
            return self._summary(cached, True, preview_chars, payload.get("focus"))
        try:
            if browser:
                content = payload["observed_text"]
                origin = "caller_reported_native_page_tool; tool name is not proof of execution"
            else:
                request = Request(payload["url"], headers={"User-Agent": "LG-AX-evidence/0.1", "Accept-Encoding": "identity"})
                opener = build_opener(ProxyHandler({}), NoRedirect())
                with opener.open(request, timeout=8) as response:
                    if response.headers.get("Content-Encoding", "identity") != "identity":
                        fail("unsupported_content", "Compressed response not supported by this bounded collector")
                    content_type = response.headers.get_content_type()
                    if content_type not in ("text/html", "text/plain"):
                        fail("unsupported_content", "Use an available native PDF/browser tool for other content types")
                    raw = response.read(MAX_PAGE_BYTES + 1)
                    if len(raw) > MAX_PAGE_BYTES:
                        fail("page_limit", "Page exceeds 2 MiB")
                    decoded = raw.decode(response.headers.get_content_charset() or "utf-8", errors="strict")
                    if content_type == "text/html":
                        parser = VisibleText()
                        parser.feed(decoded)
                        content = " ".join(" ".join(parser.parts).split())
                    else:
                        content = decoded
                origin = "http_observed_visible_text"
            if not content.strip():
                fail("empty_page", "Page had no usable text; a dynamic page may need a native browser")
            start = 0
            if "focus" in payload:
                position = content.find(payload["focus"])
                if position < 0:
                    fail("focus_not_found", "Requested literal text is absent; try an available native browser or hold")
                start = max(0, position - 1000)
            truncated = start > 0 or len(content) > 16000
            value = {"url": payload["url"], "observed_at": datetime.now(timezone.utc).isoformat(),
                     "text": content[start:start + 16000], "text_start": start, "truncated": truncated, "collection": origin,
                     "content_trust": "untrusted_source_data", "semantic_status": "unverified"}
            snapshot_id = fingerprint(value)
            value["snapshot_id"] = snapshot_id
            (self.base / (snapshot_id + ".json")).write_text(canonical(value), encoding="utf-8")
            with self.db:
                self.db.execute("UPDATE web_pages SET snapshot_id=? WHERE research_id=? AND page_id=?", (snapshot_id, payload["research_id"], payload["page_id"]))
            return self._summary(value, False, preview_chars, payload.get("focus"))
        except (HTTPError, URLError, TimeoutError) as exc:
            transient = isinstance(exc, (URLError, TimeoutError)) and not isinstance(exc, HTTPError) or isinstance(exc, HTTPError) and exc.code in (408, 429, 500, 502, 503, 504)
            attempts = self.db.execute("SELECT attempts FROM web_pages WHERE research_id=? AND page_id=?",
                                       (payload["research_id"], payload["page_id"])).fetchone()[0]
            retryable = bool(transient and attempts < 2)
            with self.db:
                self.db.execute("UPDATE web_pages SET retryable=? WHERE research_id=? AND page_id=?", (int(retryable), payload["research_id"], payload["page_id"]))
            return {"status": "unavailable", "retryable": retryable, "attempts": attempts,
                    "technical_retries_remaining": 1 if retryable else 0,
                    "reason": "http_" + str(exc.code) if isinstance(exc, HTTPError) else "network_error",
                    "semantic_status": "unverified", "next_action": "one bounded retry" if retryable else "held or a separately authorized native browser observation; do not reset this page ID"}

    @staticmethod
    def _summary(value, cached, preview_chars=4000, focus=None):
        position = value["text"].find(focus) if focus else -1
        context_chars = min(200, preview_chars - len(focus)) if focus else 200
        start = max(0, position - context_chars) if position >= 0 else 0
        preview = value["text"][start:start + preview_chars]
        return {**{k: v for k, v in value.items() if k != "text"}, "text_preview": preview,
                "preview_start": start, "preview_truncated": start > 0 or start + len(preview) < len(value["text"]),
                "snapshot_path": "runtime-data/web-evidence/" + value["snapshot_id"] + ".json", "cached": cached}

    def _check_manual_association(self, entry, snapshot, exact):
        association = self._read(entry["association_snapshot_id"])
        manual_url = urlparse(public_url(snapshot["url"]))
        product_url = urlparse(public_url(association["url"]))
        model = exact["model_id"]
        model_token = re.search(r"(?<![A-Za-z0-9])" + re.escape(model) + r"(?![A-Za-z0-9])", association["text"], re.IGNORECASE)
        observed_urls = {url.rstrip(")],.;") for url in re.findall(r"https?://[^\s<>\"']+", association["text"])}
        product_path = product_url.path.rstrip("/")
        is_product = product_path.casefold() in ("/product/refrigerators/" + model.casefold(), "/refrigerators/" + model.casefold())
        is_pdf = manual_url.hostname == "gscs-b2c.lge.com" and manual_url.path == "/open/downloadFile"
        is_html = (manual_url.hostname == "gscs-manual.lge.com"
                   and re.fullmatch(r"/CNZ/MFL[0-9]+/ko-kr/main\.html", manual_url.path) is not None
                   and not manual_url.query and (not manual_url.fragment or re.fullmatch(r"topic_[0-9]+", manual_url.fragment)))
        # Hash topics share the exact linked HTML document, not another manual.
        linked = snapshot["url"] in observed_urls or (is_html and manual_url._replace(fragment="").geturl() in observed_urls)
        # LG's exact PDP exposes an HTTP href; the manual itself is observed via
        # HTTPS. Preserve the literal href and match only the same document.
        # This does not permit HTTP collection or weaken TLS validation.
        if is_html and not linked:
            for observed in observed_urls:
                try:
                    parsed = urlparse(observed)
                    port = parsed.port
                except ValueError:
                    continue
                if (parsed.scheme == "http" and parsed.hostname == manual_url.hostname
                        and parsed.username is None and parsed.password is None and port in (None, 80)
                        and parsed.path == manual_url.path and not parsed.query and not parsed.fragment):
                    linked = True
                    break
        if (entry["kind"] != "product_fact" or entry["model_matching"] != "product_page_association"
                or not (is_pdf or is_html)
                or product_url.hostname != "www.lge.co.kr" or not is_product
                or not model_token or not linked):
            fail("scope_mismatch", "A generic manual needs the exact official product page model and the same observed manual link")

    def import_evidence(self, dataset, payload):
        obj(payload, ("data_version", "observations"))
        version = identifier(payload["data_version"], "data_version")
        if dataset.synthetic or version == dataset.version:
            fail("invalid_dataset", "Business import requires a new real dataset version")
        observations = items(payload["observations"], "observations", 10)
        if not observations:
            fail("invalid_input", "At least one observed source is required")
        records = [{**s, "data_version": version} for s in dataset.sources.values()]
        used = set(dataset.sources)
        for entry in observations:
            obj(entry, ("snapshot_id", "source_id", "kind", "scope", "location", "text", "support_quote", "published_date", "model_matching", "purchase_verified", "sponsorship"), ("feature_key", "availability", "commercial_disclosure", "association_snapshot_id"))
            exact = dataset.check_scope(entry["scope"])
            source_id = identifier(entry["source_id"], "source_id")
            if source_id in used:
                fail("invalid_dataset", "Import must add unique source IDs; existing snapshots are immutable")
            used.add(source_id)
            snapshot = self._read(entry["snapshot_id"])
            check_manual_section(snapshot["url"], snapshot["text"], entry["location"])
            text(entry["support_quote"], "support_quote", 4000)
            text(entry["text"], "source text", 4000)
            if entry["support_quote"] not in snapshot["text"]:
                fail("quote_mismatch", "Support quote is not in the observed snapshot")
            if "association_snapshot_id" in entry:
                self._check_manual_association(entry, snapshot, exact)
            elif exact["model_id"].casefold() not in (snapshot["text"] + " " + snapshot["url"]).casefold():
                fail("scope_mismatch", "Observed page must identify the selected model; option mixing still needs review")
            if entry["kind"] == "review" and entry["text"] != entry["support_quote"]:
                fail("quote_mismatch", "Customer review text must be an exact observed excerpt")
            representation = "excerpt" if entry["kind"] == "review" else "factual_summary"
            record = {"source_id": source_id, "kind": entry["kind"], **exact, "data_version": version,
                      "location": entry["location"], "text": entry["text"], "synthetic": False,
                      "sha256": hashlib.sha256(entry["text"].encode("utf-8")).hexdigest(),
                      "origin": {"source_url": snapshot["url"], "retrieved_date": snapshot["observed_at"][:10],
                                 "published_date": entry["published_date"], "representation": representation,
                                 "model_matching": entry["model_matching"], "purchase_verified": entry["purchase_verified"], "sponsorship": entry["sponsorship"]}}
            record.update({k: entry[k] for k in ("feature_key", "availability") if k in entry})
            if "commercial_disclosure" in entry:
                record["origin"]["commercial_disclosure"] = entry["commercial_disclosure"]
            records.append(record)
        base = (self.workspace / "runtime-data/catalogs").resolve()
        target = (base / version).resolve()
        if not base.is_relative_to(self.workspace / "runtime-data") or target.parent != base:
            fail("invalid_path", "Imported catalog must stay in runtime-data/catalogs")
        base.mkdir(parents=True, exist_ok=True)
        if target.exists():
            fail("version_conflict", "Dataset version already exists; never overwrite a snapshot")
        target.mkdir()
        try:
            (target / "models.json").write_text(canonical(dataset.models), encoding="utf-8")
            (target / "sources.jsonl").write_text("".join(canonical(r) + "\n" for r in records), encoding="utf-8")
            manifest = {**dataset.manifest, "data_version": version, "created_date": datetime.now(timezone.utc).date().isoformat(),
                        "provenance": "Observed-page additions. Model matching and claim support remain caller-reviewed, not automatically proven.",
                        "review_count": sum(r["kind"] == "review" for r in records), "fact_count": sum(r["kind"] == "product_fact" for r in records),
                        "files": [{"path": name, "sha256": hashlib.sha256((target / name).read_bytes()).hexdigest()} for name in ("models.json", "sources.jsonl")]}
            (target / "manifest.json").write_text(canonical(manifest), encoding="utf-8")
            checked = Dataset(target)
            (target / "import-audit.json").write_text(canonical({"input": payload, "data_fingerprint": checked.fingerprint, "semantic_status": "unverified"}), encoding="utf-8")
        except Exception:
            # Only delete the known files in the newly reserved directory, never recursively.
            for name in ("models.json", "sources.jsonl", "manifest.json", "import-audit.json"):
                path = target / name
                if path.is_file() and path.resolve().parent == target:
                    path.unlink()
            target.rmdir()
            raise
        return {"data_path": target.relative_to(self.workspace).as_posix(), "data_version": version,
                "added_sources": len(observations), "structural_valid": True, "semantic_status": "unverified", "acceptance_ready": False,
                "next_action": "Review model options and meaning; bind dataset before start_turn. Never reset a started turn to evade revisions."}
