"""Compare provisional models before and after refinement on twelve reproducible machines."""
import argparse
from collections import Counter
from itertools import product
from pathlib import Path
import random
import subprocess
import tempfile

from refine_model import refine, successor

ACTIONS = ("a", "b", "c")


def evaluate(binary, directory, seed):
    rng = random.Random(20261124 + seed)
    size = 4 + seed % 4
    target = [[rng.randrange(2), *(rng.randrange(size) for _ in ACTIONS)] for _ in range(size)]

    def observe(trace):
        return target[successor(target, 0, [ACTIONS.index(x) for x in trace])][0]

    log = directory / "observations"
    with log.open("w") as handle:
        print("events", *ACTIONS, file=handle)
        for depth in range(4):
            for trace in product(ACTIONS, repeat=depth):
                print(observe(trace), *trace, file=handle)
    count = 40
    while True:
        lines = subprocess.check_output([binary, "states", log], text=True, timeout=30).splitlines()
        if lines[0].startswith("consistent states "):
            baseline = [list(map(int, line.split())) for line in lines[1:]]
            break
        if lines[0].split()[:1] != ["observe"]:
            raise ValueError(lines[0])
        if count == 96:
            return {"no_baseline": 1}
        trace = lines[0].split()[1:]
        with log.open("a") as handle:
            print(observe(trace), *trace, file=handle)
        count += 1
    result = refine(binary, log, observe)
    if "table" not in result:
        return {"unfinished_refinement": 1}
    seen = {tuple(row.split()[1:]) for row in log.read_text().splitlines()[1:]}
    counts = Counter(paired=1)
    for trace in product(ACTIONS, repeat=6):
        if trace in seen:
            continue
        counts["held_out"] += 1
        indices = [ACTIONS.index(x) for x in trace]
        for key, model in (("original_errors", baseline), ("refined_errors", result["table"])):
            counts[key] += model[successor(model, 0, indices)][0] != observe(trace)
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    args = parser.parse_args()
    total = Counter()
    with tempfile.TemporaryDirectory() as directory:
        for seed in range(12):
            result = evaluate(args.binary.resolve(), Path(directory), seed)
            print(seed, dict(result))
            total.update(result)
    print("total", dict(total))
