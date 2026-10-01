#!/usr/bin/env python3
"""
Read one value from a JSON file (a tiny, dependency-free stand-in for jq, so the
shell tools need nothing beyond Python — also on Windows).

  json_get.py FILE PATH [DEFAULT]     print FILE's value at PATH (dot-separated keys),
                                      or DEFAULT when it is missing/null
  json_get.py FILE PATH --keys        print the keys of the object at PATH, one per line
"""

import json
import sys


def lookup(data, path):
    for key in [k for k in path.split(".") if k]:
        if isinstance(data, dict) and key in data:
            data = data[key]
        elif isinstance(data, list) and key.isdigit() and int(key) < len(data):
            data = data[int(key)]
        else:
            return None
    return data


def main() -> int:
    args = sys.argv[1:]
    if len(args) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path_file, path = args[0], args[1]
    try:
        with open(path_file, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = None
    value = lookup(data, path) if data is not None else None
    if len(args) > 2 and args[2] == "--keys":
        for key in (value or {}) if isinstance(value, dict) else []:
            print(key)
        return 0
    default = args[2] if len(args) > 2 else ""
    if value is None or value is False:
        print(default)
    elif isinstance(value, (dict, list)):
        print(json.dumps(value, ensure_ascii=False))
    else:
        print(value)
    return 0


if __name__ == "__main__":
    sys.exit(main())
