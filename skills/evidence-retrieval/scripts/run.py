"""Run this Skill's common-code operations; no LLM invocation."""
import argparse
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[3]
OPERATIONS = ['doctor', 'prepare_planning_input', 'retrieve_reviews', 'retrieve_product_facts', 'select_evidence', 'match_product_scope']

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
