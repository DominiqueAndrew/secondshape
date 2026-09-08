"""Reproduce a plan or independently check exported coordinates."""
import argparse
import json
from pathlib import Path

from .engine import demo_request, solve, validate_plan
from .proof import verify_export


def main():
    parser = argparse.ArgumentParser(description='SecondShape salvage planning')
    parser.add_argument('input', nargs='?', help='Input JSON; omit to use the illustrative example')
    parser.add_argument('--verify', action='store_true', help='Check an exported plan instead of solving')
    parser.add_argument('--output', help='Save JSON to this file')
    args = parser.parse_args()
    data = json.loads(Path(args.input).read_text()) if args.input else demo_request()
    if args.verify:
        result = verify_export(data)
    else:
        result = solve(data)
    text = json.dumps(result, indent=2, allow_nan=False) + '\n'
    if args.output:
        Path(args.output).write_text(text)
    else:
        print(text, end='')
    if args.verify and not result['valid']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
