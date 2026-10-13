"""Replay an actual saved report offline; no model call and no browser opening."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--viewer", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Output must be a new directory; existing observations are preserved")
    args.out.mkdir(parents=True)
    started = time.perf_counter()
    sys.path.insert(0, str(args.workspace / "product-tools"))
    from product_tools import reporting
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    rows = []
    names = ("validate_report_plan", "_deps", "_adapt_plan", "_write_libraries", "_write_docx", "_write_pdf", "_verify")
    originals = {name: getattr(reporting, name) for name in names}
    current = {}
    for name, original in originals.items():
        def timed(*positional, _name=name, _original=original, **keyword):
            begin = time.perf_counter()
            try:
                return _original(*positional, **keyword)
            finally:
                current[_name] = current.get(_name, 0) + time.perf_counter() - begin
        setattr(reporting, name, timed)
    setup_seconds = time.perf_counter() - started
    try:
        for index in range(2):
            current = {}
            begin = time.perf_counter()
            result = reporting.render_report(plan, args.out / ("report-" + str(index)))
            rows.append({"run": index + 1, "cache_condition": "first_process_render" if index == 0 else "same_process_repeat_new_output",
                "total_seconds": time.perf_counter() - begin, "stage_inclusive_seconds": current,
                "ready": result["ready"], "checks": result["checks"],
                "files": [{"suffix": Path(f["path"]).suffix, "bytes": Path(f["path"]).stat().st_size,
                           "sha256": digest(Path(f["path"]))} for f in result["files"]]})
    finally:
        for name, original in originals.items():
            setattr(reporting, name, original)
    html = []
    for index in range(2):
        begin = time.perf_counter()
        destination = args.out / ("html-" + str(index))
        invocation = subprocess.run([sys.executable, str(args.viewer), "--export", str(args.export),
            "--out-dir", str(destination), "--standalone", str(args.out / ("report-" + str(index) + ".html"))],
            capture_output=True, timeout=30)
        html.append({"run": index + 1, "total_seconds": time.perf_counter() - begin,
            "exit_code": invocation.returncode, "browser_paint": "not_measured",
            "files": [{"suffix": p.suffix, "bytes": p.stat().st_size, "sha256": digest(p)}
                for p in sorted(destination.glob("*")) if p.is_file()],
            "stderr": invocation.stderr.decode("utf-8", errors="replace")[:2000]})
    report = {"scope": "actual saved input offline replay, not fresh research or native execution", "model_calls": 0,
        "setup_seconds": setup_seconds, "plan_sha256": digest(args.plan), "export_sha256": digest(args.export),
        "renderer_sha256": digest(Path(reporting.__file__)), "viewer_sha256": digest(args.viewer),
        "source_count": len(plan.get("sources", [])), "reports": rows, "html": html,
        "limits": ["Stage times are inclusive, possibly nested; do not sum them as disjoint phases.",
                   "No semantic or physical layout verification; structure checks only.",
                   "Second render is same process, not the product report cache.",
                   "Only observed saved data scale; no large-corpus performance extrapolation."]}
    (args.out / "profile.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if all(r["ready"] for r in rows) and all(h["exit_code"] == 0 for h in html) else 1


if __name__ == "__main__":
    raise SystemExit(main())
