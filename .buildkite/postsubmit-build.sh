#!/bin/bash
set -xeuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs 

echo '+++ Building'
bazel build --color=yes //src:bazel

echo '--- Uploading Bazel Binary'
buildkite-agent artifact upload bazel-bin/src/bazel