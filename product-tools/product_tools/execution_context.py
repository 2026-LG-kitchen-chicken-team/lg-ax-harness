"""Resolve an omitted export catalog from one session's bound turn, never latest globally."""
from pathlib import Path
import sqlite3
from .contracts import DEFAULT_DATA_PATH, fail, identifier, obj
from .dataset import Dataset
from .paths import real_path


def operation_dataset(workspace, database, operation, payload, explicit_data=None):
    # Explicit callers retain control, including intentional historical exports.
    if explicit_data is not None:
        return Dataset(explicit_data)
    workspace = real_path(workspace)
    default = workspace / DEFAULT_DATA_PATH
    if operation != "export_session" or not Path(database).is_file():
        return Dataset(default)
    obj(payload, ("session_id",))
    session = identifier(payload["session_id"], "session_id")
    connection = sqlite3.connect(Path(database).resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        columns = {r[1] for r in connection.execute("PRAGMA table_info(turns)")}
        if not columns:
            return Dataset(default)
        # Same order as Conversation._export_session. A pending request has no
        # turn and cannot invent a new catalog; a cancelled latest turn remains
        # cancelled rather than resurrecting an older completed one.
        column = "dataset_path" if "dataset_path" in columns else "NULL AS dataset_path"
        row = connection.execute(
            "SELECT dataset_hash," + column + " FROM turns WHERE session_id=? ORDER BY created_at DESC,turn_id DESC LIMIT 1",
            (session,)).fetchone()
    finally:
        connection.close()
    if row is None:
        return Dataset(default)
    relative = row["dataset_path"]
    message = "Export needs explicit --data for this session's bound catalog; no default or global latest catalog was substituted"
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        fail("catalog_context_required", message)
    try:
        target = real_path(workspace / relative)
        if not target.is_relative_to(workspace):
            fail("catalog_context_required", message)
        dataset = Dataset(target)
    except (OSError, ValueError):
        fail("catalog_context_required", message)
    if dataset.fingerprint != row["dataset_hash"]:
        fail("catalog_context_mismatch", "Bound export catalog fingerprint changed; inspect the original catalog and supply explicit --data")
    return dataset
