#!/usr/bin/env python3
"""Bring the states and links in data/definitions.json up to date.

Standard library only. The script re-reads

  * which roadmap folders are on the main branch of TauCetiProject/TauCetiRoadmap, and
  * whether each pull request named in the data is open, merged or closed,

and then updates the states, the links, the status of each definition and the
date the data was read. A roadmap whose pull request has merged becomes a link
to its folder on main. Names, descriptions and every other piece of prose are
left exactly as they are. Run build.py afterwards.

    python3 refresh.py --clone path/to/TauCetiRoadmap   folders from a local clone (runs git fetch origin main)
    python3 refresh.py                                  folders from the GitHub API
    python3 refresh.py --check                          no network: only check that the file is consistent
    python3 refresh.py --dry-run ...                    report what would change, write nothing

Pull request states come from the GitHub API: one GraphQL request through the
GitHub CLI (`gh`) when it is installed, otherwise one unauthenticated REST
request per pull request (set GITHUB_TOKEN to raise the rate limit). Nothing is
ever written to GitHub.
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "definitions.json")

OWNER = "TauCetiProject"
REPO = "TauCetiRoadmap"
ROADMAP_REPO = "https://github.com/%s/%s" % (OWNER, REPO)
API = "https://api.github.com"

RANK = {"main": 2, "pr": 1}


# ---------------------------------------------------------------- derived fields

def main_url(folder):
    if folder.startswith("Completed/"):
        return "%s/tree/main/%s" % (ROADMAP_REPO, folder)
    return "%s/tree/main/TauCetiRoadmap/%s" % (ROADMAP_REPO, folder)


def pr_url(number):
    return "%s/pull/%d" % (ROADMAP_REPO, int(number))


def roadmap_url(rm):
    if rm["state"] == "main":
        return main_url(rm["folder"])
    if rm["state"] == "pr":
        return pr_url(rm["pr"])
    return ""


def entry_state(entry, rm):
    if entry.get("pr") or rm["state"] == "pr":
        return "pr"
    return rm["state"]


def compute_status(definition, roadmaps):
    """Headline status of a definition, and whether it holds only in part.

    A definition already formalised in the generality of the list is "library".
    Otherwise the roadmaps that define it in full decide: the most advanced of
    their states is the status. If no roadmap defines it in full, the roadmaps
    that define a special case or one component decide, and the status is
    qualified as "in part". A roadmap that only uses the notion, or treats a
    related one, never counts. With no defining roadmap the status is "planned"
    when a plan is recorded and "none" otherwise.
    """
    if definition.get("in_library"):
        return "library", False
    best = {True: 0, False: 0}
    for entry in definition.get("entries", []):
        if entry.get("role") != "defines":
            continue
        state = entry_state(entry, roadmaps[entry["roadmap"]])
        full = bool(entry.get("full", True))
        best[full] = max(best[full], RANK.get(state, 0))
    pick = best[True] or best[False]
    in_part = not best[True] and bool(best[False])
    if pick == 2:
        return "main", in_part
    if pick == 1:
        return "pr", in_part
    return ("planned" if definition.get("planned") else "none"), False


def derive(data):
    """Recompute every derived field (links and statuses). Returns the list of status changes."""
    changes = []
    roadmaps = data["roadmaps"]
    for rm in roadmaps.values():
        rm["url"] = roadmap_url(rm)
        if rm["state"] != "pr":
            rm.pop("pr", None)
    for definition in data["definitions"]:
        for entry in definition.get("entries", []):
            rm = roadmaps[entry["roadmap"]]
            if rm["state"] == "pr":
                # the whole roadmap is in that pull request; no separate entry-level number
                entry.pop("pr", None)
                entry.pop("pr_url", None)
            elif entry.get("pr"):
                entry["pr_url"] = pr_url(entry["pr"])
            else:
                entry.pop("pr", None)
                entry.pop("pr_url", None)
        new, in_part = compute_status(definition, roadmaps)
        definition["in_part"] = in_part
        if definition.get("status") != new:
            changes.append((definition["n"], definition.get("status"), new))
            definition["status"] = new
    return changes


def pr_numbers(data):
    numbers = set()
    for rm in data["roadmaps"].values():
        if rm["state"] == "pr":
            numbers.add(int(rm["pr"]))
    for definition in data["definitions"]:
        for entry in definition.get("entries", []):
            if entry.get("pr"):
                numbers.add(int(entry["pr"]))
    return sorted(numbers)


# ---------------------------------------------------------------- reading the repository

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit("command failed: %s\n%s" % (" ".join(cmd[:4]), result.stderr.strip()[:400]))
    return result.stdout


def have_gh(args):
    return (not args.no_gh) and shutil.which("gh") is not None


def api_get(path, args):
    """GET a GitHub API path, through gh when available, else urllib."""
    if have_gh(args):
        return json.loads(run(["gh", "api", path]))
    request = urllib.request.Request(API + "/" + path.lstrip("/"), headers={
        "Accept": "application/vnd.github+json", "User-Agent": "annals-definitions-refresh"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        sys.exit("GitHub API returned %d for %s" % (error.code, path))


def folders_from_paths(paths):
    """Folders that hold a README.md, as paths under TauCetiRoadmap/ or as Completed/Name."""
    folders = set()
    for path in paths:
        if not path.endswith("/README.md"):
            continue
        folder = path[: -len("/README.md")]
        if folder.startswith("TauCetiRoadmap/"):
            folders.add(folder[len("TauCetiRoadmap/"):])
        elif folder.startswith("Completed/"):
            folders.add(folder)
    return folders


def main_folders(args):
    if args.clone:
        if not args.no_fetch:
            run(["git", "-C", args.clone, "fetch", "-q", "origin", "main"])
        listing = run(["git", "-C", args.clone, "ls-tree", "-r", "--name-only", "origin/main"])
        commit = run(["git", "-C", args.clone, "rev-parse", "--short=9", "origin/main"]).strip()
        return folders_from_paths(listing.splitlines()), commit
    tree = api_get("repos/%s/%s/git/trees/main?recursive=1" % (OWNER, REPO), args)
    if tree.get("truncated"):
        sys.exit("the tree listing from the API is truncated; use --clone with a local clone instead")
    return folders_from_paths(item["path"] for item in tree["tree"]), tree.get("sha", "")[:9]


def pr_states(numbers, args):
    """Map each pull request number to OPEN, MERGED or CLOSED."""
    if not numbers:
        return {}
    if have_gh(args):
        fields = " ".join("p%d: pullRequest(number: %d) { state }" % (n, n) for n in numbers)
        query = 'query { repository(owner: "%s", name: "%s") { %s } }' % (OWNER, REPO, fields)
        reply = json.loads(run(["gh", "api", "graphql", "-f", "query=" + query]))
        repo = reply["data"]["repository"]
        return {n: repo["p%d" % n]["state"] for n in numbers}
    states = {}
    for n in numbers:
        pull = api_get("repos/%s/%s/pulls/%d" % (OWNER, REPO, n), args)
        states[n] = "MERGED" if pull.get("merged") else pull["state"].upper()
    return states


# ---------------------------------------------------------------- the refresh itself

def refresh(data, folders, states):
    notes, warnings = [], []
    roadmaps = data["roadmaps"]
    for key in sorted(roadmaps):
        rm = roadmaps[key]
        folder = rm["folder"]
        on_main = folder in folders
        if rm["state"] == "pr":
            state = states.get(int(rm["pr"]))
            if state == "MERGED" and on_main:
                notes.append("%s: pull request #%d has merged; now a link to main" % (folder, rm["pr"]))
                rm["state"] = "main"
            elif state == "MERGED":
                warnings.append("%s: pull request #%d has merged but the folder is not on main" % (folder, rm["pr"]))
            elif state == "CLOSED":
                warnings.append("%s: pull request #%d was closed without merging" % (folder, rm["pr"]))
            elif on_main:
                warnings.append("%s: the folder is on main although pull request #%d is still open" % (folder, rm["pr"]))
        elif rm["state"] == "main" and not on_main:
            moved = "Completed/" + folder.split("/")[-1]
            if moved in folders:
                notes.append("%s: moved to %s" % (folder, moved))
                rm["folder"] = moved
            else:
                warnings.append("%s: recorded as on main, but the folder is not there" % folder)
    for definition in data["definitions"]:
        for entry in definition.get("entries", []):
            if not entry.get("pr"):
                continue
            state = states.get(int(entry["pr"]))
            if state == "MERGED":
                notes.append("definition %d: pull request #%d has merged; %s entry is now on main"
                             % (definition["n"], entry["pr"], entry["roadmap"]))
                entry.pop("pr")
            elif state == "CLOSED":
                warnings.append("definition %d: pull request #%d was closed without merging"
                                % (definition["n"], entry["pr"]))
    return notes, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--clone", help="path of a local clone of the roadmap repository")
    parser.add_argument("--no-fetch", action="store_true", help="with --clone: do not run git fetch first")
    parser.add_argument("--no-gh", action="store_true", help="do not use the GitHub CLI even if it is installed")
    parser.add_argument("--check", action="store_true", help="no network: check the derived fields only")
    parser.add_argument("--dry-run", action="store_true", help="report, but do not write the file")
    parser.add_argument("--data", default=DATA, help="path of definitions.json")
    args = parser.parse_args()

    with open(args.data, encoding="utf-8") as handle:
        data = json.load(handle)
    before = json.dumps(data, sort_keys=True)

    if args.check:
        changes = derive(data)
        if json.dumps(data, sort_keys=True) != before:
            for n, old, new in changes:
                print("definition %d: status %s should be %s" % (n, old, new))
            sys.exit("derived fields are out of date; run refresh.py without --check")
        print("consistent: %d definitions, %d roadmaps" % (len(data["definitions"]), len(data["roadmaps"])))
        return

    folders, commit = main_folders(args)
    states = pr_states(pr_numbers(data), args)
    notes, warnings = refresh(data, folders, states)
    changes = derive(data)
    data["meta"]["read_at"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if commit:
        data["meta"]["main_commit"] = commit

    for line in notes:
        print(line)
    for n, old, new in changes:
        print("definition %d: status %s -> %s" % (n, old, new))
    for line in warnings:
        print("WARNING: " + line)
    open_count = sum(1 for s in states.values() if s == "OPEN")
    print("read %d folders on main (%s) and %d pull requests (%d open); %d changes"
          % (len(folders), commit or "main", len(states), open_count, len(notes) + len(changes)))
    if args.dry_run:
        print("dry run: nothing written")
        return
    with open(args.data, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=1)
        handle.write("\n")
    print("wrote %s; now run build.py" % os.path.relpath(args.data))
    if warnings:
        sys.exit(1)


if __name__ == "__main__":
    main()
