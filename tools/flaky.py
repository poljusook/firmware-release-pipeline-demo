#!/usr/bin/env python3
"""Find flaky tests by rerunning them on the same commit.

A test that both passes and fails on one commit is flaky by definition: the
code did not change, the result did. Those go to quarantine.json, where they
keep running but stop blocking promotion. Counting the passes matters as much
as counting the failures: a test that fails 9 times out of 9 is a bug, not a
flake.
"""
import argparse
import collections
import json
import subprocess
import xml.etree.ElementTree as ET


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--cmd", required=True, help="test command; gets the JUnit path appended")
    ap.add_argument("--quarantine", default="quarantine.json")
    a = ap.parse_args()

    stats = collections.defaultdict(lambda: [0, 0])  # name -> [passes, failures]
    for i in range(a.runs):
        xml_path = f"build/rerun-{i}.xml"
        subprocess.run(f"{a.cmd} {xml_path}", shell=True, capture_output=True)
        for tc in ET.parse(xml_path).getroot().iter("testcase"):
            name = f"{tc.get('classname')}.{tc.get('name')}"
            stats[name][tc.find("failure") is not None] += 1

    flaky = sorted(n for n, (p, f) in stats.items() if p and f)
    broken = sorted(n for n, (p, f) in stats.items() if f and not p)
    for n, (p, f) in sorted(stats.items()):
        tag = "FLAKY" if n in flaky else "BROKEN" if n in broken else "ok"
        print(f"{n:32} pass={p:2} fail={f:2}  {tag}")

    try:
        q = json.load(open(a.quarantine))
    except FileNotFoundError:
        q = {"tests": []}
    q["tests"] = sorted(set(q["tests"]) | set(flaky))
    json.dump(q, open(a.quarantine, "w"), indent=2)
    print(f"quarantine: {q['tests']}")
    if broken:
        print(f"consistently failing (not quarantined, these are real bugs): {broken}")


if __name__ == "__main__":
    main()
