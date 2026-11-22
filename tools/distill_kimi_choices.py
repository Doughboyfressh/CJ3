"""Compile BF16 embedding fixtures to a nearest-choice student for Pi."""
import math
import struct
from pathlib import Path

NATIVE = Path(__file__).resolve().parents[1] / "examples/native"


def load_rows():
    rows = {}
    for fixture in ("kimi_choice.txt", "kimi_near.txt"):
        for line in (NATIVE / fixture).read_text().splitlines():
            name, *cells = line.split()
            if len(cells) != 7168:
                raise ValueError(f"Unexpected embedding width for {name}")
            row = [struct.unpack(">f", struct.pack(">I", int(c) << 16))[0] for c in cells]
            if name in rows and rows[name] != row:
                raise ValueError(f"Conflicting embedding rows for {name}")
            rows[name] = row
    return rows


def main():
    rows = load_rows()
    names = sorted(rows)
    if len(names) > 94:
        raise ValueError("Printable rank encoding supports up to 94 entries")
    norms = {name: math.sqrt(math.fsum(x*x for x in row)) for name, row in rows.items()}
    records = []
    margins = []
    for query in names:
        scores = [math.fsum(x*y for x, y in zip(rows[query], rows[candidate])) /
                  (norms[query] * norms[candidate]) for candidate in names]
        margins.append(query + " " + " ".join(str(round(32767*s)) for s in scores))
        levels = {value: rank for rank, value in enumerate(sorted(set(scores), reverse=True))}
        records.append(query + " " + "".join(chr(33 + levels[s]) for s in scores))
    (NATIVE / "kimi_margins.txt").write_bytes(("\n".join(margins) + "\n").encode("ascii"))
    (NATIVE / "kimi_choice_ranks.txt").write_bytes(("\n".join(records) + "\n").encode("ascii"))


if __name__ == "__main__":
    main()
