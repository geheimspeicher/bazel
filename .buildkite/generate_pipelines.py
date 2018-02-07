PLATFORMS = [("Ubuntu 14.04", "ubuntu1404"), ("Ubuntu 16.04", "ubuntu1604")]
DOWNSTREAM_PROJECTS = ["rules_go", "rules_python"]

def bazel_presubmit_pipeline(platforms):
  steps = []
  for platform in platforms:
    label = platform[0]
    script_name = "presubmit.sh"
    script = """#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json

echo '+++ Building'
bazel build --color=yes //src:bazel || exit $?

echo '+++ Testing'
bazel test --color=yes --build_event_json_file=bep.json //scripts/... //src/test/... //third_party/ijar/... //tools/android/...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'

python3 .buildkite/failed_testlogs.py bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done

exit $TESTS_EXIT_STATUS"""
    steps.append(command_step(label, script, script_name, platform[1]))
  write_pipeline("bazel-presubmit.yml", steps)

def bazel_postsubmit_pipeline(platforms):
  steps = []
  for platform in platforms:
    label = "Bazel " + platform[0]
    script_name = "postsubmit.sh"
    script = """#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json

echo '+++ Building'
bazel build --color=yes //src:bazel || exit $?

#echo '+++ Testing'
#bazel test --color=yes --build_event_json_file=bep.json //scripts/... //src/test/... //third_party/ijar/... //tools/android/...

TESTS_EXIT_STATUS=$?

#echo '--- Uploading Failed Test Logs'
#python3 .buildkite/failed_testlogs.py bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done

echo '--- Uploading Bazel Binary'
buildkite-agent artifact upload bazel-bin/src/bazel

exit $TESTS_EXIT_STATUS
"""
    steps.append(command_step(label, script, script_name, platform[1]))

  steps.append(wait_step())

  for project in DOWNSTREAM_PROJECTS:
    for platform in platforms:
      bazel_build_step = "Bazel " + platform[0]
      label = project + " " + platform[0]
      script_name = "postsubmit-" + project + "-" + platform[1] + ".sh"
      script = """#!/bin/bash
set -xuo pipefail

echo '--- Cleanup'
bazel clean --expunge
rm -rf stashed-outputs {}

echo '--- Downloading Bazel Binary'
mkdir stashed-outputs
buildkite-agent artifact download bazel-bin/src/bazel stashed-outputs/ --step '{}'
chmod +x stashed-outputs/bazel-bin/src/bazel

echo '--- Cloning'
git clone https://github.com/geheimspeicher/{} || exit $?
cd {}

echo '+++ Building'
../stashed-outputs/bazel-bin/src/bazel build --color=yes ... || exit $?

echo '+++ Testing'
../stashed-outputs/bazel-bin/src/bazel test --color=yes --build_event_json_file=bep.json ...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'
cd ..
python3 .buildkite/failed_testlogs.py bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done

echo '--- Cleanup'
bazel clean --expunge
rm -rf stashed-outputs {}

exit $TESTS_EXIT_STATUS
""".format(project, bazel_build_step, project, project, project)
      steps.append(command_step(label, script, script_name, platform[1]))
    write_pipeline("bazel-postsubmit.yml", steps)

def wait_step():
  return " - wait"

def command_step(label, script, script_name, platform):
  with open(script_name, 'w') as f:
    f.write(script)
  return """
 - label: \"{}\"
   command: \"{}\"
   agents:
     - \"os={}\"""".format(label, ".buildkite/" + script_name, platform)

def write_pipeline(name, steps):
  with open(name, 'w') as f:
    f.write("steps:")
    for step in steps:
      f.write(step)
      f.write("\n")

if __name__ == '__main__':
  bazel_presubmit_pipeline(PLATFORMS)
  bazel_postsubmit_pipeline(PLATFORMS)

