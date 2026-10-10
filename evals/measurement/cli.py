"""Run with Python only; records human measurements and never invokes an AI."""
import argparse
import json
from pathlib import Path
import sys

from measurement import CONDITIONS, PHASES, Store, atomic_create, compare, file_sha, prepare, report, validate_event_fields


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, help="Private measurement root, default .harness/measurement")
    commands = parser.add_subparsers(dest="command", required=True)
    kit = commands.add_parser("prepare")
    kit.add_argument("--out", type=Path, required=True)
    kit.add_argument("--participant", required=True)
    kit.add_argument("--condition", choices=CONDITIONS, required=True)
    kit.add_argument("--order", default="manual,general_ai,harness")
    kit.add_argument("--model-settings", type=Path, help="Actual model/CLI/settings JSON; AI conditions only")
    kit.add_argument("--attempt", type=int, default=1)
    init = commands.add_parser("init")
    init.add_argument("--metadata", type=Path, required=True)
    for name in ("start", "pause", "finish", "billing", "usage", "quality"):
        cmd = commands.add_parser(name)
        if name in ("start", "pause", "finish"):
            cmd.add_argument("--participant", required=True)
        if name == "start":
            cmd.add_argument("--phase", choices=PHASES, required=True)
        if name == "finish":
            cmd.add_argument("--outcome", choices=("completed", "held", "failed", "aborted"), required=True)
            cmd.add_argument("--result", type=Path)
            cmd.add_argument("--additional-inputs", type=int)
            cmd.add_argument("--revisions", type=int)
        if name in ("billing", "usage", "quality"):
            cmd.add_argument("--input", type=Path, required=True)
            cmd.add_argument("--evidence", type=Path)
        cmd.add_argument("--event-id", help="Reuse only for exactly identical payload; conflicts are preserved")
    for cmd in (init, *[commands.choices[n] for n in ("start", "pause", "finish", "billing", "usage", "quality")]):
        cmd.add_argument("--run", required=True)
        cmd.add_argument("--human-confirmed", action="store_true", help="I am the human participant/reviewer performing this action")
    output = commands.add_parser("report")
    output.add_argument("--run", required=True)
    output.add_argument("--out", type=Path, required=True)
    pair = commands.add_parser("compare")
    pair.add_argument("--baseline", required=True)
    pair.add_argument("--candidate", required=True)
    pair.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    store = Store(args.root)
    try:
        if args.command == "prepare":
            settings = json.loads(args.model_settings.read_text(encoding="utf-8-sig")) if args.model_settings else None
            prepare(args.out, args.participant, args.condition, args.order.split(","), settings, args.attempt)
            result = {"status": "prepared", "metadata_sha256": file_sha(args.out / "metadata.json"), "task_sha256": file_sha(args.out / "task.json")}
        elif args.command == "init":
            store.create(args.run, json.loads(args.metadata.read_text(encoding="utf-8-sig")), args.human_confirmed)
            result = {"status": "created", "run_id": args.run}
        elif args.command in ("report", "compare"):
            result = report(store, args.run) if args.command == "report" else compare(report(store, args.baseline), report(store, args.candidate))
            atomic_create(args.out, result)
            result = {"status": "exported", "command": args.command, "sha256": file_sha(args.out)}
        else:
            data = {"kind": args.command}
            if args.command in ("start", "pause", "finish"):
                data["participant"] = args.participant
            if args.command == "start":
                data["phase"] = args.phase
            elif args.command == "finish":
                data.update(outcome=args.outcome, result_sha256=file_sha(args.result) if args.result else None,
                            additional_inputs=args.additional_inputs, revisions=args.revisions)
            elif args.command in ("billing", "usage", "quality"):
                data.update(json.loads(args.input.read_text(encoding="utf-8-sig")))
                if data.get("kind") != args.command:
                    raise ValueError("Input kind must match command")
                validate_event_fields(data)  # reject extras before reading evidence or preserving conflicts
                if args.evidence:
                    data["evidence_sha256"] = file_sha(args.evidence)
                else:
                    data["evidence_sha256"] = None
            event = store.append(args.run, data, args.event_id, args.human_confirmed)
            result = {"status": "recorded", "run_id": args.run, "event_id": event["event_id"],
                      "sequence": event["sequence"], "sha256": event["sha256"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, StopIteration) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
