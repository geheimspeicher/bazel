#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects

echo '--- Downloading Bazel Binary'
mkdir .stashed-outputs
buildkite-agent artifact download bazel-bin/src/bazel .stashed-outputs/ --step 'Build Bazel (macOS)'
chmod +x .stashed-outputs/bazel-bin/src/bazel

echo '--- Cloning'
git clone https://github.com/geheimspeicher/rules_groovy .downstream-projects/rules_groovy || exit $?
cd .downstream-projects/rules_groovy

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects

echo '+++ Building'
../../.stashed-outputs/bazel-bin/src/bazel build --color=yes ... || exit $?

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects
