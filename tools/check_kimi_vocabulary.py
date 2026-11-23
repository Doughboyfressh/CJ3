"""Compare native Pi results with direct float64 evaluation on checkpoint rows."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess

import numpy as np

from distill_kimi_context import SCALE, bf16, download
from distill_kimi_vocabulary import CHANNELS, WIDTH, fetch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("table", type=Path)
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    norm = bf16(download("input_norm", args.cache))
    value = bf16(download("value", args.cache)).reshape(CHANNELS, WIDTH)
    taps = np.frombuffer(download("conv", args.cache), dtype="<f4").reshape(CHANNELS, 4)
    ids = [0, 255, 8191, 32007, 84112, 129923, 163583, 163584, 163839]
    with ThreadPoolExecutor(4) as pool:
        rows = dict(zip(ids, pool.map(lambda token: bf16(fetch(token, 1)), ids)))
    rng = np.random.default_rng(332)
    errors = []
    for i in range(128):
        sequence = rng.choice(ids, size=1+i%9)
        reference = np.zeros(CHANNELS)
        for lag, token in enumerate(reversed(sequence[-4:])):
            x = rows[token]
            normalized = x * norm / np.sqrt(np.dot(x, x)/WIDTH + 1e-5)
            reference += taps[:, 3-lag] * (value @ normalized)
        text = subprocess.check_output([args.executable.resolve(), "--ids", args.table,
                                        *map(str, sequence)], text=True)
        got = np.array([int(cell) for cell in text.split()]) / SCALE
        if got.shape != reference.shape:
            raise ValueError("Native output has incorrect shape")
        errors.extend(np.abs(got-reference))
    print(f"{len(errors)} activations, max error {max(errors):.8g}, mean error {np.mean(errors):.8g}")
    if max(errors) > 0.0002:
        raise SystemExit("Reference tolerance exceeded")


if __name__ == "__main__":
    main()
