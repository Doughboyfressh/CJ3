"""Full-vocabulary logits from a post-normalization Kimi hidden state."""
import argparse
import base64
import hashlib
from pathlib import Path

import numpy as np

from distill_kimi_context import NATIVE, bf16
from distill_kimi_vocabulary import TOKEN_COUNT, WIDTH


def final_norm(hidden):
    """Apply Kimi's final RMSNorm to the state entering that normalization."""
    raw = base64.b64decode((NATIVE / "kimi_final_norm.b64").read_bytes())
    if hashlib.sha256(raw).hexdigest() != "3f55cfe19850509c18bca378256dc31b3ba05beb5e39086c49956c54bef609c2":
        raise ValueError("Final normalization tensor checksum mismatch")
    if hidden.shape != (WIDTH,) or not np.isfinite(hidden).all():
        raise ValueError(f"Expected {WIDTH} finite final hidden coordinates")
    # Rescale before squaring so even very large finite vectors stay finite.
    scale = max(1., float(np.max(np.abs(hidden))))
    scaled = hidden / scale
    return bf16(raw) * scaled / np.sqrt(np.mean(scaled**2) + (1e-5 / scale) / scale)


def logits(table, hidden):
    if table.shape != (WIDTH, TOKEN_COUNT) or table.dtype != np.dtype("<u2"):
        raise ValueError("Expected the column-major Kimi output weight export")
    hidden = np.asarray(hidden, dtype=np.float64)
    if hidden.shape != (WIDTH,) or not np.isfinite(hidden).all():
        raise ValueError(f"Expected {WIDTH} finite final hidden coordinates")
    result = np.zeros(TOKEN_COUNT, dtype=np.float64)
    active = np.flatnonzero(hidden)
    for first in range(0, len(active), 16):
        dims = active[first:first+16]
        weights = bf16(table[dims].tobytes()).reshape(len(dims), TOKEN_COUNT)
        result += hidden[dims] @ weights
    if not np.isfinite(result).all():
        raise ValueError("Logits exceed float64 range")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("table", type=Path)
    parser.add_argument("hidden", type=Path, help="7168 post-norm coordinates in a .npy vector")
    parser.add_argument("--pre-norm", action="store_true", help="Apply Kimi final RMSNorm first")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.top <= TOKEN_COUNT:
        parser.error("--top must be between 1 and 163840")
    hidden = np.asarray(np.load(args.hidden, allow_pickle=False), dtype=np.float64)
    if args.pre_norm:
        hidden = final_norm(hidden)
    scores = logits(np.load(args.table, mmap_mode="r", allow_pickle=False), hidden)
    for token in np.argsort(-scores, kind="stable")[:args.top]:
        print(f"{token}\t{scores[token]:.10g}")
