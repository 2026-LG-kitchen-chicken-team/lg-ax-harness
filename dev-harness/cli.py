"""Project-local helpers; native agent operations remain in Codex/Claude."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib

from checks import safe_path, run_check, verify_receipt, write_json
from sync import sync_skills


def upstream(root: Path) -> Path:
    return safe_path(root, ".agents/skills/harness/scripts", must_exist=True)


def structure(root: Path) -> list[str]:
    sys.path.insert(0, str(upstream(root)))
    from validate import validate_project, read_frontmatter
    errors, _, count_roles, count_skills = validate_project(root)
    if (count_roles, count_skills) != (6, 9):
        errors.append(f"Expected six roles and nine Skills; found {count_roles}/{count_skills}")
    errors.extend(sync_skills(root, check=True))
    for path in sorted((root / ".claude/agents").glob("*.md")):
        try:
            fields = read_frontmatter(path.read_text(encoding="utf-8"))
            if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", fields["name"]):
                errors.append("Invalid Claude role name: " + path.name)
        except ValueError as exc:
            errors.append(str(exc))
    if len(list((root / ".claude/agents").glob("*.md"))) != 6:
        errors.append("Expected six Claude roles")
    manifest = json.loads((root / "vendor/codex-harness/import-manifest.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = safe_path(root, "vendor/codex-harness/" + entry["path"], must_exist=True)
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append("Vendor original changed: " + entry["path"])
    patches = json.loads((root / "vendor/codex-harness/patches.json").read_text(encoding="utf-8"))
    for entry in patches["active_files"]:
        path = safe_path(root, entry["path"], must_exist=True)
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            errors.append("Active OSS adaptation differs from patch record: " + entry["path"])
    old = list((root / ".agents/skills").glob("openspec-*/SKILL.md")) + list((root / ".claude/skills").glob("openspec-*/SKILL.md"))
    old += list((root / "openspec").rglob("*.*")) + list((root / "dev-harness").glob("*.mjs"))
    if old or (root / "package.json").exists():
        errors.append("Active OpenSpec files remain")
    return errors


def checked_result(root: Path, relative: str) -> Path:
    path = safe_path(root, relative, must_exist=True)
    data = json.loads(path.read_text(encoding="utf-8"))
    checks = data.get("checks", [])
    if data.get("status") == "completed":
        task = task_info(root, data["run_id"], data["task_id"])
        required = [x for x in checks if x.get("required", True)]
        if not required:
            raise ValueError("Completed result requires an executed required check")
        for check in checks:
            receipt = check.get("receipt")
            if not receipt:
                raise ValueError("Every completed check needs a receipt path")
            verified = verify_receipt(root, receipt, require_pass=check.get("required", True))
            expected = task_binding(data["run_id"], task)
            if verified.get("binding") != expected or verified["started_at"] < task["started_at"]:
                raise ValueError("Receipt does not belong to this task attempt")
            if not verified["inputs"]:
                raise ValueError("Completed task check must fingerprint its relevant code/input files")
            check.update(status="passed" if verified["status"] == "passed" else "failed",
                         command=verified["argv"], exit_code=verified["exit_code"],
                         evidence=f"{receipt}; exit={verified['exit_code']}; logs+inputs verified")
    target = safe_path(root, ".harness/validated-results/" + hashlib.sha256(path.read_bytes()).hexdigest() + ".json")
    write_json(target, data)
    return target


def task_info(root: Path, run: str, task: str) -> dict:
    for value in (run, task):
        if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", value):
            raise ValueError("Invalid run/task ID")
    plan = json.loads(safe_path(root, ".harness/runs/" + run + "/plan.json", must_exist=True).read_text(encoding="utf-8"))
    return next(x for x in plan["tasks"] if x["id"] == task)


def task_binding(run: str, task: dict) -> dict:
    if not task.get("started_at"):
        raise ValueError("Task has not started")
    return {"run_id": run, "task_id": task["id"], "attempt": task["attempts"],
            "agent_id": task["agent_id"], "contract_fingerprint": task["contract_fingerprint"]}


def ledger(root: Path, arguments: list[str]) -> int:
    if not arguments:
        raise ValueError("ledger command required")
    safe_path(root, ".harness/runs")
    arguments = list(arguments)
    for flag in ("--plan-file", "--result-file"):
        if flag in arguments:
            pos = arguments.index(flag) + 1
            if pos >= len(arguments):
                raise ValueError(f"Missing {flag} value")
            path = safe_path(root, arguments[pos], must_exist=True)
            if flag == "--result-file" and arguments[0] == "result":
                path = checked_result(root, arguments[pos])
            arguments[pos] = str(path)
    if arguments[0] == "resume":
        run = arguments[arguments.index("--run") + 1]
        previous = json.loads(safe_path(root, ".harness/runs/" + run + "/plan.json", must_exist=True).read_text(encoding="utf-8"))
        invalid = receipt_issues(root, run)
        if invalid:
            if "--plan-file" in arguments:
                replacement = json.loads(Path(arguments[arguments.index("--plan-file") + 1]).read_text(encoding="utf-8"))
            else:
                replacement = previous
            for task in replacement["tasks"]:
                if task["id"] in invalid:
                    context = task.setdefault("context", {})
                    context.setdefault("decisions", []).append("Required recheck: " + "; ".join(invalid[task["id"]]))
            override = safe_path(root, ".harness/resume-inputs/" + run + "-" + hashlib.sha256(json.dumps(invalid, sort_keys=True).encode()).hexdigest() + ".json")
            write_json(override, replacement)
            if "--plan-file" in arguments:
                arguments[arguments.index("--plan-file") + 1] = str(override)
            else:
                arguments.extend(["--plan-file", str(override)])
    return subprocess.run([sys.executable, "-B", str(upstream(root) / "run.py"), "--project", str(root), *arguments],
                          cwd=root, env={**os.environ, "PYTHONUTF8": "1"}, check=False).returncode


def receipt_issues(root: Path, run: str) -> dict[str, list[str]]:
    base = safe_path(root, ".harness/runs/" + run, must_exist=True)
    plan = json.loads((base / "plan.json").read_text(encoding="utf-8"))
    issues = {}
    for task in plan["tasks"]:
        if task["status"] != "completed":
            continue
        errors = []
        result = json.loads((base / ("task-" + task["id"]) / "result.json").read_text(encoding="utf-8"))
        binding_task, binding_run, source_result = task, run, result
        seen = set()
        while source_result.get("reused_from"):
            origin = source_result["reused_from"]
            binding_run = origin["run_id"]
            if (binding_run, origin["task_id"]) in seen:
                raise ValueError("Receipt source ancestry cycle")
            seen.add((binding_run, origin["task_id"]))
            binding_task = task_info(root, binding_run, origin["task_id"])
            source_result = json.loads(safe_path(root, ".harness/runs/" + binding_run + "/task-" + origin["task_id"] + "/result.json", must_exist=True).read_text(encoding="utf-8"))
        for check in result.get("checks", []):
            try:
                if not check.get("receipt"):
                    raise ValueError("Missing executed receipt")
                verified = verify_receipt(root, check["receipt"], require_pass=check.get("required", True))
                if verified.get("binding") != task_binding(binding_run, binding_task) or verified["started_at"] < binding_task["started_at"]:
                    raise ValueError("Receipt does not belong to accepted task attempt")
                if not verified["inputs"]:
                    raise ValueError("Accepted receipt lacks code/input fingerprints")
            except (ValueError, OSError, TypeError) as exc:
                errors.append(str(exc))
        if errors:
            issues[task["id"]] = errors
    return issues


def complete(root: Path, run: str) -> list[str]:
    sys.path.insert(0, str(upstream(root)))
    from run_checks import validate_completion
    errors = validate_completion(root, safe_path(root, ".harness/runs/" + run, must_exist=True))
    for task, issues in receipt_issues(root, run).items():
        errors.extend(task + ": " + error for error in issues)
    return errors


def packet(root: Path, run: str, task: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", run + "") or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", task):
        raise ValueError("Invalid run/task ID")
    base = ".harness/runs/" + run
    plan = json.loads(safe_path(root, base + "/plan.json", must_exist=True).read_text(encoding="utf-8"))
    selected = next(x for x in plan["tasks"] if x["id"] == task)
    role = selected["role"]
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,62}", role):
        raise ValueError("Unknown project role")
    config = tomllib.loads(safe_path(root, ".codex/agents/" + role + ".toml", must_exist=True).read_text(encoding="utf-8"))
    body = safe_path(root, base + "/task-" + task + "/input.md", must_exist=True).read_text(encoding="utf-8")
    return "Role instruction fallback (not automatic TOML config enforcement):\n" + config["developer_instructions"] + "\n\n" + body


def main() -> int:
    # Windows console defaults can otherwise corrupt Korean paths in JSON/packets.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor")
    commands.add_parser("validate")
    sync = commands.add_parser("sync-claude")
    sync.add_argument("--check", action="store_true")
    check = commands.add_parser("check")
    check.add_argument("--cwd", default=".")
    check.add_argument("--input", action="append", default=[])
    check.add_argument("--timeout", type=float, default=60)
    check.add_argument("--max-output-bytes", type=int, default=1048576)
    check.add_argument("--run")
    check.add_argument("--task")
    check.add_argument("argv", nargs=argparse.REMAINDER)
    receipt = commands.add_parser("verify-receipt")
    receipt.add_argument("path")
    record = commands.add_parser("ledger")
    record.add_argument("arguments", nargs=argparse.REMAINDER)
    dispatch = commands.add_parser("packet")
    dispatch.add_argument("--run", required=True)
    dispatch.add_argument("--task", required=True)
    finished = commands.add_parser("complete")
    finished.add_argument("--run", required=True)
    args = parser.parse_args()
    try:
        root = args.project.resolve(strict=True)
        if args.command in {"doctor", "validate"}:
            errors = structure(root)
            info = {"python": sys.version.split()[0], "python_executable": sys.executable,
                    "codex": shutil.which("codex"), "claude": shutil.which("claude"),
                    "agents": 6, "skills": 9, "errors": errors, "scope": "static files; native acceptance separate"}
            print(json.dumps(info, ensure_ascii=False, indent=2))
            return 1 if errors else 0
        if args.command == "sync-claude":
            errors = sync_skills(root, check=args.check)
            print(json.dumps({"mode": "check" if args.check else "write", "errors": errors}, ensure_ascii=False))
            return 1 if errors else 0
        if args.command == "check":
            argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            if bool(args.run) != bool(args.task):
                raise ValueError("Use --run and --task together")
            binding = None
            if args.run:
                info = task_info(root, args.run, args.task)
                if info["status"] != "running":
                    raise ValueError("Bound check requires a running task")
                binding = task_binding(args.run, info)
            data, path = run_check(root, argv, cwd=args.cwd, inputs=args.input,
                                   timeout=args.timeout, max_output_bytes=args.max_output_bytes, binding=binding)
            print(json.dumps({"receipt": path, **data}, ensure_ascii=False, indent=2))
            return 0 if data["status"] == "passed" else 1
        if args.command == "verify-receipt":
            print(json.dumps(verify_receipt(root, args.path), ensure_ascii=False, indent=2))
            return 0
        if args.command == "ledger":
            return ledger(root, args.arguments)
        if args.command == "complete":
            errors = complete(root, args.run)
            print(json.dumps({"run": args.run, "errors": errors, "scope": "ledger and current receipts; native observation separate"}, ensure_ascii=False, indent=2))
            return 1 if errors else 0
        print(packet(root, args.run, args.task))
        return 0
    except (OSError, ValueError, KeyError, StopIteration, TypeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
