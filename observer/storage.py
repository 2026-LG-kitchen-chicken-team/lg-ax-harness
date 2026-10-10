"""Bounded local-first storage. Checkpoints survive log reconnect/replay."""
import json
from pathlib import Path


class LocalStore:
    def __init__(self, directory, max_bytes=4 * 1024 * 1024):
        if not 4096 <= max_bytes <= 64 * 1024 * 1024:
            raise ValueError("invalid_local_limit")
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.events = self.directory / "events.jsonl"
        self.checkpoint = self.directory / "checkpoint.json"
        self.attempts = self.directory / "export-attempts.jsonl"

    def load(self, native_id, run_id):
        if not self.checkpoint.exists():
            return None
        if self.checkpoint.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("checkpoint_size_limit")
        value = json.loads(self.checkpoint.read_text(encoding="utf-8"))
        if value.get("native_thread_id") != native_id or value.get("run_id") != run_id:
            raise ValueError("checkpoint_identity_mismatch")
        if value.get("state", {}).get("parser_version") != 2:
            # Earlier parsers skipped custom Tool records but advanced offsets.
            # Silent reuse would permanently hide those events; use a new output.
            raise ValueError("checkpoint_parser_version_mismatch")
        return value["state"]

    def append(self, event):
        encoded = (json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > self.max_bytes:
            return False
        if self.events.exists() and self.events.stat().st_size + len(encoded) > self.max_bytes:
            # Keep a bounded suffix of complete sanitized records; state keeps dedup offsets.
            with self.events.open("rb") as stream:
                stream.seek(max(0, self.events.stat().st_size - self.max_bytes // 2))
                retained = stream.read(self.max_bytes // 2)
            retained = retained.partition(b"\n")[2]
            self.events.write_bytes(retained)
        with self.events.open("ab") as stream:
            stream.write(encoded)
            stream.flush()
        return True

    def save(self, collector, extra=None):
        value = {"native_thread_id": collector.selected_id, "run_id": collector.run_id, "state": collector.state}
        temp = self.directory / "checkpoint.tmp"
        temp.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.checkpoint)
        summary = {**collector.summary(), **(extra or {})}
        temp = self.directory / "summary.tmp"
        temp.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temp.replace(self.directory / "summary.json")

    def attempted(self):
        if not self.attempts.exists():
            return set()
        if self.attempts.stat().st_size > self.max_bytes:
            # Fail closed: do not re-export when the durable dedup record is over limit.
            raise ValueError("export_attempt_limit")
        return {line.strip() for line in self.attempts.read_text(encoding="ascii").splitlines()}

    def mark_attempt(self, event_id):
        if self.attempts.exists() and self.attempts.stat().st_size + 65 > self.max_bytes:
            raise ValueError("export_attempt_limit")
        with self.attempts.open("a", encoding="ascii") as stream:
            stream.write(event_id + "\n")
            stream.flush()


class JsonlReader:
    """Bounded chunk/line reader; tail never interprets an unfinished JSON record."""
    def __init__(self, path, max_line=1024 * 1024, max_bytes=64 * 1024 * 1024):
        self.path = Path(path)
        self.max_line, self.max_bytes = max_line, max_bytes
        self.offset, self.seq, self.pending = 0, 0, b""
        self.discarding = False
        self.errors = {}

    def error(self, code):
        self.errors[code] = self.errors.get(code, 0) + 1

    def poll(self, final=False):
        records = []
        try:
            size = self.path.stat().st_size
            if size < self.offset:
                self.error("source_truncated")
                return records
            with self.path.open("rb") as stream:
                stream.seek(self.offset)
                while self.offset < min(size, self.max_bytes):
                    chunk = stream.read(min(65536, self.max_bytes - self.offset))
                    if not chunk:
                        break
                    self.offset += len(chunk)
                    self.pending += chunk
                    while b"\n" in self.pending:
                        line, self.pending = self.pending.split(b"\n", 1)
                        self.seq += 1
                        if self.discarding or len(line) > self.max_line:
                            self.error("line_limit")
                            self.discarding = False
                            continue
                        self.parse(line, records)
                    if len(self.pending) > self.max_line:
                        self.pending = b""
                        self.discarding = True
                if size > self.max_bytes:
                    self.error("source_byte_limit")
        except OSError:
            self.error("source_unavailable")
            return records
        if final and self.pending:
            self.seq += 1
            if self.discarding:
                self.error("line_limit")
            else:
                self.parse(self.pending, records)
            self.pending = b""
        return records

    def parse(self, line, records):
        if not line.strip():
            return
        try:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError()
            records.append((self.seq, value))
        except (ValueError, UnicodeError):
            self.error("invalid_json")
