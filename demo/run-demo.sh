#!/bin/sh
# Live walkthrough of the pipeline in a throwaway clone. The real repo is not touched.
#   1. a release with a changelog and channel promotion
#   2. a regression found automatically by bisect
#   3. a flaky test detected and quarantined
#   4. the gate blocking a block-listed image
#   5. promotion refusing a security-version downgrade
set -eu

src=$(cd "$(dirname "$0")/.." && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
git clone -q "$src" "$work/repo"
cd "$work/repo"
git config user.name "Demo"; git config user.email "demo@example.com"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

say "1. Release v1.0.0: build, test, gate, promote nightly -> candidate -> release"
git tag v1.0.0
make -s clean all gate >/dev/null
python3 tools/promote.py --manifest build/manifest.json --to nightly
python3 tools/promote.py --manifest build/manifest.json --to candidate
python3 tools/promote.py --manifest build/manifest.json --to release
python3 tools/promote.py --manifest build/manifest.json --to release || true

say "2. Three commits land; one of them silently breaks CRC-32 (and so rollout cohorts)"
echo '/* docs */' >> fw/include/fwlib.h && git commit -qam "docs(fwlib): describe cohort API [FW-101]"
sed -i 's/0xEDB88320u/0xEDB88321u/' fw/src/fwlib.c && git commit -qam "perf(crc): table-free CRC tweak [FW-102]"
echo '' >> README.md && git commit -qam "fix(build): tidy README [FW-103]"
make -s clean test-unit >/dev/null 2>&1 && echo "unexpected: tests pass" || echo "nightly: unit tests FAILED"
tools/bisect.sh v1.0.0

say "3. Changelog generated from Conventional Commits"
python3 tools/changelog.py --since v1.0.0 --title "Unreleased" --out build/CHANGELOG.md >/dev/null
cat build/CHANGELOG.md
git revert --no-edit HEAD~1 >/dev/null

say "4. Flaky test: rerun 10x on the same commit, quarantine what both passes and fails"
make -s build/test_fwlib >/dev/null
FLAKY_DEMO=1 python3 tools/flaky.py --runs 10 --cmd "sleep 1; build/test_fwlib"
git commit -qam "test: quarantine flaky_demo until fixed [FW-104]"

say "5. Gate blocks an image whose SHA-256 is on the block-list"
git tag v1.1.0
make -s clean all >/dev/null
sha=$(python3 -c "import json;print(json.load(open('build/manifest.json'))['components'][0]['sha256'])")
echo "$sha  FW-110 bricks EVB rev A" >> blocklist.txt
# Call the gate directly: `make gate` would see a dirty tree, restamp the version and rebuild.
python3 tools/gate.py --manifest build/manifest.json --junit build/unit.xml build/qemu.xml \
    --blocklist blocklist.txt --quarantine quarantine.json --budget 131072 || echo "-> promotion stopped"
git checkout -q blocklist.txt

say "6. Downgrade protection: a release with a lower secver cannot replace a higher one"
echo 2 > SECVER && git commit -qam "feat(security)!: bump secver after key rotation [FW-120]" && git tag v1.2.0
make -s clean all >/dev/null
for ch in nightly candidate release; do python3 tools/promote.py --manifest build/manifest.json --to $ch; done
git checkout -q v1.1.0 2>/dev/null
make -s clean all >/dev/null
python3 tools/promote.py --manifest build/manifest.json --to nightly
python3 tools/promote.py --manifest build/manifest.json --to candidate
python3 tools/promote.py --manifest build/manifest.json --to release || true
