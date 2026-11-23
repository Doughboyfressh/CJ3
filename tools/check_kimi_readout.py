"""Check both readout paths, including direct BF16 rows from the pinned teacher."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

import numpy as np

from build_kimi_readout import START
from distill_kimi_vocabulary import TOKEN_COUNT, WIDTH, fetch_range
from kimi_readout import logits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("table", type=Path)
    parser.add_argument("executable", type=Path)
    args = parser.parse_args()
    table = np.load(args.table, mmap_mode="r", allow_pickle=False)
    rng = np.random.default_rng(4631)
    dense = rng.standard_normal(WIDTH)
    scores = logits(table, dense)
    ids = [0, TOKEN_COUNT-1, int(np.argmax(scores)), *rng.choice(TOKEN_COUNT, 13, replace=False)]
    def check_row(token):
        raw = fetch_range(START + int(token)*WIDTH*2, WIDTH*2)
        words = np.frombuffer(raw, dtype="<u2")
        np.testing.assert_array_equal(words, table[:, token])
        # Independently decode sign, exponent and fraction via powers of two.
        exponent = (words >> 7) & 255
        fraction = words & 127
        value = np.ldexp(fraction.astype(np.float64) + 128*(exponent != 0),
                         np.maximum(exponent.astype(int), 1)-134)
        reference = np.dot(np.where(words >> 15, -value, value), dense)
        np.testing.assert_allclose(scores[token], reference, rtol=1e-11, atol=1e-12)
    with ThreadPoolExecutor(6) as pool:
        list(pool.map(check_row, ids))
    decided = 0
    for i in range(32):
        dims = rng.choice(WIDTH, 2+i%7, replace=False)
        coeffs = rng.choice([-9, -3, -1, 1, 3, 9], len(dims))
        hidden = np.zeros(WIDTH)
        hidden[dims] = coeffs
        reference = logits(table, hidden)
        pairs = [str(v) for pair in zip(dims, coeffs) for v in pair]
        result = subprocess.check_output([args.executable.resolve(), args.table, *pairs], text=True).strip()
        if result != "uncertain":
            if int(result) != np.argmax(reference):
                raise ValueError("Native greedy token differs from direct output projection")
            decided += 1
    if decided == 0:
        raise ValueError("Native path abstained on every comparison")
    print(f"{len(ids)} raw rows matched; {decided}/32 sparse winners certified")


if __name__ == "__main__":
    main()
