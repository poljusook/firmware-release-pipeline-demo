# Firmware release pipeline demo

A small, working release pipeline for Cortex-M firmware: versioned builds, tests
on an emulated Cortex-M3, a promotion gate, channel promotion with downgrade
protection, automatic bisect and flaky-test quarantine.

The target is QEMU's `lm3s6965evb` board, a Cortex-M3: the same core as the
application processor in InnoPhase's Talaria TWO. On real hardware the smoke
test would flash an EVB and read its UART; everything else stays the same.

## Run it

Requires `gcc-arm-none-eabi`, `qemu-system-arm`, `gcc`, `python3`.

```sh
make all gate          # build, unit tests, QEMU smoke test, manifest, gate
demo/run-demo.sh       # 6-step walkthrough in a throwaway clone
```

## Pipeline

```
commit ──> build ──> unit tests ──> smoke test ──> manifest ──> gate ──> promote
           (link-time   (host, JUnit)   (QEMU M3,      (SHA-256,    │       nightly
            size check)                  JUnit)         version     │     → candidate
                                                        read back)  │     → release
                                                                    │
                                     red? ── tools/bisect.sh ───────┘ names the first bad commit
```

| Stage | What it guarantees | Where |
| --- | --- | --- |
| Build | Version and build ID stamped into a fixed `.fw_info` record; an image larger than one A/B slot fails at link time | `Makefile`, `fw/cm3.ld` |
| Unit tests | Rollout cohort maths and anti-rollback rule, run on the host | `tests/test_fwlib.c` |
| Smoke test | The image boots, reports the expected version and passes its self-test | `tools/qemu_smoke.py` |
| Manifest | Version is read back from the binary, so the manifest cannot describe a different build | `tools/manifest.py` |
| Changelog | Generated from Conventional Commits, JIRA keys kept | `tools/changelog.py` |
| Gate | Blocks on non-quarantined test failures, slot budget, block-listed SHA-256 | `tools/gate.py` |
| Promote | No channel skipping, no re-promotion, no security-version downgrade; records the rollback target | `tools/promote.py` |
| Bisect | First bad commit since the last green build; commits that do not build are skipped, not blamed | `tools/bisect.sh` |
| Flaky tests | Reruns on one commit; a test that both passes and fails is quarantined, one that always fails is a bug | `tools/flaky.py` |

The same stages run in [Jenkinsfile](Jenkinsfile) and
[.github/workflows/ci.yml](.github/workflows/ci.yml); both only call `make` and
`tools/`, so CI and a laptop give the same answer.

## Design notes

- **Version from source only.** `git describe --dirty` feeds the stamp. Anything
  that changes the tree changes the binary, which is why the block-list belongs
  in release operations, not in the source tree (step 5 of the demo shows the
  trap).
- **Rollback vs roll-forward.** `secver` is the anti-rollback counter. Promotion
  never lowers it: once a release fixes a security issue, recovery is a new
  release, not a revert.
- **Staged rollout.** A device's cohort is `crc32(MAC) % 100`; the 1 / 10 / 30 /
  100 % ladder is monotonic, which the unit tests check.

## Not covered

Image signing, the bootloader side of A/B selection, and real hardware. These
depend on the SoC's SDK (on Talaria TWO: SSBL and its partition layout).
