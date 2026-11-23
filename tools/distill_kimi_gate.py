"""Project five saved BF16 router directions onto Pi's saved token basis."""
import struct
from fractions import Fraction

from distill_kimi_choices import NATIVE, load_rows

SCALE = 1 << 20


def gate_rows():
    rows = []
    for line in (NATIVE / "kimi_gate_rows.txt").read_text().splitlines():
        cells = list(map(int, line.split()))
        if len(cells) != 7168 or any(not 0 <= cell <= 65535 for cell in cells):
            raise ValueError("Invalid router fixture")
        rows.append([struct.unpack(">f", struct.pack(">I", x << 16))[0] for x in cells])
    if len(rows) != 5:
        raise ValueError("Expected five saved router rows")
    return rows


def integers(rows):
    denominator = max(x.as_integer_ratio()[1] for row in rows for x in row)
    return [[int(x * denominator) for x in row] for row in rows], denominator


def main():
    embeddings = load_rows()
    words = sorted(embeddings)
    basis, eb = integers([embeddings[word] for word in words])
    gates, gb = integers(gate_rows())
    output = []
    for word, vector in zip(words, basis):
        scores = [sum(x*y for x, y in zip(vector, gate)) for gate in gates]
        # A common offset has no effect on the winning direction.
        values = [round(Fraction((score-scores[0])*SCALE, eb*gb)) for score in scores[1:]]
        if max(map(abs, values)) >= 1 << 24:
            raise ValueError("Coefficient exceeds the native accumulator budget")
        output.append(word + " " + " ".join(map(str, values)))
    (NATIVE / "kimi_gate_projection.txt").write_bytes(("\n".join(output)+"\n").encode("ascii"))


if __name__ == "__main__":
    main()
