# The 100 Annals definitions in the Tau Ceti roadmaps

A one-page static site. For each of the 100 definitions needed to state the main theorems of
recent Annals of Mathematics papers, it says which Tau Ceti roadmap specifies the definition,
where in that roadmap to look, and whether the roadmap defines the notion or only uses it. A
second view lists every roadmap that appears, with a short description and the definitions it
covers.

The roadmaps live in [TauCetiProject/TauCetiRoadmap](https://github.com/TauCetiProject/TauCetiRoadmap).
An independent census of the same 100 definitions is kept in
[TauCetiProject/AnnalsDefinitions](https://github.com/TauCetiProject/AnnalsDefinitions); each
definition on the page links to its census file.

## Layout

```
data/definitions.json   the single source of truth: definitions, roadmaps, entries, statuses, links, date read
build.py                renders docs/index.html from the JSON (Python standard library only)
refresh.py              re-reads which roadmaps are on main and which pull requests are open (standard library only)
docs/index.html         the page: one self-contained file, no external scripts, styles or fonts
```

## Rebuild the page

```
python3 build.py
```

`docs/index.html` works offline and can be served as it is, for example by GitHub Pages.

## Bring the states up to date

Roadmap pull requests merge often. `refresh.py` re-reads the state of every roadmap and pull
request named in the data, turns a merged pull request into a link to the folder on main,
recomputes the status of each definition and records the time of the reading. It only reads
from GitHub and it never changes names, descriptions or any other prose.

```
python3 refresh.py --clone path/to/TauCetiRoadmap   # folders from a local clone (runs git fetch origin main)
python3 refresh.py                                  # folders from the GitHub API instead
python3 build.py
```

Pull request states are read with the GitHub CLI (`gh`) when it is installed, in one request,
and otherwise with unauthenticated API calls (set `GITHUB_TOKEN` to raise the rate limit).
`python3 refresh.py --check` verifies, without any network access, that the statuses and links
in the JSON agree with its entries. `--dry-run` reports what would change and writes nothing.

## The data

`data/definitions.json` has three parts.

- `roadmaps`: one record per roadmap, keyed by its folder under `TauCetiRoadmap/` (nested folders
  such as `RepresentationTheory/LieGroups` occur). Fields: `title`, `description`, `state`
  (`main`, `pr` or `planned`), `pr` (the pull request number while the state is `pr`) and `url`.
- `definitions`: the 100 definitions. Fields: `n`, `area`, `name`, `what` (one sentence saying
  what the notion is), `status` and `in_part` (both computed), `in_library`, `first` (where to look
  first when several roadmaps are involved), `caveat`, `library` (what Tau Ceti or Mathlib already
  has), `planned`, `census` (link) and `entries`.
- Each entry names a `roadmap`, a `role`, `full`, `where` (the layer or section, in words) and an
  optional `note`. The roles are `defines` (the roadmap states the notion as something to
  construct), `uses` (it builds on the notion) and `related` (it holds an ingredient or a
  neighbouring notion, and neither defines nor uses this one). For a defining entry, `full` says
  whether the roadmap specifies the notion in the generality of the list; when it is false the page
  shows "Defines in part". An entry may carry `pr` when the relevant part of a roadmap that is
  already on main is still in an open pull request.

In names and prose, `_{...}` and `^{...}` mark subscripts and superscripts. Prose never says whether
a roadmap is on main or in a pull request; the page takes that from `state` and `pr`, so that a
refresh cannot leave a stale sentence behind.

### Statuses

The status of a definition is computed from its entries (see `compute_status` in `refresh.py`):

| Status | Meaning |
| --- | --- |
| In the library or Mathlib | already formalised in the generality of the list (`in_library` is true) |
| On main | a roadmap on the main branch defines it |
| Open pull request | a roadmap in an open pull request defines it, and none on main does |
| Planned | no roadmap text yet, but a plan is recorded in `planned` |
| Not yet planned | none of the above |

The roadmaps that define the notion in full decide the status. Only when none does, the roadmaps
that define a special case or one component decide it; the status is then shown as "in part"
(`in_part` is true) and the `caveat` says what is missing. A roadmap that only uses a notion, or is
merely related to it, never counts.

To correct an entry, edit the JSON, run `python3 refresh.py --check` (or a full refresh), then
`python3 build.py`.
