"""Stream the pinned Kimi embedding tensor into a full-vocabulary Pi value table."""
import argparse
import concurrent.futures
import os
from pathlib import Path
import tempfile
import time
import urllib.error
import urllib.request

import numpy as np

from distill_kimi_context import REVISION, SCALE, bf16, download

URL = f"https://huggingface.co/moonshotai/Kimi-K3.1-Pro/resolve/{REVISION}/model-00094-of-000096.safetensors"
TOKEN_COUNT = 163840
BLOCK = 1024
WIDTH = 7168
CHANNELS = 128
OFFSET = 584 + 2348810240
SHARD_SIZE = 4697664072


def fetch(first, count):
    start = OFFSET + first * WIDTH * 2
    return fetch_range(start, count * WIDTH * 2)


def fetch_range(start, size):
    end = start + size - 1
    request = urllib.request.Request(f"{URL}?pi_slice={start}-{end}",
                                     headers={"Range": f"bytes={start}-{end}"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{SHARD_SIZE}":
                    raise ValueError("Incorrect checkpoint byte range")
                raw = response.read(size + 1)
            if len(raw) != size:
                raise OSError("Incomplete checkpoint range")
            return raw
        except (OSError, urllib.error.URLError):
            if attempt == 3:
                raise
            time.sleep(2**attempt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 13))
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    norm = bf16(download("input_norm", args.cache))
    values = bf16(download("value", args.cache)).reshape(CHANNELS, WIDTH)
    filters = np.frombuffer(download("conv", args.cache), dtype="<f4").reshape(CHANNELS, 4)
    taps = np.rint(filters.T.astype(float) * SCALE).astype("<i4")
    # Each worker writes a distinct fixed-width range in a private file.
    with tempfile.NamedTemporaryFile(dir=args.output.parent, delete=False) as tmp:
        tmp.write(b"PIV1" + taps.tobytes())
        path = Path(tmp.name)
        offset = tmp.tell()
        tmp.truncate(offset + TOKEN_COUNT * CHANNELS * 4)
    def project(first):
        raw = fetch(first, BLOCK)
        x = bf16(raw).reshape(BLOCK, WIDTH)
        rms = np.sqrt(np.einsum("ij,ij->i", x, x) / WIDTH + 1e-5)
        x *= norm
        x /= rms[:, None]
        scores = np.rint((x @ values.T) * SCALE)
        if not np.all(np.abs(scores) < 1 << 24):
            raise ValueError("Projection exceeds Pi accumulator budget")
        with path.open("r+b") as handle:
            handle.seek(offset + first * CHANNELS * 4)
            handle.write(scores.astype("<i4").tobytes())
    try:
        with concurrent.futures.ThreadPoolExecutor(args.workers) as pool:
            for i, _ in enumerate(pool.map(project, range(0, TOKEN_COUNT, BLOCK)), 1):
                if i % 16 == 0:
                    print(f"{i * BLOCK}/{TOKEN_COUNT} token IDs", flush=True)
        os.replace(path, args.output)
    finally:
        path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
