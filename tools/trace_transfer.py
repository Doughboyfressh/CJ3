"""Use a learned Heed transition table to propose plans in a renamed environment."""
import argparse
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

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("source_log", type=Path, help="Single-output native Heed log")
    parser.add_argument("examples", type=Path, help="JSON array of [target sensor object, success bit]")
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
    plan, episodes = try_transfer(table, args.events, examples, observe, args.depth, args.budget)
    print(json.dumps({"plan": plan, "target_episodes": episodes}))


if __name__ == "__main__":
    main()
