"""Transfer the complete Kimi output matrix into column order for Pi."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import tempfile

import numpy as np

from distill_kimi_vocabulary import BLOCK, TOKEN_COUNT, WIDTH, fetch_range

# Tensor data starts after the 8-byte safetensors length and 576-byte header.
START = 584


def build(path, workers):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
    try:
        matrix = np.lib.format.open_memmap(temp, mode="w+", dtype="<u2",
                                           shape=(WIDTH, TOKEN_COUNT))
        def transfer(first):
            raw = fetch_range(START + 2*first*WIDTH, 2*BLOCK*WIDTH)
            block = np.frombuffer(raw, dtype="<u2").reshape(BLOCK, WIDTH)
            if np.any((block & 0x7f80) == 0x7f80):
                raise ValueError("Nonfinite output weight")
            matrix[:, first:first+BLOCK] = block.T
        with ThreadPoolExecutor(workers) as pool:
            for index, _ in enumerate(pool.map(transfer, range(0, TOKEN_COUNT, BLOCK)), 1):
                if index % 32 == 0:
                    print(f"{index*BLOCK}/{TOKEN_COUNT} output rows", flush=True)
        matrix.flush()
        del matrix
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 13))
    args = parser.parse_args()
    build(args.output, args.workers)
