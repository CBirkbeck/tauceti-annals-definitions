#!/usr/bin/env python3
"""Render docs/index.html from data/definitions.json.

Standard library only. Run from anywhere:

    python3 build.py

The page is one self-contained file: inline CSS and JavaScript, no external
fonts, scripts or style sheets. The only external URLs in it are the GitHub
links in the content.
"""
import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "definitions.json")
OUT = os.path.join(HERE, "docs", "index.html")

ROADMAP_REPO = "https://github.com/TauCetiProject/TauCetiRoadmap"

STATUS_ORDER = ["library", "main", "pr", "planned", "none"]
STATUS_LABEL = {
    "library": "In the library or Mathlib",
    "main": "On main",
    "pr": "Open pull request",
    "planned": "Planned",
    "none": "Not yet planned",
}
STATUS_HELP = {
    "library": "already formalised in Tau Ceti or in Mathlib",
    "main": "specified in a roadmap that is on the main branch",
    "pr": "specified in a roadmap that is in an open pull request",
    "planned": "planned on the job board, with no roadmap text yet",
    "none": "no roadmap specifies it",
}
ROADMAP_STATE_LABEL = {
    "main": "On main",
    "pr": "Open pull request",
    "planned": "Planned, not yet written",
}
ROLE_LABEL = {"defines": "Defines", "uses": "Uses", "related": "Related"}


def esc(text):
    return html.escape(str(text), quote=True)


def fmt(text):
    """Escape, then turn _{..} and ^{..} into subscripts and superscripts."""
    out = esc(text)
    out = re.sub(r"\^\{([^{}]*)\}", r"<sup>\1</sup>", out)
    out = re.sub(r"_\{([^{}]*)\}", r"<sub>\1</sub>", out)
    return out


def plain(text):
    """The same text without the sub/superscript markers, for search and titles."""
    return re.sub(r"[_^]\{([^{}]*)\}", r"\1", str(text))


def pr_url(number):
    return "%s/pull/%d" % (ROADMAP_REPO, int(number))


def roadmap_url(rm):
    """Links are stored in the data (refresh.py keeps them up to date)."""
    return rm.get("url") or None


def anchor(folder):
    return "r-" + re.sub(r"[^A-Za-z0-9]+", "-", folder)


def entry_state(entry, rm):
    """State of one entry: an entry can sit in an open pull request that amends a roadmap on main."""
    if entry.get("pr"):
        return "pr", int(entry["pr"])
    if rm["state"] == "pr":
        return "pr", int(rm["pr"])
    return rm["state"], None


def read_date(iso):
    stamp = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ")
    return "%d %s %d, %02d:%02d UTC" % (
        stamp.day, stamp.strftime("%B"), stamp.year, stamp.hour, stamp.minute)


def validate(data):
    problems = []
    defs = data["definitions"]
    numbers = [d["n"] for d in defs]
    if sorted(numbers) != list(range(1, 101)):
        problems.append("definitions are not exactly 1..100")
    for d in defs:
        if d.get("status") not in STATUS_LABEL:
            problems.append("definition %s: bad status %r" % (d.get("n"), d.get("status")))
        if d.get("area") not in data["areas"]:
            problems.append("definition %s: unknown area" % d.get("n"))
        for e in d.get("entries", []):
            if e["roadmap"] not in data["roadmaps"]:
                problems.append("definition %s: unknown roadmap %s" % (d["n"], e["roadmap"]))
            if e.get("role") not in ROLE_LABEL:
                problems.append("definition %s: bad role" % d["n"])
    for key, rm in data["roadmaps"].items():
        if rm.get("state") not in ROADMAP_STATE_LABEL:
            problems.append("roadmap %s: bad state" % key)
        if rm.get("state") == "pr" and not rm.get("pr"):
            problems.append("roadmap %s: open pull request without a number" % key)
    if problems:
        sys.exit("data/definitions.json is not consistent:\n  " + "\n  ".join(problems))


CSS = """
:root{color-scheme:light dark;
--bg:#ffffff;--fg:#1b1d21;--muted:#5b616a;--line:#d8dce2;--soft:#f4f5f7;--link:#0b55c4;
--main-bg:#e2f3e6;--main-fg:#17502b;--pr-bg:#e3ecfb;--pr-fg:#143f8a;
--planned-bg:#f1e7fc;--planned-fg:#59218c;--library-bg:#dcf3f1;--library-fg:#0c4c47;
--none-bg:#ebedf0;--none-fg:#3c424a;}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--fg);
font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif}
.wrap{max-width:62rem;margin:0 auto;padding:0 1rem}
a{color:var(--link);text-decoration-thickness:.06em;text-underline-offset:.15em}
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--link);outline-offset:2px}
h1{font-size:1.5rem;line-height:1.25;margin:1.5rem 0 .5rem}
h2{font-size:1.2rem;margin:1.75rem 0 .25rem}
h3{font-size:1.02rem;margin:1.6rem 0 .2rem;padding-bottom:.3rem;border-bottom:2px solid var(--line)}
h4{font-size:1rem;margin:0;font-weight:600}
p{margin:.35rem 0}
p,li,h4{overflow-wrap:break-word}
sub,sup{font-size:.72em;line-height:0}
.lede{max-width:48rem}
.meta,.hint,.count{color:var(--muted);font-size:.9rem}
.counts{list-style:none;display:flex;flex-wrap:wrap;gap:.4rem;padding:0;margin:.7rem 0 .5rem}
.counts button{font:inherit;font-size:.9rem;cursor:pointer;border:1px solid transparent;border-radius:.3rem;padding:.2rem .55rem}
.counts button b{font-variant-numeric:tabular-nums}
.counts button[aria-pressed="true"]{border-color:currentColor}
.s-main{background:var(--main-bg);color:var(--main-fg)}
.s-pr{background:var(--pr-bg);color:var(--pr-fg)}
.s-planned{background:var(--planned-bg);color:var(--planned-fg)}
.s-library{background:var(--library-bg);color:var(--library-fg)}
.s-none{background:var(--none-bg);color:var(--none-fg)}
.controls{display:none;background:var(--bg);border-bottom:1px solid var(--line);padding:.6rem 0;margin-top:1rem}
.js .controls{display:block}
.controls .row{display:flex;flex-wrap:wrap;gap:.5rem;align-items:center}
.controls input,.controls select{font:inherit;font-size:.95rem;color:var(--fg);background:var(--bg);
border:1px solid var(--line);border-radius:.3rem;padding:.35rem .5rem;min-width:0}
.controls input{flex:1 1 14rem}
.controls select{flex:0 1 auto;max-width:100%}
.tabs{display:none;gap:0;margin-right:.25rem}
.js .tabs{display:inline-flex}
.tabs button{font:inherit;font-size:.95rem;cursor:pointer;color:var(--fg);background:var(--bg);
border:1px solid var(--line);padding:.35rem .7rem}
.tabs button:first-child{border-radius:.3rem 0 0 .3rem}
.tabs button:last-child{border-radius:0 .3rem .3rem 0;border-left:0}
.tabs button[aria-pressed="true"]{background:var(--fg);color:var(--bg);border-color:var(--fg)}
.count{margin:.4rem 0 0}
.controls label{position:absolute;left:-999rem}
.js main.v-def #by-roadmap,.js main.v-rm #by-definition{display:none}
.def,.rm{padding:.8rem 0;border-bottom:1px solid var(--line);scroll-margin-top:6.5rem}
.def[hidden],.rm[hidden],.area[hidden]{display:none}
.def>header,.rm>header{display:flex;flex-wrap:wrap;align-items:baseline;gap:.2rem .6rem}
.num{font-variant-numeric:tabular-nums;color:var(--muted);min-width:1.8rem}
.def>header h4,.rm>header h4{flex:1 1 16rem}
.badge{font-size:.8rem;border-radius:.3rem;padding:.05rem .45rem;white-space:nowrap}
.def .body{margin-left:2.4rem}
.what{margin-top:.25rem}
.first,.caveat,.lib,.plan{font-size:.94rem}
.lab{font-weight:600}
ul.entries{list-style:none;margin:.45rem 0 .3rem;padding:0;border-left:3px solid var(--line)}
ul.entries li{padding:.22rem 0 .22rem .7rem;font-size:.94rem}
.role{display:inline-block;font-size:.78rem;font-weight:600;letter-spacing:.02em;text-transform:uppercase;
border:1px solid var(--line);border-radius:.25rem;padding:0 .35rem;margin-right:.25rem;color:var(--muted)}
.role.defines{color:var(--fg);border-color:var(--fg)}
.role.related{border-style:dashed}
.rname{font-weight:600;overflow-wrap:anywhere}
.where{display:block;color:var(--fg)}
.note{display:block;color:var(--muted)}
.small{font-size:.86rem;color:var(--muted)}
.rm .title{font-style:italic}
.covers{font-size:.94rem;margin-top:.35rem}
.covers ul{margin:.2rem 0 0;padding-left:1.1rem}
.empty{display:none;color:var(--muted);padding:1rem 0}
footer{color:var(--muted);font-size:.88rem;padding:1.5rem 0 3rem}
"""

# Extra style sheets, each with a media condition. They are written as separate
# <style media="..."> elements so that the page needs no at-rules.
CSS_MEDIA = [
    ("(prefers-color-scheme: dark)", """
:root{--bg:#15171b;--fg:#e5e7ea;--muted:#a3aab4;--line:#353a42;--soft:#1d2026;--link:#8fb6f9;
--main-bg:#14361f;--main-fg:#a9e4b7;--pr-bg:#172d53;--pr-fg:#adc9fa;
--planned-bg:#35214f;--planned-fg:#dbbcf8;--library-bg:#103b38;--library-fg:#a2e4dd;
--none-bg:#2b2f36;--none-fg:#c5cad2;}
"""),
    ("(min-width: 44rem) and (min-height: 34rem)", """
.controls{position:sticky;top:0;z-index:2}
"""),
    ("(max-width: 36rem)", """
.def .body{margin-left:0}
.def,.rm{scroll-margin-top:1rem}
"""),
    ("print", """
.js .controls,.counts{display:none}
.js main.v-def #by-roadmap,.js main.v-rm #by-definition{display:block}
"""),
]

JS = """
(function(){
var doc=document,body=doc.body;body.classList.add('js');
var main=doc.querySelector('main'),q=doc.getElementById('q'),
area=doc.getElementById('area'),status=doc.getElementById('status'),count=doc.getElementById('count');
var defs=[].slice.call(doc.querySelectorAll('article.def')),rms=[].slice.call(doc.querySelectorAll('article.rm'));
var areas=[].slice.call(doc.querySelectorAll('section.area'));
var tabs=[].slice.call(doc.querySelectorAll('.tabs button')),chips=[].slice.call(doc.querySelectorAll('.counts button'));
var emptyD=doc.getElementById('empty-def'),emptyR=doc.getElementById('empty-rm');
function norm(s){s=s.toLowerCase();if(s.normalize){s=s.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'');}
return s.replace(/[\\u2010-\\u2015]/g,'-').replace(/\\s+/g,' ');}
defs.concat(rms).forEach(function(el){el._t=norm(el.textContent);});
var view='def';
function setView(v){view=v;main.className=(v==='rm')?'v-rm':'v-def';
tabs.forEach(function(b){b.setAttribute('aria-pressed',b.getAttribute('data-view')===v?'true':'false');});apply();}
function apply(){
var words=norm(q.value).split(' ').filter(Boolean),a=area.value,s=status.value,nd=0,nr=0;
function hit(el){for(var i=0;i<words.length;i++){if(el._t.indexOf(words[i])<0)return false;}return true;}
defs.forEach(function(el){var ok=hit(el)&&(!a||el.getAttribute('data-area')===a)&&(!s||el.getAttribute('data-status')===s);
el.hidden=!ok;if(ok)nd++;});
areas.forEach(function(sec){sec.hidden=!sec.querySelector('article.def:not([hidden])');});
rms.forEach(function(el){var ok=hit(el)&&(!a||(' '+el.getAttribute('data-areas')+' ').indexOf(' '+a+' ')>=0)&&(!s||el.getAttribute('data-state')===s);
el.hidden=!ok;if(ok)nr++;});
emptyD.style.display=nd?'none':'block';emptyR.style.display=nr?'none':'block';
count.textContent=(view==='rm')?('Showing '+nr+' of '+rms.length+' roadmaps'):('Showing '+nd+' of '+defs.length+' definitions');
chips.forEach(function(b){b.setAttribute('aria-pressed',(s&&b.getAttribute('data-status')===s)?'true':'false');});}
function clearFilters(){q.value='';area.value='';status.value='';}
function go(){var id=decodeURIComponent(location.hash.slice(1));if(!id)return;
var el=doc.getElementById(id);if(!el)return;
var want=(id==='by-roadmap'||id.indexOf('r-')===0)?'rm':'def';
if(want!==view)setView(want);
if(el.hidden){clearFilters();apply();}
el.scrollIntoView();}
q.addEventListener('input',apply);area.addEventListener('change',apply);status.addEventListener('change',apply);
tabs.forEach(function(b){b.addEventListener('click',function(){setView(b.getAttribute('data-view'));});});
chips.forEach(function(b){b.addEventListener('click',function(){var v=b.getAttribute('data-status');
status.value=(status.value===v)?'':v;if(view!=='def')setView('def');else apply();});});
window.addEventListener('hashchange',go);
setView('def');go();
})();
"""


def render_entry(entry, rm):
    state, number = entry_state(entry, rm)
    name = esc(rm["folder"])
    url = roadmap_url(rm)
    link = '<a class="rname" href="%s">%s</a>' % (esc(url), name) if url else '<span class="rname">%s</span>' % name
    role = entry["role"]
    label = ROLE_LABEL[role]
    if role == "defines" and not entry.get("full", True):
        label = "Defines in part"
    if state == "main":
        where_state = "on main"
    elif state == "pr":
        if rm["state"] == "main":
            where_state = ('this part is in open pull request <a href="%s">#%d</a>'
                           % (esc(entry.get("pr_url") or pr_url(number)), number))
        else:
            where_state = "open pull request #%d" % number
    else:
        where_state = "planned, not yet written"
    parts = ['<li><span class="role %s">%s</span> %s <span class="small">(%s; <a href="#%s">about this roadmap</a>)</span>'
             % (role, esc(label), link, where_state, anchor(rm["folder"]))]
    parts.append('<span class="where">%s</span>' % fmt(entry["where"]))
    if entry.get("note"):
        parts.append('<span class="note">%s</span>' % fmt(entry["note"]))
    parts.append("</li>")
    return "".join(parts)


def render_definition(d, data):
    n = d["n"]
    out = ['<article class="def" id="d-%d" data-status="%s" data-area="%d">'
           % (n, d["status"], data["areas"].index(d["area"]))]
    label = STATUS_LABEL[d["status"]]
    if d.get("in_part"):
        label += ", in part"
    out.append('<header><span class="num">%d</span><h4>%s</h4>'
               '<span class="badge s-%s">%s</span></header>'
               % (n, fmt(d["name"]), d["status"], esc(label)))
    out.append('<div class="body">')
    out.append('<p class="what">%s</p>' % fmt(d["what"]))
    if d.get("first"):
        out.append('<p class="first"><span class="lab">Where to look first.</span> %s</p>' % fmt(d["first"]))
    if d.get("caveat"):
        out.append('<p class="caveat"><span class="lab">Note.</span> %s</p>' % fmt(d["caveat"]))
    entries = d.get("entries", [])
    if entries:
        out.append('<ul class="entries">')
        for e in entries:
            out.append(render_entry(e, data["roadmaps"][e["roadmap"]]))
        out.append("</ul>")
    else:
        out.append('<p class="plan"><span class="lab">Roadmap.</span> Not found: no roadmap on main or in an open '
                   'pull request specifies this definition.</p>')
    if d.get("planned"):
        out.append('<p class="plan"><span class="lab">Planned.</span> %s</p>' % fmt(d["planned"]))
    if d.get("library"):
        out.append('<p class="lib"><span class="lab">In Tau Ceti or Mathlib.</span> %s</p>' % fmt(d["library"]))
    if d.get("census"):
        out.append('<p class="small"><a href="%s">Census page for definition %d</a></p>' % (esc(d["census"]), n))
    out.append("</div></article>")
    return "\n".join(out)


def render_roadmap(key, rm, data, covers):
    state = rm["state"]
    url = roadmap_url(rm)
    area_ids = sorted({data["areas"].index(d["area"]) for d, _ in covers})
    out = ['<article class="rm" id="%s" data-state="%s" data-areas="%s">'
           % (anchor(rm["folder"]), state, " ".join(str(i) for i in area_ids))]
    name = esc(rm["folder"])
    head = '<a href="%s">%s</a>' % (esc(url), name) if url else name
    label = ROADMAP_STATE_LABEL[state]
    if state == "pr":
        label += " #%d" % int(rm["pr"])
    out.append('<header><h4 class="rname">%s</h4><span class="badge s-%s">%s</span></header>'
               % (head, state, esc(label)))
    out.append('<div class="body">')
    if rm.get("title"):
        out.append('<p class="title">%s</p>' % fmt(rm["title"]))
    out.append('<p class="desc">%s</p>' % fmt(rm["description"]))
    out.append('<div class="covers"><span class="lab">Definitions it covers.</span><ul>')
    for d, e in covers:
        role = ROLE_LABEL[e["role"]].lower()
        if e["role"] == "defines" and not e.get("full", True):
            role = "defines in part"
        extra = ""
        if e.get("pr") and state == "main":
            extra = (', in open pull request <a href="%s">#%d</a>'
                     % (esc(e.get("pr_url") or pr_url(e["pr"])), int(e["pr"])))
        out.append('<li><a href="#d-%d">%d. %s</a> <span class="small">(%s%s)</span></li>'
                   % (d["n"], d["n"], fmt(d["name"]), role, extra))
    out.append("</ul></div></div></article>")
    return "\n".join(out)


def build():
    with open(DATA, encoding="utf-8") as handle:
        data = json.load(handle)
    validate(data)
    defs = sorted(data["definitions"], key=lambda d: d["n"])
    roadmaps = data["roadmaps"]

    counts = {s: 0 for s in STATUS_ORDER}
    for d in defs:
        counts[d["status"]] += 1

    covers = {key: [] for key in roadmaps}
    for d in defs:
        for e in d.get("entries", []):
            covers[e["roadmap"]].append((d, e))
    unused = [key for key, items in covers.items() if not items]
    if unused:
        sys.exit("roadmaps without any definition: " + ", ".join(sorted(unused)))

    title = data["meta"]["title"]
    page = []
    page.append('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">')
    page.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
    page.append("<title>%s</title>" % esc(title))
    page.append('<meta name="description" content="%s">' % esc(data["meta"]["description"]))
    page.append("<style>%s</style>" % CSS)
    for media, rules in CSS_MEDIA:
        page.append('<style media="%s">%s</style>' % (esc(media), rules))
    page.append("</head>\n<body>")

    page.append('<div class="wrap">\n<header>')
    page.append("<h1>%s</h1>" % esc(title))
    for para in data["meta"]["intro"]:
        page.append('<p class="lede">%s</p>' % fmt(para))
    partial = sum(1 for d in defs if d.get("in_part"))
    page.append('<p class="meta">Data read on %s. %d definitions, %d roadmaps. '
                'Of the statuses below, %d hold only in part.</p>'
                % (esc(read_date(data["meta"]["read_at"])), len(defs), len(roadmaps), partial))
    page.append('<ul class="counts" aria-label="Definitions by status">')
    for s in STATUS_ORDER:
        page.append('<li><button type="button" class="s-%s" data-status="%s" aria-pressed="false" title="%s">'
                    '<b>%d</b> %s</button></li>'
                    % (s, s, esc(STATUS_HELP[s].capitalize()), counts[s], esc(STATUS_LABEL[s])))
    page.append("</ul>")
    page.append('<p class="hint">%s.</p>' % "; ".join(
        "<b>%s</b>: %s" % (esc(STATUS_LABEL[s]), esc(STATUS_HELP[s])) for s in STATUS_ORDER))
    page.append("</header>\n</div>")

    page.append('<div class="controls"><div class="wrap"><div class="row">')
    page.append('<span class="tabs" role="group" aria-label="View">'
                '<button type="button" data-view="def" aria-pressed="true">By definition</button>'
                '<button type="button" data-view="rm" aria-pressed="false">By roadmap</button></span>')
    page.append('<label for="q">Filter by text</label>'
                '<input id="q" type="search" placeholder="Filter by text, e.g. parabolic or Enriques" autocomplete="off">')
    page.append('<label for="area">Area</label><select id="area"><option value="">All areas</option>')
    for i, a in enumerate(data["areas"]):
        page.append('<option value="%d">%s</option>' % (i, esc(a)))
    page.append("</select>")
    page.append('<label for="status">Status</label><select id="status"><option value="">All statuses</option>')
    for s in STATUS_ORDER:
        page.append('<option value="%s">%s</option>' % (s, esc(STATUS_LABEL[s])))
    page.append("</select></div>")
    page.append('<p class="count" id="count" aria-live="polite"></p>')
    page.append("</div></div>")

    page.append('<div class="wrap">\n<main class="v-def">')
    page.append('<section id="by-definition">\n<h2>By definition</h2>')
    page.append('<p class="hint">Each definition lists the roadmaps to look at. '
                '<b>Defines</b>: the roadmap states the notion as something to construct. '
                '<b>Defines in part</b>: it does so for a special case or for one component. '
                '<b>Uses</b>: it builds on the notion. '
                '<b>Related</b>: it holds an ingredient or a neighbouring notion, and neither defines nor uses this one. '
                'A status marked <b>in part</b> means that no roadmap yet defines the notion in full; '
                'the note under the definition says what is missing.</p>')
    for i, a in enumerate(data["areas"]):
        group = [d for d in defs if d["area"] == a]
        page.append('<section class="area" data-area="%d">\n<h3>%s <span class="small">(%d)</span></h3>'
                    % (i, esc(a), len(group)))
        for d in group:
            page.append(render_definition(d, data))
        page.append("</section>")
    page.append('<p class="empty" id="empty-def">No definition matches the filters.</p>')
    page.append("</section>")

    page.append('<section id="by-roadmap">\n<h2>By roadmap</h2>')
    page.append('<p class="hint">Every roadmap named in the first view, in alphabetical order, with the definitions it covers.</p>')
    for key in sorted(roadmaps, key=lambda k: roadmaps[k]["folder"].lower()):
        page.append(render_roadmap(key, roadmaps[key], data, covers[key]))
    page.append('<p class="empty" id="empty-rm">No roadmap matches the filters.</p>')
    page.append("</section>\n</main>")

    page.append("<footer>")
    page.append('<p>Roadmaps: <a href="%s">%s</a>. The independent census of the same 100 definitions: '
                '<a href="%s">%s</a>.</p>'
                % (esc(ROADMAP_REPO), esc(ROADMAP_REPO.replace("https://", "")),
                   esc(data["meta"]["census_repo"]), esc(data["meta"]["census_repo"].replace("https://", ""))))
    for para in data["meta"].get("footer", []):
        page.append("<p>%s</p>" % fmt(para))
    page.append("</footer>\n</div>")
    page.append("<script>%s</script>\n</body>\n</html>\n" % JS)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(page))
    print("wrote docs/index.html: %d definitions, %d roadmaps" % (len(defs), len(roadmaps)))
    print("  " + ", ".join("%s %d" % (STATUS_LABEL[s], counts[s]) for s in STATUS_ORDER))


if __name__ == "__main__":
    build()
