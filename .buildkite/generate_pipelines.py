PLATFORMS = [("Ubuntu 14.04", "ubuntu1404"), ("Ubuntu 16.04", "ubuntu1604"), ("macOS", "macos")]
DOWNSTREAM_PROJECTS = {
  "bazel-watcher" : {},
  "BUILD_file_generator" : {},
  "buildtools" : {'build': '', 'test': '//:tests'},
  "rules_docker" : {},
  "rules_go" : {},
  "rules_groovy" : {'test': None},
  "rules_k8s" : {},
  "rules_nodejs" : {'run': '@yarn//:yarn'},
  "rules_python" : {},
  "rules_rust" : {'build': '//... @examples//...', 'test': '//... @examples//...'},
  "rules_scala" : {'build': '//test/...', 'test': '//test/...'},
  "rules_typescript" : {'run': '@yarn//:yarn'}
}

def build_test_bazel_presubmit():
  return """
echo '+++ Building'
bazel build --color=yes //src:bazel || exit $?

echo '+++ Testing'
bazel test --color=yes --build_event_json_file=bep.json //scripts/... //src/test/... //third_party/ijar/... //tools/android/...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'

python3 .buildkite/failed_testlogs.py bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done
"""

def exit_test_status():
  return """
exit $TESTS_EXIT_STATUS
"""

def build_upload_bazel_postsubmit():
  return """
echo '+++ Building'
bazel build --color=yes //src:bazel

echo '--- Uploading Bazel Binary'
buildkite-agent artifact upload bazel-bin/src/bazel ${BUILDKITE_ARTIFACT_UPLOAD_DESTINATION}
"""

def test_bazel_postsubmit():
  return """
echo '+++ Testing'
bazel test --color=yes --build_event_json_file=bep.json //scripts/... //src/test/... //third_party/ijar/... //tools/android/...

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'
python3 .buildkite/failed_testlogs.py bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done
"""

def bazel_presubmit_pipeline(platforms):
  steps = []
  for platform in platforms:
    label = platform[0]
    script_name = "presubmit.sh"
    script = """#!/bin/bash
set -xuo pipefail"""
    script = script + cleanup_commands()
    script = script + fix_android_workspace()
    script = script + build_test_bazel_presubmit()
    script = script + cleanup_commands()
    script = script + exit_test_status()
    steps.append(command_step(label, script, script_name, platform[1]))
  write_pipeline("presubmit.yml", steps)

def bazel_postsubmit_pipeline(platforms):
  steps = []

  # Bazel Build

  for platform in platforms:
    step_name = label("Build Bazel", platform[0])
    script_name = "postsubmit-build.sh"
    script = """#!/bin/bash
set -xeuo pipefail
"""
    script = script + cleanup_commands()
    script = script + fix_android_workspace()
    script = script + build_upload_bazel_postsubmit()
    steps.append(command_step(step_name, script, script_name, platform[1]))

  steps.append(wait_step())

  # Bazel Test

  for platform in platforms:
    step_name = label("Test Bazel", platform[0])
    script_name = "postsubmit-test.sh"
    script = """#!/bin/bash
set -xuo pipefail
"""
    script = script + cleanup_commands()
    script = script + fix_android_workspace()
    script = script + test_bazel_postsubmit()
    script = script + cleanup_commands()
    script = script + exit_test_status()
    steps.append(command_step(step_name, script, script_name, platform[1]))

  # Downstream Build and Test

  for project_name, project in DOWNSTREAM_PROJECTS.items():
    for platform in platforms:
      bazel_build_step_name = label("Build Bazel", platform[0])
      build_step_name = label(project_name, platform[0])
      script_name = "postsubmit-" + project_name + "-" + platform[1] + ".sh"
      script = """#!/bin/bash
set -xuo pipefail
"""
      script = script + cleanup_commands(project_name)
      script = script + """
echo '--- Downloading Bazel Binary'
mkdir .stashed-outputs
buildkite-agent artifact download bazel-bin/src/bazel .stashed-outputs/ --step '{1}'
chmod +x .stashed-outputs/bazel-bin/src/bazel

echo '--- Cloning'
git clone https://github.com/geheimspeicher/{0} || exit $?
cd {0}
""".format(project_name, bazel_build_step_name)
      script = script + cleanup_commands()
      if "run" in project:
        script = script + """
../.stashed-outputs/bazel-bin/src/bazel run --color=yes {0} || exit $?
""".format(project["run"])
      script = script + """
echo '+++ Building'
../.stashed-outputs/bazel-bin/src/bazel build --color=yes {0} || exit $?
""".format(project.get("build", "..."))
      test_targets = project.get("test", "...")
      if test_targets != None:
        script = script + """
echo '+++ Testing'
../.stashed-outputs/bazel-bin/src/bazel test --color=yes --build_event_json_file=bep.json {1}

TESTS_EXIT_STATUS=$?

echo '--- Uploading Failed Test Logs'
cd ..
python3 .buildkite/failed_testlogs.py {0}/bep.json | while read logfile; do buildkite-agent artifact upload $logfile; done
""".format(project_name, test_targets)
      script = script + cleanup_commands(project_name)
      if test_targets != None:
        script = script + """
exit $TESTS_EXIT_STATUS
"""
      steps.append(command_step(build_step_name, script, script_name, platform[1]))
    write_pipeline("postsubmit.yml", steps)

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

def label(project, platform):
  return "{0} ({1})".format(project, platform)

def cleanup_commands(folder = ""):
  return """
echo '--- Cleanup'
bazel clean --expunge
rm -rf bep.json .failed-test-logs .stashed-outputs {}
""".format(folder)

def fix_android_workspace():
  return """
sed -i.bak \
-e 's/^# android_sdk_repository/android_sdk_repository/' \
-e 's/^# android_ndk_repository/android_ndk_repository/' \
WORKSPACE
rm -f WORKSPACE.bak
"""

if __name__ == '__main__':
  bazel_presubmit_pipeline(PLATFORMS)
  bazel_postsubmit_pipeline(PLATFORMS)

