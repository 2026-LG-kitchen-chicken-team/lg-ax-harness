"""Bounded public-page collection and versioned import. No search engine or LLM."""
from datetime import datetime, timezone
import copy
import hashlib
from http.client import HTTPSConnection
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import re
import sqlite3
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlparse
from urllib.request import build_opener, HTTPRedirectHandler, HTTPSHandler, ProxyHandler, Request
from .contracts import SCOPE_FIELDS, canonical, fail, fingerprint, identifier, integer, items, obj, product_family, scope, strict_json, text
from .dataset import Dataset

MAX_PAGE_BYTES = 2097152


def check_manual_section(url, content, location=None):
    """Bind explicit section markers; never infer a source URL from text."""
    parsed = urlparse(url)
    if (parsed.hostname != "gscs-manual.lge.com"
            or not re.fullmatch(r"/[A-Z]{3}/MFL[0-9]+/ko-kr/main\.html", parsed.path)):
        return
    marker = r"(?<![A-Za-z0-9_])topic_[0-9]+(?![A-Za-z0-9_])"
    topics = set(re.findall(marker, content))
    if location is not None:
        text(location, "location", 500)
        located = set(re.findall(marker, location))
        if (parsed.fragment and located != {parsed.fragment}) or (not parsed.fragment and located):
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
    host = parsed.hostname or ""
    if (parsed.scheme != "https" or not host or parsed.username is not None or parsed.password is not None
            or port not in (None, 443) or any(c.isspace() for c in value) or "\\" in value or "%" in host):
        fail("unsupported_url", "Use a public HTTPS source host without credentials/custom ports")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if ("." not in host or host.endswith((".local", ".localhost", ".internal", ".invalid", ".test"))
                or not re.fullmatch(r"[A-Za-z0-9.-]+", host)):
            fail("unsupported_url", "Source host must be a public DNS name or global IP")
    else:
        if not address.is_global:
            fail("unsupported_url", "Private/reserved source addresses are not allowed")
    return value


class PublicHTTPSConnection(HTTPSConnection):
    """Resolve once, reject every nonpublic answer, and pin TLS to that address."""
    def connect(self):
        answers = socket.getaddrinfo(self.host, self.port, type=socket.SOCK_STREAM)
        addresses = [answer[4][0] for answer in answers]
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            fail("unsupported_url", "DNS resolved to a private/reserved address")
        family, socktype, protocol, _, address = answers[0]
        raw_socket = socket.socket(family, socktype, protocol)
        try:
            raw_socket.settimeout(self.timeout)
            if self.source_address:
                raw_socket.bind(self.source_address)
            # Connect to the resolved sockaddr directly: no second DNS lookup.
            raw_socket.connect(address)
            # Keep certificate verification and SNI bound to the original hostname.
            self.sock = self._context.wrap_socket(raw_socket, server_hostname=self.host)
        except BaseException:
            raw_socket.close()
            raise


class PublicHTTPSHandler(HTTPSHandler):
    def https_open(self, request):
        return self.do_open(PublicHTTPSConnection, request, context=self._context)


def model_token(model_id, observed):
    return re.search(r"(?<![A-Za-z0-9_.:-])" + re.escape(model_id)
                     + r"(?![A-Za-z0-9_.:-])", observed, re.IGNORECASE) is not None


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
        self.db.execute("CREATE TABLE IF NOT EXISTS web_research_budgets (research_id TEXT, version INTEGER, max_pages INTEGER, reason TEXT, observed_at TEXT, PRIMARY KEY(research_id,version))")
        self.db.commit()

    def close(self):
        self.db.close()

    def configure(self, payload):
        """Amend a registered request's bounded budget without resetting attempts."""
        obj(payload, ("research_id", "max_pages", "reason"))
        research = identifier(payload["research_id"], "research_id")
        maximum = integer(payload["max_pages"], "max_pages", 6, 30)
        reason = text(payload["reason"], "budget reason", 2000)
        try:
            requests = self.db.execute("SELECT session_id,request_key FROM conversation_requests").fetchall()
        except sqlite3.OperationalError:
            requests = []
        if not any(research == "research-" + fingerprint([session, key]) for session, key in requests):
            fail("research_not_registered", "Configure the research ID returned by the saved original request")
        with self.db:
            self.db.execute("BEGIN IMMEDIATE")
            count = self.db.execute("SELECT COUNT(*) FROM web_pages WHERE research_id=?", (research,)).fetchone()[0]
            if maximum < count:
                fail("research_limit", "A budget cannot discard already attempted pages")
            previous = self.db.execute("SELECT version,max_pages,reason FROM web_research_budgets WHERE research_id=? ORDER BY version DESC LIMIT 1", (research,)).fetchone()
            reused = bool(previous and previous[1:] == (maximum, reason))
            version = previous[0] if reused else (previous[0] + 1 if previous else 1)
            if not reused:
                self.db.execute("INSERT INTO web_research_budgets VALUES(?,?,?,?,?)", (research, version, maximum, reason, datetime.now(timezone.utc).isoformat()))
        return {"research_id": research, "budget_version": version, "max_pages": maximum,
                "attempted_pages": count, "remaining_pages": maximum - count, "reused": reused,
                "technical_retries_per_page": 1, "semantic_status": "unverified"}

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
                budget = self.db.execute("SELECT max_pages FROM web_research_budgets WHERE research_id=? ORDER BY version DESC LIMIT 1", (payload["research_id"],)).fetchone()
                maximum = budget[0] if budget else 6
                if count >= maximum:
                    fail("research_limit", "Research reached its declared page budget (" + str(maximum) + "); preserve this request and attempted pages")
                self.db.execute("INSERT INTO web_pages VALUES (?,?,?,1,0,NULL)", (payload["research_id"], payload["page_id"], key))
        return None, False

    def _read(self, snapshot_id):
        identifier(snapshot_id, "snapshot_id")
        try:
            path = (self.base / (snapshot_id + ".json")).resolve(strict=True)
        except FileNotFoundError:
            fail("snapshot_not_found", "No retained observation exists for the requested snapshot")
        if path.parent != self.base or path.stat().st_size > 262144:
            fail("invalid_path", "Invalid snapshot path/size")
        value = strict_json(path.read_text(encoding="utf-8"))
        if value["snapshot_id"] != snapshot_id or fingerprint({k: v for k, v in value.items() if k != "snapshot_id"}) != snapshot_id:
            fail("snapshot_integrity", "Snapshot fingerprint mismatch")
        return value

    def report_sources(self, payload, expected_research_id):
        """Return contextual excerpts from snapshots of this same saved request.

        These sources enrich reports only. They cannot satisfy target-model
        ProductResult evidence references or prove an undocumented feature absent.
        """
        obj(payload, ("research_id", "sources"))
        if identifier(payload["research_id"], "research_id") != expected_research_id:
            fail("report_source_scope", "Context must belong to this saved request's research ID")
        records, used = [], set()
        for entry in items(payload["sources"], "context sources", 100):
            obj(entry, ("id", "snapshot_id", "kind", "title", "quote", "location", "subject", "scope_note"))
            sid = identifier(entry["id"], "source id")
            if sid in used:
                fail("report_source_integrity", "Duplicate context source ID")
            used.add(sid)
            snapshot = self._read(entry["snapshot_id"])
            if not self.db.execute("SELECT 1 FROM web_pages WHERE research_id=? AND snapshot_id=?", (expected_research_id, snapshot["snapshot_id"])).fetchone():
                fail("report_source_scope", "Context snapshot was not collected for this request")
            if entry["kind"] not in ("market", "product_document", "survey", "interview", "usability", "other"):
                fail("invalid_report_sources", "Target reviews belong in the exact-model catalog")
            for key, maximum in (("title", 500), ("quote", 4000), ("location", 500), ("subject", 500), ("scope_note", 2000)):
                text(entry[key], key, maximum)
            if entry["quote"] not in snapshot["text"]:
                fail("report_source_integrity", "Context quote is not an exact retained excerpt")
            check_manual_section(snapshot["url"], snapshot["text"], entry["location"])
            public_url(snapshot["url"])
            records.append({"id": sid, "kind": entry["kind"], "title": entry["title"],
                            "text": entry["quote"], "location": entry["location"], "url": snapshot["url"],
                            "synthetic": False,
                            "model": "자료 대상: " + entry["subject"] + " / 적용 범위: " + entry["scope_note"]
                                     + " / 관찰 시각: " + snapshot["observed_at"]
                                     + " / 관측 방식: " + snapshot["collection"]
                                     + " / 원문 의미·대상·주장 지지 여부는 별도 검토"})
        return records

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
                opener = build_opener(ProxyHandler({}), NoRedirect(), PublicHTTPSHandler())
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

    def _check_manual_association(self, entry, snapshot, exact, identity_urls):
        association = self._read(entry["association_snapshot_id"])
        manual_url = urlparse(public_url(snapshot["url"]))
        public_url(association["url"])
        model = exact["model_id"]
        identified = model_token(model, association["text"])
        observed_urls = {url.rstrip(")],.;") for url in re.findall(r"https?://[^\s<>\"']+", association["text"])}
        def identity_key(url):
            parsed = urlparse(url)
            path = parsed.path.rstrip("/").casefold()
            # Legacy LG catalog records use both published aliases of one PDP.
            if parsed.hostname == "www.lge.co.kr" and path.startswith("/product/"):
                path = path[len("/product"):]
            return parsed.hostname, path
        is_product = identity_key(association["url"]) in {identity_key(url) for url in identity_urls}
        # A model-specific manufacturer support page is also a legitimate
        # observed link origin. Never paste its href into an unrelated PDP.
        association_url = urlparse(association["url"])
        manufacturer_support = (association_url.hostname in {urlparse(url).hostname for url in identity_urls}
                                and "support" in association_url.path.casefold().split("/")
                                and re.search(r"(?<![A-Za-z0-9_.:])" + re.escape(model)
                                              + r"(?![A-Za-z0-9_.:-])", association_url.path, re.IGNORECASE) is not None)
        # Hash topics share the exact linked HTML document, not another manual.
        linked = snapshot["url"] in observed_urls or (manual_url.fragment and manual_url._replace(fragment="").geturl() in observed_urls)
        # LG's exact PDP exposes an HTTP href; the manual itself is observed via
        # HTTPS. Preserve the literal href and match only the same document.
        # This does not permit HTTP collection or weaken TLS validation.
        if not linked:
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
                or not (is_product or manufacturer_support) or not identified or not linked):
            fail("scope_mismatch", "A generic manual needs the exact model identity source and the same observed manual link")

    def _check_review_association(self, entry, snapshot, exact, identity_urls):
        """Bind a model-less same-site review popup without adding model text."""
        association = self._read(entry["association_snapshot_id"])
        parent = urlparse(public_url(association["url"]))
        child = urlparse(public_url(snapshot["url"]))
        originals = {urlparse(url)._replace(fragment="").geturl() for url in identity_urls}
        observed_urls = {url.rstrip(")],.;") for url in re.findall(r"https?://[^\s<>\"']+", association["text"])}
        # Only explicit product-identity keys count. Campaign/review/tracking
        # IDs cannot hide a different product, and absent identity is not proof.
        keys = ("modelid", "productid", "sku", "itemid")
        parent_pairs = [(key.casefold(), value) for key, value in parse_qsl(parent.query, keep_blank_values=True)]
        key = next((key for key in keys if any(pair[0] == key for pair in parent_pairs)), None)
        product_ids = [value for name, value in parent_pairs if name == key] if key else []
        child_values = [value for name, value in parse_qsl(child.query, keep_blank_values=True) if name.casefold() == key]
        identity_matches = (len(product_ids) == 1 and bool(product_ids[0])
                            and (product_ids[0] in child.path.split("/") or child_values == product_ids)
                            and (not child_values or child_values == product_ids))
        popup = re.fullmatch(r"/mkt/review/([^/]+)/pdpReviewListPopup/?", child.path)
        if popup and (len(product_ids) != 1 or popup[1] != product_ids[0]):
            # This observed popup endpoint's product identity is in its path;
            # an added matching query must not conceal another product there.
            identity_matches = False
        if (entry["kind"] != "review" or entry["model_matching"] != "product_page_association"
                or parent._replace(fragment="").geturl() not in originals
                or parent.hostname != child.hostname
                or not identity_matches
                or not model_token(exact["model_id"], association["text"])
                or snapshot["url"] not in observed_urls):
            fail("scope_mismatch", "A review popup needs its exact registered product page and observed same-site child URL")

    def import_evidence(self, dataset, payload):
        obj(payload, ("data_version", "observations"), ("new_models",))
        version = identifier(payload["data_version"], "data_version")
        if dataset.synthetic or version == dataset.version:
            fail("invalid_dataset", "Business import requires a new real dataset version")
        observations = items(payload["observations"], "observations", 10)
        if not observations:
            fail("invalid_input", "At least one observed source is required")
        new_models = copy.deepcopy(items(payload.get("new_models", []), "new_models", 10))
        models = copy.deepcopy(dataset.models)
        scopes = set(dataset.scopes)
        for model in new_models:
            obj(model, (*SCOPE_FIELDS, "name", "product_family", "synthetic", "spec_source_id", "identity_review"))
            exact = scope({key: model[key] for key in SCOPE_FIELDS})
            product_family(model["product_family"])
            text(model["name"], "model name", 200)
            identifier(model["spec_source_id"], "spec_source_id")
            if model["synthetic"] is not False:
                fail("invalid_dataset", "A business model requires nonsynthetic observed identity")
            review = obj(model["identity_review"], ("source_id", "manufacturer", "authority", "rationale"))
            text(review["manufacturer"], "manufacturer", 200)
            text(review["rationale"], "identity rationale", 2000)
            if review["source_id"] != model["spec_source_id"] or review["authority"] != "manufacturer":
                fail("identity_mismatch", "Identity review must declare the same manufacturer source")
            if canonical(exact) in scopes:
                fail("invalid_dataset", "An existing exact model scope cannot be replaced")
            for existing in models:
                if existing["model_id"].casefold() == model["model_id"].casefold() and any(
                        existing[field] != model[field] for field in ("model_id", "name", "product_family")):
                    fail("identity_mismatch", "New scope conflicts with the registered model identity")
            scopes.add(canonical(exact))
            models.append(model)
        if len(models) > 20:
            fail("dataset_limit", "Catalog supports at most 20 exact model scopes")
        observed_entries = {}
        for entry in observations:
            obj(entry, ("snapshot_id", "source_id", "kind", "scope", "location", "text", "support_quote", "published_date", "model_matching", "purchase_verified", "sponsorship"), ("feature_key", "availability", "commercial_disclosure", "association_snapshot_id"))
            identifier(entry["source_id"], "source_id")
            if entry["source_id"] in observed_entries:
                fail("invalid_dataset", "Duplicate observed source ID")
            observed_entries[entry["source_id"]] = entry
        identity_urls = {}
        review_identity_urls = {}
        for model in models:
            exact = {key: model[key] for key in SCOPE_FIELDS}
            identity_urls[canonical(exact)] = [record["origin"]["source_url"] for record in dataset.sources.values()
                if record["kind"] == "product_fact" and all(record[key] == exact[key] for key in SCOPE_FIELDS)]
            review_identity_urls[canonical(exact)] = ([dataset.source(model["spec_source_id"])["origin"]["source_url"]]
                if "spec_source_id" in model and model["spec_source_id"] in dataset.sources else [])
        for model in new_models:
            entry = observed_entries.get(model["spec_source_id"])
            exact = {key: model[key] for key in SCOPE_FIELDS}
            if (entry is None or entry["kind"] != "product_fact" or entry["scope"] != exact
                    or entry.get("availability") != "present" or "association_snapshot_id" in entry):
                fail("identity_mismatch", "New model needs a same-import exact-scope product identity fact")
            snapshot = self._read(entry["snapshot_id"])
            text(entry["support_quote"], "support_quote", 4000)
            if (entry["text"] != entry["support_quote"] or entry["support_quote"] not in snapshot["text"]
                    or not model_token(model["model_id"], entry["support_quote"])):
                fail("identity_mismatch", "New model identity needs its exact model token in an observed verbatim quote")
            if model["model_version"] != "unspecified" and not model_token(model["model_version"], entry["support_quote"]):
                fail("identity_mismatch", "A claimed hardware version needs explicit observed support; otherwise use unspecified")
            identity_urls[canonical(exact)].append(public_url(snapshot["url"]))
            review_identity_urls[canonical(exact)].append(snapshot["url"])
        records = [{**s, "data_version": version} for s in dataset.sources.values()]
        used = set(dataset.sources)
        for entry in observations:
            obj(entry, ("snapshot_id", "source_id", "kind", "scope", "location", "text", "support_quote", "published_date", "model_matching", "purchase_verified", "sponsorship"), ("feature_key", "availability", "commercial_disclosure", "association_snapshot_id"))
            exact = scope(entry["scope"])
            if canonical(exact) not in scopes:
                dataset.check_scope(exact)
            source_id = identifier(entry["source_id"], "source_id")
            if source_id in used:
                fail("invalid_dataset", "Import must add unique source IDs; existing snapshots are immutable")
            used.add(source_id)
            snapshot = self._read(entry["snapshot_id"])
            public_url(snapshot["url"])
            check_manual_section(snapshot["url"], snapshot["text"], entry["location"])
            text(entry["support_quote"], "support_quote", 4000)
            text(entry["text"], "source text", 4000)
            if entry["support_quote"] not in snapshot["text"]:
                fail("quote_mismatch", "Support quote is not in the observed snapshot")
            if "association_snapshot_id" in entry:
                if entry["kind"] == "review":
                    self._check_review_association(entry, snapshot, exact, review_identity_urls[canonical(exact)])
                else:
                    self._check_manual_association(entry, snapshot, exact, identity_urls[canonical(exact)])
            elif not model_token(exact["model_id"], snapshot["text"]):
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
            (target / "models.json").write_text(canonical(models), encoding="utf-8")
            (target / "sources.jsonl").write_text("".join(canonical(r) + "\n" for r in records), encoding="utf-8")
            manifest = {**dataset.manifest, "data_version": version, "created_date": datetime.now(timezone.utc).date().isoformat(),
                        "provenance": "Observed-page additions. Model matching and claim support remain caller-reviewed, not automatically proven.",
                        "model_count": len({model["model_id"] for model in models}), "scope_count": len(models),
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
                "added_sources": len(observations), "added_models": len(new_models), "structural_valid": True, "semantic_status": "unverified", "acceptance_ready": False,
                "next_action": "Review model options and meaning; bind dataset before start_turn. Never reset a started turn to evade revisions."}
