"""Request-bound target policy; never chooses a model from question keywords."""
import re
from urllib.parse import urlparse
from .contracts import canonical, fail, obj, strict_json, text


def compact(value):
    return re.sub(r"[^a-z0-9가-힣]", "", value.casefold())


def domestic_lg(url):
    parsed = urlparse(url)
    if parsed.path.startswith(("/support", "/mkt", "/kr/support", "/kr/customer")):
        return False
    return parsed.hostname in ("www.lge.co.kr", "lge.co.kr") or (
        parsed.hostname in ("www.lg.com", "lg.com") and (parsed.path == "/kr" or parsed.path.startswith("/kr/")))


MARKET_LITERALS = {
    "KR": ("KR", "한국", "대한민국", "국내", "South Korea"),
    "US": ("US", "USA", "미국", "United States"),
    "JP": ("JP", "일본", "Japan"), "GB": ("GB", "UK", "영국", "United Kingdom"),
    "CA": ("CA", "캐나다", "Canada"), "AU": ("AU", "호주", "Australia"),
    "FR": ("FR", "프랑스", "France"), "DE": ("DE", "독일", "Germany")}


def market_literal(market, quote):
    if not isinstance(market, str) or not re.fullmatch(r"[A-Z]{2}", market):
        return False
    from .web_evidence import model_token
    return any(model_token(term, quote) for term in MARKET_LITERALS.get(market, (market,)))


def market_url(market, url):
    if market == "KR" and domestic_lg(url):
        return True
    parsed = urlparse(url)
    code = market.casefold()
    segments = parsed.path.casefold().strip("/").split("/")
    return (parsed.hostname or "").endswith("." + code) or (parsed.hostname or "").startswith(code + ".") or any(
        s in (code, "en-" + code, "en_" + code) for s in segments)


class SelectionPolicy:
    def __init__(self, db):
        self.db = db
        db.execute("""CREATE TABLE IF NOT EXISTS request_selection_policies(
            session_id TEXT NOT NULL, request_key TEXT NOT NULL, payload TEXT NOT NULL,
            PRIMARY KEY(session_id,request_key))""")

    def initialize(self, session, key, original):
        if not self.get(session, key):
            from .web_evidence import model_token
            model = original.get("model_id")
            prior_policy = None
            if original.get("prior_turn_id") and not model:
                prior = self.db.execute("SELECT request_key FROM conversation_requests WHERE session_id=? AND turn_id=?", (session, original["prior_turn_id"])).fetchall()
                turn = self.db.execute("SELECT input_json FROM turns WHERE session_id=? AND turn_id=?", (session, original["prior_turn_id"])).fetchone()
                if len(prior) == 1 and turn:
                    prior_input = strict_json(turn[0])
                    if not original.get("product_family") or original["product_family"] == prior_input.get("product_family"):
                        prior_policy = self.get(session, prior[0][0])
            value = ({"mode": "explicit_model", "model_id": model, "user_quote": model}
                     if model and model_token(model, original["question"]) else
                     prior_policy or {"mode": "project_default", "brand": "LG전자", "market": "KR"})
            self.db.execute("INSERT INTO request_selection_policies VALUES(?,?,?)", (session, key, canonical(value)))

    def get(self, session, key):
        row = self.db.execute("SELECT payload FROM request_selection_policies WHERE session_id=? AND request_key=?", (session, key)).fetchone()
        return strict_json(row[0]) if row else None

    def for_research(self, research):
        from .contracts import fingerprint
        if research is None or not self.db.execute("SELECT name FROM sqlite_master WHERE name='conversation_requests'").fetchone():
            return None
        for row in self.db.execute("SELECT session_id,request_key FROM conversation_requests"):
            if research == "research-" + fingerprint(list(row)):
                return self.get(*row)
        return None

    def set(self, session, key, value):
        if isinstance(value, dict) and value.get("mode") == "explicit_market":
            obj(value, ("mode", "market", "market_quote", "user_quote"), ("brand",))
            if value.get("brand", "LG전자") != "LG전자":
                fail("selection_policy_conflict", "A market-only request keeps the project's LG brand")
            value = {**value, "brand": "LG전자"}
        request = self.db.execute("SELECT payload,turn_id FROM conversation_requests WHERE session_id=? AND request_key=?", (session, key)).fetchone()
        if not request:
            fail("request_not_found", "A selection policy needs the original request")
        old = self.get(session, key)
        if old == value:
            return old
        if request[1] is not None or old and old["mode"] != "project_default":
            fail("selection_policy_conflict", "Bound or explicit intent cannot be changed")
        obj(value, ("mode", "user_quote"), ("model_id", "brand", "market", "market_quote"))
        question = strict_json(request[0])["question"]
        quote = text(value["user_quote"], "user_quote", 2000)
        if quote not in question:
            fail("selection_policy_conflict", "Policy must retain a literal part of the original user request")
        if value["mode"] == "explicit_model":
            obj(value, ("mode", "model_id", "user_quote"), ("market", "market_quote"))
            from .web_evidence import model_token
            model = text(value.get("model_id"), "model_id", 200)
            if not model_token(model, quote) or any(k in value for k in ("brand",)):
                fail("selection_policy_conflict", "Exact-model override needs that original model token")
        elif value["mode"] == "explicit_brand_market":
            obj(value, ("mode", "brand", "user_quote"), ("market", "market_quote"))
            brand = text(value.get("brand"), "brand", 200)
            if not compact(brand) or compact(brand) not in compact(quote):
                fail("selection_policy_conflict", "Do not infer a different brand from an unrelated user quote")
        elif value["mode"] == "explicit_market":
            market_quote = text(value.get("market_quote"), "market_quote", 500)
            if not market_literal(value["market"], market_quote):
                fail("selection_policy_conflict", "Market-only intent needs a matching original country name/code")
        else:
            fail("invalid_input", "Use an explicit model or explicit brand/market declaration")
        if value.get("market") is not None:
            market_quote = text(value.get("market_quote"), "market_quote", 500)
            if market_quote not in question or not market_literal(value["market"], market_quote):
                fail("selection_policy_conflict", "Market declaration needs the matching original country name/code")
        elif "market_quote" in value:
            fail("selection_policy_conflict", "A market quote needs its declared country code")
        self.db.execute("INSERT OR REPLACE INTO request_selection_policies VALUES(?,?,?)", (session, key, canonical(value)))
        return value

    def check(self, policy, models, sources, synthetic=False):
        if policy is None or synthetic:
            return
        for model in models:
            exact = {k: model[k] for k in ("model_id", "model_version", "document_version")}
            candidates = [s for s in sources if s["kind"] == "product_fact" and all(s[k] == v for k, v in exact.items())]
            if model.get("spec_source_id"):
                candidates = [s for s in candidates if s["source_id"] == model["spec_source_id"]]
            if policy["mode"] == "explicit_model":
                if model["model_id"].casefold() != policy["model_id"].casefold():
                    fail("target_scope_mismatch", "Keep the user's exact named model")
                if policy.get("market") and not any(market_url(policy["market"], s["origin"]["source_url"]) for s in candidates):
                    fail("target_scope_mismatch", "Named model evidence does not identify the explicitly requested market")
                continue
            maker = model.get("identity_review", {}).get("manufacturer", "")
            if policy["mode"] == "project_default":
                if maker and compact(maker) not in ("lg", "lg전자", "lgelectronics", "lge"):
                    fail("target_scope_mismatch", "Brand-unspecified planning targets domestic LG products")
                if not any(domestic_lg(s["origin"]["source_url"]) for s in candidates):
                    fail("target_scope_mismatch", "Default LG/KR needs exact-model facts from the domestic manufacturer product site")
            elif not maker or not (compact(policy["brand"]) in compact(maker) or
                    compact(policy["brand"]) in ("lg", "lg전자", "lgelectronics", "lge") and compact(maker) in ("lg", "lg전자", "lgelectronics", "lge")):
                fail("target_scope_mismatch", "Observed manufacturer differs from the requested or preserved project brand")
            elif policy.get("market") and not any(market_url(policy["market"], s["origin"]["source_url"]) for s in candidates):
                fail("target_scope_mismatch", "Manufacturer product evidence needs an explicit matching market URL; do not infer country from document language")

    def check_turn(self, turn_id, dataset, planning):
        for row in self.db.execute("SELECT session_id,request_key FROM conversation_requests WHERE turn_id=?", (turn_id,)):
            scopes = planning["model_scope"]
            models = [m for m in dataset.models if any(all(m[k] == s[k] for k in s) for s in scopes)]
            self.check(self.get(*row), models, dataset.sources.values(), dataset.synthetic)
