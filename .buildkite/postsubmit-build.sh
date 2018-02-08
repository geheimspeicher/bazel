#!/bin/bash
set -xe

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json

echo '+++ Building'
bazel build --color=yes //src:bazel

echo '--- Uploading Bazel Binary'
buildkite-agent artifact upload bazel-bin/src/bazel