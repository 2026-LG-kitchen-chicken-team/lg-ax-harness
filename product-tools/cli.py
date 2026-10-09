"""JSON/stdin command tools for existing native Agent runtimes; no LLM calls."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
from product_tools.contracts import MAX_BYTES, ToolError, fail, obj, strict_json
from product_tools.dataset import Dataset
from product_tools.state import StateStore
from product_tools.tools import ProductTools
from product_tools.planning import review_product_result
from product_tools.web_evidence import WebEvidence

ROOT = Path(__file__).resolve().parents[1]

def dispatch(data, store, operation, payload):
    tools = ProductTools(data)
    if operation == "review_product_result":
        return review_product_result(data, payload)
    if operation in ("fetch_web_page", "capture_web_page", "import_web_evidence"):
        web = WebEvidence(store.path, ROOT)
        try:
            return web.import_evidence(data, payload) if operation == "import_web_evidence" else web.collect(payload, browser=operation == "capture_web_page")
        finally:
            web.close()
    if operation == "prepare_planning_input":
        return tools.prepare_planning_input(payload)
    if operation == "doctor":
        obj(payload, ())
        return {"data_version": data.version, "dataset_fingerprint": data.fingerprint, "models": data.models,
                "counts": {k: data.manifest[k] for k in ("model_count", "scope_count", "review_count", "fact_count")},
                "synthetic": data.synthetic, "purpose": data.manifest["purpose"], "scope": "common local tools only; native Agent and semantic quality not verified"}
    if operation in ("retrieve_reviews", "retrieve_product_facts"):
        obj(payload, ("scope",), ("query", "limit", "feature_key"))
        if operation == "retrieve_reviews" and "feature_key" in payload:
            fail("invalid_input", "feature_key is only for product facts")
        return store.retrieve("review" if operation == "retrieve_reviews" else "product_fact", payload["scope"], payload.get("query", ""), payload.get("limit", 12), payload.get("feature_key"))
    if operation == "select_evidence":
        obj(payload, ("scope", "source_ids"))
        return tools.select_evidence(payload["scope"], payload["source_ids"])
    if operation == "match_product_scope":
        obj(payload, ("scope",))
        return {"scope": data.check_scope(payload["scope"]), "scope_valid": True}
    if operation == "validate_source_refs":
        obj(payload, ("evidence_refs", "model_scope"))
        return tools.validate_source_refs(payload["evidence_refs"], payload["model_scope"])
    if operation in ("validate_result_contract", "validate_constraints"):
        obj(payload, ("input", "result"))
        return tools.validate_result_contract(payload["input"], payload["result"])
    contracts = {
        "start_turn": ("input", "user_submitted"), "get_turn": ("session_id", "turn_id"),
        "save_result": ("session_id", "turn_id", "result_key", "result", "expected_result_version"),
        "record_usage": ("session_id", "turn_id", "call"),
        "begin_invocation": ("session_id", "turn_id", "invocation_id", "tool_name", "request_fingerprint"),
        "finish_invocation": ("session_id", "turn_id", "invocation_id", "status", "retryable"),
    }
    obj(payload, contracts[operation])
    method = getattr(store, "invocation" if operation == "begin_invocation" else operation)
    return method(**({"planning": payload["input"], "user_submitted": payload["user_submitted"]} if operation == "start_turn" else payload))

def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=ROOT / "data/business/lg-research-v3")
    parser.add_argument("--db", type=Path, default=ROOT / "runtime-data/product.sqlite")
    parser.add_argument("operation", choices=("doctor", "prepare_planning_input", "retrieve_reviews", "retrieve_product_facts", "select_evidence", "match_product_scope", "validate_source_refs", "validate_constraints", "validate_result_contract", "review_product_result", "fetch_web_page", "capture_web_page", "import_web_evidence", "start_turn", "get_turn", "save_result", "record_usage", "begin_invocation", "finish_invocation"))
    parser.add_argument("--input", default="-", help="UTF-8 JSON file or - for stdin; doctor needs no input")
    args = parser.parse_args()
    store = None
    try:
        db = args.db.resolve()
        allowed = (ROOT / "runtime-data").resolve()
        if not allowed.is_relative_to(ROOT) or not db.is_relative_to(allowed) or db == allowed:
            fail("invalid_path", "CLI database must be a file below this project's runtime-data/")
        if args.operation == "doctor" and args.input == "-":
            raw = "{}"
        elif args.input == "-":
            raw = sys.stdin.buffer.read(MAX_BYTES + 1).decode("utf-8")
        else:
            path = Path(args.input)
            if path.stat().st_size > MAX_BYTES:
                fail("input_limit", "Input exceeds 64 KiB")
            raw = path.read_text(encoding="utf-8")
        if len(raw.encode("utf-8")) > MAX_BYTES:
            fail("input_limit", "Input exceeds 64 KiB")
        payload = strict_json(raw)
        data = Dataset(args.data)
        store = StateStore(db, data)
        result = dispatch(data, store, args.operation, payload)
        output = json.dumps({"ok": True, "result": result}, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if len(output.encode("utf-8")) > MAX_BYTES:
            fail("output_limit", "Output exceeds 64 KiB; use narrower scope/query or lower limit")
        print(output)
        return 0
    except ToolError as exc:
        error = {"code": exc.code, "message": str(exc), "retryable": False}
    except sqlite3.Error as exc:
        error = {"code": "storage_error", "message": str(exc), "retryable": isinstance(exc, sqlite3.OperationalError) and "locked" in str(exc).lower()}
    except (OSError, UnicodeError, ValueError, TypeError, KeyError, RecursionError) as exc:
        error = {"code": "tool_error", "message": str(exc), "retryable": False}
    finally:
        if store is not None:
            store.close()
    print(json.dumps({"ok": False, "error": error}, ensure_ascii=False))
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
