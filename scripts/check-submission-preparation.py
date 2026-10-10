"""Check the reviewable demo plan only, never certify filming or final submission."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check():
    plan = json.loads((ROOT / "submission/demo-plan.json").read_text(encoding="utf-8"))
    slides = plan["slides"]
    errors = []
    if plan["status"] != "preparation_only" or plan["recorded_video"] is not False or plan["actual_rehearsal"] is not False:
        errors.append("This preparation source cannot certify unobserved filming/rehearsal")
    if not 1 <= len(slides) <= 20 or [r["page"] for r in slides] != list(range(1, len(slides) + 1)):
        errors.append("Page count/order invalid")
    if any(type(r["seconds"]) is not int or r["seconds"] <= 0 for r in slides):
        errors.append("Invalid planned duration")
    total = sum(r["seconds"] for r in slides)
    if total != plan["planned_seconds"] or total > 600:
        errors.append("Planned presentation exceeds ten minutes or total mismatch")
    required = {"C" + str(i).zfill(2) for i in range(1, 10)}
    if {cid for slide in slides for cid in slide["requirements"]} != required:
        errors.append("C01-C09 coverage mismatch")
    for slide in slides:
        if not slide["evidence"]:
            errors.append("Slide has no evidence path")
        for name in slide["evidence"]:
            path = (ROOT / name).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file() or ".harness" in path.parts or "runtime-data" in path.parts:
                errors.append("Unsupported evidence path: " + name)
    return {"errors": errors, "pages": len(slides), "planned_seconds": total, "scope": "Preparation structure/path check only; facts, actual timing/filming and final submission require review"}


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(int(bool(result["errors"])))
