#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects

echo '--- Downloading Bazel Binary'
mkdir .stashed-outputs
buildkite-agent artifact download bazel-bin/src/bazel .stashed-outputs/ --step 'Build Bazel (Ubuntu 14.04)'
chmod +x .stashed-outputs/bazel-bin/src/bazel

echo '--- Cloning'
git clone https://github.com/geheimspeicher/rules_jsonnet .downstream-projects/rules_jsonnet || exit $?
cd .downstream-projects/rules_jsonnet

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects

echo '+++ Building'
../../.stashed-outputs/bazel-bin/src/bazel build --color=yes //... @examples//... || exit $?

echo '+++ Testing'
../../.stashed-outputs/bazel-bin/src/bazel test --color=yes --build_event_json_file=bep.json //... @examples//...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'
cd ../..
python3 .buildkite/failed_testlogs.py .downstream-projects/rules_jsonnet/bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs .downstream-projects

exit $TESTS_EXIT_STATUS
