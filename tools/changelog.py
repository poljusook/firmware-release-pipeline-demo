#!/usr/bin/env python3
"""Changelog from Conventional Commits since the previous release tag.

feat/fix/perf are grouped, `!` or a BREAKING CHANGE footer is called out,
and JIRA keys (ABC-123) are kept so every line traces back to a ticket.
"""
import argparse
import re
import subprocess

CC = re.compile(r"^(?P<type>\w+)(?:\((?P<scope>[^)]+)\))?(?P<bang>!)?: (?P<desc>.+)$")
JIRA = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
SECTIONS = [("breaking", "Breaking changes"), ("feat", "Features"),
            ("fix", "Fixes"), ("perf", "Performance")]


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", help="previous tag (default: latest v* tag)")
    ap.add_argument("--title", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    since = a.since or git("describe", "--tags", "--match", "v*", "--abbrev=0", "HEAD^").strip()
    rng = f"{since}..HEAD" if since else "HEAD"
    log = git("log", rng, "--no-merges", "--format=%h%x1f%s%x1f%b%x1e")

    groups = {k: [] for k, _ in SECTIONS}
    for rec in filter(str.strip, log.split("\x1e")):
        sha, subject, body = (rec.strip("\n").split("\x1f") + ["", ""])[:3]
        m = CC.match(subject)
        if not m:
            continue
        tickets = sorted(set(JIRA.findall(subject + " " + body)))
        scope = f"**{m['scope']}:** " if m["scope"] else ""
        line = f"- {scope}{m['desc']} ({sha}{', ' + ', '.join(tickets) if tickets else ''})"
        if m["bang"] or "BREAKING CHANGE" in body:
            groups["breaking"].append(line)
        if m["type"] in groups:
            groups[m["type"]].append(line)

    title = a.title or git("describe", "--tags", "--always").strip()
    out = [f"# {title}", "", f"Changes since {since or 'the first commit'}.", ""]
    for key, heading in SECTIONS:
        if groups[key]:
            out += [f"## {heading}", "", *groups[key], ""]
    text = "\n".join(out)
    open(a.out, "w").write(text)
    print(text)


if __name__ == "__main__":
    main()
