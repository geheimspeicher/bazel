#!/bin/bash
set -xuo pipefail
echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs 

sed -i.bak -e 's/^# android_sdk_repository/android_sdk_repository/' -e 's/^# android_ndk_repository/android_ndk_repository/' WORKSPACE
rm -f WORKSPACE.bak

echo '+++ Building'
bazel build --color=yes //src:bazel || exit $?

echo '+++ Testing'
bazel test --color=yes --build_event_json_file=bep.json //scripts/... //src/test/... //third_party/ijar/... //tools/android/...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'

python3 .buildkite/failed_testlogs.py bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs 

exit $TESTS_EXIT_STATUS
