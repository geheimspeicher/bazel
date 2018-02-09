#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects

echo '--- Downloading Bazel Binary'
mkdir .stashed-outputs
buildkite-agent artifact download bazel-bin/src/bazel .stashed-outputs/ --step 'Build Bazel (Ubuntu 16.04)'
chmod +x .stashed-outputs/bazel-bin/src/bazel

echo '--- Cloning'
git clone https://github.com/geheimspeicher/examples .downstream-projects/examples || exit $?
cd .downstream-projects/examples

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects

echo '+++ Building'
../../.stashed-outputs/bazel-bin/src/bazel build --color=yes //:all || exit $?

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects
