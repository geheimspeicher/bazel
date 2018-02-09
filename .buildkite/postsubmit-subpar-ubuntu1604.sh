#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs subpar

echo '--- Downloading Bazel Binary'
mkdir .stashed-outputs
buildkite-agent artifact download bazel-bin/src/bazel .stashed-outputs/ --step 'Build Bazel (Ubuntu 16.04)'
chmod +x .stashed-outputs/bazel-bin/src/bazel

echo '--- Cloning'
git clone https://github.com/google/subpar || exit $?
cd subpar

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs 

echo '+++ Building'
../.stashed-outputs/bazel-bin/src/bazel build --color=yes ... || exit $?

echo '+++ Testing'
../.stashed-outputs/bazel-bin/src/bazel test --color=yes --build_event_json_file=bep.json ...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'
cd ..
python3 .buildkite/failed_testlogs.py subpar/bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs subpar

exit $TESTS_EXIT_STATUS
