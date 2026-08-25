"""Command-line surface.

Exit statuses are part of the contract, because CI depends on them:
0 success, 1 the repository was rejected, 2 the invocation was wrong.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional

from . import HarrierError, find_root
from .chain import Chain
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

    chain = sub.add_parser(
        "chain",
        help="show what a unit needs, what it gives, and what a positive result opens up",
    )
    chain.add_argument("unit", nargs="?", metavar="UNIT-ID", help="a unit identifier; omit for a summary")
    chain.add_argument("--fact", metavar="FACT-ID", help="show which units produce and consume one fact")
    return parser


def _chain(root, args) -> int:
    """Print one view of the derived graph. Never writes: the graph is not stored."""
    chain = Chain.load(root)
    if args.fact:
        if args.fact not in chain.facts:
            print(f"harrier: no such fact: {args.fact}", file=sys.stderr)
            return EXIT_FAILED
        fact = chain.facts[args.fact]
        print(f"{fact['id']}  {fact['label']}" + ("  [given]" if fact.get("given") else ""))
        for label, ids in (
            ("established by", chain.producers.get(args.fact, [])),
            ("needed by", chain.consumers.get(args.fact, [])),
        ):
            print(f"  {label}:")
            for uid in sorted(ids):
                print(f"    {uid}")
            if not ids:
                print("    (nothing yet)")
        return EXIT_OK

    if args.unit:
        if args.unit not in chain.nodes:
            print(f"harrier: no such unit: {args.unit}", file=sys.stderr)
            return EXIT_FAILED
        node = chain.nodes[args.unit]
        print(f"{node.id}  {node.title}")
        for label, ids in (
            ("requires all of", node.all_of),
            ("requires any of", node.any_of),
            ("motivated by", node.motivated_by),
            ("yields", node.yields),
        ):
            if ids:
                print(f"  {label}: {', '.join(ids)}")
        onward = chain.next_after(args.unit)
        for label in ("unlocks", "motivates"):
            if onward[label]:
                print(f"  {label}:")
                for nxt in onward[label]:
                    print(f"    {nxt.id}  {nxt.title}")
        return EXIT_OK

    given = chain.given()
    print(f"facts            {len(chain.facts)}")
    print(f"units charted    {chain.charted()} of {len(chain.nodes)}")
    print(f"given facts      {len(given)}")
    print(f"available at start {len(chain.available(given))}")
    return EXIT_OK


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
        if args.command == "chain":
            return _chain(root, args)
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
