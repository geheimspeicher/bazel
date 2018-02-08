#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf stashed-outputs rules_nodejs

echo '--- Downloading Bazel Binary'
mkdir stashed-outputs
buildkite-agent artifact download bazel-bin/src/bazel stashed-outputs/ --step 'Bazel Ubuntu 14.04'
chmod +x stashed-outputs/bazel-bin/src/bazel

echo '--- Cloning'
git clone https://github.com/geheimspeicher/rules_nodejs || exit $?
cd rules_nodejs

echo '+++ Building'
../stashed-outputs/bazel-bin/src/bazel build --color=yes ... || exit $?

echo '+++ Testing'
../stashed-outputs/bazel-bin/src/bazel test --color=yes --build_event_json_file=bep.json ...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'
cd ..
python3 .buildkite/failed_testlogs.py rules_nodejs/bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done

echo '--- Cleanup'
bazel clean --expunge
rm -rf stashed-outputs rules_nodejs

exit $TESTS_EXIT_STATUS
