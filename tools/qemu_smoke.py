#!/usr/bin/env python3
"""Boot the firmware on QEMU's Cortex-M3 board and check what it reports.

Stands in for a hardware-in-the-loop smoke test: on a real EVB the same checks
would run against the UART after flashing.
"""
import argparse
import subprocess
import sys
from xml.sax.saxutils import escape


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qemu", default="qemu-system-arm")
    ap.add_argument("--elf", required=True)
    ap.add_argument("--expect-version", required=True)
    ap.add_argument("--junit", required=True)
    ap.add_argument("--timeout", type=int, default=10)
    a = ap.parse_args()

    cmd = [a.qemu, "-M", "lm3s6965evb", "-nographic", "-semihosting",
           "-monitor", "none", "-serial", "stdio", "-kernel", a.elf]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=a.timeout)
        out, rc = p.stdout, p.returncode
    except subprocess.TimeoutExpired as e:
        out, rc = (e.stdout or b"").decode(errors="replace"), "timeout"
    print(out, end="")

    checks = {
        "boots": "BOOT version=" in out,
        "reports_expected_version": f"version={a.expect_version} " in out,
        "selftest_pass": "SELFTEST PASS" in out,
        "clean_exit": rc == 0,
    }

    with open(a.junit, "w") as f:
        f.write(f'<testsuite name="qemu-smoke" tests="{len(checks)}" '
                f'failures="{sum(not v for v in checks.values())}">\n')
        for name, ok in checks.items():
            f.write(f'  <testcase classname="qemu-smoke" name="{name}">')
            if not ok:
                f.write(f'<failure message="{escape(f"exit={rc}")}"/>')
            f.write("</testcase>\n")
        f.write("</testsuite>\n")

    for name, ok in checks.items():
        print(f"{name:26} {'PASS' if ok else 'FAIL'}")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()
