"""JSON/stdin command tools for existing native Agent runtimes; no LLM calls."""
import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from product_tools.contracts import MAX_BYTES, MAX_INPUT_BYTES, ToolError, decode_json_bytes, fail, obj, strict_json
from product_tools.state import StateStore
from product_tools.tools import ProductTools
from product_tools.planning import review_product_result
from product_tools.web_evidence import WebEvidence
from product_tools.conversation import Conversation
from product_tools.error_receipts import preserve_failure
from product_tools.instructions import InstructionLoader
from product_tools.execution_context import operation_dataset

ROOT = Path(__file__).resolve().parents[1]

# Explicit state-detail operations can return the complete stored candidate.
# Evidence/bundle/receipt operations keep their smaller context budget.
STATE_DETAIL_OPERATIONS = frozenset(("get_turn", "get_completion_summary", "current_request", "open_request", "start_turn", "resolve_request",
                                    "record_request_research", "cancel_turn", "save_result", "save_reviewed_result"))

def output_limit(operation):
    return MAX_INPUT_BYTES if operation in STATE_DETAIL_OPERATIONS else MAX_BYTES

def dispatch(data, store, operation, payload):
    if operation == "get_work_instructions":
        return InstructionLoader(ROOT).get_work_instructions(payload)
    tools = ProductTools(data)
    if operation in ("prepare_review_packet", "verify_review_packet"):
        from product_tools.reviewer_packet import ReviewPackets
        return getattr(ReviewPackets(store, ROOT), operation)(payload)
    if operation in ("evidence_inventory", "read_evidence_batch", "record_evidence_review", "evidence_coverage", "set_request_scope_policy", "open_product_workflow", "record_workflow_event", "workflow_status", "open_request", "open_request_bundle", "resolve_request", "resolve_request_bundle", "record_request_research", "current_request", "export_session", "save_and_export", "deliver_result", "prepare_web_result", "get_completion_summary"):
        return getattr(Conversation(store, ROOT), operation)(payload)
    if operation == "save_reviewed_result":
        obj(payload, ("session_id", "turn_id", "result_key", "result", "expected_result_version"), ("assessment", "response_mode"))
        payload = {**payload, "assessment": payload.get("assessment")}
        return store.save_result(**payload, require_review=True)
    if operation == "review_product_result":
        return review_product_result(data, payload)
    if operation in ("fetch_web_page", "capture_web_page", "import_web_evidence", "import_web_evidence_bulk", "configure_web_research"):
        web = WebEvidence(store.path, ROOT)
        try:
            if operation == "configure_web_research":
                return web.configure(payload)
            if operation == "import_web_evidence_bulk":
                from product_tools.bulk_import import BulkImporter
                return BulkImporter(web).run(data, payload)
            return web.import_evidence(data, payload) if operation == "import_web_evidence" else web.collect(payload, browser=operation == "capture_web_page")
        finally:
            web.close()
    if operation == "prepare_planning_input":
        return tools.prepare_planning_input(payload)
    if operation == "list_models":
        return tools.list_models(payload)
    if operation == "doctor":
        obj(payload, ())
        document_modules = {"python-docx": "docx", "openpyxl": "openpyxl", "reportlab": "reportlab", "Pillow": "PIL", "pypdf": "pypdf"}
        document_versions = {}
        missing = []
        for package, module in document_modules.items():
            try:
                found = importlib.util.find_spec(module) is not None
                document_versions[package] = importlib.metadata.version(package) if found else None
            except (ImportError, ValueError, importlib.metadata.PackageNotFoundError):
                found = False
                document_versions[package] = None
            if not found:
                missing.append(package)
        return {"data_version": data.version, "dataset_fingerprint": data.fingerprint, "models": data.models,
                "counts": {k: data.manifest[k] for k in ("model_count", "scope_count", "review_count", "fact_count")},
                "synthetic": data.synthetic, "purpose": data.manifest["purpose"],
                "reporting_dependencies": {"available": not missing, "versions": document_versions, "missing": missing},
                "scope": "common local tools and dependency availability only; native Agent and semantic quality not verified"}
    if operation in ("retrieve_reviews", "retrieve_product_facts"):
        obj(payload, ("scope",), ("query", "limit", "feature_key", "offset"))
        if operation == "retrieve_reviews" and "feature_key" in payload:
            fail("invalid_input", "feature_key is only for product facts")
        return store.retrieve("review" if operation == "retrieve_reviews" else "product_fact", payload["scope"], payload.get("query", ""), payload.get("limit", 12), payload.get("feature_key"), payload.get("offset", 0))
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
        "cancel_turn": ("session_id", "turn_id", "cancel_key", "reason", "expected_result_version", "user_submitted"),
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
    parser.add_argument("--data", type=Path, default=None)
    parser.add_argument("--db", type=Path, default=ROOT / "runtime-data/product.sqlite")
    parser.add_argument("operation", choices=("get_work_instructions", "prepare_review_packet", "verify_review_packet", "evidence_inventory", "read_evidence_batch", "record_evidence_review", "evidence_coverage", "set_request_scope_policy", "doctor", "list_models", "prepare_planning_input", "retrieve_reviews", "retrieve_product_facts", "select_evidence", "match_product_scope", "validate_source_refs", "validate_constraints", "validate_result_contract", "review_product_result", "fetch_web_page", "capture_web_page", "import_web_evidence", "import_web_evidence_bulk", "configure_web_research", "open_product_workflow", "record_workflow_event", "workflow_status", "open_request", "open_request_bundle", "resolve_request", "resolve_request_bundle", "record_request_research", "current_request", "export_session", "save_reviewed_result", "save_and_export", "get_completion_summary", "prepare_web_result", "deliver_result", "start_turn", "get_turn", "save_result", "record_usage", "cancel_turn", "begin_invocation", "finish_invocation"))
    parser.add_argument("--input", default="-", help="UTF-8 JSON file or - for stdin; doctor needs no input")
    args = parser.parse_args()
    store = None
    input_sha256 = None
    try:
        db = args.db.resolve()
        allowed = (ROOT / "runtime-data").resolve()
        if not allowed.is_relative_to(ROOT) or not db.is_relative_to(allowed) or db == allowed:
            fail("invalid_path", "CLI database must be a file below this project's runtime-data/")
        if args.operation == "doctor" and args.input == "-":
            raw = "{}"
        elif args.input == "-":
            raw = decode_json_bytes(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        else:
            path = Path(args.input)
            if path.stat().st_size > MAX_INPUT_BYTES:
                fail("input_limit", "Input exceeds 256 KiB")
            raw = decode_json_bytes(path.read_bytes())
        if len(raw.encode("utf-8")) > MAX_INPUT_BYTES:
            fail("input_limit", "Input exceeds 256 KiB")
        input_sha256 = hashlib.sha256(raw.encode("utf8")).hexdigest()
        payload = strict_json(raw)
        if args.operation == "get_work_instructions":
            # Instruction access precedes model selection and needs no dataset/DB.
            result = dispatch(None, None, args.operation, payload)
        else:
            data = operation_dataset(ROOT, db, args.operation, payload, args.data)
            store = StateStore(db, data, workspace=ROOT)
            result = dispatch(data, store, args.operation, payload)
        output = json.dumps({"ok": True, "result": result}, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        if len(output.encode("utf-8")) > output_limit(args.operation):
            fail("output_limit", "Output exceeds operation byte budget; use receipt/export for state or narrower evidence batches")
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
    receipt = preserve_failure(ROOT, args.operation, error, input_sha256)
    print(json.dumps({"ok": False, "error": error, "failure_receipt": receipt}, ensure_ascii=False))
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
