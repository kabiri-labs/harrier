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


def _text(value: Any) -> str:
    """Collapse the whitespace a folded YAML scalar leaves behind."""
    if not isinstance(value, str):
        return value
    return " ".join(value.split())


def _clean(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _clean(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_clean(v) for v in data]
    return _text(data)


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
code { background: #0f1115; border-radius: 2px; padding: 0 .25rem; font-size: .85em; }
pre code { background: none; padding: 0; }
a { color: var(--accent); }
.tag { display: inline-block; background: #232833; border-radius: 2px;
  padding: .05rem .4rem; font-size: .76rem; color: var(--dim); margin: .1rem .2rem .1rem 0;
  font-family: var(--mono); cursor: pointer; }
.tag.yield { color: var(--good); } .tag.req { color: var(--warn); }
.muted { color: var(--dim); }
label.fact { display: block; font-size: .8rem; padding: .12rem .3rem; cursor: pointer;
  font-family: var(--mono); }
label.fact input { margin-right: .4rem; }
.pill { font-size: .7rem; border: 1px solid var(--line); border-radius: 8px;
  padding: 0 .45rem; color: var(--dim); }
.empty { color: var(--dim); font-style: italic; }
</style>
</head>
<body>
<header>
  <h1>Harrier</h1>
  <span class="counts" id="counts"></span>
  <input id="q" type="search" placeholder="search units, topics, payloads">
  <nav>
    <button data-view="surfaces" class="on">Surfaces</button>
    <button data-view="next">Now &amp; next</button>
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
let view = "surfaces", held = new Set(D.given), current = null;

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
const factTag = (f, cls) => '<span class="tag ' + cls + '" data-fact="' + esc(f) + '">' + esc(f) + "</span>";

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
  const cardMd = u.card && D.cards[u.card];
  const mitMd = u.mitigation && D.mitigations[u.mitigation];

  body.innerHTML =
    '<h2>' + esc(u.title) + '</h2><div class="sub"><span class="id">' + esc(u.id) +
    '</span> · ' + esc(t.title || u.topic) + ' · <span class="pill">' + esc(u.kind || "test") +
    '</span> <span class="pill">' + esc(u.status || "authored") + "</span></div>" +
    rows.join("") + chain + payHtml +
    (cardMd ? "<h3>Card</h3>" + md(cardMd) : "") +
    (mitMd ? "<h3>Mitigation</h3>" + md(mitMd) : "");
  body.scrollTop = 0;
}

function renderTopic(tid) {
  const t = D.topics[tid];
  const us = unitsOf(tid);
  body.innerHTML = "<h2>" + esc(t.title) + '</h2><div class="sub"><span class="id">' + esc(tid) +
    "</span> · " + esc(t.domain) + (t.axis ? " · axis " + esc(t.axis) : " · no axis") + "</div>" +
    (t.boundaries ? "<h3>Boundaries</h3>" + t.boundaries.map(b =>
      '<div class="card"><span class="k">' + esc(b.subject) + "</span><p>" + esc(b.note) +
      (b.home ? ' <span class="tag" data-unit-topic="' + esc(b.home) + '">' + esc(b.home) + "</span>" :
      ' <span class="muted">not written</span>') + "</p></div>").join("") : "") +
    "<h3>Units</h3>" + (t.order || us.map(u => u.id)).map(id => {
      const u = D.units[id]; if (!u) return "";
      return '<div class="card" data-unit="' + esc(id) + '" style="cursor:pointer">' +
        '<h4><span class="id">' + esc(id) + "</span> · " + esc(u.title) + "</h4><p>" +
        esc(u.objective) + "</p></div>";
    }).join("");
  body.scrollTop = 0;
}

function sideSurfaces() {
  const counts = {};
  Object.values(D.topics).forEach(t => {
    const s = t.surfaces || {};
    (s.any_of || []).forEach(tag => counts[tag] = (counts[tag] || 0) + unitsOf(t.id).length);
    if (s.always) counts["*always*"] = (counts["*always*"] || 0) + unitsOf(t.id).length;
  });
  side.innerHTML = '<div class="group">Attack surface</div>' +
    D.surfaces.filter(s => counts[s.tag]).sort((a, b) => counts[b.tag] - counts[a.tag])
      .map(s => '<div class="item" data-surface="' + esc(s.tag) + '"><span>' + esc(s.tag) +
        '</span><span class="n">' + counts[s.tag] + "</span></div>").join("") +
    '<div class="group">Everywhere</div><div class="item" data-surface="*always*"><span>applies to any target</span>' +
    '<span class="n">' + (counts["*always*"] || 0) + "</span></div>";
}

function showSurface(tag) {
  const ts = Object.values(D.topics).filter(t => {
    const s = t.surfaces || {};
    return tag === "*always*" ? s.always : (s.any_of || []).includes(tag);
  });
  const meta = D.surfaces.find(s => s.tag === tag);
  body.innerHTML = "<h2>" + esc(tag) + "</h2>" +
    (meta ? '<div class="sub">' + esc(meta.label) + "</div><p>" + esc(meta.description) +
      '</p><div class="card"><span class="k">How to recognise it</span><p>' +
      esc(meta.discovery_hint) + "</p></div>" : "") +
    "<h3>Topics</h3>" + ts.map(t => '<div class="card" data-topic="' + esc(t.id) + '" style="cursor:pointer">' +
      '<h4><span class="id">' + esc(t.id) + "</span> · " + esc(t.title) + "</h4>" +
      '<p class="muted">' + unitsOf(t.id).length + " units</p></div>").join("");
  body.scrollTop = 0;
}

function sideNext() {
  const fams = {};
  Object.values(D.facts).forEach(f => {
    const fam = f.id.split(".")[0]; (fams[fam] = fams[fam] || []).push(f);
  });
  side.innerHTML = '<div class="group">What you hold</div>' +
    Object.keys(fams).sort().map(fam => '<div class="group">' + fam + "</div>" +
      fams[fam].sort((a, b) => a.id.localeCompare(b.id)).map(f =>
        '<label class="fact"><input type="checkbox" data-hold="' + esc(f.id) + '"' +
        (held.has(f.id) ? " checked" : "") + ">" + esc(f.id.slice(fam.length + 1)) +
        (f.given ? ' <span class="pill">given</span>' : "") +
        (f.granted ? ' <span class="pill">granted</span>' : "") + "</label>").join("")).join("");
}

function showNext() {
  const avail = Object.values(D.units).filter(u => reachable(u) &&
    !((u.yields || []).length && (u.yields || []).every(f => held.has(f))));
  const motivated = avail.filter(u => (u.motivated_by || []).some(f => held.has(f)));
  const byTopic = {};
  avail.forEach(u => (byTopic[u.topic] = byTopic[u.topic] || []).push(u));
  const list = us => us.map(u => '<div class="card" data-unit="' + esc(u.id) + '" style="cursor:pointer">' +
    '<h4><span class="id">' + esc(u.id) + "</span> · " + esc(u.title) + "</h4><p>" + esc(u.objective) +
    "</p>" + ((u.yields || []).length ? "<p>Yields " + u.yields.map(f => factTag(f, "yield")).join(" ") + "</p>" : "") +
    "</div>").join("");
  body.innerHTML = "<h2>What you can do now</h2>" +
    '<div class="sub">' + held.size + " facts held · " + avail.length +
    " units reachable · " + (Object.keys(D.units).length - avail.length) + " not yet</div>" +
    (motivated.length ? "<h3>Worth doing first</h3><p class=\"muted\">Something you hold makes these more likely to pay.</p>" + list(motivated) : "") +
    "<h3>Reachable</h3>" +
    Object.keys(byTopic).sort().map(tid => '<div class="group">' + esc(tid) + " · " +
      esc((D.topics[tid] || {}).title || "") + "</div>" + list(byTopic[tid])).join("");
  body.scrollTop = 0;
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
      authored.map(u => '<div class="card" data-unit="' + esc(u.id) + '" style="cursor:pointer"><h4><span class="id">' +
        esc(u.id) + "</span> · " + esc(u.title) + "</h4><p>" + esc(u.objective) + "</p></div>").join("");
  }
  body.scrollTop = 0;
}

function search(term) {
  const t = term.toLowerCase();
  const hits = Object.values(D.units).filter(u =>
    (u.id + " " + u.title + " " + u.objective).toLowerCase().includes(t)).slice(0, 80);
  const pay = [];
  Object.values(D.payloads).forEach(p => p.entries.forEach(e => {
    if ((e.name + " " + e.payload).toLowerCase().includes(t)) pay.push([p, e]);
  }));
  body.innerHTML = "<h2>" + esc(term) + "</h2>" +
    (pay.length ? "<h3>Payloads</h3><table><tr><th>File</th><th>Name</th><th>Payload</th></tr>" +
      pay.slice(0, 40).map(([p, e]) => "<tr><td>" + esc(p.id) + "</td><td>" + esc(e.name) +
        "</td><td><code>" + esc(e.payload) + "</code></td></tr>").join("") + "</table>" : "") +
    "<h3>Units</h3>" + (hits.length ? hits.map(u => '<div class="card" data-unit="' + esc(u.id) +
      '" style="cursor:pointer"><h4><span class="id">' + esc(u.id) + "</span> · " + esc(u.title) +
      "</h4><p>" + esc(u.objective) + "</p></div>").join("") : '<p class="empty">nothing</p>');
  body.scrollTop = 0;
}

function draw() {
  document.querySelectorAll("nav button").forEach(b => b.classList.toggle("on", b.dataset.view === view));
  if (view === "surfaces") { sideSurfaces(); if (!current) body.innerHTML =
    "<h2>Start from what is in front of you</h2><p class=\"muted\">Pick the surface you are looking at. " +
    "Every topic that applies to it is listed, and every unit under those topics is a separate result to record.</p>"; }
  if (view === "next") { sideNext(); showNext(); }
  if (view === "coverage") { sideCoverage(); showCoverage("wstg"); }
}

document.addEventListener("click", e => {
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
  if (f) { view = "next"; held.add(f.dataset.fact); draw(); return; }
});

side.addEventListener("change", e => {
  const h = e.target.closest("[data-hold]");
  if (!h) return;
  if (h.checked) held.add(h.dataset.hold); else held.delete(h.dataset.hold);
  showNext();
});

document.getElementById("q").addEventListener("input", e => {
  const v = e.target.value.trim();
  if (v.length >= 3) search(v); else if (!v) draw();
});

draw();
</script>
</body>
</html>
"""
