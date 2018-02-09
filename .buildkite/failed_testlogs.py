import json
import sys
import os
from urllib.parse import urlparse
from shutil import copyfile

def main(bep_path):
  raw_data = ""
  with open(bep_path) as f:
    raw_data = f.read()
  decoder = json.JSONDecoder()

  pos = 0
  while pos < len(raw_data):
    json_dict, size = decoder.raw_decode(raw_data[pos:])
    if "testResult" in json_dict:
      test_result = json_dict["testResult"]
      if test_result["status"] != "PASSED":
        outputs = test_result["testActionOutput"]
        for output in outputs:
          if output["name"] == "test.log":
            new_path = label_to_path(json_dict["id"]["testResult"]["label"])
            os.makedirs(os.path.dirname(new_path), exist_ok=True)
            copyfile(urlparse(output["uri"]).path, new_path)
            print(new_path)
    pos += size + 1

def label_to_path(label):
  # remove leading //
  path = label[2:]
  path = path.replace(":", "/")
  return ".failed-test-logs/" + path + ".log"

if __name__ == '__main__':
  main(sys.argv[1])
