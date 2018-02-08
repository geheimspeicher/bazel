#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf stashed-outputs rules_k8s

echo '--- Downloading Bazel Binary'
mkdir stashed-outputs
buildkite-agent artifact download bazel-bin/src/bazel stashed-outputs/ --step 'Bazel (Ubuntu 14.04)'
chmod +x stashed-outputs/bazel-bin/src/bazel

echo '--- Cloning'
git clone https://github.com/geheimspeicher/rules_k8s || exit $?
cd rules_k8s

echo '+++ Building'
../stashed-outputs/bazel-bin/src/bazel build --color=yes //test/... || exit $?

echo '+++ Testing'
../stashed-outputs/bazel-bin/src/bazel test --color=yes --build_event_json_file=bep.json //test/...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'
cd ..
python3 .buildkite/failed_testlogs.py rules_k8s/bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done

echo '--- Cleanup'
bazel clean --expunge
rm -rf stashed-outputs rules_k8s

exit $TESTS_EXIT_STATUS
