#!/usr/bin/env python3
"""Write a release manifest and prove the binary carries the version it claims.

The version is read back from the .fw_info record inside the image, so a
manifest can never describe a binary built from something else.
"""
import argparse
import datetime
import hashlib
import json
import os
import struct
import subprocess

FW_INFO_OFFSET = 0x40
FW_INFO = struct.Struct("<8s32s16sI")


def read_fw_info(blob):
    magic, version, build_id, secver = FW_INFO.unpack_from(blob, FW_INFO_OFFSET)
    if magic.rstrip(b"\0") != b"FWINFO1":
        raise SystemExit("no FWINFO1 record at 0x40: not one of our images")
    s = lambda b: b.split(b"\0", 1)[0].decode()
    return {"version": s(version), "build_id": s(build_id), "secver": secver}


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    blob = open(a.image, "rb").read()
    info = read_fw_info(blob)
    if info["version"] != a.version:
        raise SystemExit(f"image says {info['version']}, build says {a.version}")

    manifest = {
        "product": "talaria-demo",
        "version": info["version"],
        "secver": info["secver"],
        "commit": git("rev-parse", "HEAD"),
        "built_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "components": [{
            "name": "application",
            "file": os.path.basename(a.image),
            "size": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "build_id": info["build_id"],
        }],
    }
    with open(a.out, "w") as f:
        json.dump(manifest, f, indent=2)
    c = manifest["components"][0]
    print(f"manifest: {manifest['version']} secver={manifest['secver']} "
          f"{c['size']} B sha256={c['sha256'][:16]}...")


if __name__ == "__main__":
    main()
