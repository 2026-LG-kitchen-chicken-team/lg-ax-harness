"""Run this Skill's common-code operations; no LLM invocation."""
import argparse
from pathlib import Path
import runpy
import sys

ROOT = next((p for p in Path(__file__).resolve().parents if (p / 'skills/manifest.json').is_file() and (p / 'product-tools/cli.py').is_file()), None)
if ROOT is None:
    raise SystemExit('Cannot locate the product bundle root')
OPERATIONS = ['get_work_instructions', 'evidence_inventory', 'read_evidence_batch', 'record_evidence_review', 'evidence_coverage', 'doctor', 'list_models', 'set_request_scope_policy', 'open_product_workflow', 'record_workflow_event', 'workflow_status', 'open_request', 'open_request_bundle', 'resolve_request', 'resolve_request_bundle', 'record_request_research', 'current_request', 'prepare_planning_input', 'retrieve_reviews', 'retrieve_product_facts', 'select_evidence', 'match_product_scope']

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=OPERATIONS)
    parser.add_argument('--input', default='-')
    parser.add_argument('--data')
    parser.add_argument('--db')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'product-tools'))
    sys.argv = [str(ROOT / 'product-tools/cli.py')]
    for flag, value in (('--data', args.data), ('--db', args.db)):
        if value is not None:
            sys.argv.extend([flag, value])
    sys.argv.extend([args.operation, '--input', args.input])
    runpy.run_path(str(ROOT / 'product-tools/cli.py'), run_name='__main__')

if __name__ == '__main__':
    main()
