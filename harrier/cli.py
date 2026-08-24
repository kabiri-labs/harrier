"""Command-line surface.

Exit statuses are part of the contract, because CI depends on them:
0 success, 1 the repository was rejected, 2 the invocation was wrong.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import HarrierError, find_root
from .validate import coverage, validate

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m harrier",
        description="Harrier -- validate the taxonomy and its vocabularies.",
    )
    parser.add_argument(
        "--root",
        metavar="DIR",
        help="repository root (default: the nearest ancestor holding vocab/, knowledge/ and standards/)",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    check = sub.add_parser(
        "validate", help="check every document against its schema and resolve every reference"
    )
    check.add_argument("-q", "--quiet", action="store_true", help="print nothing on success")

    sub.add_parser("coverage", help="print the counts the roadmap reports")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_USAGE

    try:
        root = find_root(args.root)
        if args.command == "validate":
            problems = validate(root)
            if problems:
                for item in problems.items:
                    print(f"harrier: {item}", file=sys.stderr)
                print(
                    f"harrier: {len(problems)} problem(s) in {root}", file=sys.stderr
                )
                return EXIT_FAILED
            if not args.quiet:
                print(f"harrier: {root} is valid")
            return EXIT_OK
        if args.command == "coverage":
            for key, value in coverage(root).items():
                print(f"{key:16} {value}")
            return EXIT_OK
    except HarrierError as exc:
        print(f"harrier: {exc}", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
