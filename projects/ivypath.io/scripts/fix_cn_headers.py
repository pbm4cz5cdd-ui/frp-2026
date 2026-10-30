#!/usr/bin/env python3
"""Give a proposal file its header line back.

An early run opened the output in append mode by mistake, so the rows were
written without the column names. The rows themselves are fine: this puts the
header in front of them, and does nothing to a file that already has one.
"""

import sys

HEAD = ["name", "country", "fact", "status", "value", "note", "quote",
        "source", "checked", "tier"]


def main():
    for path in sys.argv[1:]:
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except FileNotFoundError:
            continue
        if not lines or lines[0].startswith("name,"):
            continue
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(",".join(HEAD) + "\n")
            for line in lines:
                f.write(line + "\n")
        print("fixed", path, len(lines), "rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
