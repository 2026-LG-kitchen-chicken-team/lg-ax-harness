"""Read selected logs only; never starts, stops or signals an execution process."""
import argparse
import json
from pathlib import Path
import sys
import time

from .collector import Collector, digest
from .otlp import Exporter
from .storage import JsonlReader, LocalStore


def collect(args, environment=None):
    output_root = Path(args.output).resolve()
    if any(Path(path).resolve().is_relative_to(output_root) for path in (args.cli_log, args.rollout_log) if path):
        raise ValueError("source_output_conflict")
    args.native_id = args.native_id.lower()
    store = LocalStore(args.output, args.local_limit)
    state = store.load(args.native_id, args.run_id)
    collector = Collector(args.native_id, args.run_id, args.mode, state)
    exporter = Exporter(store, environment=environment, timeout=args.http_timeout, capacity=args.queue_limit)
    readers = [(kind, JsonlReader(path), digest(str(Path(path).resolve())))
        for kind, path in (("cli", args.cli_log), ("rollout", args.rollout_log)) if path]
    exporter.start()
    started, stop_reason = time.monotonic(), "replay_finished"
    reader_errors = {}
    try:
        while True:
            terminal = False
            for kind, reader, reference in readers:
                for seq, raw in reader.poll(final=args.mode == "replay"):
                    # With both logs, CLI owns item observations; rollout supplies cumulative usage.
                    if len(readers) > 1 and kind == "rollout" and raw.get("type") == "response_item":
                        continue
                    event = collector.feed(raw, reference, seq, kind)
                    if event is None:
                        continue
                    if store.append(event):
                        # Save the checkpoint before any network attempt.
                        store.save(collector, {"export": exporter.summary()})
                        exporter.submit(event)
                    else:
                        collector.count("local_event_dropped")
                    terminal |= event["event_kind"] in ("turn.completed", "turn.failed", "task_complete", "turn_aborted")
                reader_errors[reference] = dict(reader.errors)
            if args.mode == "replay":
                break
            if args.stop_file and Path(args.stop_file).exists():
                stop_reason = "observer_stop_file"
                break
            if args.until_complete and terminal:
                stop_reason = "observed_terminal_event"
                break
            if time.monotonic() - started >= args.max_seconds:
                stop_reason = "observer_time_limit"
                break
            time.sleep(args.poll_seconds)
    except KeyboardInterrupt:
        stop_reason = "observer_interrupted"
    finally:
        exporter.close(grace=min(args.http_timeout + 0.2, 3))
        store.save(collector, {"export": exporter.summary(), "reader_errors": reader_errors, "stop_reason": stop_reason})
    return {**collector.summary(), "export": exporter.summary(), "reader_errors": reader_errors, "stop_reason": stop_reason}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Separate metadata-only observer; no native/model launch")
    parser.add_argument("mode", choices=("replay", "tail"))
    parser.add_argument("--native-id", required=True, help="Explicit native UUID; source must report this identity")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cli-log", help="Existing Codex exec --json JSONL")
    parser.add_argument("--rollout-log", help="Explicit ID-selected Codex rollout JSONL; no directory scan")
    parser.add_argument("--output", required=True, help="Private local observer directory, preferably below .harness")
    parser.add_argument("--stop-file", help="Existing sentinel stops only this observer")
    parser.add_argument("--until-complete", action="store_true")
    parser.add_argument("--max-seconds", type=float, default=60)
    parser.add_argument("--poll-seconds", type=float, default=0.2)
    parser.add_argument("--http-timeout", type=float, default=2)
    parser.add_argument("--queue-limit", type=int, default=128)
    parser.add_argument("--local-limit", type=int, default=4 * 1024 * 1024)
    args = parser.parse_args(argv)
    if not args.cli_log and not args.rollout_log:
        parser.error("select_at_least_one_log")
    if not 0.01 <= args.max_seconds <= 3600 or not 0.01 <= args.poll_seconds <= 5:
        parser.error("invalid_tail_bounds")
    try:
        result = collect(args)
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"status": "observer_failed", "reason": "local_or_configuration_error"}))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["counters"].get("accepted_events", 0) else 1


if __name__ == "__main__":
    sys.exit(main())
