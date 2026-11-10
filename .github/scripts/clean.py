#!/usr/bin/env python3
"""Delete diff pages older than N days and regenerate index.html.

Usage: clean.py <days> [--dry-run]   (run from the root of the pages repository)

The age of a page is the date of the last commit that touched it. The history is squashed after every
clean (see clean.yml), which would make every page look new, so the effective ages are kept in
.diffs-ages.json: {"files": {<path>: <epoch>}}. A page that was not changed since the commit that
carries that file (the squash commit) keeps the age stored there; a page added or rewritten later uses
its own commit date.

Prints "deleted=<n>" and "kept=<n>" (also appended to $GITHUB_OUTPUT) and a markdown list for the job
summary on stderr.
"""
import html
import json
import os
import subprocess
import sys
import time

AGES = ".diffs-ages.json"


def last_change_times():
    """Epoch of the last commit touching each path, from one pass over the history."""
    out = subprocess.run(
        ["git", "-c", "core.quotepath=off", "log", "--no-renames", "--name-only", "--format=@%ct"],
        check=True, capture_output=True, text=True).stdout
    seen, ts = {}, 0
    for line in out.splitlines():
        if line.startswith("@"):
            ts = int(line[1:])
        elif line and line not in seen:
            seen[line] = ts           # newest commit first: the first sighting is the last change
    return seen


def pages():
    found = []
    for dp, dn, fn in os.walk("."):
        dn[:] = [d for d in dn if not d.startswith(".")]
        for f in fn:
            p = os.path.relpath(os.path.join(dp, f), ".")
            if f.endswith(".html") and p != "index.html":
                found.append(p)
    return sorted(found)


def write_index(rows):
    rows = sorted(rows, key=lambda r: r[1], reverse=True)
    out = ['<!doctype html><meta charset="utf-8"><title>ArgoCD manifest diffs</title>',
           '<style>body{font:15px/1.6 system-ui,sans-serif;margin:2rem auto;max-width:60rem}td{padding:.2rem .8rem}</style>',
           '<h1>ArgoCD manifest diffs</h1><table>']
    for rel, ts in rows:
        when = time.strftime("%Y-%m-%d %H:%M", time.gmtime(ts))
        out.append(f'<tr><td>{when} UTC</td><td><a href="{html.escape(rel)}">{html.escape(rel)}</a></td></tr>')
    out.append("</table>")
    with open("index.html", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


def main():
    if len(sys.argv) < 2 or not sys.argv[1].isdigit() or int(sys.argv[1]) < 1:
        sys.exit("usage: clean.py <days >= 1> [--dry-run]")
    days, dry = int(sys.argv[1]), "--dry-run" in sys.argv[2:]
    now = int(time.time())
    cutoff = now - days * 86400

    stored = {"files": {}}
    if os.path.exists(AGES):
        with open(AGES, encoding="utf-8") as fh:
            stored = json.load(fh)
    changed = last_change_times()
    squash_ts = changed.get(AGES, 0)   # commit that wrote the stored ages

    age, old, keep = {}, [], []
    for p in pages():
        ts = changed.get(p, now)       # untracked file: treat as new
        if p in stored["files"] and ts <= squash_ts:
            ts = stored["files"][p]    # untouched since the last squash
        age[p] = ts
        (old if ts < cutoff else keep).append(p)

    summary = [f"### Clean diffs older than {days} days{' (dry run)' if dry else ''}", "",
               f"- pages: {len(old) + len(keep)}, to delete: {len(old)}, kept: {len(keep)}"]
    summary += [f"- `{p}` ({time.strftime('%Y-%m-%d', time.gmtime(age[p]))})" for p in old]
    print("\n".join(summary), file=sys.stderr)

    if not dry:
        for p in old:
            os.remove(p)
        for dp, dn, fn in sorted(os.walk(".", topdown=False)):
            if dp != "." and not dp.startswith("./.") and not os.listdir(dp):
                os.rmdir(dp)
        write_index([(p, age[p]) for p in keep])
        with open(AGES, "w", encoding="utf-8") as fh:
            json.dump({"files": {p: age[p] for p in keep}}, fh, indent=1, sort_keys=True)
            fh.write("\n")

    for line in (f"deleted={len(old)}", f"kept={len(keep)}"):
        print(line)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
                fh.write(line + "\n")


main()
