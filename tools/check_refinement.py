"""Compare provisional models before and after refinement on twelve reproducible machines."""
import argparse
from collections import Counter
from itertools import count as depths, product
from pathlib import Path
import random
import subprocess
import tempfile

from refine_model import refine, successor

ACTIONS = ("a", "b", "c")


def shortest_unseen(table, seen, alphabet_size):
    for depth in depths():
        for trace in product(range(alphabet_size), repeat=depth):
            if trace not in seen:
                return trace


def observations(log):
    return {tuple(row.split()[1:]) for row in log.read_text().splitlines()[1:]}


def compare(binary, log, observe, baseline, depth):
    """The control pays exactly the treatment's total, including refit queries."""
    control_log = log.with_suffix(".control")
    control_log.write_bytes(log.read_bytes())
    targeted = refine(binary, log, observe)
    control = refine(binary, control_log, observe, budget=targeted["queries"], choose_probe=shortest_unseen)
    assert control["queries"] == targeted["queries"]
    counts = Counter(observations_per_arm=control["queries"])
    for name, result in (("targeted", targeted), ("shortest", control)):
        counts[name + "_complete"] = int("table" in result)
    if "table" not in targeted or "table" not in control:
        return counts
    counts["paired"] = 1
    seen = observations(log) | observations(control_log)
    for trace in product(ACTIONS, repeat=depth):
        if trace in seen:
            continue
        label = observe(trace)
        indices = [ACTIONS.index(x) for x in trace]
        counts["held_out"] += 1
        counts["positives"] += label
        for name, model in (("original", baseline), ("targeted", targeted["table"]), ("shortest", control["table"])):
            predicted = model[successor(model, 0, indices)][0]
            counts[name + "_errors"] += predicted != label
            counts[name + "_hits"] += predicted == label == 1
    delta = counts["shortest_errors"] - counts["targeted_errors"]
    counts["targeted_win" if delta > 0 else "shortest_win" if delta < 0 else "tie"] = 1
    return counts


def evaluate(binary, directory, seed, matched=False):
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
    if matched:
        return compare(binary, log, observe, baseline, 6)
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
    parser.add_argument("--matched", action="store_true", help="Compare to shortest-unseen at identical cost")
    parser.add_argument("--fraction-log", type=Path, help="Run the matched comparison on a copy of a frozen fraction log")
    parser.add_argument("--first-seed", type=int, default=0)
    parser.add_argument("--machines", type=int, default=12)
    args = parser.parse_args()
    if args.machines < 1:
        parser.error("--machines must be positive")
    total = Counter()
    with tempfile.TemporaryDirectory() as directory:
        if args.fraction_log:
            from frozen_tasks import outcome
            from trace_transfer import read_table
            log = Path(directory) / "fraction"
            log.write_bytes(args.fraction_log.read_bytes())
            binary = args.binary.resolve()
            print("fraction", dict(compare(binary, log, lambda trace: outcome("fraction", trace),
                                           read_table(binary, log), 7)))
            raise SystemExit(0)
        for seed in range(args.first_seed, args.first_seed + args.machines):
            result = evaluate(args.binary.resolve(), Path(directory), seed, args.matched)
            print(seed, dict(result))
            total.update(result)
    print("total", dict(total))
