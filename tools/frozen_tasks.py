"""Evaluate a prebuilt Heed on fixed opaque tasks, using only black-box feedback."""
import argparse
import codecs
from fractions import Fraction
from hashlib import blake2s, sha256
from itertools import product
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ACTIONS = ("a", "b", "c")
TASKS = ("utf8", "fraction", "nesting", "digest")
BUDGET = 96
TARGET_DIGEST = blake2s(b"cbac").digest()


def outcome(task, actions):
    if task == "utf8":
        decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        chunks = {"a": b"\xac", "b": b"\xe2", "c": b"\x82"}
        decoded = "".join(decoder.decode(chunks[a]) for a in actions)
        return int(decoded.endswith("€"))
    if task == "fraction":
        x = Fraction(1)
        for a in actions:
            x = x * 2 if a == "a" else (x + 1 if a == "b" else 1 / x)
        return int(x == Fraction(3, 2))
    if task == "nesting":
        depth = peak = 0
        for a in actions:
            if a == "b":
                depth = peak = 0
            elif a == "c":
                depth += 1
                peak = max(peak, depth)
            else:
                depth -= 1
                if depth < 0:
                    return 0
        return int(depth == 0 and peak >= 2)
    if task == "digest":
        return int(blake2s("".join(actions).encode()).digest() == TARGET_DIGEST)
    raise ValueError(task)


def traces(depth):
    for n in range(depth + 1):
        yield from product(ACTIONS, repeat=n)


def main():
    from trace_agent import run_agent
    from trace_transfer import predict, read_table, try_transfer

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--first-plan", action="store_true", help="Measure goal discovery without requiring a model")
    args = parser.parse_args()
    binary = args.binary.resolve()
    print("Heed sha256", sha256(binary.read_bytes()).hexdigest(), flush=True)
    models = {}
    with tempfile.TemporaryDirectory() as directory:
        for task in TASKS:
            log = Path(directory) / task
            oracle = [sys.executable, str(Path(__file__).resolve()), "--observe", task]
            try:
                run = run_agent(binary, log, list(ACTIONS), None, 1, [], oracle, BUDGET, 10,
                                finish_model=not args.first_plan)
            except ValueError as err:
                if "Experiment budget reached" not in str(err):
                    raise
                run = {"plan": None, "queries": BUDGET}
            rows = [line.split() for line in log.read_text().splitlines()[1:]]
            assert len(rows) == run["queries"]
            seen = {tuple(row[1:]) for row in rows}
            run["distinct_training_traces"] = len(seen)
            run["first_positive_episode"] = next((i for i, row in enumerate(rows, 1)
                                                   if row[0] == "1"), None)
            if run["plan"] is not None:
                assert outcome(task, run["plan"]) == 1
            if run["plan"] is not None and run.get("states") is not None:
                table = models[task] = read_table(binary, log)
                held = [t for t in traces(5) if t not in seen]
                positives = hits = correct = 0
                for t in held:
                    actual = outcome(task, t)
                    pred = predict(table, [ACTIONS.index(a) for a in t])
                    positives += actual
                    hits += int(actual == pred == 1)
                    correct += int(actual == pred)
                run["unseen_correct_total"] = [correct, len(held)]
                run["unseen_positive_hits_total"] = [hits, positives]
            direct = next((i for i, t in enumerate(traces(5), 1)
                           if i <= BUDGET and outcome(task, t)), None)
            print(task, json.dumps(run), "direct_search_episodes", direct, flush=True)
    if args.first_plan:
        return
    # Try each successful model on every other task with the existing transfer
    # driver. Both sides get identical feedback, depth and target-query budgets.
    wins = ties = losses = 0
    for source, table in models.items():
        for task in TASKS:
            if task == source:
                continue
            oracle = lambda trace: {"goal": outcome(task, trace)}
            params = (list(ACTIONS), [({"goal": 0}, 0), ({"goal": 1}, 1)], oracle, 4, BUDGET)
            warm, w = try_transfer(table, *params)
            cold, c = try_transfer(None, *params)
            # Reaching the goal ranks ahead of exhausting the budget.
            a, b = (warm is None, w), (cold is None, c)
            wins += a < b
            ties += a == b
            losses += a > b
            print(f"{source}->{task}: warm {w} ({warm}), direct {c} ({cold})")
    print("Transfer wins, ties, losses:", wins, ties, losses)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--observe"]:
        print(outcome(sys.argv[2], json.load(sys.stdin)))
    else:
        main()
