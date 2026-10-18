#!/bin/sh
# Find the first commit that breaks the gate tests between a known-good ref and HEAD.
# CI calls this when a gate goes red; the result names the commit and its author.
#
# usage: tools/bisect.sh <good-ref> [test-command]
set -eu

good=${1:?usage: tools/bisect.sh <good-ref> [test-command]}
test_cmd=${2:-"make -s clean test-unit test-qemu >/dev/null 2>&1"}

git bisect start HEAD "$good" >/dev/null
trap 'git bisect reset >/dev/null 2>&1' EXIT

# Exit 125 = "cannot test this commit" (it does not build), so bisect skips it
# instead of blaming it.
git bisect run sh -c "make -s clean fw >/dev/null 2>&1 || exit 125; $test_cmd" >/dev/null

bad=$(git rev-parse refs/bisect/bad)
echo "first bad commit: $(git log -1 --format='%h %s (%an)' "$bad")"
