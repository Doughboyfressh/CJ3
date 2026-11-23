"""Factor the causal value convolution for layer 0, head 0 over Pi's token basis."""
import argparse
import hashlib
import urllib.request
from pathlib import Path

import numpy as np

from distill_kimi_choices import NATIVE, load_rows

REVISION = "d9e99b0792a5e93b78ea9bea62a68167e36ddd9e"
SHARD = f"https://huggingface.co/moonshotai/Kimi-K3.1-Pro/resolve/{REVISION}/model-00001-of-000096.safetensors"
# Absolute byte offsets (including the safetensors header) in the pinned shard.
SLICES = {
    "input_norm": (642928, 7168 * 2),
    "value": (2165055344, 128 * 7168 * 2),
    "conv": (446320, 128 * 4 * 4),
}
DIGESTS = {
    "input_norm": "e64ef4fa5d0747bfe74726be229b39ec51e57e8f6571f0780e6bdaca8e375401",
    "value": "9a895327a3752062e42b3e220966a3b744ec7c54df8c35cb4ca96b5c8329ec07",
    "conv": "5e7a6eac4c75ecb777684feb09f5c39237c4964af7abe2e13d2b3445fbd622d3",
}
SCALE = 65536


def download(name, directory):
    start, size = SLICES[name]
    end = start + size - 1
    path = directory / name
    if not path.exists():
        request = urllib.request.Request(f"{SHARD}?pi_slice={start}-{end}",
                                         headers={"Range": f"bytes={start}-{end}"})
        with urllib.request.urlopen(request, timeout=90) as response:
            if response.status != 206 or response.headers["Content-Range"] != f"bytes {start}-{end}/2341216112":
                raise ValueError("Server did not return the requested tensor slice")
            data = response.read(size + 1)
        if len(data) != size:
            raise ValueError("Truncated tensor slice")
    else:
        data = path.read_bytes()
    if len(data) != size or hashlib.sha256(data).hexdigest() != DIGESTS[name]:
        raise ValueError(f"Invalid cached tensor slice: {path}")
    if not path.exists():
        path.write_bytes(data)
    return data


def bf16(raw):
    return (np.frombuffer(raw, dtype="<u2").astype(np.uint32) << 16).view(np.float32).astype(np.float64)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cache", type=Path)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    norm = bf16(download("input_norm", args.cache))
    value = bf16(download("value", args.cache)).reshape(128, 7168)
    taps = np.frombuffer(download("conv", args.cache), dtype="<f4").reshape(128, 4)
    embeddings = load_rows()
    words = sorted(embeddings)
    x = np.array([embeddings[word] for word in words])
    x = x * norm / np.sqrt(np.mean(x*x, axis=1, keepdims=True) + 1e-5)
    projected = x @ value.T
    lines = []
    for tag, row in [*zip(("tap0", "tap1", "tap2", "tap3"), taps.T), *zip(words, projected)]:
        fixed = np.rint(row.astype(np.float64) * SCALE).astype(np.int64)
        if np.max(np.abs(fixed)) >= 1 << 24:
            raise ValueError("Exceeds native accumulator budget")
        lines.append(tag + " " + " ".join(map(str, fixed)))
    (NATIVE / "kimi_value_context.txt").write_bytes(("\n".join(lines)+"\n").encode("ascii"))


if __name__ == "__main__":
    main()
