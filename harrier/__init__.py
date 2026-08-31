"""Harrier -- the loading layer and repository layout.

The loader lives here rather than in the validator so that the catalogue is
parsed exactly once per process and in exactly one way. Anything that reads the
repository -- the validator today, the artefact builder later -- reads it through
this module, so no consumer can accept a document another consumer would read
differently.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple

import yaml

try:  # pragma: no cover - depends on whether PyYAML was built against libyaml
    from yaml import CSafeLoader as _SafeLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader as _SafeLoader

#: The only loader this package ever uses. Both branches are *safe* loaders --
#: the C one is the same grammar and the same restrictions, implemented in
#: libyaml, and it parses the pinned standards several times faster. Neither can
#: construct arbitrary Python objects, which is the property that matters.
SAFE_LOADER = _SafeLoader

#: Versioning starts with the published artefact and tracks it, because it is
#: the only thing anybody consumes. A change that alters what the artefact says
#: bumps this; a change to the tests, the documents or the validator's internals
#: does not. Not 1.0: that needs two topics written to full depth, and one is.
#:
#: 0.4.0 is a breaking change to the artefact rather than a feature on top of
#: 0.3.0 -- the engagement board and every run file it wrote are gone. Minor
#: rather than major because the project is pre-1.0 and this is exactly the
#: period in which such a change is meant to be taken. See docs/PIVOT.md.
#:
#: 0.5.0 gives every fact a tier, so that the three different relations the
#: derived graph has always contained stop printing under one heading. No edge
#: was added or removed; what changed is that a reader can now tell an
#: escalation from the prerequisite it used to sort beneath.
#:
#: 0.6.0 gives every unit a role. A topic listed its units flat, so "perform all
#: of these" and "pick one of these" -- opposite instructions -- were rendered
#: identically, and the list had to be opened unit by unit to be read.
#:
#: 0.7.0 gives HRR-ACL-04 the stage it never had. The topic offered three
#: escalation routes and nothing that established what any of them attacks, so
#: a tester was asked to choose before there was anything to choose between.
#:
#: 0.8.0 links the standard in both directions. The catalogue could always say
#: which test cases a topic claims and never which units cover a test case --
#: derivable, but reachable only from inside the built file, which is not the
#: same as available.
#:
#: 0.8.1 makes the index resolve. It was schema-checked and not reference-checked,
#: which for a derived file is the difference between a document and a claim.
#:
#: 0.9.0 gives the chain somewhere to arrive. Twenty-five capabilities were
#: established by a test and declared as a use by nothing, so most chains ended
#: at the capability that reached them; the outcome layer is what they end at
#: now, and it asks what the capability obtained rather than asserting it.
#:
#: 0.10.0 puts a tier between an outline and a unit written in full. The two it
#: had are five minutes apart and two hours apart, so nothing sat between them
#: and the depth figure read as further from the truth than it is. A sketch
#: carries what it takes to run the test and recognise a wrong answer; what it
#: takes to claim either of the tiers above it is now checked rather than
#: trusted.
#:
#: 0.11.0 sketches the seventeen topics an engagement opens with. Reconnaissance
#: and configuration were the thinnest part of the catalogue and the first part
#: anybody reads, which is the worst combination: 38 units across RCN, CFG, ERR
#: and PRT now carry the procedure, the reading of a result and the thing that
#: most often imitates one.
#:
#: 0.12.0 gives a unit somewhere to say where to start. Every field it had
#: described the test -- what it is for, how to run it, how to read the answer
#: -- and none described the target: the parameter naming and the endpoint
#: shapes that make one test worth reaching for before another. That sentence
#: is also the only way into the catalogue that does not begin at the standard,
#: so it is searched.
#:
#: 0.13.0 makes the page named for attack chains be about them. It opened on a
#: matrix that said in its own second sentence that it drew no route, which is
#: a page taking its name back; that matrix counts tests per pair of families
#: and belongs with the other figures about the catalogue. What replaces it is
#: the model as a picture -- every capability in a column for what kind of
#: thing it is, shaded by how far the chart reaches from it, each one a way
#: into the routes that run through it.
#:
#: 0.13.1 fixes a test that measured a transient. The sticky column heading
#: takes its offset from a resize observer, which reports after layout rather
#: than during it, so for a frame after the viewport changes the offset still
#: holds the previous width's header height. The check asserted the settled
#: state without waiting for it and failed about once in fifteen runs at the
#: width where the header wraps -- a red build that said nothing about the
#: artefact, which is the kind that teaches people to re-run rather than read.
#:
#: 0.14.0 gives the chains somewhere to end. Every route in the catalogue
#: stopped at a capability: a tester who confirmed a read, a write to another
#: party's record, or execution in somebody else's browser had established a
#: primitive and had nowhere that said what it was worth. The three terminal
#: outcome units are written to full depth, once for the whole catalogue rather
#: than for one topic, with the card that decides how much is enough to answer
#: the question -- the smallest observation, agreed before the first read.
#:
#: 0.15.0 writes the supporting layer for SQL injection: two cards split by what
#: their units reason about rather than by identifier, and the mitigation keyed
#: to the weakness. Two payload entries were wrong and running them is what
#: showed it -- a balanced probe and an engine fingerprint that both errored on
#: the engines they claimed, neither of which a reading would have caught.
#:
#: 0.16.0 takes the nine remaining SQL injection units to full depth, which
#: makes HRR-INJ-01 the first topic readable end to end: WSTG-INPV-05 to a
#: probe that names the context, to seven non-substitutable techniques, to an
#: outcome unit that asks what the reachable data was worth. The decomposition
#: argument the README makes is now demonstrated rather than asserted.
__version__ = "0.16.0"

__all__ = [
    "SAFE_LOADER",
    "__version__",
    "STANDARD_SCHEMAS",
    "HarrierError",
    "Repository",
    "find_root",
    "load_yaml",
]

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"

#: Which schema applies to each file under standards/. Explicit rather than
#: derived, so a new standard cannot be added without deciding how it is checked
#: -- an unrecognised file there would otherwise be loaded and silently trusted.
STANDARD_SCHEMAS = {
    "wstg": "standard",
    "wstg-map": "wstg-map",
    "wstg-index": "wstg-index",
    "asvs": "asvs",
    "cwe": "cwe",
}

#: Directories that make up a loadable repository. Used to locate the root from
#: any working directory inside a checkout.
MARKER_DIRS = ("vocab", "knowledge", "standards")


class HarrierError(Exception):
    """A condition the caller can act on: bad input, missing file, broken reference.

    Raised instead of letting an arbitrary exception escape, so the command line
    can exit with a message and a status rather than a traceback.
    """


def find_root(start: str | os.PathLike[str] | None = None) -> Path:
    """Return the repository root: the nearest ancestor holding the marker directories.

    Walking upwards means the command works from anywhere inside a checkout.
    """
    here = Path(start).resolve() if start else Path.cwd().resolve()
    if here.is_file():
        here = here.parent
    for candidate in (here, *here.parents):
        if all((candidate / d).is_dir() for d in MARKER_DIRS):
            return candidate
    raise HarrierError(
        f"no Harrier repository found at or above {here} "
        f"(expected sibling {', '.join(MARKER_DIRS)} directories)"
    )


def load_yaml(path: Path) -> Any:
    """Parse one YAML document, safely.

    ``safe_load`` rather than ``load`` is a security decision, not a style one.
    The catalogue is contributor-submitted YAML; full loading would let a
    document construct arbitrary Python objects at parse time, turning the
    repository into a code-execution channel into every contributor's machine
    and into CI.
    """
    try:
        with path.open(encoding="utf-8") as handle:
            return yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise HarrierError(f"{path}: not valid YAML: {exc}") from exc
    except OSError as exc:
        raise HarrierError(f"{path}: cannot be read: {exc}") from exc


@dataclass
class Document:
    """One parsed file, kept with its path so every message can name its source."""

    path: Path
    data: Any

    @property
    def rel(self) -> str:
        return str(self.path)


@dataclass
class Repository:
    """Every document in one checkout, parsed once.

    Collections are kept separate rather than merged into one bag because the
    schema that applies is decided by location, and a document in the wrong
    directory is itself a finding.
    """

    root: Path
    vocab: Dict[str, Document] = field(default_factory=dict)
    standards: Dict[str, Document] = field(default_factory=dict)
    topics: List[Document] = field(default_factory=list)
    units: List[Document] = field(default_factory=list)
    payloads: List[Document] = field(default_factory=list)
    toolbox: List[Document] = field(default_factory=list)
    #: Files whose name says nothing about what they are: under knowledge/, or a
    #: standards/ file with no schema. Collected rather than raised on, so one
    #: structural error cannot hide every other problem in the repository.
    unrecognised: List[Path] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path) -> "Repository":
        repo = cls(root=root)
        for path in sorted((root / "vocab").glob("*.yaml")):
            repo.vocab[path.stem] = Document(path, load_yaml(path))
        for path in sorted((root / "standards").glob("*.yaml")):
            repo.standards[path.stem] = Document(path, load_yaml(path))
            if path.stem not in STANDARD_SCHEMAS:
                repo.unrecognised.append(path)
        for path in sorted((root / "knowledge").rglob("*.yaml")):
            doc = Document(path, load_yaml(path))
            if path.name.endswith(".topic.yaml"):
                repo.topics.append(doc)
            elif path.name.endswith(".unit.yaml"):
                repo.units.append(doc)
            else:
                repo.unrecognised.append(path)
        payload_dir = root / "payloads"
        if payload_dir.is_dir():
            for path in sorted(payload_dir.rglob("*.yaml")):
                repo.payloads.append(Document(path, load_yaml(path)))
        registry = root / "toolbox" / "registry.yaml"
        if registry.is_file():
            repo.toolbox.append(Document(registry, load_yaml(registry)))
        return repo

    def documents(self) -> Iterator[Tuple[str, Document]]:
        """Yield ``(schema name, document)`` for every file that has a schema."""
        for name, doc in self.vocab.items():
            yield "vocab", doc
        for name, doc in self.standards.items():
            schema = STANDARD_SCHEMAS.get(name)
            if schema is not None:
                yield schema, doc
        for doc in self.topics:
            yield "topic", doc
        for doc in self.units:
            yield "unit", doc
        for doc in self.payloads:
            yield "payloads", doc
        for doc in self.toolbox:
            yield "toolbox", doc
