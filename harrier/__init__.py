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
__version__ = "0.3.0"

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
