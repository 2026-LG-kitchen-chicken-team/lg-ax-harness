"""Record source fingerprints; does not install or discover native skills."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {
    "evidence-retrieval": ["doctor", "list_models", "set_request_scope_policy", "open_product_workflow", "record_workflow_event", "workflow_status", "open_request", "open_request_bundle", "resolve_request", "resolve_request_bundle", "record_request_research", "current_request", "prepare_planning_input", "retrieve_reviews", "retrieve_product_facts", "select_evidence", "match_product_scope", "evidence_inventory", "read_evidence_batch", "record_evidence_review", "evidence_coverage"],
    "web-evidence-collection": ["fetch_web_page", "capture_web_page", "import_web_evidence", "configure_web_research", "import_web_evidence_bulk"],
    "needs-structuring": ["select_evidence", "validate_source_refs"],
    "feature-comparison": ["match_product_scope", "retrieve_product_facts", "select_evidence"],
    "concept-writing": ["validate_constraints", "validate_source_refs"],
    "review-and-revise": ["validate_result_contract", "review_product_result", "start_turn", "get_turn", "save_result", "save_reviewed_result", "save_and_export", "prepare_web_result", "get_completion_summary", "deliver_result", "export_session", "current_request", "record_usage", "cancel_turn", "begin_invocation", "finish_invocation", "prepare_review_packet", "verify_review_packet"],
}
for operations in TOOLS.values():
    operations.insert(0, "get_work_instructions")


def build():
    skills = []
    for name, operations in TOOLS.items():
        path = ROOT / "skills" / name / "SKILL.md"
        body = path.read_text(encoding="utf-8")
        description = re.search(r'^description: "(.+)"$', body, re.M).group(1)
        files = [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                 for p in sorted(path.parent.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
        skills.append({"name": name, "description": description, "path": path.relative_to(ROOT).as_posix(), "operations": operations, "files": files})
    roles = ["agents/product-evidence-reviewer.md", "agents/product-official-researcher.md", "agents/product-review-researcher.md"]
    common = [ROOT / "agents/product-planning.md", *[ROOT / p for p in roles], ROOT / "product-tools/cli.py", *sorted((ROOT / "product-tools/product_tools").glob("*.py")),
              ROOT / "docs/contracts/common-tools.md", ROOT / "docs/contracts/product-planning.md", ROOT / "docs/contracts/web-evidence.md", ROOT / "docs/contracts/codex-product.md",
              ROOT / "docs/contracts/reader-deliverables.md", ROOT / "docs/contracts/product-workflow.md", ROOT / "docs/contracts/instruction-loading.md", ROOT / "product-tools/requirements.in", ROOT / "product-tools/requirements.lock",
              ROOT / "docs/contracts/product-reviewer-packet.md", ROOT / "docs/contracts/product-research-agents.md", ROOT / "docs/contracts/web-result.md", ROOT / "docs/contracts/runtime-access.md",
              *[ROOT / "web/prototypes/visual-viewer" / name for name in ("README.md", "viewer.py", "hook.py", "build_view.py", "index.html")],
              *[ROOT / "web/prototypes/agent-office" / name for name in ("README.md", "office.py", "observe.py", "codex_follow.py", "index.html", "factory.html")],
              ROOT / "docs/contracts/judge-test.md"]
    return {"version": "product-skills-v1", "agent": "agents/product-planning.md", "data_path": "data/business/empty", "skills": skills,
            "shared_files": [{"path": p.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in common],
            "optional_agents": roles, "native_installation_verified": False, "native_discovery_verified": False}


if __name__ == "__main__":
    (ROOT / "skills/manifest.json").write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("Recorded six product Skills and one main-Agent source; not a native installer.")
