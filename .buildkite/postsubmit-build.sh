#!/bin/bash
set -xeuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs 

sed -i.bak -e 's/^# android_sdk_repository/android_sdk_repository/' -e 's/^# android_ndk_repository/android_ndk_repository/' WORKSPACE
rm -f WORKSPACE.bak

echo '+++ Building'
bazel build --color=yes //src:bazel

echo '--- Uploading Bazel Binary'
buildkite-agent artifact upload bazel-bin/src/bazel
