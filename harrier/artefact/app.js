/* The artefact's application.

   Harrier is an execution companion for a testing standard. WSTG provides the
   navigation -- standard, testing group, test case -- and Harrier provides what
   the standard does not reach: the atomic tests inside a test case, and where a
   successful one may lead.

   Nothing here knows anything about a target, and the wording has to keep
   saying so. A chain edge is a statement about two tests, not about somebody's
   application: "potential continuation", never "unlocked"; "still required",
   never "you are missing". See docs/PIVOT.md for why that distinction is load
   bearing rather than cosmetic.

   The pure functions -- the graph model, its layout, path finding, search -- are
   exported so they can be tested directly instead of by asserting on substrings
   of a page that a broken script satisfies just as well as a working one. */

(function () {
  "use strict";

  /* Plain objects inherit "constructor", "__proto__" and "toString", so every
     one of them indexes truthy on a bare lookup. A unit identifier arriving from
     a URL fragment could name one and take a view down. Membership is asked
     properly instead, everywhere, without exception. */
  var own = function (obj, key) {
    return !!obj && Object.prototype.hasOwnProperty.call(obj, key);
  };
  var get = function (obj, key) {
    return own(obj, key) ? obj[key] : undefined;
  };

  var esc = function (s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };

  /* Minimal markdown: headings, fenced code, tables, lists, inline emphasis.
     A card is prose a tester reads mid-test, so it renders rather than sitting
     in a <pre>. Every path escapes before it emits: the input is catalogue
     content, and the renderer is the only place that content becomes markup. */
  var md = function (src) {
    var out = [];
    var lines = String(src == null ? "" : src).split("\n");
    var i = 0;
    var inline = function (t) {
      return esc(t)
        .replace(/`([^`]+)`/g, "<code>$1</code>")
        .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
        .replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>")
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1");
    };
    while (i < lines.length) {
      var l = lines[i];
      if (/^```/.test(l)) {
        var buf = [];
        i++;
        while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
        i++;
        out.push("<pre><code>" + esc(buf.join("\n")) + "</code></pre>");
        continue;
      }
      var m = l.match(/^(#{1,4})\s+(.*)$/);
      if (m) {
        var n = Math.min(m[1].length + 2, 6);
        out.push("<h" + n + ">" + inline(m[2]) + "</h" + n + ">");
        i++;
        continue;
      }
      if (/^\s*\|/.test(l) && /^\s*\|[\s:|-]+\|?\s*$/.test(lines[i + 1] || "")) {
        var cells = function (r) {
          return r.trim().replace(/^\||\|$/g, "").split("|").map(function (c) {
            return inline(c.trim());
          });
        };
        var head = cells(l);
        i += 2;
        var rows = [];
        while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(cells(lines[i++]));
        out.push(
          "<table><tr>" + head.map(function (h) { return "<th>" + h + "</th>"; }).join("") + "</tr>" +
          rows.map(function (r) {
            return "<tr>" + r.map(function (c) { return "<td>" + c + "</td>"; }).join("") + "</tr>";
          }).join("") + "</table>"
        );
        continue;
      }
      if (/^\s*[-*]\s+/.test(l) || /^\s*\d+\.\s+/.test(l)) {
        var ordered = /^\s*\d+\./.test(l);
        var items = [];
        while (i < lines.length && (/^\s*[-*]\s+/.test(lines[i]) || /^\s*\d+\.\s+/.test(lines[i]))) {
          items.push(inline(lines[i].replace(/^\s*(?:[-*]|\d+\.)\s+/, "")));
          i++;
          while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*[-*]\s/.test(lines[i])) {
            items[items.length - 1] += " " + inline(lines[i++].trim());
          }
        }
        var t = ordered ? "ol" : "ul";
        out.push("<" + t + ">" + items.map(function (x) { return "<li>" + x + "</li>"; }).join("") + "</" + t + ">");
        continue;
      }
      if (/^---+$/.test(l)) { out.push("<hr>"); i++; continue; }
      if (!l.trim()) { i++; continue; }
      var para = [];
      while (i < lines.length && lines[i].trim() &&
             !/^(#{1,4}\s|```|\s*[-*]\s|\s*\d+\.\s|\s*\|)/.test(lines[i])) {
        para.push(lines[i++]);
      }
      out.push("<p>" + inline(para.join(" ")) + "</p>");
    }
    return out.join("\n");
  };

  /* --------------------------------------------------------------------- *
   * View models. Pure: catalogue in, plain data out, no DOM anywhere.
   * --------------------------------------------------------------------- */

  var LIMIT = 3;

  var bound = function (list, limit) {
    var items = list || [];
    return { shown: items.slice(0, limit), hidden: Math.max(0, items.length - limit) };
  };

  var familyOf = function (fact) { return String(fact || "").split(".")[0]; };

  /* The local chain around one test.

     Five ranks, because collapsing them loses the reason each edge exists:
     the tests that establish a prerequisite, the prerequisite itself, this
     test, what succeeding here establishes, and the tests that capability
     could make relevant. A unit may have several of each; nothing here
     pretends the shape is a line. */
  var localGraph = function (D, unitId, limit) {
    if (!own(D.units, unitId)) return null;
    var cap = limit || LIMIT;
    var edge = get(D.chain, unitId) || { in: [], yields: [], out: [], terminal: [] };

    var incoming = (edge["in"] || []).map(function (link) {
      var producers = (get(D.producers, link.fact) || []).filter(function (id) {
        return id !== unitId && own(D.units, id);
      });
      return {
        fact: link.fact,
        kind: link.kind,
        given: (D.given || []).indexOf(link.fact) >= 0,
        granted: (D.granted || []).indexOf(link.fact) >= 0,
        producers: producers
      };
    });

    var outgoing = (edge.out || []).filter(function (link) {
      return own(D.units, link.unit);
    }).map(function (link) {
      var also = link.also || {};
      return {
        unit: link.unit,
        kind: link.kind,
        tier: link.tier || "chain",
        via: link.via || [],
        hint: link.hint || [],
        also: { all_of: also.all_of || [], any_of: also.any_of || [] },
        alsoCount: (also.all_of || []).length + (also.any_of || []).length
      };
    });

    var yields = (edge.yields || []).map(function (fact) {
      var terminal = (edge.terminal || []).filter(function (t) { return t.fact === fact; })[0];
      return {
        fact: fact,
        family: familyOf(fact),
        terminal: terminal ? terminal.why : null,
        consumers: outgoing.filter(function (link) {
          return link.via.indexOf(fact) >= 0 || link.hint.indexOf(fact) >= 0;
        }).map(function (link) { return link.unit; })
      };
    });

    /* Counted over every edge, not over the bounded preview below. The count is
       the whole reason the engagement heading is safe to skip past, and one
       taken from a three-item slice would read "(1)" where the truth is ninety
       -- worse than no count, because a reader would believe it. */
    var tierTotals = {};
    outgoing.forEach(function (link) {
      tierTotals[link.tier] = (tierTotals[link.tier] || 0) + 1;
    });

    return {
      unit: unitId,
      incoming: bound(incoming, cap),
      yields: bound(yields, cap),
      outgoing: bound(outgoing, cap),
      tierTotals: tierTotals,
      terminal: edge.terminal || [],
      /* An honest empty answer is a result, not a gap. A test that establishes
         nothing chartable says so, and so does one whose every capability is
         where a chain stops. */
      leaf: yields.length === 0,
      allTerminal: yields.length > 0 && yields.every(function (y) { return !!y.terminal; })
    };
  };

  /* What a negative result here does and does not exclude.

     `closes` is a subset of `yields` and is only ever declared by a unit that
     is the sole producer of the fact, so anything yielded and not closed has
     another route to it. Naming those routes is the whole point: a clean
     UNION result does not mean there is no SQL injection while boolean and
     timing routes remain untried. */
  var negativeReading = function (D, unitId) {
    if (!own(D.units, unitId)) return null;
    var unit = D.units[unitId];
    var closes = unit.closes || [];
    var yields = unit.yields || [];
    var open = yields.filter(function (f) { return closes.indexOf(f) < 0; }).map(function (fact) {
      return {
        fact: fact,
        others: (get(D.producers, fact) || []).filter(function (id) {
          return id !== unitId && own(D.units, id);
        })
      };
    });
    var topic = get(D.topics, unit.topic) || {};
    var siblings = (topic.units || []).filter(function (id) {
      return id !== unitId && own(D.units, id);
    });
    return { closes: closes, open: open, siblings: siblings };
  };

  /* Family-scale overview for the general graph: seven nodes, not five hundred. */
  var familyOverview = function (D) {
    var counts = {};
    (D.families || []).forEach(function (fam) {
      counts[fam.name] = {
        name: fam.name,
        label: fam.label,
        note: fam.note,
        facts: (fam.facts || []).length,
        produced: 0,
        required: 0
      };
    });
    (D.families || []).forEach(function (fam) {
      (fam.facts || []).forEach(function (fact) {
        counts[fam.name].produced += (get(D.producers, fact) || []).length;
        counts[fam.name].required += (get(D.requiredBy, fact) || []).length;
      });
    });
    return {
      nodes: (D.families || []).map(function (fam) { return counts[fam.name]; }),
      edges: (D.familyEdges || []).slice()
    };
  };

  /* The seven families, ordered by where this catalogue's own edges actually
     run rather than by any claim about how an attack proceeds.

     Derived, not asserted: of the 368 cross-family edges the catalogue holds,
     14 run against this order and every one of them is reported on the page.
     That is what makes the columns honest -- they are a measurement with its
     own exceptions printed, not a kill chain. `PIVOT.md` rejected a view that
     told a tester what came next; a column here says what a capability *is*
     and where the chart happens to lead from it. */
  var CHAIN_ORDER = ["recon", "access", "surface", "artifact", "control",
                     "primitive", "impact"];

  /* Where the chart reaches, per capability. Four states that partition the
     whole set, so the picture cannot quietly leave anything out:

       impact   where a chain is meant to end
       routed   a charted route from here reaches one
       short    a test uses it, and nothing charted goes on to an outcome
       unused   nothing declares a use for it at all

     `unused` is read from the same set the status page publishes rather than
     recomputed, so the picture and the figure beside it cannot disagree. The
     walk is the same one the README's route figure comes from, for the same
     reason. */
  var chainMap = function (D) {
    var dead = {};
    (D.deadEnds || []).forEach(function (f) { dead[f] = true; });
    var byName = {};
    (D.families || []).forEach(function (fam) { byName[fam.name] = fam; });

    return CHAIN_ORDER.filter(function (name) { return own(byName, name); })
      .map(function (name) {
        var fam = byName[name];
        var cells = (fam.facts || []).map(function (fact) {
          var state = "short";
          if (familyOf(fact) === "impact") state = "impact";
          else if (dead[fact]) state = "unused";
          else if (pathsToImpact(D, fact, { maxPaths: 1, maxDepth: 6 }).length) state = "routed";
          return {
            fact: fact,
            state: state,
            establishedBy: (get(D.producers, fact) || []).length,
            requiredBy: (get(D.requiredBy, fact) || []).length
          };
        });
        var tally = { impact: 0, routed: 0, short: 0, unused: 0 };
        cells.forEach(function (c) { tally[c.state] += 1; });
        return {
          name: name, label: fam.label, note: fam.note,
          cells: cells, tally: tally
        };
      });
  };

  /* The edges that run against the column order, which the map prints rather
     than hides. A picture whose exceptions are invisible is a picture making a
     claim it has not earned. */
  var chainBackEdges = function (D) {
    var pos = {};
    CHAIN_ORDER.forEach(function (name, i) { pos[name] = i; });
    return (D.familyEdges || []).filter(function (e) {
      return e.from !== e.to && pos[e.from] > pos[e.to];
    }).map(function (e) {
      return { from: e.from, to: e.to, units: e.units };
    }).sort(function (a, b) { return b.units - a.units; });
  };

  /* What a unit still declares that a set of established capabilities does not
     cover. The same rule the build applies to a single edge, applied here to a
     whole partial route, so a step in the middle of a path states its own
     unmet conditions rather than inheriting the first edge's. */
  var stillRequired = function (D, unitId, established) {
    var unit = get(D.units, unitId) || {};
    var requires = unit.requires || {};
    var have = {};
    (established || []).forEach(function (f) { have[f] = true; });
    (D.given || []).forEach(function (f) { have[f] = true; });
    var all_of = (requires.all_of || []).filter(function (f) { return !own(have, f); });
    var any_of = (requires.any_of || []);
    if (!any_of.length || any_of.some(function (f) { return own(have, f); })) any_of = [];
    return { all_of: all_of, any_of: any_of };
  };

  /* Routes from one capability to a terminal impact.

     Breadth-first over capability -> consuming unit -> that unit's capabilities,
     so the shortest routes come out first.

     What terminates a walk is **path-local**: a route may not reuse a unit or
     revisit a capability it has already passed through. A shared `seen` across
     the whole search would be cheaper and wrong -- two units can establish the
     same capability, and marking it globally lets whichever route reached it
     first claim it, silently discarding a second route that could have carried
     on to an impact when the first could not. Cycles still terminate, because
     the thing that stops them is the path's own history.

     Performing a unit establishes **everything it yields**, not only the one
     capability the route continues through. Carrying only the latter understated
     what the route had in hand, so a later step was reported as still owing a
     condition an earlier step had already established -- cautious in a way that
     is simply wrong, and the kind of wrong a reader cannot detect.

     A route is identified by its whole shape -- the capability each step
     arrives on, the unit, and the capability it leaves on -- rather than by its
     units alone. Two routes through the same tests by different capabilities are
     different routes, and collapsing them on the unit list would drop one.

     The exploration budget is what keeps that affordable. Without a global
     visited set the frontier can branch widely, so the walk stops after a fixed
     number of expansions and reports the routes it has -- an honest "here are
     the shortest ones" rather than an unbounded search on an engagement laptop. */
  var pathsToImpact = function (D, startFact, options) {
    var opts = options || {};
    var maxPaths = opts.maxPaths || 5;
    var maxDepth = opts.maxDepth || 6;
    var budget = opts.maxExplore || 4000;
    if (!own(D.facts, startFact)) return [];

    var found = [];
    var signatures = {};
    var queue = [{ fact: startFact, steps: [], units: {}, facts: {} }];
    queue[0].facts[startFact] = true;

    while (queue.length && found.length < maxPaths && budget > 0) {
      var here = queue.shift();
      budget--;
      if (here.steps.length >= maxDepth) continue;
      var consumers = get(D.requiredBy, here.fact) || [];
      for (var c = 0; c < consumers.length && found.length < maxPaths; c++) {
        var uid = consumers[c];
        if (!own(D.units, uid) || own(here.units, uid)) continue;
        var established = Object.keys(here.facts);
        var also = stillRequired(D, uid, established);
        var produced = D.units[uid].yields || [];
        for (var y = 0; y < produced.length; y++) {
          var next = produced[y];
          if (own(here.facts, next)) continue;
          var steps = here.steps.concat([
            { from: here.fact, unit: uid, to: next, also: also }
          ]);
          if (familyOf(next) === "impact") {
            var signature = steps.map(function (s) {
              return s.from + ">" + s.unit + ">" + s.to;
            }).join("|");
            if (own(signatures, signature)) continue;
            signatures[signature] = true;
            found.push({ start: startFact, steps: steps, impact: next });
            if (found.length >= maxPaths) break;
            continue;
          }
          var units = {}, facts = {};
          Object.keys(here.units).forEach(function (k) { units[k] = true; });
          Object.keys(here.facts).forEach(function (k) { facts[k] = true; });
          units[uid] = true;
          // Everything the unit yields, not only the capability continued
          // through: performing it established all of them.
          produced.forEach(function (f) { facts[f] = true; });
          queue.push({ fact: next, steps: steps, units: units, facts: facts });
        }
      }
    }
    return found;
  };

  var searchAll = function (D, term) {
    var t = String(term || "").toLowerCase();
    if (t.length < 2) return [];
    var has = function (s) { return String(s == null ? "" : s).toLowerCase().indexOf(t) >= 0; };
    var groups = [];
    var push = function (kind, items) { if (items.length) groups.push({ kind: kind, items: items }); };

    push("Test cases", Object.keys(D.wstg || {}).filter(function (id) {
      return has(id) || has(D.wstg[id]);
    }).sort().map(function (id) {
      return { title: D.wstg[id], sub: id, href: "#/case/" + encodeURIComponent(id) };
    }));

    /* Searched over the orientation fields as well as the title: a tester who
       has just seen a parameter named `tpl` has no way in from the standard,
       and that -- from evidence in front of you to the test that reads it --
       is the one route into the catalogue nothing else answers. */
    push("Tests", Object.keys(D.units || {}).filter(function (id) {
      var u = D.units[id];
      return has(id) || has(u.title) || has(u.objective) || has(u.sink) ||
        (u.triage || []).some(has);
    }).sort().map(function (id) {
      return {
        title: D.units[id].title, sub: id,
        note: D.units[id].objective, href: "#/unit/" + encodeURIComponent(id)
      };
    }));

    push("Topics", Object.keys(D.topics || {}).filter(function (id) {
      return has(id) || has(D.topics[id].title);
    }).sort().map(function (id) {
      return { title: D.topics[id].title, sub: id, href: "#/topic/" + encodeURIComponent(id) };
    }));

    push("Capabilities", Object.keys(D.facts || {}).filter(function (id) {
      var f = D.facts[id];
      return has(id) || has(f.label) || has(f.description);
    }).sort().map(function (id) {
      return {
        title: D.facts[id].label, sub: id,
        note: D.facts[id].description, href: "#/capability/" + encodeURIComponent(id)
      };
    }));

    var pay = [];
    Object.keys(D.payloads || {}).forEach(function (pid) {
      (D.payloads[pid].entries || []).forEach(function (e) {
        if (has(e.name) || has(e.payload) || has(e.detect) || has(e.note)) {
          pay.push({ title: e.name, sub: pid, code: e.payload, href: "#/payloads/" + encodeURIComponent(pid) });
        }
      });
    });
    push("Payloads", pay);

    var ownerOf = function (key) {
      var ids = Object.keys(D.units || {});
      for (var i = 0; i < ids.length; i++) {
        var u = D.units[ids[i]];
        if (u.card === key || u.mitigation === key) return ids[i];
      }
      return null;
    };
    ["cards", "mitigations"].forEach(function (store) {
      var kind = store === "cards" ? "Cards" : "Mitigations";
      push(kind, Object.keys(D[store] || {}).filter(function (key) {
        return has(D[store][key]) || has(key);
      }).sort().map(function (key) {
        var owner = ownerOf(key);
        var text = D[store][key];
        var at = text.toLowerCase().indexOf(t);
        var from = Math.max(0, at - 80);
        return {
          title: key.split("/").pop().replace(/\.md$/, "").replace(/-/g, " "),
          sub: key,
          note: (from ? "… " : "") + text.slice(from, at + t.length + 120).replace(/\s+/g, " ") + " …",
          href: owner ? "#/unit/" + encodeURIComponent(owner) : null
        };
      }));
    });

    push("Tools", Object.keys(D.toolbox || {}).filter(function (id) {
      var tool = D.toolbox[id];
      return has(id) || has(tool.name) || has(tool.purpose);
    }).sort().map(function (id) {
      return {
        title: D.toolbox[id].name, sub: id, note: D.toolbox[id].purpose,
        href: "#/tools/" + encodeURIComponent(id)
      };
    }));

    return groups;
  };

  /* --------------------------------------------------------------------- *
   * Deterministic layout for the local graph. No library, no fetch: five
   * ranks at fixed x, each column centred on a common axis.
   * --------------------------------------------------------------------- */

  /* Four ranks, not five. Squeezing a producer column in as well left every box
     148px wide and the type at nine pixels, which is a diagram nobody reads --
     and the producers were the least of what it cost. They are listed in full
     under the graph instead, with room for all of them rather than the first
     one, and the capability node says how many there are.
     4 x 185 + 3 x 60 + 2 x 10 = 940, against roughly 947 of content width. */
  var NODE_W = 185, NODE_H = 62, VGAP = 20, HGAP = 60, TOP = 36, PAD = 10;
  var TITLE_CHARS = 25, SUB_CHARS = 32;

  var wrap = function (text, perLine, maxLines) {
    var words = String(text == null ? "" : text).split(/\s+/).filter(Boolean);
    var lines = [];
    var line = "";
    for (var i = 0; i < words.length; i++) {
      var candidate = line ? line + " " + words[i] : words[i];
      if (candidate.length > perLine && line) { lines.push(line); line = words[i]; }
      else { line = candidate; }
      if (lines.length === maxLines) break;
    }
    if (lines.length < maxLines && line) lines.push(line);
    if (lines.length === maxLines) {
      var used = lines.join(" ").split(/\s+/).length;
      if (used < words.length) {
        lines[maxLines - 1] = lines[maxLines - 1].slice(0, Math.max(0, perLine - 1)) + "…";
      }
    }
    return lines;
  };

  var layout = function (columns) {
    var heights = columns.map(function (col) {
      return col.nodes.length ? col.nodes.length * NODE_H + (col.nodes.length - 1) * VGAP : 0;
    });
    var tallest = Math.max.apply(null, heights.concat([NODE_H]));
    var centre = TOP + tallest / 2;
    var placed = [];
    columns.forEach(function (col, c) {
      var x = PAD + c * (NODE_W + HGAP);
      var top = centre - heights[c] / 2;
      col.nodes.forEach(function (node, r) {
        placed.push({
          id: node.id, col: c, kind: node.kind, href: node.href,
          title: node.title, sub: node.sub,
          x: x, y: top + r * (NODE_H + VGAP), w: NODE_W, h: NODE_H
        });
      });
    });
    var byId = {};
    placed.forEach(function (node) { byId[node.id] = node; });
    return {
      width: PAD * 2 + columns.length * NODE_W + (columns.length - 1) * HGAP,
      height: TOP + tallest + PAD,
      headings: columns.map(function (col, c) {
        return { text: col.heading, x: PAD + c * (NODE_W + HGAP) };
      }),
      nodes: placed,
      node: function (id) { return get(byId, id); }
    };
  };

  /* The topic's own order, cut where the role changes. Pure and exported, so
     what the page files a unit as can be checked without rendering it.

     Contiguous runs rather than two collected blocks, because the declared
     order carries meaning that collecting destroys: HRR-INJ-01 lists EVADE
     last, after the seven techniques, and its objective is to determine whether
     a *negative result from another technique* was caused by a filter. Gathering
     every stage together moves it third, ahead of the tests it reads. No topic
     alternates more than twice, so the cost of honouring the order is at most
     three headings.

     A unit whose role the page cannot file runs as "unroled" and is still
     shown: one missing from the only page that lists it is a worse failure than
     the flat list this replaces. */
  var unitRuns = function (D, topic) {
    var runs = [];
    ((topic && topic.units) || []).forEach(function (uid) {
      var unit = get(D.units, uid);
      if (!unit) return;
      var role = unit.role === "stage" || unit.role === "variant" ? unit.role : "unroled";
      var last = runs[runs.length - 1];
      if (last && last.role === role) last.units.push(uid);
      else runs.push({ role: role, units: [uid] });
    });
    return runs;
  };

  /* Depth, as three tiers rather than two. Pure and exported: the label a page
     puts on a unit decides how much of the catalogue a reader believes is
     written, and "not an outline" quietly counted a sketch as full depth. */
  var DEPTH_LABEL = {
    outline: "outline",
    sketched: "sketched",
    authored: "written in full"
  };

  var depthOf = function (unit) {
    var status = (unit && unit.status) || "authored";
    return status === "outline" || status === "sketched" ? status : "authored";
  };

  var depthLabel = function (unit) { return DEPTH_LABEL[depthOf(unit)]; };

  /* ------------------------- context selection ------------------------- *
   *
   * The other way into the catalogue. Standards answer "what does the
   * methodology require me to cover"; this answers "given the kind of thing in
   * front of me, which tests may be relevant".
   *
   * The join key is the attack-surface tag, which the catalogue has carried on
   * every topic since before this view existed and which until now was rendered
   * as inert text. Nothing about a target is asked for, entered or kept: a tag
   * describes a kind of surface, not an instance of one, and the selection
   * lives in the URL for the length of one visit.
   * --------------------------------------------------------------------- */

  /* Chosen tags plus everything they imply, in one sorted list.

     The implication is read from the build's closure rather than walked here.
     A tag emitting another states something true of every surface carrying it,
     so a tester who said "search box" has already said "parameter reaching a
     query" and should not have to say it twice. */
  var contextClosure = function (D, chosen) {
    var picked = {}, implied = {};
    var byTag = {};
    (D.surfaces || []).forEach(function (s) { byTag[s.tag] = s; });
    (chosen || []).forEach(function (tag) {
      if (!own(byTag, tag)) return;
      picked[tag] = true;
      (byTag[tag].implies || []).forEach(function (t) { implied[t] = true; });
    });
    // A tag chosen outright is chosen, even where another selection also
    // implies it. Reporting it as implied would tell the reader the catalogue
    // inferred something they had said themselves.
    Object.keys(picked).forEach(function (t) { delete implied[t]; });
    return { selected: Object.keys(picked).sort(), implied: Object.keys(implied).sort() };
  };

  /* The topics a context reaches, each with the tags that put it there.

     Two kinds of match, never merged. A topic matched by a tag the reader chose
     is the answer to their question. A topic matched only through an implied
     tag is a step further out, and one that matches every context regardless --
     `always` in the catalogue -- is not an answer to any question at all: it is
     the part of the methodology that does not depend on what you are looking
     at. Merging the three would make the third bury the first, because there
     are seventeen of them and they never vary. */
  var contextTopics = function (D, chosen) {
    var closure = contextClosure(D, chosen);
    var direct = {}, weak = {};
    (D.surfaces || []).forEach(function (s) {
      var isSelected = closure.selected.indexOf(s.tag) >= 0;
      var isImplied = !isSelected && closure.implied.indexOf(s.tag) >= 0;
      if (!isSelected && !isImplied) return;
      (s.topics || []).forEach(function (tid) {
        var into = isSelected ? direct : weak;
        (into[tid] = into[tid] || []).push(s.tag);
      });
    });
    // A topic reached both ways is reported the stronger way only, with every
    // tag that reached it, so the reason line is complete and the topic appears
    // once.
    var order = function (a, b) { return a < b ? -1 : a > b ? 1 : 0; };
    var rows = Object.keys(direct).sort(order).map(function (tid) {
      return { topic: tid, via: direct[tid].concat(weak[tid] || []).sort(), implied: false };
    });
    Object.keys(weak).sort(order).forEach(function (tid) {
      if (!own(direct, tid)) rows.push({ topic: tid, via: weak[tid].sort(), implied: true });
    });
    return {
      selected: closure.selected,
      implied: closure.implied,
      topics: rows,
      always: (D.alwaysTopics || []).slice()
    };
  };

  /* What a unit still owes, split by the kind of thing it owes it to.

     A context is a kind of surface and establishes no capability, so this can
     never say "your context supplies this" -- there is no mapping from a
     surface tag to a fact, and inventing one would be the page asserting
     something about a target it has never seen. What it can say is which of the
     two kinds of precondition a unit carries, and the vocabulary already
     records that on every fact:

       engagement   a general condition of the engagement -- holding a session,
                    having mapped the entrypoints. An engagement usually
                    supplies it, and it is not a test you have to have run.
       topic/chain  something another test has to establish first. Named with
                    the test that establishes it, which is the chain the rest of
                    this file is about.

     Neither list may be dropped when the page renders this. An engagement-tier
     fact is not a step, and it is also not nothing: `access.user` and
     `recon.entrypoints.mapped` are each established by a test in this
     catalogue, so a unit requiring them has a condition a reader has to have
     met, even though naming it says nothing about where to go next. Showing
     only the second list reports such a unit as free; showing them merged
     reports all but eight of the catalogue as blocked. Both are shown, apart.

     A unit owing nothing of the second kind is one no chain step precedes --
     which is a statement about the catalogue's own filing, and never a claim
     that a target permits the test. */
  var entryCost = function (D, unitId) {
    var unit = get(D.units, unitId) || {};
    var requires = unit.requires || {};
    var given = {};
    (D.given || []).forEach(function (f) { given[f] = true; });
    var engagement = [], earned = [];
    var needed = (requires.all_of || []).concat(requires.any_of || []);
    needed.forEach(function (f) {
      var body = get(D.facts, f) || {};
      // `given` is supplied unconditionally and `granted` may be; neither is
      // earned by a test, so neither belongs in the list of things still owed.
      if (own(given, f) || body.granted || body.tier === "engagement") engagement.push(f);
      else earned.push(f);
    });
    return {
      engagement: engagement,
      earned: earned,
      // Any-of is a choice, so one of several alternatives being earned still
      // leaves the unit enterable where another alternative is not. Reported as
      // the weaker claim: entry-level means nothing here has to be earned.
      entry: earned.length === 0
    };
  };

  var Harrier = {
    own: own, esc: esc, md: md, bound: bound, familyOf: familyOf,
    localGraph: localGraph, negativeReading: negativeReading,
    familyOverview: familyOverview, pathsToImpact: pathsToImpact,
    stillRequired: stillRequired,
    searchAll: searchAll, wrap: wrap, layout: layout, LIMIT: LIMIT,
    unitRuns: unitRuns, depthOf: depthOf, depthLabel: depthLabel,
    contextClosure: contextClosure, contextTopics: contextTopics,
    entryCost: entryCost,
    chainMap: chainMap, chainBackEdges: chainBackEdges, CHAIN_ORDER: CHAIN_ORDER
  };
  if (typeof module !== "undefined" && module.exports) module.exports = Harrier;
  if (typeof globalThis !== "undefined") globalThis.Harrier = Harrier;

  /* Loaded by the test runner for the functions above; everything below needs a
     document and there is not one. */
  if (typeof document === "undefined") return;

  /* --------------------------------------------------------------------- *
   * The page.
   * --------------------------------------------------------------------- */

  var D = JSON.parse(document.getElementById("data").textContent);
  var main = document.getElementById("main");

  var href = function (kind, id) { return "#/" + kind + "/" + encodeURIComponent(id); };
  var idChip = function (id) { return '<span class="idchip">' + esc(id) + "</span>"; };
  var factLabel = function (f) { var body = get(D.facts, f); return (body && body.label) || f; };
  var unitTitle = function (id) { var u = get(D.units, id); return (u && u.title) || id; };
  var topicTitle = function (id) { var t = get(D.topics, id); return (t && t.title) || id; };
  var groupOf = function (wid) { return String(wid || "").split("-")[1]; };
  var groupName = function (code) {
    var hit = (D.groups || []).filter(function (g) { return g.code === code; })[0];
    return hit ? hit.name : code;
  };

  var statusPill = function (unit) {
    var status = depthOf(unit);
    return '<span class="pill ' + status + '">' + status + "</span>";
  };

  /* The same label without the link. A row is itself a link, and an anchor
     inside an anchor is not nesting the parser accepts: it closes the outer one
     and everything after it becomes a sibling, so the row visibly breaks apart.
     Nothing is lost by dropping the link -- the row leads to the test, and the
     test names the same capability as a link. */
  var capLabel = function (fact, cls) {
    return '<span class="tag ' + (cls || "cap") + '" title="' + esc(fact) + '">' +
      esc(factLabel(fact)) + "</span>";
  };

  var capTag = function (fact, cls) {
    return '<a class="tag ' + (cls || "cap") + '" href="' + href("capability", fact) +
      '" title="' + esc(fact) + '">' + esc(factLabel(fact)) + "</a>";
  };

  var crumbs = function (trail) {
    return '<div class="crumbs">' + trail.map(function (step, i) {
      var part = step.href
        ? '<a href="' + step.href + '">' + esc(step.text) + "</a>"
        : esc(step.text);
      return (i ? '<span class="sep">/</span>' : "") + part;
    }).join("") + "</div>";
  };

  var rowLink = function (target, title, sub, right) {
    return '<a class="row" href="' + target + '"><span class="who"><span class="t">' +
      esc(title) + '</span>' + (sub ? '<span class="s">' + esc(sub) + "</span>" : "") +
      '</span><span class="n">' + (right || "") + "</span></a>";
  };

  var unitsOfCase = function (wid) {
    var out = [];
    (get(D.claims, wid) || []).forEach(function (tid) {
      var topic = get(D.topics, tid);
      if (topic) out = out.concat(topic.units || []);
    });
    return out;
  };

  var caseCounts = function (wid) {
    var units = unitsOfCase(wid);
    return {
      topics: (get(D.claims, wid) || []).length,
      units: units.length,
      authored: units.filter(function (id) {
        var u = get(D.units, id);
        return u && depthOf(u) === "authored";
      }).length,
      sketched: units.filter(function (id) {
        var u = get(D.units, id);
        return u && depthOf(u) === "sketched";
      }).length
    };
  };

  /* Which axis slug a unit's name is drawn from, and what that slug means.
     It is the honest answer to "why is this a separate test": the topic split
     on that axis, and this is the value it took. */
  var axisOf = function (unit) {
    var parts = String(unit.id || "").split("-");
    var slug = parts.length > 3 ? parts[3] : "";
    var topic = get(D.topics, unit.topic) || {};
    var order = [topic.axis].concat(Object.keys(D.axes || {}));
    for (var i = 0; i < order.length; i++) {
      var axis = get(D.axes, order[i]);
      if (axis && own(axis.slugs, slug)) {
        return { axis: order[i], slug: slug, note: axis.slugs[slug] };
      }
    }
    return slug ? { axis: null, slug: slug, note: null } : null;
  };

  /* ---------------------------- views ---------------------------------- */

  var viewStandards = function () {
    var pinned = Object.keys(D.wstg || {}).length;
    var extensions = (D.extensions || []).length;
    return crumbs([{ text: "Standards" }]) +
      "<h2>Standards</h2>" +
      '<p class="lede">WSTG tells you what to cover. Harrier shows you the real tests ' +
      "inside it and where each successful test can lead.</p>" +
      '<div class="rows">' +
      rowLink("#/wstg", D.standard.name,
        (D.groups || []).length + " testing groups · " + pinned + " test cases",
        D.counts.units + " tests") +
      rowLink("#/extensions", "Harrier Extensions",
        "Topics with no test case in the standard",
        extensions ? extensions + " topics" : "none yet") +
      "</div>" +
      '<p class="muted">One execution standard is supported. ASVS is a control and ' +
      "remediation mapping and CWE is a weakness classification; neither is an " +
      "execution methodology, and neither appears here as one.</p>" +
      '<p class="muted"><a href="#/status">Catalogue status and model</a> · ' +
      '<a href="#/chains">Attack chains</a> · <a href="#/about">About</a></p>';
  };

  var viewStandard = function () {
    var rows = (D.groups || []).map(function (group) {
      var units = 0, cases = group.ids.length;
      group.ids.forEach(function (wid) { units += caseCounts(wid).units; });
      return rowLink(href("wstg", group.code), group.name,
        group.code, cases + " test cases · " + units + " tests");
    }).join("");
    return crumbs([{ text: "Standards", href: "#/standards" }, { text: D.standard.short }]) +
      "<h2>" + esc(D.standard.name) + "</h2>" +
      '<div class="sub">Pinned at ' + esc(D.standard.commit.slice(0, 12)) +
      ", retrieved " + esc(D.standard.retrieved) + "</div>" +
      '<p class="lede">The groups below are the standard\'s own navigation order, not a ' +
      "mandatory testing workflow. Pick the one you are working in.</p>" +
      '<div class="rows">' + rows + "</div>";
  };

  var viewGroup = function (code) {
    var group = (D.groups || []).filter(function (g) { return g.code === code; })[0];
    if (!group) return notFound("testing group", code);
    var rows = group.ids.map(function (wid) {
      var c = caseCounts(wid);
      var right = c.units
        ? c.units + " tests" + (c.authored ? " · " + c.authored + " in full" : "") +
          (c.sketched ? " · " + c.sketched + " sketched" : "")
        : '<span class="empty">not decomposed</span>';
      return rowLink(href("case", wid), D.wstg[wid], wid, right);
    }).join("");
    return crumbs([
      { text: "Standards", href: "#/standards" },
      { text: D.standard.short, href: "#/wstg" },
      { text: group.name }
    ]) +
      "<h2>" + esc(group.name) + "</h2>" +
      '<div class="sub">' + group.ids.length + " test cases · " + esc(group.code) + "</div>" +
      '<div class="rows">' + rows + "</div>";
  };

  var viewCase = function (wid) {
    if (!own(D.wstg, wid)) return notFound("test case", wid);
    var claiming = get(D.claims, wid) || [];
    var code = groupOf(wid);
    var head = crumbs([
      { text: "Standards", href: "#/standards" },
      { text: D.standard.short, href: "#/wstg" },
      { text: groupName(code), href: href("wstg", code) },
      { text: wid }
    ]) +
      "<h2>" + esc(D.wstg[wid]) + "</h2>" +
      '<div class="sub">' + idChip(wid) + " · " + esc(groupName(code)) + "</div>";

    if (!claiming.length) {
      var unresolved = (D.unresolved || []).indexOf(wid) >= 0;
      return head + '<div class="card"><p>' +
        (unresolved
          ? "Harrier does not decompose this test case. The domain map records it as " +
            "one the ordered procedure deliberately does not resolve — it is not one " +
            "test, or not a test at all."
          : "No Harrier topic claims this test case yet.") +
        "</p></div>";
    }

    var body = '<p class="lede">Harrier decomposes this test case into ' +
      "independently performable tests. Each one carries its own objective and its " +
      "own boundary against the others; where it is written in full it carries its " +
      "own oracle too." +
      (claiming.length > 1
        ? " This identifier is claimed by " + claiming.length +
          " topics, which is the model working rather than a defect: it is more than one test."
        : "") +
      "</p>";

    body += claiming.map(function (tid) {
      var topic = get(D.topics, tid);
      if (!topic) return "";
      // The same split the topic page uses. This is the documented primary
      // route -- standard, group, test case, units -- so leaving it flat here
      // would mean the distinction existed only on the page a reader reaches
      // second.
      var units = unitRoles(topic);
      var boundaries = (topic.boundaries || []).map(function (b) {
        return "<li><b>" + esc(b.subject) + ".</b> " + esc(b.note) +
          (b.home && own(D.topics, b.home)
            ? ' <a href="' + href("topic", b.home) + '">' + esc(topicTitle(b.home)) + "</a>"
            : "") + "</li>";
      }).join("");
      /* Units first. A boundary note explains what is deliberately *not* here,
         which matters once the reader is oriented and is an obstacle before
         they are -- so it follows, and it is folded away until asked for. */
      return "<h3>" + esc(topic.title) + " <a class=\"idchip\" href=\"" + href("topic", tid) +
        '">' + esc(tid) + "</a></h3>" +
        (topic.wstg.length > 1
          ? '<p class="muted">This topic also covers ' + topic.wstg.filter(function (w) {
              return w !== wid;
            }).map(function (w) {
              return '<a href="' + href("case", w) + '">' + esc(w) + "</a>";
            }).join(", ") + ".</p>"
          : "") +
        units +
        (boundaries
          ? "<details class=\"fold\"><summary>Boundaries · " +
            (topic.boundaries || []).length + " note" +
            ((topic.boundaries || []).length === 1 ? "" : "s") +
            " on what is deliberately elsewhere</summary><ul>" + boundaries + "</ul></details>"
          : "");
    }).join("");

    return head + body;
  };

  var viewExtensions = function () {
    var ids = D.extensions || [];
    var head = crumbs([{ text: "Standards", href: "#/standards" }, { text: "Harrier Extensions" }]) +
      "<h2>Harrier Extensions</h2>" +
      '<p class="lede">Topics Harrier carries that no WSTG test case claims. They live ' +
      "here rather than being forced into a group they do not belong to.</p>";
    if (!ids.length) {
      return head + '<div class="card"><p class="muted">Nothing yet. Every topic in the ' +
        "catalogue currently maps to a WSTG test case. This is where beyond-WSTG " +
        "material — JWT, OAuth and OIDC, GraphQL, request smuggling, cache poisoning, " +
        "prototype pollution, race conditions, cloud metadata — appears as it is " +
        "written.</p></div>";
    }
    return head + '<div class="rows">' + ids.map(function (tid) {
      var topic = get(D.topics, tid);
      return rowLink(href("topic", tid), topic.title, tid, (topic.units || []).length + " tests");
    }).join("") + "</div>";
  };

  var viewTopic = function (tid) {
    var topic = get(D.topics, tid);
    if (!topic) return notFound("topic", tid);
    var cases = (topic.wstg || []).map(function (w) {
      return '<a href="' + href("case", w) + '">' + esc(w) + " · " + esc(get(D.wstg, w) || "") + "</a>";
    }).join("<br>");
    var trail = [{ text: "Standards", href: "#/standards" }];
    if (topic.wstg && topic.wstg.length) {
      trail.push({ text: D.standard.short, href: "#/wstg" });
      trail.push({
        text: groupName(groupOf(topic.wstg[0])),
        href: href("wstg", groupOf(topic.wstg[0]))
      });
    } else {
      trail.push({ text: "Harrier Extensions", href: "#/extensions" });
    }
    trail.push({ text: topic.title });

    return crumbs(trail) +
      "<h2>" + esc(topic.title) + "</h2>" +
      '<div class="sub">' + idChip(tid) + " · domain " + esc(topic.domain) +
      (topic.axis ? " · split on " + esc(topic.axis) : "") + "</div>" +
      (cases ? '<div class="card"><span class="k">Covers</span>' + cases + "</div>" : "") +
      ((topic.surfaces && topic.surfaces.any_of)
        ? '<div class="card"><span class="k">Applies where</span>' +
          topic.surfaces.any_of.map(function (s) {
            return '<span class="tag">' + esc(s) + "</span>";
          }).join("") + "</div>"
        : "") +
      ((topic.boundaries || []).length
        ? "<h3>Boundaries</h3>" + topic.boundaries.map(function (b) {
            return '<div class="card"><span class="k">' + esc(b.subject) + "</span><p>" +
              esc(b.note) + (b.home && own(D.topics, b.home)
                ? ' <a href="' + href("topic", b.home) + '">' + esc(topicTitle(b.home)) + "</a>"
                : ' <span class="muted">not written</span>') + "</p></div>";
          }).join("")
        : "") +
      unitRoles(topic);
  };

  /* A topic holds two kinds of unit and the flat list said which was which
     nowhere. "Perform all three, in order" and "pick one on the evidence" are
     opposite instructions, and a reader given ten rows with no marking has to
     open each one to find out. The order inside each block is the topic's own. */
  var ROLE_BLOCKS = {
    stage: {
      heading: "Stages",
      note: "Perform each of these. The order is the one the topic sets."
    },
    variant: {
      heading: "Alternatives",
      note: "Choose among these on the evidence in front of you. They are routes " +
        "to the same finding, not steps toward it."
    },
    unroled: {
      heading: "Unclassified",
      note: "These declare no role. That is a gap in the catalogue, not a third " +
        "kind of unit."
    }
  };

  var unitCard = function (uid) {
    var unit = get(D.units, uid);
    if (!unit) return "";
    return '<a class="card" href="' + href("unit", uid) + '"><h4>' + esc(unit.title) +
      " " + statusPill(unit) + '</h4><p class="muted">' + esc(unit.objective) +
      '</p><div class="meta">' + idChip(uid) + "</div></a>";
  };

  var unitRoles = function (topic) {
    var explained = {};
    return unitRuns(D, topic).map(function (run) {
      var block = ROLE_BLOCKS[run.role];
      // The instruction is spelled out the first time each role appears and not
      // repeated: a topic that returns to its stages is continuing, not
      // starting something the reader has not been told about.
      var note = explained[run.role] ? "" : block.note;
      explained[run.role] = true;
      return "<h3>" + esc(block.heading) + " · " + run.units.length + "</h3>" +
        (note ? '<p class="muted">' + esc(note) + "</p>" : "") +
        run.units.map(unitCard).join("");
    }).join("");
  };

  /* ------------------------- the test detail ---------------------------- */

  var graphSvg = function (model) {
    var columns = [
      { heading: "Prerequisite", nodes: [] },
      { heading: "This test", nodes: [] },
      { heading: "Establishes", nodes: [] },
      { heading: "Potential continuation", nodes: [] }
    ];
    var edges = [];

    var selfId = "u:" + model.unit;
    var unit = D.units[model.unit];
    columns[1].nodes.push({
      id: selfId, kind: "self", title: unit.title,
      sub: depthLabel(unit), href: null
    });

    model.incoming.shown.forEach(function (link) {
      var capId = "c:" + link.fact;
      columns[0].nodes.push({
        id: capId,
        kind: link.kind === "motivated_by" ? "hintcap" : "req",
        title: factLabel(link.fact),
        sub: link.given ? "given — a root of the graph"
          : link.granted ? "the engagement may supply it"
          : link.producers.length
            ? link.producers.length + (link.producers.length === 1
                ? " test establishes it" : " tests establish it")
            : "no test establishes it",
        href: href("capability", link.fact)
      });
      edges.push({
        from: capId, to: selfId,
        kind: link.kind === "motivated_by" ? "soft" : "hard",
        label: link.kind === "motivated_by" ? "motivates"
          : link.kind === "any_of" ? "any of" : "requires"
      });
    });

    model.yields.shown.forEach(function (y) {
      var capId = "y:" + y.fact;
      columns[2].nodes.push({
        id: capId, kind: "cap", title: factLabel(y.fact),
        sub: y.terminal === "impact" ? "impact — a chain ends here"
          : y.terminal === "unconsumed" ? "no test declares a use for it"
          : y.consumers.length + (y.consumers.length === 1 ? " test may follow" : " tests may follow"),
        href: href("capability", y.fact)
      });
      edges.push({ from: selfId, to: capId, kind: "hard", label: "establishes" });
    });

    model.outgoing.shown.forEach(function (link) {
      var nodeId = "n:" + link.unit;
      columns[3].nodes.push({
        id: nodeId, kind: "unit", title: unitTitle(link.unit),
        sub: link.alsoCount
          ? link.alsoCount + (link.alsoCount === 1 ? " further condition" : " further conditions")
          : "no further hard prerequisite",
        href: href("unit", link.unit)
      });
      var via = link.via.length ? link.via : link.hint;
      via.slice(0, 1).forEach(function (fact) {
        edges.push({
          from: "y:" + fact, to: nodeId,
          kind: link.kind === "requires" ? "hard" : "soft",
          label: link.kind === "requires" ? "requires" : "motivated by"
        });
      });
    });

    var plan = layout(columns);
    var parts = [
      '<defs><marker id="arw" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" ' +
      'markerHeight="7" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="currentColor"></path>' +
      "</marker></defs>"
    ];
    plan.headings.forEach(function (h, i) {
      if (!columns[i].nodes.length) return;
      parts.push('<text class="gcol" x="' + h.x + '" y="16">' + esc(h.text) + "</text>");
    });
    edges.forEach(function (e) {
      var a = plan.node(e.from), b = plan.node(e.to);
      if (!a || !b) return;
      var x1 = a.x + a.w, y1 = a.y + a.h / 2, x2 = b.x - 9, y2 = b.y + b.h / 2;
      var mid = (x1 + x2) / 2;
      parts.push('<path class="gedge ' + e.kind + '" marker-end="url(#arw)" d="M' + x1 + " " + y1 +
        " C" + mid + " " + y1 + " " + mid + " " + y2 + " " + x2 + " " + y2 + '"></path>');
      parts.push('<text class="glabel" x="' + mid + '" y="' + ((y1 + y2) / 2 - 5) +
        '" text-anchor="middle">' + esc(e.label) + "</text>");
    });
    plan.nodes.forEach(function (node) {
      var lines = wrap(node.title, TITLE_CHARS, 2);
      var body = '<rect x="0" y="0" width="' + node.w + '" height="' + node.h + '" rx="4"></rect>' +
        "<title>" + esc(node.title + " — " + node.sub) + "</title>" +
        lines.map(function (line, i) {
          return '<text x="10" y="' + (20 + i * 15) + '">' + esc(line) + "</text>";
        }).join("") +
        '<text class="s" x="10" y="' + (node.h - 10) + '">' +
        esc(wrap(node.sub, SUB_CHARS, 1)[0] || "") + "</text>";
      /* A node that navigates is a link, and a link a mouse can use and a
         keyboard cannot is not one. `tabindex` and the role put it in the tab
         order and name it; the document handler treats Enter and Space the same
         as a click. */
      var cls = "gnode " + node.kind + (node.href ? " link" : "");
      var attrs = node.href
        ? ' data-go="' + esc(node.href) + '" tabindex="0" role="link" aria-label="' +
          esc(node.title + ", " + node.sub) + '"'
        : ' role="img" aria-label="' + esc(node.title + ", " + node.sub) + '"';
      parts.push('<g class="' + cls + '" transform="translate(' + node.x + "," + node.y + ')"' +
        attrs + ">" + body + "</g>");
    });

    return '<div class="scroller graph"><svg width="' + plan.width + '" height="' + plan.height +
      '" viewBox="0 0 ' + plan.width + " " + plan.height + '" role="group" ' +
      'aria-label="Local attack chain around this test">' + parts.join("") + "</svg></div>";
  };

  /* The producers the graph no longer has a column for -- all of them, named,
     rather than the first of them squeezed into a box. Where a prerequisite has
     several, that is the thing worth seeing: it is why a clean result on any one
     of them settles nothing. */
  var prerequisiteDetail = function (model) {
    if (!model.incoming.shown.length) return "";
    return model.incoming.shown.map(function (link) {
      var how = link.kind === "motivated_by" ? "Worth doing sooner given"
        : link.kind === "any_of" ? "Prerequisite (any one of the alternatives)"
        : "Prerequisite";
      var route;
      if (link.given) {
        route = '<p class="also">A root of the graph: nothing has to establish it.</p>';
      } else if (link.granted) {
        route = '<p class="also">An engagement may supply this and often does not. ' +
          "No test in the catalogue establishes it.</p>";
      } else if (!link.producers.length) {
        route = '<p class="also">No test in the catalogue establishes this.</p>';
      } else {
        route = '<p class="also"><b>Established by:</b> ' +
          link.producers.map(function (id) {
            return '<a href="' + href("unit", id) + '">' + esc(unitTitle(id)) + "</a>";
          }).join(", ") +
          (link.producers.length > 1
            ? ' <span class="muted">— more than one route, so a clean result on any ' +
              "single one does not settle it.</span>"
            : "") + "</p>";
      }
      return '<div class="stack"><span class="k">' + how + "</span>" +
        "<h4>" + capTag(link.fact, link.kind === "motivated_by" ? "hint" : "req") + "</h4>" +
        (get(D.facts, link.fact) && D.facts[link.fact].description
          ? '<p class="muted">' + esc(D.facts[link.fact].description) + "</p>" : "") +
        route + "</div>";
    }).join("");
  };

  /* The three relations this list has always held, named. An edge through a
     held session and an edge through a captured token were printed identically
     before, which made the second unfindable among ninety of the first. */
  var TIER_ORDER = ["chain", "topic", "engagement"];
  var TIER_HEADING = {
    chain: "Escalates to",
    topic: "Another technique for this test",
    engagement: "This is a general prerequisite of"
  };
  var TIER_NOTE = {
    chain: "",
    topic: "Same topic: an alternative route to the same finding, not a step past it.",
    engagement: "Reached by holding what most of the catalogue starts from. True, " +
      "and not a route onward."
  };

  /* Engagement-tier edges are named and linked, not expanded. Every one of them
     says the same thing -- this test also needs what most of the catalogue needs
     -- and spending an objective, an established-here list and a still-required
     list on that is what buried the tiers above it. */
  var continuationBrief = function (link) {
    var unit = D.units[link.unit];
    return '<div class="brief"><a href="' + href("unit", link.unit) + '">' +
      esc(unit.title) + "</a> " + statusPill(unit) + "</div>";
  };

  var continuationLink = function (link) {
    var unit = D.units[link.unit];
    var established = link.via.length ? link.via : link.hint;
    var still = link.also.all_of.map(function (f) { return capTag(f, "req"); }).join("") +
      (link.also.any_of.length
        ? '<span class="muted"> any one of </span>' +
          link.also.any_of.map(function (f) { return capTag(f, "req"); }).join("")
        : "");
    return '<div class="stack"><span class="k">' +
      (link.kind === "requires" ? "Requires what this establishes" : "Becomes worth doing sooner") +
      '</span><h4><a href="' + href("unit", link.unit) + '">' + esc(unit.title) + "</a> " +
      statusPill(unit) + "</h4>" +
      '<p class="muted">' + esc(unit.objective) + "</p>" +
      '<div class="also"><b>Established here:</b> ' +
      established.map(function (f) { return capTag(f, "cap"); }).join("") + "</div>" +
      '<div class="also">' + (still
        ? "<b>Still required:</b> " + still +
          ' <span class="muted">— Harrier has no view of a target and does not claim these hold.</span>'
        : "<b>No additional declared hard prerequisite.</b> What a unit declares " +
          "is what the catalogue knows, which may be less than the whole of it — " +
          "and Harrier has no view of a target either way.") +
      "</div></div>";
  };

  var continuationDetail = function (model) {
    if (!model.outgoing.shown.length) return "";
    /* An unrecognised tier is shown rather than dropped: bucketing by a value
       no heading claims would silently lose the edge, and losing an escalation
       is the one outcome this grouping exists to prevent. */
    var buckets = {};
    model.outgoing.shown.forEach(function (link) {
      var tier = TIER_ORDER.indexOf(link.tier) >= 0 ? link.tier : "chain";
      (buckets[tier] = buckets[tier] || []).push(link);
    });
    var totals = model.tierTotals || {};
    return TIER_ORDER.filter(function (tier) { return buckets[tier]; }).map(function (tier) {
      var links = buckets[tier];
      var total = totals[tier] || links.length;
      var render = tier === "engagement" ? continuationBrief : continuationLink;
      var more = total > links.length
        ? '<p class="muted tiernote">' + (total - links.length) + " more not shown here.</p>"
        : "";
      return '<div class="tier tier-' + tier + '">' +
        '<h3 class="tierhead">' + esc(TIER_HEADING[tier]) +
        ' <span class="muted">(' + total + ')</span></h3>' +
        (TIER_NOTE[tier] ? '<p class="muted tiernote">' + esc(TIER_NOTE[tier]) + "</p>" : "") +
        links.map(render).join("") + more + "</div>";
    }).join("");
  };

  var negativeSection = function (uid) {
    var reading = negativeReading(D, uid);
    if (!reading) return "";
    var parts = [];
    if (reading.closes.length) {
      parts.push("<p><b>Rules out.</b> A negative result here settles " +
        reading.closes.map(function (f) { return capTag(f, "req"); }).join("") +
        ". This test is the only route to it in the catalogue, which is why it may " +
        "close it at all.</p>");
    }
    reading.open.forEach(function (item) {
      if (!item.others.length) return;
      parts.push("<p><b>Does not rule out " + esc(factLabel(item.fact)) + ".</b> " +
        item.others.length + " other " + (item.others.length === 1 ? "test" : "tests") +
        " can establish the same capability by a different route: " +
        item.others.slice(0, 6).map(function (id) {
          return '<a href="' + href("unit", id) + '">' + esc(unitTitle(id)) + "</a>";
        }).join(", ") + ".</p>");
    });
    if (!parts.length) {
      parts.push('<p class="muted">Nothing in the catalogue is settled by a negative result ' +
        "here. That is the honest reading: this test not succeeding is evidence about " +
        "this route and not about the condition behind it.</p>");
    }
    if (reading.siblings.length) {
      parts.push('<p class="muted">Sibling tests in the same topic, in the order the topic ' +
        "declares: " + reading.siblings.slice(0, 8).map(function (id) {
          return '<a href="' + href("unit", id) + '">' + esc(unitTitle(id)) + "</a>";
        }).join(" · ") + "</p>");
    }
    return "<h3>If this test is unsuccessful</h3><div class=\"card\">" + parts.join("") + "</div>";
  };

  /* Where this sits and where it can lead, in three lines, immediately.

     The full graph stays below the procedure, because a tester who has decided
     to perform the test should not have to scroll past a diagram to reach the
     oracle. But on an authored unit the procedure runs for several screens, and
     a reader who has to reach the end of it before learning that a success here
     opens four other tests has been given the product's best feature last. The
     strip is the answer up front; the graph is the same answer with its
     reasoning attached. */
  var chainStrip = function (uid) {
    var model = localGraph(D, uid, 9999);
    if (!model) return "";
    var line = function (label, body) {
      return '<div class="striprow"><span class="k">' + label + "</span><span>" + body + "</span></div>";
    };
    var parts = [];

    var needs = model.incoming.shown.filter(function (l) { return l.kind !== "motivated_by"; });
    parts.push(line("Needs first", needs.length
      ? needs.map(function (l) { return capTag(l.fact, "req"); }).join("")
      : '<span class="muted">Nothing declared: this test states no condition.</span>'));

    parts.push(line("Success establishes", model.yields.shown.length
      ? model.yields.shown.map(function (y) { return capTag(y.fact, "cap"); }).join("")
      : '<span class="muted">Nothing declared, so no continuation is derived.</span>'));

    var onward = model.outgoing.shown;
    var body;
    if (onward.length) {
      body = onward.slice(0, 4).map(function (l) {
        return '<a href="' + href("unit", l.unit) + '">' + esc(unitTitle(l.unit)) + "</a>";
      }).join(" · ") +
        (onward.length > 4 ? ' <span class="muted">and ' + (onward.length - 4) + " more</span>" : "") +
        ' <span class="muted">— each with its own further conditions, below.</span>';
    } else if (model.terminal.length) {
      body = model.terminal.some(function (t) { return t.why === "impact"; })
        ? '<span class="muted">An impact. A chain ends here.</span>'
        : '<span class="muted">Nothing in the catalogue declares a use for what this ' +
          "establishes, so the result is reportable rather than a step onward.</span>";
    } else {
      body = '<span class="muted">Nothing is derived from this test.</span>';
    }
    parts.push(line("May then be relevant", body));

    return '<div class="strip">' + parts.join("") + "</div>";
  };

  var viewUnit = function (uid, open) {
    var unit = get(D.units, uid);
    if (!unit) return notFound("test", uid);
    var topic = get(D.topics, unit.topic) || {};
    var wid = (unit.wstg || [])[0];
    var trail = [{ text: "Standards", href: "#/standards" }];
    if (wid) {
      trail.push({ text: D.standard.short, href: "#/wstg" });
      trail.push({ text: groupName(groupOf(wid)), href: href("wstg", groupOf(wid)) });
      trail.push({ text: wid, href: href("case", wid) });
    } else {
      trail.push({ text: "Harrier Extensions", href: "#/extensions" });
    }
    trail.push({ text: topic.title || unit.topic, href: href("topic", unit.topic) });
    trail.push({ text: unit.title });

    var out = [crumbs(trail)];
    out.push("<h2>" + esc(unit.title) + "</h2>");
    out.push('<div class="sub">' + idChip(uid) + " · " + statusPill(unit) +
      ' · <span class="pill">' + esc(unit.kind || "test") + "</span></div>");

    var block = function (label, html) {
      if (html) out.push('<div class="card"><span class="k">' + label + "</span>" + html + "</div>");
    };
    var list = function (items, tag) {
      return "<" + tag + ">" + (items || []).map(function (s) {
        return "<li>" + esc(s) + "</li>";
      }).join("") + "</" + tag + ">";
    };

    block("Objective", "<p>" + esc(unit.objective) + "</p>");
    out.push(chainStrip(uid));

    var axis = axisOf(unit);
    if (axis && axis.note) {
      block("Why this is a separate test",
        "<p>" + esc(topic.title || unit.topic) + " splits on <b>" + esc(axis.axis) +
        "</b>, and this is <b>" + esc(axis.slug) + "</b>: " + esc(axis.note) + "</p>" +
        (topic.boundaries && topic.boundaries.length
          ? '<p class="muted">The topic records ' + topic.boundaries.length +
            " boundary note" + (topic.boundaries.length === 1 ? "" : "s") +
            ' against neighbouring topics — see <a href="' + href("topic", unit.topic) +
            '">' + esc(topic.title || unit.topic) + "</a>.</p>"
          : ""));
    }

    /* Orientation before procedure: what this assumes, where to start looking,
       and where a controlled input comes to rest. A reader who cannot answer
       the second one has nothing to point the sequence at. */
    if (unit.hypotheses) block("What this assumes", list(unit.hypotheses, "ul"));
    if (unit.triage) block("Where to start", list(unit.triage, "ul"));
    if (unit.sink) block("Where the input lands", "<p>" + esc(unit.sink) + "</p>");

    if (unit.enter_when) block("Enter when", list(unit.enter_when, "ul"));
    if (unit.preconditions) block("Preconditions", list(unit.preconditions, "ul"));
    if (unit.oracle) {
      block("Oracle",
        "<p><b>Positive.</b> " + esc(unit.oracle.positive) + "</p>" +
        "<p><b>Negative.</b> " + esc(unit.oracle.negative) + "</p>" +
        (unit.oracle.inconclusive ? "<p><b>Inconclusive.</b> " + esc(unit.oracle.inconclusive) + "</p>" : ""));
    }
    if (unit.questions) block("Questions", list(unit.questions, "ul"));
    if (unit.sequence) block("Sequence", list(unit.sequence, "ol"));
    if (unit.first_false_positive) {
      block("First false positive", '<p class="warn">' + esc(unit.first_false_positive) + "</p>");
    }
    if (unit.false_positives) block("Other false positives", list(unit.false_positives, "ul"));
    if (unit.evidence) block("Evidence", list(unit.evidence, "ul"));
    if (unit.done_when) block("Done when", "<p>" + esc(unit.done_when) + "</p>");
    if (unit.safety) block("Safety boundary", '<p class="warn">' + esc(unit.safety) + "</p>");

    if (depthOf(unit) === "outline") {
      out.push('<div class="notice">This test is an outline. It carries an identifier, a ' +
        "falsifiable objective and its place in the chain; the procedure has not been " +
        "written. Nothing below is invented to fill the gap.</div>");
    } else if (depthOf(unit) === "sketched") {
      out.push('<div class="notice">This test is sketched. It carries the steps that ' +
        "produce a result, how to tell a real one from the mistake that most often " +
        "imitates it, and what finishing means; when it is worth entering, what to " +
        "record and how far to take it are not written. Nothing below is invented to " +
        "fill the gap.</div>");
    }

    var payKey = String(unit.payloads || "").replace(/^payloads\//, "").replace(/\.yaml$/, "");
    var pay = get(D.payloads, payKey);
    if (pay) {
      out.push("<h3>Payloads · " + esc(pay.title) + "</h3>");
      out.push('<p class="muted">reviewed ' + esc(pay.reviewed) +
        (pay.safety ? " · " + esc(pay.safety) : "") + "</p>");
      out.push('<div class="scroller"><table><tr><th>Name</th><th>Payload</th><th>Detect</th></tr>' +
        (pay.entries || []).map(function (e) {
          return "<tr><td>" + esc(e.name) + "</td><td><code>" + esc(e.payload) + "</code></td><td>" +
            esc(e.detect || "") +
            (e.note ? '<br><span class="muted">' + esc(e.note) + "</span>" : "") + "</td></tr>";
        }).join("") + "</table></div>");
    }

    (unit.tools || []).forEach(function (id) {
      var tool = get(D.toolbox, id);
      if (!tool) return;
      out.push("<h3>Tool · " + esc(tool.name) + "</h3>");
      out.push('<p class="muted">' + esc(tool.purpose) + "</p>");
      out.push((tool.invocations || []).map(function (v) {
        return '<div class="card"><span class="k">' + esc(v.purpose) + "</span><pre><code>" +
          esc(v.cmd) + "</code></pre>" +
          (v.flags
            ? '<div class="scroller"><table><tr><th>Flag</th><th>Why</th></tr>' +
              Object.keys(v.flags).map(function (f) {
                return "<tr><td><code>" + esc(f) + "</code></td><td>" + esc(v.flags[f]) + "</td></tr>";
              }).join("") + "</table></div>"
            : "") + "</div>";
      }).join(""));
    });

    var cardMd = get(D.cards, unit.card);
    if (cardMd) out.push("<h3>Card</h3>" + md(cardMd));
    var mitMd = get(D.mitigations, unit.mitigation);
    if (mitMd) out.push("<h3>Mitigation</h3>" + md(mitMd));

    var refs = unit.refs || topic.refs || {};
    var mappings = [];
    if ((unit.wstg || []).length) {
      mappings.push("<tr><th>WSTG</th><td>" + unit.wstg.map(function (w) {
        return '<a href="' + href("case", w) + '">' + esc(w) + "</a>";
      }).join(", ") + "</td></tr>");
    }
    if (refs.cwe) mappings.push("<tr><th>CWE</th><td>" + refs.cwe.map(function (c) {
      return "CWE-" + esc(c);
    }).join(", ") + "</td></tr>");
    if (refs.asvs) mappings.push("<tr><th>ASVS</th><td>" + refs.asvs.map(esc).join(", ") + "</td></tr>");
    if (mappings.length) out.push("<h3>Standards and weakness mappings</h3><table>" + mappings.join("") + "</table>");

    out.push(chainSection(uid, open));
    out.push(negativeSection(uid));
    return out.join("");
  };

  /* The expanded graph is a route rather than a toggle held in memory. It costs
     nothing, it survives a reload, and it is a link a tester can hand to
     somebody else -- which a piece of state in a closure is not. */
  var chainSection = function (uid, open) {
    var model = localGraph(D, uid, open ? 12 : LIMIT);
    var full = localGraph(D, uid, 9999);
    var out = ["<h3>Local attack chain</h3>"];
    out.push('<p class="muted">If this test succeeds, these are the paths that may become ' +
      "relevant. Every edge is a statement about tests, not about a target.</p>");
    out.push(graphSvg(model));
    out.push('<p class="legend"><b>Solid</b> a declared prerequisite · ' +
      "<b>Dashed</b> a motivation, never a gate · " +
      "capability nodes carry the reason each edge exists.</p>");

    var hidden = full.incoming.shown.length - model.incoming.shown.length +
      (full.outgoing.shown.length - model.outgoing.shown.length) +
      (full.yields.shown.length - model.yields.shown.length);
    if (hidden > 0) {
      out.push('<a class="more" href="' + href("unit", uid) + '/all">Show more · ' +
        hidden + " further relationship" + (hidden === 1 ? "" : "s") + "</a>");
    } else if (open) {
      out.push('<a class="more" href="' + href("unit", uid) + '">Show less</a>');
    }

    if (model.leaf) {
      out.push('<div class="card"><p class="muted">This test declares no capability of its ' +
        "own, so no continuation is derived from it. That is a gap in the chart, not a " +
        "claim that nothing follows.</p></div>");
    } else if (!full.outgoing.shown.length) {
      var why = model.terminal.filter(function (t) { return t.why === "impact"; });
      out.push('<div class="card"><p>' + (why.length
        ? "What this establishes is an impact: " +
          why.map(function (t) { return capTag(t.fact, "cap"); }).join("") +
          ". A chain ends there — nothing in the catalogue requires an impact, and " +
          "the outcome is reportable rather than a step to somewhere else."
        : "Nothing in the catalogue consumes what this establishes. The result is a " +
          "reportable outcome rather than a step to a further test.") + "</p></div>");
    }

    out.push(prerequisiteDetail(model));
    out.push(continuationDetail(model));
    return out.join("");
  };

  /* --------------------------- attack chains ---------------------------- */

  /* The whole model, at the only scale that reads.

     This was an arc diagram and the arcs were the problem: undirected, all one
     weight, the counts computed and never drawn, and a dozen curves crossing
     each other -- a smaller hairball is still a hairball. A matrix says the
     same thing without a single ambiguity. A row is what a test requires, a
     column is what it establishes, the number is how many tests span the two,
     and every cell is a way in.

     The families are an ontology, not the stages of an attack, so nothing here
     claims a chain runs left to right. What runs somewhere is a route, and a
     route is chosen rather than drawn over the whole catalogue at once. */
  var MAP_STATE = {
    impact: "where a chain is meant to end",
    routed: "a charted route from here reaches an outcome",
    short: "a test uses it, and nothing charted goes on to an outcome",
    unused: "nothing declares a use for it at all"
  };

  /* The catalogue at the scale a person can look at, as a picture.

     Columns rather than a node-link drawing on purpose: 185 capabilities and
     six hundred edges rendered at once is the hairball PIVOT.md already
     rejected once, and a smaller hairball is still a hairball. Columns of
     cells carry the same two things a reader wants -- what kind of thing each
     capability is, and how far the chart reaches from it -- and carry them
     without drawing a single line that would have to be believed. */
  var viewChainMap = function () {
    var columns = chainMap(D);
    var totals = { impact: 0, routed: 0, short: 0, unused: 0 };
    columns.forEach(function (col) {
      Object.keys(totals).forEach(function (k) { totals[k] += col.tally[k]; });
    });
    var facts = Object.keys(D.facts).length;

    var tally = function (col) {
      return ["routed", "short", "unused", "impact"].filter(function (k) {
        return col.tally[k];
      }).map(function (k) {
        return '<span class="t ' + k + '" title="' + col.tally[k] + " " +
          esc(MAP_STATE[k]) + '">' + col.tally[k] + "</span>";
      }).join("");
    };

    var grid = columns.map(function (col) {
      return '<div class="mcol"><div class="mhead"><a href="' +
        href("chains/family", col.name) + '">' + esc(col.label) + "</a>" +
        '<div class="mtally">' + tally(col) + "</div></div>" +
        col.cells.map(function (cell) {
          return '<a class="mcell ' + cell.state + '" href="' +
            href("capability", cell.fact) + '" title="' + esc(cell.fact) + " — " +
            esc(MAP_STATE[cell.state]) + " · " + cell.establishedBy +
            " establish · " + cell.requiredBy + ' consume">' +
            esc(factLabel(cell.fact)) + "</a>";
        }).join("") + "</div>";
    }).join("");

    var back = chainBackEdges(D);
    var backNote = back.length
      ? "Of the cross-family relationships the catalogue holds, " +
        back.reduce(function (t, e) { return t + e.units; }, 0) +
        " run against this order — " +
        back.map(function (e) {
          return e.units + " from " + esc(e.from) + " back to " + esc(e.to);
        }).join(", ") +
        ". They are printed rather than hidden: an order whose exceptions are " +
        "invisible is a claim rather than a measurement."
      : "";

    return "<h3>The chart, at the scale of the whole catalogue</h3>" +
      '<p class="lede">Every capability in the file, in the family that says what ' +
      "kind of thing it is, shaded by how far the chart reaches from it. Each one " +
      "opens on the tests that establish it and the tests that declare it a " +
      "condition — which is where a route is followed.</p>" +
      '<p class="muted">The columns are ordered by where this catalogue\'s own ' +
      "edges run, not by any claim about how an attack proceeds. " + backNote + "</p>" +
      /* The key is above the picture. Below it, a reader meets the colours
         first and the meaning after two thousand pixels of scrolling, by which
         point they have already decided what the shades meant. */
      '<div class="mlegend">' +
      ["routed", "short", "unused", "impact"].map(function (k) {
        return '<span class="mkey"><span class="mswatch ' + k + '"></span>' +
          totals[k] + " " + esc(MAP_STATE[k]) + "</span>";
      }).join("") +
      "</div>" +
      '<div class="mfilter"><input id="mapfilter" type="search" ' +
      'placeholder="Filter capabilities" aria-label="Filter capabilities">' +
      '<span id="mapcount" class="muted">' + facts + " capabilities</span></div>" +
      /* Not inside a scroller. `overflow-x: auto` computes overflow-y to auto
         as well, which makes the wrapper the nearest scrollport and leaves the
         column headings sticky to a box that never scrolls -- so they slid away
         at every width. The columns shrink instead: the map only overflowed
         below about 900px, which is a narrow screen where wrapped text reads
         better than a sideways scrollbar anyway. */
      '<div class="chainmap">' + grid + "</div>";
  };

  /* The tag grid. Every tag in the vocabulary, each a link to the selection it
     would produce, so selecting is navigation and there is no state held
     anywhere. A tag reaching no topic is shown as that rather than omitted: a
     vocabulary entry the catalogue never uses is a fact about the catalogue,
     and hiding it would leave the reader to conclude the tag does not exist. */
  var contextChips = function (chosen) {
    var on = {};
    chosen.forEach(function (t) { on[t] = true; });
    return '<div class="chips">' + (D.surfaces || []).map(function (s) {
      var reach = (s.topics || []).length;
      var next = own(on, s.tag)
        ? chosen.filter(function (t) { return t !== s.tag; })
        : chosen.concat([s.tag]);
      var target = next.length ? "#/chains/context/" + next.join("+") : "#/chains/context";
      var title = s.label + (s.hint ? " — " + s.hint : "");
      /* The href is escaped even though the schema constrains a tag to
         `[a-z0-9-]` and the validator refuses anything else. This is the one
         attribute here built by concatenation rather than from a fixed string,
         and a value reaching it that the schema was supposed to have stopped is
         exactly the case worth surviving. */
      return '<a class="chip' + (own(on, s.tag) ? " on" : "") +
        (reach ? "" : " none") + '" href="' + esc(target) +
        '" title="' + esc(title) + '">' + esc(s.tag) +
        '<span class="c">' + reach + "</span></a>";
    }).join("") + "</div>";
  };

  /* One topic in a context result: why it is here, and its tests in the order
     the topic declares. The reason line is the whole point -- a list of tests
     with no statement of what put them in front of the reader is a
     recommendation, and this file does not make recommendations. */
  var contextTopicCard = function (row) {
    var topic = get(D.topics, row.topic);
    if (!topic) return "";
    var byTag = {};
    (D.surfaces || []).forEach(function (s) { byTag[s.tag] = s; });
    var why = row.via.map(function (tag) {
      var s = byTag[tag];
      return '<span class="tag ctx" title="' + esc((s && s.hint) || tag) + '">' +
        esc((s && s.label) || tag) + "</span>";
    }).join("");

    var units = (topic.units || []).map(function (uid) {
      var unit = get(D.units, uid);
      if (!unit) return "";
      var cost = entryCost(D, uid);
      /* Both lists are shown. Printing only the second said "no earlier test
         declared" over a unit that requires `recon.entrypoints.mapped`, which
         one test in the catalogue establishes -- a claim that is simply false,
         and false on the 176 units the view is most likely to be read for.
         Kept as two lines rather than merged into one, because merging them is
         the other way to be useless: nearly every unit in the catalogue
         declares an engagement condition, so one combined list puts the same
         warning on all but eight of them and stops distinguishing anything. */
      var note = cost.engagement.length
        ? '<span class="need assumed">assumed held: ' +
          cost.engagement.map(function (f) { return capLabel(f, "eng"); }).join("") +
          "</span>"
        : "";
      note += cost.earned.length
        ? '<span class="need">a chain step establishes first: ' +
          cost.earned.map(function (f) { return capLabel(f, "req"); }).join("") + "</span>"
        : cost.engagement.length
          ? '<span class="need ok">no chain step has to precede it</span>'
          : '<span class="need ok">declares no prerequisite</span>';
      /* The requirement line sits in the left column with the title, not in
         the right one with the depth pill. The right column is a short status
         and does not wrap; a capability label put there overflows the row and
         lands outside the box it belongs to. */
      return '<a class="row" href="' + href("unit", uid) + '"><span class="who">' +
        '<span class="t">' + esc(unit.title) + "</span>" +
        '<span class="s">' + esc(uid) + " · " +
        esc(unit.role === "variant" ? "alternative technique" : "stage") + "</span>" +
        note + "</span><span class=\"n\">" + statusPill(unit) + "</span></a>";
    }).join("");

    return '<div class="card"><h4><a href="' + href("topic", row.topic) + '">' +
      esc(topic.title) + "</a></h4>" +
      '<div class="why">Matched because the context is: ' + why + "</div>" +
      '<div class="rows">' + units + "</div></div>";
  };

  var viewContext = function (raw) {
    var known = {};
    (D.surfaces || []).forEach(function (s) { known[s.tag] = true; });
    /* Unknown tags are dropped rather than reported as an error page. The
       selection arrives in a URL a reader may have edited or a colleague may
       have sent from a different version of this file, and the useful answer to
       a tag this build does not carry is the rest of the selection. */
    var chosen = String(raw || "").split("+").filter(function (t) {
      return t && own(known, t);
    });
    chosen = chosen.filter(function (t, i) { return chosen.indexOf(t) === i; }).sort();

    var result = contextTopics(D, chosen);
    var head = crumbs([
      { text: "Attack Chains", href: "#/chains" },
      { text: chosen.length ? "Context: " + chosen.join(", ") : "Choose a context" }
    ]) +
      "<h2>Tests by context</h2>" +
      '<p class="lede">Describe the kind of surface in front of you and this lists the ' +
      "tests that may apply to it, and what each one would have to establish first. " +
      "Every tag below names a <i>kind</i> of surface, never one you are looking at: " +
      "nothing you choose here is stored, sent, or kept after you close the page.</p>" +
      contextChips(chosen);

    if (!chosen.length) {
      return head +
        '<p class="empty">Nothing chosen yet. Pick one or more tags above — the number ' +
        "on each is how many topics in this catalogue declare it.</p>" +
        '<p class="muted">Choosing more than one narrows nothing and adds: a surface is ' +
        "usually several of these at once, and each tag brings its own tests. Some tags " +
        "imply others, so a search box already counts as a parameter reaching a query " +
        "and does not have to be said twice.</p>" +
        '<p class="muted">This is a reading of the catalogue, not of an application. It ' +
        "cannot tell you a test is applicable, reachable or worth doing here — only that " +
        "the catalogue files it under the kind of surface you described.</p>";
    }

    var strong = result.topics.filter(function (r) { return !r.implied; });
    var weak = result.topics.filter(function (r) { return r.implied; });
    var counted = function (rows) {
      var n = 0;
      rows.forEach(function (r) {
        var t = get(D.topics, r.topic);
        n += t ? (t.units || []).length : 0;
      });
      return n;
    };

    var implied = result.implied.length
      ? '<p class="muted">Also counted as chosen, because the tags above imply them: ' +
        result.implied.map(function (t) { return "<code>" + esc(t) + "</code>"; }).join(", ") +
        ". A tag implies another where the second is true of every surface carrying " +
        "the first.</p>"
      : "";

    var body = implied +
      "<h3>" + strong.length + " topic" + (strong.length === 1 ? "" : "s") +
      (strong.length === 1 ? " declares" : " declare") +
      " a tag you chose <span class=\"muted\">— " + counted(strong) +
      " tests</span></h3>";

    body += strong.length
      ? strong.map(contextTopicCard).join("")
      : '<p class="empty">No topic in this catalogue declares any of these tags.</p>';

    if (weak.length) {
      body += "<h3>" + weak.length + " more through an implied tag " +
        '<span class="muted">— ' + counted(weak) + " tests</span></h3>" +
        '<p class="muted">Reached one step further out: these declare a tag your ' +
        "selection implies rather than one you chose.</p>" +
        weak.map(contextTopicCard).join("");
    }

    body += "<details class=\"fold\"><summary>" + result.always.length +
      " topics that apply to every context <span class=\"muted\">— " +
      counted(result.always.map(function (t) { return { topic: t }; })) +
      " tests</span></summary>" +
      '<p class="muted">These declare no surface at all: they are the part of the ' +
      "methodology that does not depend on what you are looking at, and they would " +
      "appear under every tag. Folded away rather than repeated into each result.</p>" +
      '<div class="rows">' + result.always.map(function (tid) {
        var t = get(D.topics, tid);
        return t ? rowLink(href("topic", tid), t.title, tid,
          (t.units || []).length + " tests") : "";
      }).join("") + "</div></details>";

    body += '<h3>What this list is not</h3>' +
      '<p class="muted">A tag is carried by the topic, not by the individual test, so ' +
      "every test in a matched topic is listed even where the topic spans contexts a " +
      "single tag cannot separate. The two conditions under a test are read from the " +
      "capability vocabulary and are different things. <b>Assumed held</b> is a " +
      "general condition of the engagement — a session, a map of the entrypoints — " +
      "which a broad test may well establish, and which tells you nothing about " +
      "where to go next; <b>a chain step establishes first</b> is a capability " +
      "another test has to produce, and that is the chain. Neither is ever a claim " +
      "that you do or do not have it. Outcomes — what a chain is for — " +
      "carry no surface tag and are reached through the chain from a test here, not " +
      "from this page.</p>";

    return head + body;
  };

  var viewChains = function () {
    var reach = 0;
    (D.surfaces || []).forEach(function (s) { reach += (s.topics || []).length ? 1 : 0; });
    return crumbs([{ text: "Attack Chains" }]) +
      "<h2>Attack chains</h2>" +
      '<p class="lede">A route is a sequence of tests, each establishing something ' +
      "the next one declares it needs. Nothing here is a statement about a target: " +
      "the file has never seen one, and which of these applies today is yours to " +
      "decide.</p>" +
      '<div class="card"><h4><a href="#/chains/context">Start from what you are ' +
      "looking at</a></h4><p>Choose the kind of surface in front of you — " + reach +
      " of the " + (D.surfaces || []).length + " tags reach a topic — and read the " +
      "tests filed under it, each with what it would have to establish first. The " +
      "way in that needs neither a " + esc(D.standard.short) +
      " identifier nor a capability name.</p></div>" +
      viewChainMap() +
      "<h3>Where chains are meant to end</h3>" +
      '<p class="muted">Nothing in the catalogue requires an impact: it is where a ' +
      "chain stops on purpose, and the validator enforces that. Open one to see the " +
      "routes charted to it.</p>" +
      '<div class="rows">' + (D.impacts || []).map(function (f) {
        return rowLink(href("capability", f), factLabel(f), f,
          (get(D.producers, f) || []).length + " tests establish it");
      }).join("") + "</div>" +
      '<p class="muted">How many tests span each pair of families, and how much of ' +
      'the catalogue exists at what depth, are on <a href="#/status">catalogue ' +
      "status and model</a>.</p>";
  };

  /* One cell of the matrix: the tests that span two families, each with the
     capability it consumed and the one it established. The cell is a number
     until it is opened; opening it has to say what the number was counting. */
  var viewSpan = function (from, to) {
    var families = {};
    (D.families || []).forEach(function (f) { families[f.name] = f; });
    if (!own(families, from) || !own(families, to)) return notFound("family transition", from + " to " + to);

    var spanning = Object.keys(D.units || {}).sort().filter(function (uid) {
      var unit = D.units[uid];
      var requires = unit.requires || {};
      var needs = (requires.all_of || []).concat(requires.any_of || []);
      return needs.some(function (f) { return familyOf(f) === from; }) &&
        (unit.yields || []).some(function (f) { return familyOf(f) === to; });
    });

    /* A cell of the matrix, so the trail leads back to where the matrix is
       rather than to the page it used to be on. */
    return crumbs([
      { text: "Catalogue status and model", href: "#/status" },
      { text: families[from].label + " → " + families[to].label }
    ]) +
      "<h2>" + esc(families[from].label) + " → " + esc(families[to].label) + "</h2>" +
      '<p class="lede">' + spanning.length + " test" + (spanning.length === 1 ? "" : "s") +
      " require a capability in " + esc(families[from].label.toLowerCase()) +
      " and establish one in " + esc(families[to].label.toLowerCase()) + ".</p>" +
      spanning.map(function (uid) {
        var unit = D.units[uid];
        var requires = unit.requires || {};
        var consumed = (requires.all_of || []).concat(requires.any_of || [])
          .filter(function (f) { return familyOf(f) === from; });
        var made = (unit.yields || []).filter(function (f) { return familyOf(f) === to; });
        return '<div class="card"><h4><a href="' + href("unit", uid) + '">' +
          esc(unit.title) + "</a> " + statusPill(unit) + "</h4>" +
          '<div class="also"><b>Requires:</b> ' +
          consumed.map(function (f) { return capTag(f, "req"); }).join("") +
          " <b>Establishes:</b> " +
          made.map(function (f) { return capTag(f, "cap"); }).join("") + "</div>" +
          '<div class="meta">' + idChip(uid) + "</div></div>";
      }).join("");
  };

  var viewFamily = function (name) {
    var fam = (D.families || []).filter(function (f) { return f.name === name; })[0];
    if (!fam) return notFound("capability family", name);
    return crumbs([{ text: "Attack Chains", href: "#/chains" }, { text: fam.label }]) +
      "<h2>" + esc(fam.label) + "</h2>" +
      '<p class="lede">' + esc(fam.note) + "</p>" +
      '<div class="rows">' + fam.facts.map(function (f) {
        var producers = (get(D.producers, f) || []).length;
        var consumers = (get(D.requiredBy, f) || []).length;
        return rowLink(href("capability", f), factLabel(f), f,
          producers + " establish · " + consumers + " consume");
      }).join("") + "</div>";
  };

  var viewCapability = function (fid) {
    var fact = get(D.facts, fid);
    if (!fact) return notFound("capability", fid);
    var producers = get(D.producers, fid) || [];
    var consumers = get(D.requiredBy, fid) || [];
    var motivated = get(D.motivates, fid) || [];
    var family = (D.families || []).filter(function (f) { return f.name === familyOf(fid); })[0];

    var listing = function (label, ids, note) {
      if (!ids.length) return "";
      return "<h3>" + label + " · " + ids.length + "</h3>" +
        (note ? '<p class="muted">' + note + "</p>" : "") +
        '<div class="rows">' + ids.map(function (id) {
          var unit = get(D.units, id);
          if (!unit) return "";
          return rowLink(href("unit", id), unit.title, id,
            depthLabel(unit));
        }).join("") + "</div>";
    };

    var routes = pathsToImpact(D, fid, { maxPaths: 4, maxDepth: 5 });
    var pathHtml = routes.length
      ? "<h3>Routes to an impact</h3>" +
        '<p class="muted">Shortest first. Each step is a test that requires the capability ' +
        "above it and establishes the one below. A step may declare conditions the route " +
        "does not supply, and those are named: a route drawn as an unbroken line would " +
        "read as executable when one of its tests is not. Whether any of it applies to a " +
        "given target is not something this file can know.</p>" +
        routes.map(function (route, n) {
          var owed = route.steps.reduce(function (t, step) {
            return t + step.also.all_of.length + step.also.any_of.length;
          }, 0);
          return '<div class="card"><span class="k">Route ' + (n + 1) + " · " +
            route.steps.length + " step" + (route.steps.length === 1 ? "" : "s") +
            (owed
              ? " · " + owed + " unmet condition" + (owed === 1 ? "" : "s") + " along the way"
              : " · nothing further declared") +
            "</span>" +
            '<div class="route"><div class="rstep start">' + capTag(route.start, "req") + "</div>" +
            route.steps.map(function (step) {
              var still = step.also.all_of.map(function (f) { return capTag(f, "req"); }).join("") +
                (step.also.any_of.length
                  ? '<span class="muted">any one of </span>' +
                    step.also.any_of.map(function (f) { return capTag(f, "req"); }).join("")
                  : "");
              return '<div class="rstep unit"><a href="' + href("unit", step.unit) + '">' +
                esc(unitTitle(step.unit)) + "</a>" +
                (still
                  ? '<div class="also"><b>Still required here:</b> ' + still + "</div>"
                  : '<div class="also muted">No additional declared hard prerequisite.</div>') +
                '</div><div class="rstep">' + capTag(step.to, "cap") + "</div>";
            }).join("") + "</div></div>";
        }).join("")
      : (familyOf(fid) === "impact"
          ? '<p class="muted">This is an impact. A chain ends here.</p>'
          : '<p class="muted">No route from here to an impact is charted within five steps.</p>');

    return crumbs([
      { text: "Attack Chains", href: "#/chains" },
      { text: family ? family.label : familyOf(fid), href: href("chains/family", familyOf(fid)) },
      { text: fact.label }
    ]) +
      "<h2>" + esc(fact.label) + "</h2>" +
      '<div class="sub">' + idChip(fid) +
      (fact.given ? " · given — a root of the graph" : "") +
      (fact.granted ? " · the engagement may supply it" : "") + "</div>" +
      "<p>" + esc(fact.description) + "</p>" +
      listing("Established by", producers,
        producers.length > 1
          ? "More than one route establishes this, so a negative result on any single one " +
            "does not settle it."
          : "") +
      listing("Required by", consumers,
        "These tests declare it a condition of being possible at all.") +
      listing("Motivated by", motivated,
        "Already possible without it; this makes them worth doing sooner. Never a gate.") +
      pathHtml;
  };

  /* Payload files and tools have their own pages because search already
     offered them and the router had nowhere to send either -- a result that
     silently landed on Standards, for two of the content types the search page
     advertises. Linking to a unit instead would be wrong as often as not: a
     payload file is shared by several units, and a tool by nine. */
  var usedBy = function (test) {
    return Object.keys(D.units || {}).sort().filter(function (uid) {
      return test(D.units[uid]);
    });
  };

  var viewPayloads = function (pid) {
    var pack = get(D.payloads, pid);
    if (!pack) return notFound("payload file", pid);
    var rel = "payloads/" + pid + ".yaml";
    var users = usedBy(function (u) { return u.payloads === rel; });
    return crumbs([{ text: "Search", href: "#/search" }, { text: pack.title }]) +
      "<h2>" + esc(pack.title) + "</h2>" +
      '<div class="sub">' + idChip(rel) + " · reviewed " + esc(pack.reviewed) + "</div>" +
      (pack.safety ? '<div class="notice">' + esc(pack.safety) + "</div>" : "") +
      '<div class="scroller"><table><tr><th>Name</th><th>Payload</th><th>Detect</th></tr>' +
      (pack.entries || []).map(function (e) {
        return "<tr><td>" + esc(e.name) + "</td><td><code>" + esc(e.payload) + "</code></td><td>" +
          esc(e.detect || "") +
          (e.note ? '<br><span class="muted">' + esc(e.note) + "</span>" : "") + "</td></tr>";
      }).join("") + "</table></div>" +
      "<h3>Tests that use this file · " + users.length + "</h3>" +
      (users.length
        ? '<div class="rows">' + users.map(function (uid) {
            return rowLink(href("unit", uid), D.units[uid].title, uid,
              depthLabel(D.units[uid]));
          }).join("") + "</div>"
        : '<p class="empty">No test names this file.</p>');
  };

  var viewTool = function (id) {
    var tool = get(D.toolbox, id);
    if (!tool) return notFound("tool", id);
    var users = usedBy(function (u) { return (u.tools || []).indexOf(id) >= 0; });
    return crumbs([{ text: "Search", href: "#/search" }, { text: tool.name }]) +
      "<h2>" + esc(tool.name) + "</h2>" +
      '<div class="sub">' + idChip(id) + "</div>" +
      "<p>" + esc(tool.purpose) + "</p>" +
      (tool.invocations || []).map(function (v) {
        return '<div class="card"><span class="k">' + esc(v.purpose) + "</span><pre><code>" +
          esc(v.cmd) + "</code></pre>" +
          (v.flags
            ? '<div class="scroller"><table><tr><th>Flag</th><th>Why</th></tr>' +
              Object.keys(v.flags).map(function (f) {
                return "<tr><td><code>" + esc(f) + "</code></td><td>" + esc(v.flags[f]) + "</td></tr>";
              }).join("") + "</table></div>"
            : "") + "</div>";
      }).join("") +
      "<h3>Tests that name this tool · " + users.length + "</h3>" +
      (users.length
        ? '<div class="rows">' + users.map(function (uid) {
            return rowLink(href("unit", uid), D.units[uid].title, uid,
              depthLabel(D.units[uid]));
          }).join("") + "</div>"
        : '<p class="empty">No test names this tool.</p>');
  };

  /* ------------------------------ the rest ------------------------------ */

  var viewSearch = function (term) {
    var head = crumbs([{ text: "Search" }]) + "<h2>Search</h2>";
    if (!term) {
      return head + '<p class="lede">Everything the file carries is searchable: test cases, ' +
        "tests, topics, capabilities, payloads, cards, mitigations and tools. Search is " +
        "for retrieval — the tests inside a WSTG test case are reached by navigating to " +
        "it, not by finding them here.</p>";
    }
    var groups = searchAll(D, term);
    if (!groups.length) {
      return head + '<p class="empty">Nothing carries "' + esc(term) + '".</p>';
    }
    return head + '<div class="sub">' + esc(term) + "</div>" + groups.map(function (group) {
      return "<h3>" + esc(group.kind) + " · " + group.items.length + "</h3>" +
        group.items.slice(0, 40).map(function (item) {
          var body = "<h4>" + esc(item.title) + "</h4>" +
            (item.note ? '<p class="muted">' + esc(item.note) + "</p>" : "") +
            (item.code ? "<p><code>" + esc(item.code) + "</code></p>" : "") +
            '<div class="meta">' + idChip(item.sub) + "</div>";
          return item.href
            ? '<a class="card" href="' + item.href + '">' + body + "</a>"
            : '<div class="card">' + body + "</div>";
        }).join("") +
        (group.items.length > 40
          ? '<p class="muted">' + (group.items.length - 40) + " more not shown.</p>"
          : "");
    }).join("");
  };

  /* The whole model, at the only scale that reads, and a statement about the
     catalogue rather than about any target -- which is why it sits here and not
     under a page named for routes.

     This was an arc diagram and the arcs were the problem: undirected, all one
     weight, the counts computed and never drawn, and a dozen curves crossing
     each other. A matrix says the same thing without a single ambiguity.

     What it did not say was which axis was which. The legend below carried it,
     and a legend below a table is read after the table has already been
     misread, so both axes now name themselves in the table and every cell
     spells out the sentence it stands for. */
  var familyMatrix = function () {
    var model = familyOverview(D);
    var present = {};
    model.nodes.forEach(function (n) { present[n.name] = true; });
    // Ordered like the map rather than like the vocabulary file. Two views of
    // the same seven families in two different orders is two things to learn,
    // and in this order the matrix says something extra for free: almost every
    // number sits above the diagonal, which is the model running one way.
    var names = CHAIN_ORDER.filter(function (n) { return present[n]; })
      .concat(model.nodes.map(function (n) { return n.name; })
        .filter(function (n) { return CHAIN_ORDER.indexOf(n) < 0; }));
    var byName = {};
    model.nodes.forEach(function (n) { byName[n.name] = n; });
    var count = {};
    model.edges.forEach(function (e) { count[e.from + ">" + e.to] = e.units; });
    var busiest = model.edges.reduce(function (m, e) { return Math.max(m, e.units); }, 0);

    var axis = '<tr><td class="corner"></td>' +
      '<th class="axis" colspan="' + names.length + '">establishes →</th></tr>';
    var header = '<tr><th class="corner">requires ↓</th>' + names.map(function (n) {
      return '<th class="rot"><a href="' + href("chains/family", n) + '">' +
        esc(byName[n].label) + "</a></th>";
    }).join("") + "</tr>";

    var rows = names.map(function (from) {
      return '<tr><th class="rowhead"><a href="' + href("chains/family", from) + '">' +
        esc(byName[from].label) + "</a></th>" +
        names.map(function (to) {
          var n = count[from + ">" + to] || 0;
          var says = n + " test" + (n === 1 ? "" : "s") + " require " +
            byName[from].label.toLowerCase() + " and establish " +
            byName[to].label.toLowerCase();
          if (!n) {
            return '<td class="cell zero" title="' + esc("No test requires " +
              byName[from].label.toLowerCase() + " and establishes " +
              byName[to].label.toLowerCase()) + '">·</td>';
          }
          // Shaded by share of the busiest transition, so the shape of the
          // model is legible before a single number is read.
          var weight = Math.min(4, 1 + Math.floor((n / busiest) * 4));
          return '<td class="cell w' + weight + '" title="' + esc(says) + '"><a href="' +
            href("chains/span", from) + "/" + encodeURIComponent(to) + '">' + n + "</a></td>";
        }).join("") + "</tr>";
    }).join("");

    return "<h3>How the model connects</h3>" +
      '<p class="lede">Seven families of capability, and how many tests require one ' +
      "in the row and establish one in the column. The families classify what a " +
      "capability <em>is</em>; they are not the stages of an attack, and a route " +
      "through them is something you choose rather than something this table draws." +
      "</p>" +
      '<div class="scroller"><table class="matrix">' + axis + header + rows + "</table></div>" +
      '<p class="legend">Follow a number to the tests that span the two. ' +
      "<b>·</b> means no test does. Each cell says its own sentence when pointed at. " +
      "The families are in the order the chain map uses, which is why nearly every " +
      "number sits above the diagonal: that is the model running one way, measured " +
      "rather than asserted.</p>" +
      "<h4>Drill in</h4>" +
      // In the order the table above uses. A list of the same seven families
      // in a different order on the same page is a reader wondering which of
      // the two orders means something.
      '<div class="rows">' + names.map(function (name) {
        var n = byName[name];
        return rowLink(href("chains/family", n.name), n.label, n.note,
          n.facts + " capabilities");
      }).join("") + "</div>";
  };

  var viewStatus = function () {
    var c = D.counts;
    var reach = D.reach || {continuation: 0, impact: 0, short: 0, uncharted: 0};
    var total = reach.continuation + reach.impact + reach.short + reach.uncharted;
    var domains = {};
    Object.keys(D.topics).forEach(function (tid) {
      var d = D.topics[tid].domain;
      domains[d] = (domains[d] || 0) + 1;
    });
    return crumbs([{ text: "About", href: "#/about" },
                   { text: "Catalogue status and model" }]) +
      "<h2>Catalogue status and model</h2>" +
      '<p class="lede">How much of the catalogue exists, at what depth, how far the ' +
      "chain runs from it, and how the seven families of capability connect. Every " +
      "figure is a statement about Harrier, not about anybody's coverage of a " +
      "target.</p>" +
      "<table>" +
      "<tr><th>WSTG test cases pinned</th><td>" + c.wstg_pinned + "</td></tr>" +
      "<tr><th>Claimed by a topic</th><td>" + c.wstg_covered + " of " + c.wstg_coverable + " resolvable</td></tr>" +
      "<tr><th>Topics</th><td>" + c.topics + " across " + Object.keys(domains).length + " domains</td></tr>" +
      "<tr><th>Tests</th><td>" + c.units + "</td></tr>" +
      "<tr><th>Written to full depth</th><td>" + c.units_authored + "</td></tr>" +
      "<tr><th>Sketched</th><td>" + c.units_sketched +
      ' <span class="muted">— the procedure and what refutes it, without the record-keeping</span></td></tr>' +
      // Reported rather than left as the remainder. It is the tier most of the
      // catalogue sits at, and naming the other two while leaving the largest
      // to be worked out is the half-honest figure this table exists to avoid.
      "<tr><th>Outline only</th><td>" + (c.units - c.units_authored - c.units_sketched) +
      ' <span class="muted">— an identifier, an objective and a place in the chain</span></td></tr>' +
      "<tr><th>Placed in the chain</th><td>" + c.units_charted + "</td></tr>" +
      "<tr><th>Capabilities</th><td>" + Object.keys(D.facts).length + "</td></tr>" +
      "</table>" +
      '<p class="muted">A test that exists as an outline already appears here, already ' +
      "counts, and already stops a test being skipped silently. Depth is written on " +
      "demand and never speculatively.</p>" +
      "<h3>How far the chain runs</h3>" +
      '<p class="lede">Every test is in exactly one of these four, and the four sum to ' +
      "the catalogue. Reported rather than left to be inferred one page at a time.</p>" +
      "<table>" +
      "<tr><th>Has a potential continuation</th><td>" + reach.continuation + "</td></tr>" +
      "<tr><th>Establishes an impact</th><td>" + reach.impact +
      ' <span class="muted">— where a chain is meant to end</span></td></tr>' +
      "<tr><th>Stops short</th><td>" + reach.short +
      ' <span class="muted">— establishes something no test uses</span></td></tr>' +
      "<tr><th>Declares no capability</th><td>" + reach.uncharted +
      ' <span class="muted">— nothing is derived from it either way</span></td></tr>' +
      "<tr><th>Total</th><td>" + total + "</td></tr>" +
      "</table>" +
      "<table>" +
      "<tr><th>Capabilities that are impacts</th><td>" + (D.impacts || []).length + "</td></tr>" +
      "<tr><th>Capabilities no test uses</th><td>" + (D.deadEnds || []).length +
      ' <span class="muted">— impacts excluded</span></td></tr>' +
      "</table>" +
      /* Written from the figures beside it rather than from a phase that has
         since been done: primitive to impact is charted now, and a page still
         saying otherwise would be describing the version before last. */
      '<p class="muted">Reconnaissance through to a primitive is charted, and so is ' +
      "primitive to an outcome. What a defeated control permits is not: that is " +
      "where most of the unused capabilities are, and it is a gap in the chart " +
      'rather than a claim that nothing follows. The <a href="#/chains">chain ' +
      "map</a> shows where it thins out.</p>" +
      familyMatrix();
  };

  var viewAbout = function () {
    /* Every number here is read from the catalogue at render time. A figure
       maintained separately from the data it describes is a figure that is
       wrong somewhere, and this file is the copy a reader has offline. */
    var reach = D.reach || {continuation: 0, impact: 0, short: 0, uncharted: 0};
    var units = Object.keys(D.units).length;
    var authored = Object.keys(D.units).filter(function (id) {
      return depthOf(D.units[id]) === "authored";
    }).length;
    var sketched = Object.keys(D.units).filter(function (id) {
      return depthOf(D.units[id]) === "sketched";
    }).length;

    return crumbs([{ text: "About" }]) +
      "<h2>About Harrier</h2>" +
      '<p class="lede">An offline execution companion for web application security ' +
      "testing standards. It breaks broad standard test cases into atomic, separately " +
      "addressable tests, and derives the attack-chain continuations each success may " +
      "open.</p>" +
      '<div class="card"><p><b>' + esc(D.standard.short) + " tells you what to cover. " +
      "Harrier shows you the real tests inside each test case, and where a successful " +
      "one may lead.</b></p></div>" +

      '<div class="notice">Version ' + esc(D.version) + " is an early public alpha. " +
      "The decomposition is broad — " + units + " tests across " +
      Object.keys(D.topics).length + " topics — and the depth behind it is not: " +
      authored + " are written to full procedural depth, " + sketched + " are sketched, " +
      "and what a defeated control permits is largely unwritten. " +
      '<a href="#/status">Catalogue status and model</a> has the figures.</div>' +

      "<h3>How to use it</h3>" +
      "<ol><li>Choose the standard, then the testing group you are working in.</li>" +
      "<li>Choose the test case.</li>" +
      "<li>Read the tests it decomposes into, and open one.</li>" +
      "<li>Perform it from the objective, oracle, sequence and safety boundary.</li>" +
      "<li>Read the chain to see which tests a success may make relevant.</li></ol>" +

      "<h3>Tests and capabilities</h3>" +
      "<p>A <b>test</b> is the atomic thing you perform and record one result for. It " +
      "carries an objective that can be wrong and a boundary against its siblings; where " +
      "it is written in full it also carries an oracle, a sequence, payloads, false " +
      "positives and a limit on how far to take it. A test marked <b>outline</b> has the " +
      "identifier, the objective, the boundary and its place in the chain, and no " +
      "procedure; one marked <b>sketched</b> has the procedure and what refutes it, " +
      "without the record-keeping and the safety limit. Each page says which it is " +
      "rather than inventing the rest.</p>" +
      "<p>A <b>capability</b> is what a success establishes, or what a test needs before " +
      "it is possible at all. Capabilities are the join keys: no test ever names another " +
      "test. A <b>declared prerequisite</b> is a condition of performing the test; a " +
      "<b>motivation</b> makes it worth reaching for sooner and is never a gate. An " +
      "<b>impact</b> is terminal — nothing may require one.</p>" +

      "<h3>What this file does not know</h3>" +
      "<p>It has never seen the application you are testing and does not ask about it. " +
      "Every chain statement " +
      "is about the relationship between two tests — <i>potential continuation</i>, " +
      "<i>may become relevant</i>, <i>no additional declared hard prerequisite</i> — and " +
      "never a claim that something is true of an application. A continuation always " +
      "names what succeeding here does not supply, because being reached through one " +
      "capability is not the same as being possible.</p>" +
      "<p>Not a scanner, an exploit framework, a reporting platform, an engagement " +
      "tracker, or a target-aware recommendation engine. It holds no target, no " +
      "engagement, no results and no findings, and stores nothing in this browser. " +
      "Deciding which of this applies today is yours, and that is where the knowledge " +
      "is.</p>" +

      "<h3>Offline by design</h3>" +
      "<p>One self-contained file. It fetches no stylesheet, script, font or image and " +
      "makes no network request of any kind. It is opened from disk on an engagement " +
      "network, where a request to a third party would tell that party which target is " +
      "being tested and when.</p>" +

      "<h3>Standards</h3>" +
      "<p>" + esc(D.standard.name) + " is the execution-navigation standard, pinned at " +
      "<code>" + esc(D.standard.commit.slice(0, 12)) + "</code> and retrieved " +
      esc(D.standard.retrieved) + ". ASVS is referenced as a control and remediation " +
      "mapping, CWE as a weakness classification. Identifiers, official test titles and " +
      "group headings are cross-referenced; no prose from any of them is reproduced " +
      "here.</p>" +
      "<p>Harrier is not affiliated with, endorsed by, or sponsored by OWASP.</p>" +
      '<p class="muted">Version ' + esc(D.version) + " · " +
      '<a href="#/status">Catalogue status and model</a></p>';
  };

  var notFound = function (kind, id) {
    return crumbs([{ text: "Standards", href: "#/standards" }]) +
      "<h2>Not here</h2>" +
      '<p class="empty">This file carries no ' + esc(kind) + " called " + esc(id) + ".</p>";
  };

  /* ------------------------------ routing ------------------------------- */

  var route = function () {
    var raw = (location.hash || "").replace(/^#\/?/, "");
    var parts = raw.split("/").map(decodeURIComponent);
    var head = parts[0] || "standards";
    var arg = parts[1] || "";

    if (head === "standards") return { nav: "standards", html: viewStandards() };
    if (head === "wstg") {
      return arg
        ? { nav: "standards", html: viewGroup(arg) }
        : { nav: "standards", html: viewStandard() };
    }
    if (head === "case") return { nav: "standards", html: viewCase(arg) };
    if (head === "topic") return { nav: "standards", html: viewTopic(arg) };
    if (head === "unit") {
      return { nav: "standards", html: viewUnit(arg, parts[2] === "all") };
    }
    if (head === "extensions") return { nav: "standards", html: viewExtensions() };
    if (head === "chains") {
      if (arg === "context") return { nav: "chains", html: viewContext(parts[2] || "") };
      if (arg === "family") return { nav: "chains", html: viewFamily(parts[2] || "") };
      if (arg === "span") {
        return { nav: "chains", html: viewSpan(parts[2] || "", parts[3] || "") };
      }
      return { nav: "chains", html: viewChains() };
    }
    if (head === "capability") return { nav: "chains", html: viewCapability(arg) };
    if (head === "payloads") return { nav: "search", html: viewPayloads(arg) };
    if (head === "tools") return { nav: "search", html: viewTool(arg) };
    if (head === "search") return { nav: "search", html: viewSearch(arg) };
    if (head === "about") return { nav: "about", html: viewAbout() };
    if (head === "status") return { nav: "about", html: viewStatus() };
    return { nav: "standards", html: viewStandards() };
  };

  /* How far down the site header reaches, published to the stylesheet so a
     sticky heading inside the page can stop underneath it rather than behind
     it. Measured because the header wraps at narrow widths and is a different
     height in each regime.

     Observed rather than measured at two moments chosen by hand. The first
     version read the height on every draw and on every resize, which is two
     guesses at when layout has settled: under load the suite caught it holding
     the one-row height while a two-row header was on screen, and a heading
     stuck forty pixels too high is a heading behind the bar it exists to clear.
     A resize observer is the browser saying the size changed, after it has
     changed, for whatever reason it changed -- including the ones nobody
     enumerated. It also fires once on observe, so the initial value needs no
     separate call. */
  var siteHeader = document.querySelector("header");
  var measureHeader = function () {
    if (!siteHeader) return;
    document.documentElement.style.setProperty(
      "--stick", Math.round(siteHeader.getBoundingClientRect().height) + "px"
    );
  };
  if (siteHeader && typeof ResizeObserver === "function") {
    new ResizeObserver(measureHeader).observe(siteHeader);
  } else {
    // Older browser: back to the two hand-placed measurements. Worse, and
    // better than a sticky heading with no offset at all.
    window.addEventListener("resize", measureHeader);
    measureHeader();
  }

  var draw = function () {
    var page = route();
    main.innerHTML = page.html;
    Array.prototype.forEach.call(document.querySelectorAll("nav a"), function (a) {
      a.classList.toggle("on", a.dataset.nav === page.nav);
    });
    var title = main.querySelector("h2");
    document.title = "Harrier " + D.version + (title ? " · " + title.textContent : "");
    window.scrollTo(0, 0);
  };

  var follow = function (target) {
    var node = target && target.closest ? target.closest("[data-go]") : null;
    if (!node) return false;
    location.hash = node.dataset.go;
    return true;
  };

  document.addEventListener("click", function (e) { follow(e.target); });

  /* A graph node is a link. Enter and Space have to reach it, or it is a link
     only a mouse can use. */
  document.addEventListener("keydown", function (e) {
    if (e.key !== "Enter" && e.key !== " " && e.key !== "Spacebar") return;
    if (follow(e.target)) e.preventDefault();
  });

  /* Delegated rather than attached after each draw: the page is re-rendered
     wholesale on every hash change, and a listener bound to an element that no
     longer exists is a filter that silently stops filtering. */
  document.addEventListener("input", function (e) {
    if (!e.target || e.target.id !== "mapfilter") return;
    var term = String(e.target.value || "").trim().toLowerCase();
    var cells = document.querySelectorAll(".chainmap .mcell");
    var shown = 0;
    Array.prototype.forEach.call(cells, function (cell) {
      var hit = !term ||
        cell.textContent.toLowerCase().indexOf(term) >= 0 ||
        String(cell.getAttribute("title") || "").toLowerCase().indexOf(term) >= 0;
      cell.classList.toggle("off", !hit);
      if (hit) shown += 1;
    });
    var count = document.getElementById("mapcount");
    if (count) {
      count.textContent = term
        ? shown + " of " + cells.length + " capabilities"
        : cells.length + " capabilities";
    }
  });

  var box = document.getElementById("q");
  box.addEventListener("input", function () {
    var value = box.value.trim();
    location.hash = value.length >= 2 ? "#/search/" + encodeURIComponent(value) : "#/search";
  });

  window.addEventListener("hashchange", draw);
  if (!location.hash) location.hash = "#/standards";
  draw();
})();
