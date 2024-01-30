import json
import pickle
import sys
import os


def print_usage():
    print(f"Usage: python3 json_to_pickle.py <json file> <pickle file>")


def converter(input_file, output_file):
    with open(input_file, "r") as json_file:
        data = json.load(json_file)

    with open(output_file, "wb") as pickle_file:
        pickle.dump(data, pickle_file)


def _main(argv):
    if len(argv) < 3:
        print_usage()
        exit(1)

    input_file = argv[1]
    output_file = argv[2]

    if not os.path.exists(input_file):
        print(f"File '{input_file}' doesn't exist.")
        exit(1)
    converter(input_file, output_file)


if __name__ == "__main__":
    _main(sys.argv)
