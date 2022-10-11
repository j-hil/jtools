r"""Tool to remove Byte Order Marks (BOMs) from files.

Removes characters `ï»¿` (aka "\xEF\xBB\xBF") from the head         ,--.!,
of any python file in the target directory.                      __/   -*-
                                                               ,d08b.  '|`
To see usage help, run the following:                          0088MM
    python -m jtools.bom_disposal -h                           `9MMP'
"""
# originally developed as the BOMs in files seemed to impede `pylint`

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="python -m jtools.bom_disposal",
        description="Tools to remove Byte Order Marks (BOMs).",
    )
    parser.add_argument(
        "folder_path",
        type=str,
        help="Directory to (recursively) search for `.py` files to remove BOMs from.",
    )

    args = parser.parse_args()
    folder_path = Path(args.folder_path)

    if not folder_path.is_dir():
        print(f"Invalid path {folder_path}. Input an existent folder path.")
        sys.exit()

    for file in folder_path.glob("**/*.py"):

        with open(file) as fh:
            text = fh.read()

        if text.startswith("ï»¿"):
            with open(file, "w") as fh:
                fh.write(text[3:])
            print(f"Successfully diffused BOM in '{file}'.")


if __name__ == "__name__":
    main()
