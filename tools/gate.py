#!/usr/bin/env python3
"""Promotion gate: decides whether a build may move to the next channel.

Blocks on: any failing test that is not quarantined, an image over its slot
budget, or an image whose SHA-256 is on the block-list. Quarantined failures
are reported but do not block.
"""
import argparse
import json
import sys
import xml.etree.ElementTree as ET


def load_results(paths):
    for path in paths:
        for tc in ET.parse(path).getroot().iter("testcase"):
            name = f"{tc.get('classname')}.{tc.get('name')}"
            yield name, tc.find("failure") is None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--junit", nargs="+", required=True)
    ap.add_argument("--blocklist", required=True)
    ap.add_argument("--quarantine", required=True)
    ap.add_argument("--budget", type=int, required=True, help="slot size in bytes")
    a = ap.parse_args()

    manifest = json.load(open(a.manifest))
    quarantined = set(json.load(open(a.quarantine)).get("tests", []))
    blocked = {line.split()[0] for line in open(a.blocklist)
               if line.strip() and not line.startswith("#")}

    reasons, notes = [], []
    for name, ok in load_results(a.junit):
        if ok:
            continue
        (notes if name in quarantined else reasons).append(
            f"test failed: {name}" + (" (quarantined)" if name in quarantined else ""))

    for c in manifest["components"]:
        if c["size"] > a.budget:
            reasons.append(f"{c['name']}: {c['size']} B exceeds slot budget {a.budget} B")
        elif c["size"] > a.budget * 0.9:
            notes.append(f"{c['name']}: {c['size'] * 100 // a.budget}% of slot budget")
        if c["sha256"] in blocked:
            reasons.append(f"{c['name']}: sha256 is on the block-list")

    for n in notes:
        print(f"NOTE   {n}")
    for r in reasons:
        print(f"BLOCK  {r}")
    print(f"GATE   {manifest['version']}: {'BLOCKED' if reasons else 'PASS'}")
    sys.exit(1 if reasons else 0)


if __name__ == "__main__":
    main()
