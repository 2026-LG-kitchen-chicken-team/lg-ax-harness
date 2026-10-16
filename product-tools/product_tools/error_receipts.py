"""Immutable local failure receipts; no model calls or input bodies."""
from datetime import datetime, timezone
import hashlib
from .contracts import canonical
from .paths import real_path


def preserve_failure(workspace, operation, error, input_sha256=None):
    """Best effort: a journal failure must not disguise the original Tool error."""
    try:
        root = real_path(workspace)
        runtime = (root / "runtime-data").resolve()
        folder = (runtime / "tool-errors").resolve()
        if not runtime.is_relative_to(root) or not folder.is_relative_to(runtime):
            raise ValueError("Failure receipt must stay in this workspace runtime-data")
        folder.mkdir(parents=True, exist_ok=True)
        message = error["message"]
        value = {"contract_version": "product-tool-error-v1", "operation": operation,
                 "observed_at": datetime.now(timezone.utc).isoformat(),
                 "input_sha256": input_sha256,
                 "input_sha256_scope": "decoded_json_text_encoded_as_utf8; not original file bytes",
                 "error_message": {"truncated": len(message) > 2000,
                                   "original_chars": len(message),
                                   "original_utf8_sha256": hashlib.sha256(message.encode("utf8")).hexdigest()},
                 "error": {"code": error["code"], "message": message[:2000],
                           "retryable": error["retryable"]},
                 "scope": "Local Tool failure only; no native/backend stop or semantic certification"}
        raw = canonical(value).encode("utf8")
        digest = hashlib.sha256(raw).hexdigest()
        target = (folder / ("error-" + digest + ".json")).resolve()
        if target.parent != folder:
            raise ValueError("Invalid failure receipt destination")
        with target.open("xb") as handle:
            handle.write(raw)
        if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
            raise ValueError("Failure receipt integrity check failed")
        return {"ready": True, "path": target.relative_to(root).as_posix(),
                "sha256": digest, "bytes": len(raw)}
    except (OSError, ValueError, KeyError, TypeError):
        return {"ready": False, "path": None, "sha256": None,
                "reason": "failure_receipt_unavailable; original error remains in CLI/native output"}
