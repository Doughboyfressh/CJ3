"""Challenge an inferred transition table using only resettable binary observations."""
import argparse
from itertools import product
import json
from pathlib import Path
import subprocess


def successor(table, state, word):
    for action in word:
        state = table[state][1 + action]
    return state


def challenge(table, seen, alphabet_size):
    """Try inserting two-step returns into observed positives where the model predicts failure."""
    best = None
    for loop in product(range(alphabet_size), repeat=2):
        support = sum(successor(table, state, loop[:1]) != state
                      and successor(table, state, loop) == state for state in range(len(table)))
        if not support:
            continue
        for trace, label in seen.items():
            if not label:
                continue
            for i in range(len(trace) + 1):
                trial = trace[:i] + loop + trace[i:]
                if trial not in seen and table[successor(table, 0, trial)][0] == 0:
                    rank = (-support, len(trial), trial)
                    if best is None or rank < best:
                        best = rank
    return None if best is None else best[2]


def refine(binary, log, observe, budget=96, timeout=30, *, choose_probe=challenge):
    data = log.read_text()
    if not data.endswith("\n"):
        raise ValueError("Incomplete observation log")
    header, *rows = data.splitlines()
    tag, *alphabet = header.split()
    if tag != "events" or not alphabet or len(alphabet) != len(set(alphabet)):
        raise ValueError("Expected distinct event names")
    indices = {a: i for i, a in enumerate(alphabet)}
    seen = {}
    for row in rows:
        label, *trace = row.split()
        key = tuple(indices[a] for a in trace)
        if label not in ("0", "1") or seen.get(key, int(label)) != int(label):
            raise ValueError("Invalid or conflicting observations")
        seen[key] = int(label)
    count = len(rows)
    if count > budget:
        raise ValueError("Existing observations exceed budget")
    while True:
        lines = subprocess.check_output([binary, "states-refine", log], text=True, timeout=timeout).splitlines()
        if lines[0].startswith("consistent states "):
            table = [list(map(int, row.split())) for row in lines[1:]]
            trial = None if count == budget else choose_probe(table, seen, len(alphabet))
            if trial is None or count == budget:
                return {"status": "consistent with observations", "queries": count, "table": table}
        elif lines[0].split()[:1] == ["observe"]:
            trial = tuple(indices[a] for a in lines[0].split()[1:])
        else:
            raise ValueError(lines[0])
        if count == budget:
            return {"status": "incomplete refinement", "queries": count}
        if trial in seen:
            raise ValueError("Learner requested an observation already in the log")
        trace = [alphabet[a] for a in trial]
        label = observe(trace)
        if type(label) is not int or label not in (0, 1):
            raise ValueError("Expected a binary observation")
        with log.open("a") as handle:
            print(label, *trace, file=handle)
        seen[trial] = label
        count += 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("--budget", type=int, default=96, help="Total, including previous observations")
    parser.add_argument("--oracle", nargs=argparse.REMAINDER, required=True)
    args = parser.parse_args()
    if not args.oracle:
        parser.error("Supply a resettable oracle executable")
    def observe(trace):
        return int(subprocess.check_output(args.oracle, input=json.dumps(trace), text=True, timeout=30))
    print(json.dumps(refine(args.binary.resolve(), args.log, observe, args.budget)))
