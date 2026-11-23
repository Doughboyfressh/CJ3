"""Use a learned Heed transition table to propose plans in a renamed environment."""
import argparse
from collections import deque
from math import factorial
import json
from pathlib import Path
from itertools import permutations, product
import subprocess


def goal_sensor(examples):
    """Identify a binary sensor from labeled snapshots, without action demonstrations."""
    if {label for _, label in examples} != {0, 1}:
        raise ValueError("Provide positive and negative examples")
    matches = [key for key in examples[0][0]
               if all(snapshot.get(key) == label for snapshot, label in examples)]
    if len(matches) != 1:
        raise ValueError("Examples must distinguish one goal sensor")
    return matches[0]


def read_table(binary, log):
    result = subprocess.check_output([binary, "states", log], text=True, timeout=30)
    header, *lines = result.splitlines()
    if not header.startswith("consistent states "):
        raise ValueError("Source log needs more observations: " + header)
    return [tuple(map(int, line.split())) for line in lines]


def try_transfer(table, actions, examples, observe, max_depth, budget):
    """Seek a verified positive outcome; count every target episode including success."""
    sensor = goal_sensor(examples)
    if len(set(actions)) != len(actions) or not actions or max_depth < 0 or budget < 1:
        raise ValueError("Expected distinct actions and a finite search budget")
    # Search small action interfaces. Larger or incompatible ones use direct exploration.
    maps = []
    if table and len(actions) <= 6 and all(len(row) == len(actions) + 1 for row in table):
        maps = list(permutations(range(1, len(actions) + 1)))

    def predicts(mapping, trace):
        state = 0
        for action in trace:
            state = table[state][mapping[action]]
        return table[state][0]

    # Search lengths in order within each pass. If the source is wrong,
    # unexplored traces with no model support remain eligible in the second pass.
    tried = set()
    for guided in ([True, False] if maps else [False]):
        for depth in range(max_depth + 1):
            while not guided or maps:
                best = None
                best_votes = 0
                for trace in product(range(len(actions)), repeat=depth):
                    if trace in tried:
                        continue
                    yes = sum(predicts(mapping, trace) for mapping in maps) if guided else 1
                    if yes > best_votes:
                        best, best_votes = trace, yes
                        if not guided:
                            break
                if best is None:
                    break
                trace = best
                if len(tried) == budget:
                    return None, len(tried)
                tried.add(trace)
                plan = [actions[i] for i in trace]
                result = observe(plan)[sensor]
                if result == 1:
                    return plan, len(tried)
                if result != 0:
                    raise ValueError("Expected a binary target observation")
                maps = [m for m in maps if not predicts(m, trace)]
    return None, len(tried)

def distinguish(reference, hypothesis):
    """Shortest differing output trace, or None if all reachable outputs agree."""
    pending = deque([(0, 0, ())])
    seen = {(0, 0)}
    while pending:
        left, right, trace = pending.popleft()
        if reference[left][0] != hypothesis[right][0]:
            return trace
        for symbol, pair in enumerate(zip(reference[left][1:], hypothesis[right][1:])):
            if pair not in seen:
                seen.add(pair)
                pending.append((*pair, trace + (symbol,)))
    return None


def predict(table, trace):
    state = 0
    for action in trace:
        state = table[state][action + 1]
    return table[state][0]


def repair_transfer(table, actions, examples, observe, budget):
    """Identify target behavior within all bijections and zero/one edge changes."""
    sensor = goal_sensor(examples)
    n, k = len(table), len(actions)
    if not n or not k or len(set(actions)) != k or any(len(row) != k + 1 for row in table):
        raise ValueError("Repair requires matching source and target alphabet sizes")
    if k > 6 or factorial(k) * (1 + n * k * (n - 1)) > 10000:
        raise ValueError("Repair exceeds the 10000-candidate search limit")
    if budget < 0:
        raise ValueError("Expected a nonnegative episode budget")
    candidates = {}
    for order in permutations(range(1, k + 1)):
        base = tuple((row[0], *(row[i] for i in order)) for row in table)
        candidates[base] = 0
        for state, row in enumerate(base):
            for col in range(1, k + 1):
                for target in range(n):
                    if row[col] != target:
                        changed = row[:col] + (target,) + row[col + 1:]
                        variant = base[:state] + (changed,) + base[state + 1:]
                        candidates.setdefault(variant, 1)

    episodes = 0
    while candidates:
        first = min(candidates, key=candidates.get)
        witnesses = set()
        for other in candidates:
            trace = distinguish(first, other)
            if trace is not None:
                witnesses.add(trace)
                if len(witnesses) >= 16:
                    break
        if not witnesses:
            return {"status": "identified within family", "events": list(actions), "table": first,
                    "minimum_edits": candidates[first], "target_episodes": episodes}
        if episodes == budget:
            return {"status": "budget exhausted", "target_episodes": episodes}
        def split_cost(trace):
            yes = sum(predict(model, trace) for model in candidates)
            return max(yes, len(candidates) - yes), len(trace), trace
        probe = min(witnesses, key=split_cost)
        answer = observe([actions[i] for i in probe])[sensor]
        if answer not in (0, 1):
            raise ValueError("Expected a binary target observation")
        episodes += 1
        candidates = {m: edits for m, edits in candidates.items() if predict(m, probe) == answer}
    return {"status": "observations contradict family", "target_episodes": episodes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("source_log", type=Path, help="Single-output native Heed log")
    parser.add_argument("examples", type=Path, help="JSON array of [target sensor object, success bit]")
    parser.add_argument("--repair", action="store_true", help="Identify a renamed table with up to one changed transition")
    parser.add_argument("--events", nargs="+", required=True)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--budget", type=int, default=100)
    parser.add_argument("--oracle", nargs=argparse.REMAINDER, required=True)
    args = parser.parse_args()
    if not args.oracle:
        parser.error("Supply a resettable local oracle command")
    examples = json.loads(args.examples.read_text(encoding="utf-8"))

    def observe(trace):
        result = subprocess.run(args.oracle, input=json.dumps(trace), capture_output=True,
                                text=True, timeout=30, check=True)
        return json.loads(result.stdout)

    table = read_table(args.binary.resolve(), args.source_log)
    if args.repair:
        print(json.dumps(repair_transfer(table, args.events, examples, observe, args.budget)))
        return
    plan, episodes = try_transfer(table, args.events, examples, observe, args.depth, args.budget)
    print(json.dumps({"plan": plan, "target_episodes": episodes}))


if __name__ == "__main__":
    main()
