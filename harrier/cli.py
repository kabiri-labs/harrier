"""Command-line surface.

Exit statuses are part of the contract, because CI depends on them:
0 success, 1 the repository was rejected, 2 the invocation was wrong.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from . import HarrierError, __version__, find_root
from .build import build
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
        "--version", action="version", version=f"harrier {__version__}"
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

    artefact = sub.add_parser(
        "build", help="write the published artefact: one self-contained HTML file"
    )
    artefact.add_argument(
        "-o", "--output", metavar="FILE", default="harrier.html",
        help="where to write it (default: harrier.html)",
    )

    chain = sub.add_parser(
        "chain",
        help="show what a test needs, what success establishes, and what may follow",
    )
    chain.add_argument("unit", nargs="?", metavar="UNIT-ID", help="a unit identifier; omit for a summary")
    chain.add_argument(
        "--fact", metavar="FACT-ID",
        help="show which tests establish one capability and which declare a use for it",
    )
    return parser


def _chain(root, args) -> int:
    """Print one view of the derived graph. Never writes: the graph is not stored.

    Everything printed is generic, and the wording has to keep saying so. A
    continuation is a statement about two tests -- *if this succeeds, that may
    become relevant* -- never a claim that it is now possible, and never a claim
    about a target. The command line has no more idea what is true of an
    application than the published artefact does, and it reads the same
    derivation so the two cannot describe different models.
    """
    chain = Chain.load(root)

    if args.fact:
        if args.fact not in chain.facts:
            print(f"harrier: no such capability: {args.fact}", file=sys.stderr)
            return EXIT_FAILED
        fact = chain.facts[args.fact]
        note = " [given]" if fact.get("given") else (" [granted]" if fact.get("granted") else "")
        print(f"{fact['id']}  {fact['label']}{note}")
        for label, ids in (
            ("established by", chain.producers.get(args.fact, [])),
            ("required by", chain.consumers.get(args.fact, [])),
            ("makes worth doing sooner", chain.motivates.get(args.fact, [])),
        ):
            print(f"  {label}:")
            for uid in sorted(ids):
                print(f"    {uid}  {chain.nodes[uid].title}")
            if not ids:
                print("    (nothing yet)")
        if not chain.consumers.get(args.fact) and not chain.motivates.get(args.fact):
            print("  no test declares a use for this: a chain reaching it stops here")
        return EXIT_OK

    if args.unit:
        index = chain.index()

        if args.unit not in chain.nodes:
            print(f"harrier: no such test: {args.unit}", file=sys.stderr)
            return EXIT_FAILED
        node = chain.nodes[args.unit]
        edge = index[args.unit]
        label = lambda fid: chain.facts.get(fid, {}).get("label", fid)

        print(f"{node.id}  {node.title}")
        for heading, ids in (
            ("prerequisite (all of)", node.all_of),
            ("prerequisite (any of)", node.any_of),
            ("worth doing sooner given", node.motivated_by),
        ):
            for fid in ids:
                producers = [u for u in chain.producers.get(fid, []) if u != node.id]
                route = (
                    "given -- a root of the graph"
                    if fid in chain.given()
                    else f"{len(producers)} test(s) establish it"
                    if producers
                    else "no test establishes it"
                )
                print(f"  {heading}: {label(fid)}  [{fid}] -- {route}")
        for fid in edge["yields"]:
            print(f"  success establishes: {label(fid)}  [{fid}]")

        if edge["out"]:
            print("  potential continuations:")
            for link in edge["out"]:
                other = chain.nodes[link["unit"]]
                via = link["via"] or link.get("hint") or []
                how = "requires" if link["kind"] == "requires" else "motivated by"
                print(f"    {other.id}  {other.title}")
                print(f"      {how} what this establishes: {', '.join(label(f) for f in via)}")
                also = link["also"]
                if also:
                    parts = [label(f) for f in also.get("all_of", [])]
                    if also.get("any_of"):
                        parts.append(
                            "any one of " + ", ".join(label(f) for f in also["any_of"])
                        )
                    print(f"      still required: {'; '.join(parts)}")
                else:
                    print("      no additional declared hard prerequisite")
        for item in edge["terminal"]:
            reason = (
                "an impact -- a chain ends here"
                if item["why"] == "impact"
                else "no test declares a use for it -- a reportable outcome"
            )
            print(f"  terminal: {label(item['fact'])}  [{item['fact']}] -- {reason}")
        if not edge["out"] and not edge["terminal"]:
            print("  this test declares no capability, so nothing is derived from it")
        return EXIT_OK

    reach = chain.reach()
    dead = chain.dead_ends()
    print(f"capabilities        {len(chain.facts)}")
    print(f"  impacts           {len(chain.impacts())}  terminal by construction")
    print(f"  dead ends         {len(dead)}  established by a test, used by none")
    print(f"tests               {len(chain.nodes)}")
    print(f"  charted           {chain.charted()}")
    print(f"  with a continuation {reach['continuation']}")
    print(f"  establishing an impact {reach['impact']}")
    print(f"  stopping short    {reach['short']}  the chart does not go on from here")
    print(f"  declaring nothing {reach['uncharted']}")
    print(f"given               {len(chain.given())}")
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
        if args.command == "build":
            target = build(root, Path(args.output))
            size = target.stat().st_size
            print(f"harrier: wrote {target} ({size // 1024} KiB)")
            return EXIT_OK
        if args.command == "chain":
            return _chain(root, args)
        if args.command == "coverage":
            for key, value in coverage(root).items():
                print(f"{key:16} {value}")
            return EXIT_OK
    except BrokenPipeError:
        # Piping into head or less closes the stream early. That is the reader's
        # decision, not an error, and a traceback here would be the first thing
        # a tester saw from a tool they piped out of habit.
        try:
            sys.stdout.close()
        finally:
            return EXIT_OK
    except HarrierError as exc:
        print(f"harrier: {exc}", file=sys.stderr)
        return EXIT_FAILED
    return EXIT_USAGE


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
