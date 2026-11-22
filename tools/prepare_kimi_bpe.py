"""Convert Moonshot's pinned merge table into a byte-safe vocabulary for Pi."""
import base64
import hashlib
import sys
from pathlib import Path

EXPECTED = "b6c497a7469b33ced9c38afb1ad6e47f03f5e5dc05f15930799210ec050c5103"


def main():
    source, target = map(Path, sys.argv[1:])
    data = source.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED:
        raise SystemExit("Unexpected Kimi merge-table digest")
    pieces = [None] * 163584
    for line in data.splitlines():
        token, rank = line.split()
        pieces[int(rank)] = base64.b64decode(token, validate=True).hex()
    target.write_bytes(("\n".join(pieces) + "\n").encode("ascii"))


if __name__ == "__main__":
    main()
