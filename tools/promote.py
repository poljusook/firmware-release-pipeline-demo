#!/usr/bin/env python3
"""Promote a gated build one channel up: nightly -> candidate -> release.

A channel file points at the manifest currently served on that channel.
Promotion refuses to skip a channel, to lower the security version (that
would be an unsafe downgrade: roll forward with a fix instead), and to
re-promote a block-listed image.
"""
import argparse
import json
import os
import shutil
import sys

ORDER = ["nightly", "candidate", "release"]


def load(path):
    try:
        return json.load(open(path))
    except FileNotFoundError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--to", choices=ORDER, required=True)
    ap.add_argument("--channels", default="channels")
    ap.add_argument("--blocklist", default="blocklist.txt")
    a = ap.parse_args()

    new = json.load(open(a.manifest))
    os.makedirs(a.channels, exist_ok=True)
    blocked = {l.split()[0] for l in open(a.blocklist) if l.strip() and not l.startswith("#")}

    idx = ORDER.index(a.to)
    if idx > 0:
        below = load(f"{a.channels}/{ORDER[idx - 1]}.json")
        if not below or below["commit"] != new["commit"]:
            sys.exit(f"refused: {new['version']} is not on {ORDER[idx - 1]} yet")

    current = load(f"{a.channels}/{a.to}.json")
    if current and current["commit"] == new["commit"]:
        sys.exit(f"refused: {new['version']} is already on {a.to}")
    if current and new["secver"] < current["secver"]:
        sys.exit(f"refused: secver {new['secver']} < {current['secver']} on {a.to}; "
                 "roll forward instead of downgrading")
    if any(c["sha256"] in blocked for c in new["components"]):
        sys.exit("refused: image is on the block-list")

    if current:
        new["previous"] = current["version"]  # what a rollback would go back to
    with open(f"{a.channels}/{a.to}.json", "w") as f:
        json.dump(new, f, indent=2)
    shutil.copy(a.manifest, f"{a.channels}/{a.to}-{new['version']}.json")
    print(f"promoted {new['version']} to {a.to}"
          + (f" (rollback target: {new['previous']})" if current else ""))


if __name__ == "__main__":
    main()
