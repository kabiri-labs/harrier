"""The published artefact: one self-contained HTML file.

Everything the reader needs is embedded, because the file is opened from a
laptop on an engagement network and must not emit a request a monitored target
could observe. No stylesheet, no script, no font, no image is fetched. The data
travels as one JSON blob and the page renders from it.

The three views follow ARCHITECTURE.md section 8, in the order a tester meets
them: what is in front of me, what can I do with what I hold, and what did I
cover. The second is the working view, and it exists only because the chain
layer does.
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any, Dict, List

from . import Repository, __version__
from .chain import Chain
from .validate import coverage


#: Keys whose value is a literal to be copied and sent, not prose to be read.
#: Whitespace in them is syntax: a MySQL comment is "-- " and stops being one
#: without the trailing space, and a numeric-context probe starts with a space
#: because it is appended to a bare number.
VERBATIM = frozenset({"payload"})


def _text(value: Any) -> str:
    """Collapse the whitespace a folded YAML scalar leaves behind."""
    if not isinstance(value, str):
        return value
    return " ".join(value.split())


def _clean(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: (v if k in VERBATIM else _clean(v))
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_clean(v) for v in data]
    return _text(data)


def surface_closure(surfaces: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """For each surface tag, every tag it implies -- itself included.

    A tester names the thing in front of them, not the set of things it drags in
    with it. `login-form` is a session cookie whether or not they said so, and a
    search box is a database-backed parameter and a stored-then-rendered one.
    Closing this here rather than in the page keeps it testable, and keeps a
    cycle in the vocabulary from becoming an infinite loop in a browser on an
    engagement.
    """
    emits = {s["tag"]: list(s.get("emits") or []) for s in surfaces}
    closed: Dict[str, List[str]] = {}
    for tag in emits:
        seen = {tag}
        stack = list(emits[tag])
        while stack:
            nxt = stack.pop()
            # A tag already seen is a cycle or a diamond; either way there is
            # nothing further down it that is not already in hand.
            if nxt in seen or nxt not in emits:
                continue
            seen.add(nxt)
            stack.extend(emits[nxt])
        closed[tag] = sorted(seen)
    return closed


def surface_scope(
    surfaces: List[Dict[str, Any]], topics: Dict[str, Any]
) -> Dict[str, List[str]]:
    """Surface tag -> the topics that apply when a tester is looking at it.

    Topics marked `always` are left out on purpose. They apply to every target,
    so folding them into each tag would bury the handful of topics that are
    actually about the thing in front of the tester under the several dozen that
    are about any thing at all. The page shows them, separately and labelled.
    """
    closed = surface_closure(surfaces)
    scope: Dict[str, List[str]] = {}
    for tag, implied in closed.items():
        wanted = set(implied)
        scope[tag] = sorted(
            tid
            for tid, topic in topics.items()
            if wanted & set(((topic.get("surfaces") or {}).get("any_of") or []))
        )
    return scope


def catalogue(root: Path) -> Dict[str, Any]:
    """Everything the page renders, in the shape the page reads it.

    Assembled here rather than in the template so that what the artefact
    contains is reviewable as data, and so a second consumer -- a report
    generator, a coverage export -- can read the same structure.
    """
    repo = Repository.load(root)
    chain = Chain.load(root)

    topics = {d.data["id"]: _clean(d.data) for d in repo.topics}
    units = {d.data["id"]: _clean(d.data) for d in repo.units}

    # Cards and payloads travel with the units that name them: a card behind a
    # link the reader cannot follow is a card they do not have.
    cards: Dict[str, str] = {}
    payloads: Dict[str, Any] = {}
    mitigations: Dict[str, str] = {}
    for unit in units.values():
        for key, store in (("card", cards), ("mitigation", mitigations)):
            rel = unit.get(key)
            if rel and rel not in store:
                path = root / rel
                if path.is_file():
                    store[rel] = path.read_text(encoding="utf-8")
    for doc in repo.payloads:
        payloads[doc.data["id"]] = _clean(doc.data)

    facts = {f["id"]: _clean(f) for f in (repo.vocab["facts"].data["facts"])}
    surfaces = [_clean(s) for s in repo.vocab["surfaces"].data["surfaces"]]

    # The order to meet the units in, decided here so the page compares integers
    # rather than re-deriving an opinion the tests can pin down. What the tester
    # holds is applied on top of this, in the page, because only the page knows it.
    for unit_id, position in chain.reading_order().items():
        if unit_id in units:
            units[unit_id]["order_hint"] = position

    wstg = {e["id"]: e["title"] for e in repo.standards["wstg"].data["wstg"]}
    claims: Dict[str, List[str]] = {}
    for tid, topic in topics.items():
        for wid in (topic.get("refs") or {}).get("wstg") or []:
            claims.setdefault(wid, []).append(tid)

    return {
        "version": __version__,
        "counts": coverage(root),
        "topics": topics,
        "units": units,
        "facts": facts,
        "surfaces": surfaces,
        "cards": cards,
        "mitigations": mitigations,
        "payloads": payloads,
        "wstg": wstg,
        "claims": claims,
        "scope": surface_scope(surfaces, topics),
        "always": sorted(
            tid
            for tid, t in topics.items()
            if ((t.get("surfaces") or {}).get("always"))
        ),
        "given": sorted(chain.given()),
        "granted": sorted(f for f, b in facts.items() if b.get("granted")),
        "toolbox": {t["id"]: _clean(t) for doc in repo.toolbox for t in doc.data},
    }


def render(data: Dict[str, Any]) -> str:
    blob = json.dumps(data, separators=(",", ":"), sort_keys=True)
    # </script> inside a string would end the block early; escaping the slash
    # keeps the JSON valid and the parser inside the tag.
    blob = blob.replace("</", "<\\/")
    return _PAGE.replace("{{VERSION}}", html.escape(data["version"])).replace(
        "{{DATA}}", blob
    )


def build(root: Path, target: Path) -> Path:
    target.write_text(render(catalogue(root)), encoding="utf-8")
    return target


_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harrier {{VERSION}}</title>
<style>
:root {
  --bg: #14161a; --panel: #1b1e24; --line: #2a2f38; --ink: #e6e8ec;
  --dim: #9aa3b2; --accent: #7fb8ff; --warn: #f0b429; --good: #6fcf97;
  --mono: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
header {
  display: flex; align-items: baseline; gap: 1rem; flex-wrap: wrap;
  padding: .7rem 1rem; border-bottom: 1px solid var(--line); background: var(--panel);
  position: sticky; top: 0; z-index: 5;
}
header h1 { font-size: 1rem; margin: 0; letter-spacing: .04em; text-transform: uppercase; }
header .counts { color: var(--dim); font-size: .82rem; }
nav { display: flex; gap: .35rem; margin-left: auto; }
nav button, .chip {
  background: transparent; color: var(--dim); border: 1px solid var(--line);
  border-radius: 3px; padding: .3rem .7rem; font-size: .82rem; cursor: pointer;
}
nav button.on { color: var(--ink); border-color: var(--accent); }
#q {
  background: var(--bg); border: 1px solid var(--line); border-radius: 3px;
  color: var(--ink); padding: .3rem .6rem; font-size: .85rem; width: 15rem;
}
main { display: grid; grid-template-columns: 20rem 1fr; min-height: calc(100vh - 3rem); }
@media (max-width: 860px) { main { grid-template-columns: 1fr; } #side { max-height: 40vh; } }
#side { border-right: 1px solid var(--line); overflow: auto; padding: .6rem; }
#body { overflow: auto; padding: 1rem 1.4rem 4rem; }
.item {
  padding: .35rem .5rem; border-radius: 3px; cursor: pointer; font-size: .87rem;
  display: flex; justify-content: space-between; gap: .5rem;
}
.item:hover { background: #232833; }
.item.on { background: #232833; color: var(--accent); }
.item .n { color: var(--dim); font-size: .78rem; }
.group { color: var(--dim); font-size: .72rem; text-transform: uppercase;
  letter-spacing: .08em; margin: .9rem .5rem .3rem; }
h2 { font-size: 1.15rem; margin: 0 0 .2rem; }
h3 { font-size: .95rem; margin: 1.4rem 0 .4rem; }
.id, code, pre { font-family: var(--mono); }
.id { color: var(--accent); font-size: .8rem; }
.sub { color: var(--dim); font-size: .85rem; margin-bottom: 1rem; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 4px;
  padding: .7rem .9rem; margin: .5rem 0; }
.card h4 { margin: 0 0 .25rem; font-size: .9rem; }
.k { color: var(--dim); font-size: .74rem; text-transform: uppercase;
  letter-spacing: .07em; display: block; margin-bottom: .15rem; }
ul { margin: .3rem 0; padding-left: 1.1rem; }
li { margin: .15rem 0; }
table { border-collapse: collapse; width: 100%; font-size: .85rem; margin: .5rem 0; }
th, td { text-align: left; padding: .3rem .5rem; border-bottom: 1px solid var(--line); vertical-align: top; }
th { color: var(--dim); font-weight: 500; font-size: .76rem; text-transform: uppercase; }
pre { background: #0f1115; border: 1px solid var(--line); border-radius: 3px;
  padding: .6rem .8rem; overflow-x: auto; font-size: .82rem; }
code { background: #0f1115; border-radius: 2px; padding: 0 .25rem; font-size: .85em;
  white-space: pre-wrap; }
/* A payload is copied, not read: the browser would collapse the trailing space
   that makes "-- " a comment and the leading one that makes " AND 1=1" append
   to a bare number, and the reader would never see what went missing. */
td code, .payload { white-space: pre; }
pre code { background: none; padding: 0; }
a { color: var(--accent); }
.tag { display: inline-block; background: #232833; border-radius: 2px;
  padding: .05rem .4rem; font-size: .76rem; color: var(--dim); margin: .1rem .2rem .1rem 0;
  cursor: pointer; }
.tag.yield { color: var(--good); } .tag.req { color: var(--warn); }
.muted { color: var(--dim); }
label.fact { display: block; font-size: .82rem; padding: .14rem .3rem; cursor: pointer; }
label.fact input { margin-right: .4rem; }
.pill { font-size: .7rem; border: 1px solid var(--line); border-radius: 8px;
  padding: 0 .45rem; color: var(--dim); }
.empty { color: var(--dim); font-style: italic; }
.idchip { font-family: var(--mono); font-size: .7rem; color: var(--dim); opacity: .75; }
.card .meta { margin-top: .45rem; font-size: .75rem; color: var(--dim); }
.card.unit { cursor: pointer; }
.card.unit:hover { border-color: var(--accent); }
.card.unit h4 { font-size: .95rem; font-weight: 600; }
.written { color: var(--good); border-color: var(--good); }
.outcomes { display: flex; gap: .3rem; margin-top: .5rem; flex-wrap: wrap; }
.outcomes button {
  background: transparent; color: var(--dim); border: 1px solid var(--line);
  border-radius: 3px; padding: .18rem .55rem; font-size: .76rem; cursor: pointer;
}
.outcomes button:hover { color: var(--ink); border-color: var(--accent); }
.outcomes button.found { color: var(--good); border-color: var(--good); }
.outcomes button.clean { color: var(--accent); border-color: var(--accent); }
.outcomes button.unclear { color: var(--warn); border-color: var(--warn); }
.lane { margin: 1.6rem 0 .3rem; }
.lane h3 { margin: 0; display: inline-block; }
.lane .n { color: var(--dim); font-size: .8rem; margin-left: .4rem; }
.lane p.why { color: var(--dim); font-size: .82rem; margin: .2rem 0 .5rem; }
.anchor { padding: .35rem .5rem; border-radius: 3px; cursor: pointer; font-size: .85rem; }
.anchor:hover { background: #232833; }
.anchor.on { background: #232833; color: var(--accent); }
.anchor .hint { display: block; color: var(--dim); font-size: .72rem; line-height: 1.35; }
.runbar { display: flex; gap: .35rem; flex-wrap: wrap; margin: .5rem .3rem; }
.runbar button {
  background: transparent; color: var(--dim); border: 1px solid var(--line);
  border-radius: 3px; padding: .25rem .6rem; font-size: .78rem; cursor: pointer;
}
.runbar button:hover { color: var(--ink); border-color: var(--accent); }
#target {
  background: var(--bg); border: 1px solid var(--line); border-radius: 3px;
  color: var(--ink); padding: .3rem .5rem; font-size: .85rem; width: 100%;
}
.notice { background: #2a2118; border: 1px solid var(--warn); color: var(--warn);
  border-radius: 4px; padding: .5rem .8rem; margin: .5rem 0; font-size: .84rem; }
.done-row { display: flex; justify-content: space-between; gap: .6rem;
  padding: .3rem .5rem; border-bottom: 1px solid var(--line); font-size: .85rem; }
.done-row .o { font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; }
.o.found { color: var(--good); } .o.clean { color: var(--accent); } .o.unclear { color: var(--warn); }
</style>
</head>
<body>
<header>
  <h1>Harrier</h1>
  <span class="counts" id="counts"></span>
  <input id="q" type="search" placeholder="search units, topics, payloads">
  <nav>
    <button data-view="board" class="on">Board</button>
    <button data-view="surfaces">Surfaces</button>
    <button data-view="coverage">Coverage</button>
  </nav>
</header>
<main>
  <div id="side"></div>
  <div id="body"></div>
</main>
<script id="data" type="application/json">{{DATA}}</script>
<script>
const D = JSON.parse(document.getElementById("data").textContent);
const side = document.getElementById("side"), body = document.getElementById("body");

/* The run: what this tester is looking at, what they hold, and what they have
   settled. It is the only state in the page that is about a target rather than
   about the catalogue, and it is the reason the file is a companion rather than
   a reference. It never travels inside the artefact -- it is written to this
   browser and to a file the tester exports on purpose. */
const RUN_KEY = "harrier.run.v1";
const OUTCOMES = { found: "Found", clean: "Clean", unclear: "Unclear" };

let view = "board", current = null;
let anchor = null;              /* a surface tag, or null for the whole target */
let held = new Set(D.given);
let results = {};               /* unit id -> { outcome, at } */
let target = "";
let allFacts = false;
let storageBroken = false;

const alwaysTopics = new Set(D.always || []);

function runOut() {
  return {
    format: RUN_KEY,
    harrier_version: D.version,
    target: target,
    anchor: anchor,
    held: [...held].sort(),
    results: results
  };
}

/* Anything read back is treated as hostile: a run file travels between machines
   and an identifier that is not in this catalogue means the file was written by
   a different build or by something else entirely. Unknown keys, unknown units,
   unknown facts and unknown outcomes are dropped rather than merged, because a
   run that silently gained a fact would tell the tester a test was possible
   when it is not. */
function runIn(raw) {
  if (!raw || typeof raw !== "object" || raw.format !== RUN_KEY) return false;
  target = typeof raw.target === "string" ? raw.target.slice(0, 200) : "";
  anchor = (typeof raw.anchor === "string" && D.scope[raw.anchor]) ? raw.anchor : null;
  held = new Set((Array.isArray(raw.held) ? raw.held : []).filter(f => D.facts[f]));
  D.given.forEach(f => held.add(f));
  results = {};
  const src = (raw.results && typeof raw.results === "object") ? raw.results : {};
  Object.keys(src).forEach(id => {
    const r = src[id];
    if (!D.units[id] || !r || !OUTCOMES[r.outcome]) return;
    results[id] = { outcome: r.outcome, at: typeof r.at === "string" ? r.at : "" };
  });
  return true;
}

function save() {
  try { localStorage.setItem(RUN_KEY, JSON.stringify(runOut())); }
  catch (e) { storageBroken = true; }
}

function restore() {
  let raw = null;
  try { raw = localStorage.getItem(RUN_KEY); }
  catch (e) { storageBroken = true; return; }
  if (!raw) return;
  try { runIn(JSON.parse(raw)); } catch (e) { /* a corrupt run starts a fresh one */ }
}

function clearRun() {
  anchor = null; held = new Set(D.given); results = {}; target = "";
  try { localStorage.removeItem(RUN_KEY); } catch (e) { storageBroken = true; }
}

document.getElementById("counts").textContent =
  D.counts.topics + " topics · " + D.counts.units + " units · " +
  D.counts.units_authored + " authored · " + Object.keys(D.facts).length + " facts";

const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

/* Minimal markdown: headings, fenced code, tables, lists, inline emphasis.
   A card is prose a tester reads mid-test, so it renders rather than sitting in
   a <pre>; anything richer than this belongs in the card's own wording. */
function md(src) {
  const out = []; let i = 0; const lines = src.split("\n");
  const inline = t => esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1");
  while (i < lines.length) {
    const l = lines[i];
    if (/^```/.test(l)) {
      const buf = []; i++;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i++; out.push("<pre><code>" + esc(buf.join("\n")) + "</code></pre>"); continue;
    }
    let m = l.match(/^(#{1,4})\s+(.*)$/);
    if (m) { const n = Math.min(m[1].length + 1, 5);
      out.push("<h" + n + ">" + inline(m[2]) + "</h" + n + ">"); i++; continue; }
    if (/^\s*\|/.test(l) && /^\s*\|[\s:|-]+\|?\s*$/.test(lines[i + 1] || "")) {
      const cells = r => r.trim().replace(/^\||\|$/g, "").split("|").map(c => inline(c.trim()));
      const head = cells(l); i += 2; const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(cells(lines[i++]));
      out.push("<table><tr>" + head.map(h => "<th>" + h + "</th>").join("") + "</tr>" +
        rows.map(r => "<tr>" + r.map(c => "<td>" + c + "</td>").join("") + "</tr>").join("") +
        "</table>"); continue;
    }
    if (/^\s*[-*]\s+/.test(l) || /^\s*\d+\.\s+/.test(l)) {
      const ordered = /^\s*\d+\./.test(l); const items = [];
      while (i < lines.length && (/^\s*[-*]\s+/.test(lines[i]) || /^\s*\d+\.\s+/.test(lines[i]))) {
        items.push(inline(lines[i].replace(/^\s*(?:[-*]|\d+\.)\s+/, ""))); i++;
        while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*[-*]\s/.test(lines[i]))
          items[items.length - 1] += " " + inline(lines[i++].trim());
      }
      const t = ordered ? "ol" : "ul";
      out.push("<" + t + ">" + items.map(x => "<li>" + x + "</li>").join("") + "</" + t + ">");
      continue;
    }
    if (/^---+$/.test(l)) { out.push("<hr>"); i++; continue; }
    if (!l.trim()) { i++; continue; }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,4}\s|```|\s*[-*]\s|\s*\d+\.\s|\s*\|)/.test(lines[i]))
      para.push(lines[i++]);
    out.push("<p>" + inline(para.join(" ")) + "</p>");
  }
  return out.join("\n");
}

const unitsOf = tid => Object.values(D.units).filter(u => u.topic === tid);

/* A tester reads titles, not identifiers. The identifier is how a finding is
   written down and how two people refer to the same test, so it stays -- small,
   dim, and after the name of the thing. Everywhere a fact, topic or unit is
   shown, the words come first and the code is a label on the side. */
const idChip = id => '<span class="idchip">' + esc(id) + "</span>";
const factLabel = f => (D.facts[f] && D.facts[f].label) || f;
const topicTitle = tid => (D.topics[tid] && D.topics[tid].title) || tid;
const factTag = (f, cls) => '<span class="tag ' + cls + '" data-fact="' + esc(f) +
  '" title="' + esc(f) + '">' + esc(factLabel(f)) + "</span>";

const isDone = u => !!results[u.id];
const inScope = u => !anchor ||
  (D.scope[anchor] || []).indexOf(u.topic) >= 0;

/* The facts a unit still needs. An `any_of` group is one missing requirement
   with several ways to satisfy it, so it contributes its alternatives only when
   none of them is held. */
function missing(u) {
  const r = u.requires || {};
  const out = (r.all_of || []).filter(f => !held.has(f));
  const any = r.any_of || [];
  if (any.length && !any.some(f => held.has(f))) any.forEach(f => out.push(f));
  return out;
}

function unitCard(u, extra) {
  return '<div class="card unit" data-unit="' + esc(u.id) + '">' +
    "<h4>" + esc(u.title) +
    (u.status === "authored" ? ' <span class="pill written">written in full</span>' : "") +
    "</h4><p class=\"muted\">" + esc(u.objective) + "</p>" + (extra || "") +
    '<div class="meta">' + esc(topicTitle(u.topic)) + " · " + idChip(u.id) + "</div></div>";
}

function reachable(u) {
  const r = u.requires || {};
  if ((r.all_of || []).some(f => !held.has(f))) return false;
  if ((r.any_of || []).length && !(r.any_of || []).some(f => held.has(f))) return false;
  return true;
}

function renderUnit(u) {
  const t = D.topics[u.topic] || {};
  const r = u.requires || {};
  const rows = [];
  const add = (k, v) => { if (v && v.length) rows.push(
    '<div class="card"><span class="k">' + k + "</span>" + v + "</div>"); };
  add("Objective", "<p>" + esc(u.objective) + "</p>");
  if (u.oracle) add("Oracle",
    "<p><strong>Positive.</strong> " + esc(u.oracle.positive) + "</p><p><strong>Negative.</strong> " +
    esc(u.oracle.negative) + "</p>" + (u.oracle.inconclusive ?
    "<p><strong>Inconclusive.</strong> " + esc(u.oracle.inconclusive) + "</p>" : ""));
  if (u.questions) add("Questions", "<ul>" + u.questions.map(q => "<li>" + esc(q) + "</li>").join("") + "</ul>");
  if (u.sequence) add("Sequence", "<ol>" + u.sequence.map(s => "<li>" + esc(s) + "</li>").join("") + "</ol>");
  if (u.first_false_positive) add("First false positive", "<p>" + esc(u.first_false_positive) + "</p>");
  if (u.false_positives) add("Other false positives",
    "<ul>" + u.false_positives.map(s => "<li>" + esc(s) + "</li>").join("") + "</ul>");
  if (u.preconditions) add("Preconditions",
    "<ul>" + u.preconditions.map(s => "<li>" + esc(s) + "</li>").join("") + "</ul>");
  if (u.evidence) add("Evidence", "<ul>" + u.evidence.map(s => "<li>" + esc(s) + "</li>").join("") + "</ul>");
  if (u.done_when) add("Done when", "<p>" + esc(u.done_when) + "</p>");
  if (u.safety) add("Safety", '<p class="warn" style="color:var(--warn)">' + esc(u.safety) + "</p>");

  const chain = '<div class="card"><span class="k">Chain</span>' +
    ((r.all_of || []).length ? "<p>Requires all of " + (r.all_of).map(f => factTag(f, "req")).join(" ") + "</p>" : "") +
    ((r.any_of || []).length ? "<p>Requires any of " + (r.any_of).map(f => factTag(f, "req")).join(" ") + "</p>" : "") +
    ((u.motivated_by || []).length ? "<p>Worth doing sooner given " + u.motivated_by.map(f => factTag(f, "req")).join(" ") + "</p>" : "") +
    ((u.yields || []).length ? "<p>Yields " + u.yields.map(f => factTag(f, "yield")).join(" ") + "</p>" : "") +
    ((u.closes || []).length ? "<p>A clean result closes " + u.closes.map(f => factTag(f, "yield")).join(" ") + "</p>" : "") +
    "</div>";

  const pay = u.payloads && D.payloads[u.payloads.replace(/^payloads\//, "").replace(/\.yaml$/, "")];
  let payHtml = "";
  if (pay) {
    payHtml = "<h3>Payloads · " + esc(pay.title) + '</h3><p class="muted">reviewed ' +
      esc(pay.reviewed) + (pay.safety ? " · " + esc(pay.safety) : "") + "</p><table><tr><th>Name</th><th>Payload</th><th>Detect</th></tr>" +
      pay.entries.map(e => "<tr><td>" + esc(e.name) + "</td><td><code>" + esc(e.payload) +
        "</code></td><td>" + esc(e.detect || "") + (e.note ? '<br><span class="muted">' + esc(e.note) + "</span>" : "") +
        "</td></tr>").join("") + "</table>";
  }
  let toolHtml = "";
  (u.tools || []).forEach(id => {
    const t = D.toolbox[id];
    if (!t) return;
    toolHtml += "<h3>Tool · " + esc(t.name) + '</h3><p class="muted">' + esc(t.purpose) + "</p>" +
      (t.invocations || []).map(v => '<div class="card"><span class="k">' + esc(v.purpose) +
        "</span><pre><code>" + esc(v.cmd) + "</code></pre>" +
        (v.flags ? "<table><tr><th>Flag</th><th>Why</th></tr>" +
          Object.keys(v.flags).map(f => "<tr><td><code>" + esc(f) + "</code></td><td>" +
            esc(v.flags[f]) + "</td></tr>").join("") + "</table>" : "") +
        "</div>").join("");
  });
  const cardMd = u.card && D.cards[u.card];
  const mitMd = u.mitigation && D.mitigations[u.mitigation];

  body.innerHTML =
    '<h2>' + esc(u.title) + '</h2><div class="sub">' + esc(t.title || u.topic) +
    ' · <span class="pill">' + esc(u.kind || "test") + '</span> <span class="pill' +
    (u.status === "authored" ? " written" : "") + '">' + esc(u.status || "authored") +
    "</span> · " + idChip(u.id) + "</div>" +
    rows.join("") + chain + payHtml + toolHtml +
    (cardMd ? "<h3>Card</h3>" + md(cardMd) : "") +
    (mitMd ? "<h3>Mitigation</h3>" + md(mitMd) : "");
  body.scrollTop = 0;
}

function renderTopic(tid) {
  const t = D.topics[tid];
  const us = unitsOf(tid);
  body.innerHTML = "<h2>" + esc(t.title) + '</h2><div class="sub">' + esc(t.domain) +
    (t.axis ? " · axis " + esc(t.axis) : " · no axis") + " · " + idChip(tid) + "</div>" +
    (t.boundaries ? "<h3>Boundaries</h3>" + t.boundaries.map(b =>
      '<div class="card"><span class="k">' + esc(b.subject) + "</span><p>" + esc(b.note) +
      (b.home ? ' <span class="tag" data-unit-topic="' + esc(b.home) + '">' + esc(b.home) + "</span>" :
      ' <span class="muted">not written</span>') + "</p></div>").join("") : "") +
    "<h3>Units</h3>" + (t.order || us.map(u => u.id)).map(id => {
      const u = D.units[id];
      return u ? unitCard(u, "") : "";
    }).join("");
  body.scrollTop = 0;
}

function sideSurfaces() {
  /* Counted through the closure, so the number next to a surface is the number
     of units a tester looking at it would actually be handed. */
  const counts = {};
  D.surfaces.forEach(s => {
    counts[s.tag] = (D.scope[s.tag] || []).reduce((n, tid) => n + unitsOf(tid).length, 0);
  });
  counts["*always*"] = (D.always || []).reduce((n, tid) => n + unitsOf(tid).length, 0);
  side.innerHTML = '<div class="group">Attack surface</div>' +
    D.surfaces.filter(s => counts[s.tag]).sort((a, b) => a.label.localeCompare(b.label))
      .map(s => '<div class="item" data-surface="' + esc(s.tag) + '"><span>' + esc(s.label) +
        '</span><span class="n">' + counts[s.tag] + "</span></div>").join("") +
    '<div class="group">Everywhere</div><div class="item" data-surface="*always*"><span>applies to any target</span>' +
    '<span class="n">' + counts["*always*"] + "</span></div>";
}
function showSurface(tag) {
  const ids = tag === "*always*" ? (D.always || []) : (D.scope[tag] || []);
  const ts = ids.map(tid => D.topics[tid]).filter(Boolean);
  const meta = D.surfaces.find(s => s.tag === tag);
  const implied = meta && (meta.emits || []).length
    ? '<p class="muted">Looking at this means you are also looking at ' +
      meta.emits.map(t => {
        const m = D.surfaces.find(x => x.tag === t);
        return esc(m ? m.label.toLowerCase() : t);
      }).join(", ") + ". Those are included below.</p>"
    : "";
  body.innerHTML = "<h2>" + esc(meta ? meta.label : tag) + "</h2>" +
    (meta ? '<div class="sub">' + idChip(meta.tag) + "</div><p>" + esc(meta.description) +
      '</p><div class="card"><span class="k">How to recognise it</span><p>' +
      esc(meta.discovery_hint) + "</p></div>" + implied : "") +
    (tag === "*always*" ? "" :
      '<div class="runbar"><button data-anchor="' + esc(tag) +
      '">Work from this on the board</button></div>') +
    "<h3>Topics · " + ts.length + "</h3>" +
    ts.map(t => '<div class="card unit" data-topic="' + esc(t.id) + '">' +
      "<h4>" + esc(t.title) + "</h4>" +
      '<div class="meta">' + unitsOf(t.id).length + " units · " + idChip(t.id) +
      "</div></div>").join("");
  body.scrollTop = 0;
}

/* The side panel is the run: what is being tested, what is in front of the
   tester, and what they hold. The fact list is deliberately not the whole
   vocabulary -- several hundred checkboxes is the catalogue asking the tester to
   do the catalogue's job. It shows what is held and what is one step from
   opening something, which is the set a person can actually answer about. */
function sideBoard() {
  const parts = [];

  parts.push('<div class="group">What you are testing</div>' +
    '<div style="padding:0 .3rem"><input id="target" type="text" placeholder="target or scope label"' +
    ' value="' + esc(target) + '"></div>');

  parts.push('<div class="group">What is in front of you</div>' +
    '<div class="anchor' + (anchor ? "" : " on") + '" data-anchor="">The whole target' +
    '<span class="hint">Everything in scope, from the beginning.</span></div>' +
    D.surfaces.filter(s => (D.scope[s.tag] || []).length)
      .sort((a, b) => a.label.localeCompare(b.label))
      .map(s => '<div class="anchor' + (anchor === s.tag ? " on" : "") +
        '" data-anchor="' + esc(s.tag) + '">' + esc(s.label) +
        '<span class="hint">' + esc(s.discovery_hint || "") + "</span></div>").join(""));

  /* Ranked by how much each fact would open, so the question the panel asks is
     "is this true of your target?" in the order worth asking it. */
  const opens = {};
  Object.values(D.units).forEach(u => {
    if (isDone(u) || !inScope(u)) return;
    missing(u).forEach(f => { opens[f] = (opens[f] || 0) + 1; });
  });
  const shown = allFacts
    ? Object.keys(D.facts).sort((a, b) => factLabel(a).localeCompare(factLabel(b)))
    : [...new Set([...held].concat(
        Object.keys(opens).sort((a, b) => opens[b] - opens[a]).slice(0, 12)))]
        .sort((a, b) => (held.has(b) - held.has(a)) || factLabel(a).localeCompare(factLabel(b)));

  parts.push('<div class="group">What you hold</div>' +
    shown.map(f => '<label class="fact" title="' + esc(f) + '">' +
      '<input type="checkbox" data-hold="' + esc(f) + '"' + (held.has(f) ? " checked" : "") + ">" +
      esc(factLabel(f)) +
      (opens[f] && !held.has(f) ? ' <span class="idchip">opens ' + opens[f] + "</span>" : "") +
      "</label>").join("") +
    '<div class="runbar"><button data-act="allfacts">' +
    (allFacts ? "Show only what matters" : "Show every fact") + "</button></div>");

  parts.push('<div class="group">Run</div><div class="runbar">' +
    '<button data-act="export">Export</button>' +
    '<button data-act="import">Import</button>' +
    '<button data-act="clear">Clear run</button></div>');

  side.innerHTML = parts.join("");
}

/* Ranking. The static half was decided at build time and travels as
   `order_hint`; the only thing decided here is what the tester holds, because
   the page is the only thing that knows it. A unit something in hand makes more
   likely to pay goes first -- that is what `motivated_by` is for. */
const motivated = u => (u.motivated_by || []).some(f => held.has(f));
const rank = u => (motivated(u) ? 0 : 1) * 1e7 + (u.order_hint || 0);

function showBoard() {
  const scoped = Object.values(D.units).filter(inScope);
  const done = scoped.filter(isDone);
  const open = scoped.filter(u => !isDone(u));
  /* A unit whose every yield is already held has nothing left to establish.
     `Chain.available` draws the same line, and the board must not quietly draw
     a different one: a tester who ticked the fact by hand has already answered
     the question the unit asks. */
  const spent = u => (u.yields || []).length && (u.yields || []).every(f => held.has(f));
  const now = open.filter(u => missing(u).length === 0 && !spent(u))
    .sort((a, b) => rank(a) - rank(b));
  const blocked = open.filter(u => missing(u).length > 0)
    .sort((a, b) => (missing(a).length - missing(b).length) || rank(a) - rank(b));

  const surface = anchor && D.surfaces.find(s => s.tag === anchor);
  const out = [];

  out.push("<h2>" + (target ? esc(target) : "Untitled run") + "</h2>" +
    '<div class="sub">' + (surface ? esc(surface.label) : "The whole target") +
    " · " + done.length + " settled · " + now.length + " ready · " +
    blocked.length + " waiting on something</div>");

  if (storageBroken) out.push('<div class="notice">This browser will not keep the run ' +
    "when the tab closes -- opening a file from disk often blocks storage. " +
    "Export before you finish.</div>");

  if (!now.length && !blocked.length) {
    out.push('<p class="empty">Nothing in the catalogue applies to that surface yet.</p>');
  }

  /* Naming a surface is not the same as holding what testing it needs. Somebody
     looking at a login form has not necessarily inventoried the application's
     entry points, and the catalogue is right to ask rather than assume. What it
     must not do is answer "nothing" and stop: the way in is one or two facts,
     so they are put in front of the tester as questions about their target,
     ordered by how much each one opens. */
  if (!now.length && blocked.length) {
    const opens = {};
    blocked.forEach(u => missing(u).forEach(f => { opens[f] = (opens[f] || 0) + 1; }));
    const keys = Object.keys(opens).sort((a, b) => opens[b] - opens[a]).slice(0, 4);
    out.push('<div class="lane"><h3>What would open this up</h3></div>' +
      "<p class=\"why\">Nothing is ready yet. These are true of most targets -- " +
      "tick the ones true of yours.</p>" +
      keys.map(f => '<div class="card"><label class="fact" title="' + esc(f) + '">' +
        '<input type="checkbox" data-hold="' + esc(f) + '">' + esc(factLabel(f)) +
        ' <span class="idchip">opens ' + opens[f] + "</span></label>" +
        (D.facts[f] && D.facts[f].description
          ? '<p class="muted">' + esc(D.facts[f].description) + "</p>" : "") +
        "</div>").join(""));
  }

  if (now.length) {
    out.push('<div class="lane"><h3>Start here</h3><span class="n">' + now.length +
      "</span></div><p class=\"why\">Everything you hold makes these possible now. " +
      "The order is the one to work in.</p>" +
      now.slice(0, 40).map(u => unitCard(u, outcomeRow(u))).join("") +
      (now.length > 40 ? '<p class="muted">' + (now.length - 40) +
        " more ready once these are settled.</p>" : ""));
  }

  if (blocked.length) {
    out.push('<div class="lane"><h3>Waiting on something</h3><span class="n">' +
      blocked.length + "</span></div><p class=\"why\">Nearest first. " +
      "Tick what it needs, or settle the test that establishes it.</p>" +
      blocked.slice(0, 25).map(u => unitCard(u,
        '<p class="muted">Needs ' + missing(u).map(f => factTag(f, "req")).join(" ") + "</p>"
      )).join(""));
  }

  if (anchor) {
    const everywhere = Object.values(D.units).filter(u =>
      alwaysTopics.has(u.topic) && !isDone(u) && missing(u).length === 0);
    if (everywhere.length) out.push('<div class="lane"><h3>Applies to any target</h3>' +
      '<span class="n">' + everywhere.length + "</span></div>" +
      "<p class=\"why\">Not about this surface in particular, and still owed before the " +
      "engagement closes.</p>" +
      everywhere.sort((a, b) => rank(a) - rank(b)).slice(0, 10)
        .map(u => unitCard(u, outcomeRow(u))).join(""));
  }

  if (done.length) {
    out.push('<div class="lane"><h3>Settled</h3><span class="n">' + done.length +
      "</span></div><p class=\"why\">A test recorded clean is the half of coverage " +
      "nothing else records.</p>" +
      done.sort((a, b) => rank(a) - rank(b)).map(u =>
        '<div class="done-row" data-unit="' + esc(u.id) + '"><span>' + esc(u.title) +
        "</span><span class=\"o " + esc(results[u.id].outcome) + '">' +
        esc(OUTCOMES[results[u.id].outcome]) + "</span></div>").join(""));
  }

  body.innerHTML = out.join("");
  body.scrollTop = 0;
}

/* Four states, because three of them are results and the fourth is "not yet".
   A positive result hands the tester what the unit yields; a clean one closes
   what a clean result closes, which is the only way an outline of a catalogue
   ever narrows. Undo forgets the result and leaves the facts alone: a fact can
   have been established by more than one route, and retracting it here would
   quietly withdraw a route the tester still has. */
function outcomeRow(u) {
  const r = results[u.id];
  return '<div class="outcomes">' +
    Object.keys(OUTCOMES).map(o => '<button data-out="' + o + '" data-for="' + esc(u.id) +
      '" class="' + (r && r.outcome === o ? o : "") + '">' + OUTCOMES[o] + "</button>").join("") +
    (r ? '<button data-out="undo" data-for="' + esc(u.id) + '">Undo</button>' : "") +
    "</div>";
}

function record(id, outcome) {
  const u = D.units[id];
  if (!u) return;
  if (outcome === "undo") { delete results[id]; }
  else {
    results[id] = { outcome: outcome, at: new Date().toISOString() };
    if (outcome === "found") (u.yields || []).forEach(f => held.add(f));
    if (outcome === "clean") (u.closes || []).forEach(f => held.add(f));
  }
  save();
  draw();
}

function sideCoverage() {
  side.innerHTML = '<div class="group">Views</div>' +
    '<div class="item" data-cov="wstg"><span>WSTG</span><span class="n">' + D.counts.wstg_covered + "</span></div>" +
    '<div class="item" data-cov="domains"><span>Domains</span><span class="n">' + D.counts.topics + "</span></div>" +
    '<div class="item" data-cov="depth"><span>Depth</span><span class="n">' + D.counts.units_authored + "</span></div>";
}

function showCoverage(which) {
  if (which === "wstg") {
    body.innerHTML = "<h2>WSTG coverage</h2><div class=\"sub\">" + D.counts.wstg_covered + " of " +
      D.counts.wstg_coverable + " identifiers claimed by a topic</div><table><tr><th>Identifier</th><th>Title</th><th>Topics</th></tr>" +
      Object.keys(D.wstg).sort().map(w => "<tr><td><code>" + esc(w) + "</code></td><td>" + esc(D.wstg[w]) +
        "</td><td>" + ((D.claims[w] || []).map(t => '<span class="tag" data-topic="' + esc(t) + '">' +
        esc(t) + "</span>").join(" ") || '<span class="empty">not a test</span>') + "</td></tr>").join("") + "</table>";
  } else if (which === "domains") {
    const by = {};
    Object.values(D.topics).forEach(t => (by[t.domain] = by[t.domain] || []).push(t));
    body.innerHTML = "<h2>Domains</h2><table><tr><th>Domain</th><th>Topics</th><th>Units</th></tr>" +
      Object.keys(by).sort().map(d => "<tr><td><code>" + esc(d) + "</code></td><td>" + by[d].length +
        "</td><td>" + by[d].reduce((n, t) => n + unitsOf(t.id).length, 0) + "</td></tr>").join("") + "</table>";
  } else {
    const authored = Object.values(D.units).filter(u => u.status === "authored");
    body.innerHTML = "<h2>Depth</h2><div class=\"sub\">" + authored.length + " of " +
      Object.keys(D.units).length + " units authored in full; the rest carry an identifier and an objective</div>" +
      authored.map(u => unitCard(u, "")).join("");
  }
  body.scrollTop = 0;
}

/* Search reads everything the file carries, because everything the file carries
   is what the reader was promised. A term that appears only in a card is the
   case that matters: the cards are where the reasoning lives. */
function excerpt(text, t) {
  const i = text.toLowerCase().indexOf(t);
  const from = Math.max(0, i - 90), to = Math.min(text.length, i + t.length + 130);
  return (from ? "… " : "") + text.slice(from, to).replace(/\s+/g, " ") + (to < text.length ? " …" : "");
}

function search(term) {
  const t = term.toLowerCase();
  const has = s => String(s || "").toLowerCase().includes(t);
  const units = Object.values(D.units).filter(u => has(u.id + " " + u.title + " " + u.objective));
  const topics = Object.values(D.topics).filter(x => has(x.id + " " + x.title));
  const facts = Object.values(D.facts).filter(f => has(f.id + " " + f.label + " " + f.description));
  const pay = [];
  Object.values(D.payloads).forEach(p => p.entries.forEach(e => {
    if (has(e.name + " " + e.payload + " " + (e.detect || "") + " " + (e.note || ""))) pay.push([p, e]);
  }));
  const prose = [];
  const scan = (store, kind, owner) => Object.keys(store).forEach(k => {
    if (has(store[k])) prose.push([kind, k, excerpt(store[k], t), owner(k)]);
  });
  const ownerOf = key => (Object.values(D.units).find(u => u.card === key || u.mitigation === key) || {}).id;
  scan(D.cards, "card", ownerOf);
  scan(D.mitigations, "mitigation", ownerOf);
  const tools = Object.values(D.toolbox).filter(x => has(JSON.stringify(x)));

  const unitCards = us => us.slice(0, 60).map(u => unitCard(u, "")).join("");

  const parts = [];
  if (units.length) parts.push("<h3>Units · " + units.length + "</h3>" + unitCards(units));
  if (prose.length) parts.push("<h3>Cards and mitigations</h3>" + prose.map(([kind, key, ex, owner]) =>
    '<div class="card"' + (owner ? ' data-unit="' + esc(owner) + '" style="cursor:pointer"' : "") +
    '><h4>' + esc(key.split("/").pop().replace(/\.md$/, "").replace(/-/g, " ")) +
    ' <span class="pill">' + kind + "</span></h4><p>" + esc(ex) + '</p><div class="meta">' +
    idChip(key) + "</div></div>").join(""));
  if (pay.length) parts.push("<h3>Payloads · " + pay.length + "</h3><table><tr><th>File</th><th>Name</th><th>Payload</th></tr>" +
    pay.slice(0, 40).map(([p, e]) => "<tr><td>" + esc(p.id) + "</td><td>" + esc(e.name) +
      "</td><td><code>" + esc(e.payload) + "</code></td></tr>").join("") + "</table>");
  if (topics.length) parts.push("<h3>Topics</h3>" + topics.map(x =>
    '<div class="card unit" data-topic="' + esc(x.id) + '"><h4>' + esc(x.title) +
    '</h4><div class="meta">' + idChip(x.id) + "</div></div>").join(""));
  if (facts.length) parts.push("<h3>Facts</h3>" + facts.map(f =>
    '<div class="card"><h4>' + factTag(f.id, "yield") + " " + esc(f.label) + "</h4><p>" +
    esc(f.description) + "</p></div>").join(""));
  if (tools.length) parts.push("<h3>Tools</h3>" + tools.map(x =>
    '<div class="card"><h4>' + esc(x.name) + "</h4><p>" + esc(x.purpose) + "</p></div>").join(""));

  body.innerHTML = "<h2>" + esc(term) + "</h2>" +
    (parts.length ? parts.join("") : '<p class="empty">nothing carries that</p>');
  body.scrollTop = 0;
}

function draw() {
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("on", b.dataset.view === view));
  if (view === "board") { sideBoard(); showBoard(); }
  if (view === "surfaces") { sideSurfaces(); if (!current) body.innerHTML =
    "<h2>Every surface the catalogue knows</h2><p class=\"muted\">A reference listing. " +
    "To work from one, set it as what is in front of you on the board.</p>"; }
  if (view === "coverage") { sideCoverage(); showCoverage("wstg"); }
}

/* Export writes a file the tester chose to write. Nothing leaves the page any
   other way: the run holds a client's target name and what was found on it, and
   that is theirs to move, not this file's to send. */
function exportRun() {
  const blob = new Blob([JSON.stringify(runOut(), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = (target ? target.replace(/[^a-zA-Z0-9._-]+/g, "-") : "harrier") + ".run.json";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function importRun() {
  const picker = document.createElement("input");
  picker.type = "file";
  picker.accept = "application/json,.json";
  picker.addEventListener("change", () => {
    const file = picker.files && picker.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      let ok = false;
      try { ok = runIn(JSON.parse(reader.result)); } catch (e) { ok = false; }
      if (!ok) {
        body.innerHTML = '<div class="notice">That file is not a Harrier run.</div>';
        return;
      }
      save();
      view = "board";
      draw();
    };
    reader.readAsText(file);
  });
  picker.click();
}

document.addEventListener("click", e => {
  /* Outcome buttons live inside a card that is itself clickable, so they are
     read first: pressing "Clean" must settle the test, not open it. */
  const o = e.target.closest("[data-out]");
  if (o) { record(o.dataset.for, o.dataset.out); return; }
  const act = e.target.closest("[data-act]");
  if (act) {
    const what = act.dataset.act;
    if (what === "export") exportRun();
    if (what === "import") importRun();
    if (what === "clear") { clearRun(); draw(); }
    if (what === "allfacts") { allFacts = !allFacts; sideBoard(); }
    return;
  }
  const an = e.target.closest("[data-anchor]");
  if (an) { anchor = an.dataset.anchor || null; view = "board"; save(); draw(); return; }
  const b = e.target.closest("nav button");
  if (b) { view = b.dataset.view; current = null; draw(); return; }
  const s = e.target.closest("[data-surface]");
  if (s) { side.querySelectorAll(".item").forEach(i => i.classList.remove("on"));
    s.classList.add("on"); current = s.dataset.surface; showSurface(current); return; }
  const c = e.target.closest("[data-cov]");
  if (c) { side.querySelectorAll(".item").forEach(i => i.classList.remove("on"));
    c.classList.add("on"); showCoverage(c.dataset.cov); return; }
  const t = e.target.closest("[data-topic]");
  if (t) { renderTopic(t.dataset.topic); return; }
  const tp = e.target.closest("[data-unit-topic]");
  if (tp && D.topics[tp.dataset.unitTopic]) { renderTopic(tp.dataset.unitTopic); return; }
  const u = e.target.closest("[data-unit]");
  if (u) { renderUnit(D.units[u.dataset.unit]); return; }
  const f = e.target.closest("[data-fact]");
  if (f) { view = "board"; held.add(f.dataset.fact); save(); draw(); return; }
});

/* Bound to the document, not to the panel: a fact is tickable from the side
   list and from the way-in block in the body, and the two must behave alike. */
document.addEventListener("change", e => {
  const h = e.target.closest("[data-hold]");
  if (!h) return;
  if (h.checked) held.add(h.dataset.hold); else held.delete(h.dataset.hold);
  save();
  draw();
});

document.addEventListener("input", e => {
  if (e.target.id !== "target") return;
  target = e.target.value.slice(0, 200);
  save();
});

document.getElementById("q").addEventListener("input", e => {
  const v = e.target.value.trim();
  if (v.length >= 3) search(v); else if (!v) draw();
});

restore();
draw();
</script>
</body>
</html>
"""
