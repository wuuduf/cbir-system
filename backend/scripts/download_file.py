"""Download a file from URL to a local path."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlretrieve


def main() -> None:
    parser = argparse.ArgumentParser(description="Download one file")
    parser.add_argument("url")
    parser.add_argument("target")
    args = parser.parse_args()
    target = Path(args.target)
    target.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(args.url, target)
    print(f"downloaded {args.url} -> {target}")


if __name__ == "__main__":
    main()
