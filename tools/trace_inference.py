"""Exercise Heed's trace learner against independent binary-output machines."""
import argparse
import json
from pathlib import Path
from queue import Empty, Full, Queue
import random
import sqlite3
import subprocess
import tempfile
import sys

from trace_agent import run_agent
from trace_transfer import distinguish


def learn(binary, directory, alphabet, reference, autonomous=False, observe=None):
    path = directory / "observations"
    path.write_text("events " + " ".join(alphabet) + "\n")
    known = set()
    queries = corrections = 0
    for _ in range(2000):
        args = [binary, "states-check", path, str(len(reference))] if autonomous else [binary, "states", path]
        output = subprocess.check_output(args, text=True, timeout=10)
        if output.split(maxsplit=1)[0] == "observe":
            trace = tuple(alphabet.index(token) for token in output.split()[1:])
            queries += 1
        else:
            header, *rows = output.splitlines()
            if not header.startswith("consistent states "):
                raise ValueError(output)
            hypothesis = [list(map(int, row.split())) for row in rows]
            count = int(header.split()[-1])
            if count != len(hypothesis) or any(
                len(row) != len(alphabet) + 1 or row[0] not in (0, 1)
                or any(target < 0 or target >= count for target in row[1:])
                for row in hypothesis
            ):
                raise ValueError("Invalid hypothesis table")
            trace = distinguish(reference, hypothesis)
            if trace is None:
                return queries, corrections, count
            if autonomous:
                raise ValueError("Bounded search accepted an inequivalent machine")
            corrections += 1
        if trace in known:
            raise ValueError("The learner requested or mispredicted a known history")
        known.add(trace)
        state = 0
        for symbol in trace:
            state = reference[state][1 + symbol]
        outcome = reference[state][0] if observe is None else observe(trace)
        with path.open("a") as handle:
            print(outcome, *(alphabet[i] for i in trace), file=handle)
    raise ValueError("Inference exceeded the experiment budget")


def queue_full(trace):
    queue = Queue(maxsize=2)
    for action in trace:
        try:
            if action == 0:
                queue.put_nowait("item")
            else:
                queue.get_nowait()
        except (Full, Empty):
            pass
    return int(queue.full())


def check_queue(binary, directory):
    alphabet = ["put", "take"]
    reference = [[0, 1, 0], [0, 2, 0], [1, 2, 1]]
    counts = learn(binary, directory, alphabet, reference, autonomous=True, observe=queue_full)
    for prefix, goal, expected in [
        ("take", 1, ["put", "put"]),
        ("put take put", 1, ["put"]),
        ("put put", 0, ["take"]),
        ("put put", 1, []),
    ]:
        output = subprocess.check_output(
            [binary, "states-plan", directory / "observations", str(goal), prefix], text=True
        ).split()
        if output != ["plan", *expected]:
            raise ValueError(f"Unexpected queue plan {output}")
        actions = [alphabet.index(token) for token in [*prefix.split(), *output[1:]]]
        if queue_full(actions) != goal:
            raise ValueError("Plan failed on the real queue")
    live_log = directory / "queue.obs"
    oracle = [sys.executable, str(Path(__file__).resolve()), "--queue-oracle"]
    result = run_agent(binary, live_log, alphabet, 3, 1, ["put"], oracle, 100, 10)
    if result != {"states": 3, "queries": counts[0], "plan": ["put"], "observed": 1}:
        raise ValueError(f"Live agent failed: {result}")
    resume = run_agent(binary, live_log, alphabet, 3, 0, ["put", "put"], oracle, 0, 10)
    if resume != {"states": 3, "queries": 0, "plan": ["take"], "observed": 0}:
        raise ValueError(f"Resumed agent failed: {resume}")
    provisional = run_agent(binary, directory / "queue-unbounded.obs", alphabet, None, 1, [],
                            oracle, 100, 10)
    if provisional["plan"] != ["put", "put"] or provisional["observed"] != 1:
        raise ValueError(f"Goal-directed learning failed: {provisional}")
    early_log = directory / "queue-first-hit.obs"
    first = run_agent(binary, early_log, alphabet, None, 1, ["put"], oracle, 4, 10)
    if first["plan"] != ["put"] or first["queries"] != 4 or first["states"] is not None:
        raise ValueError(f"Goal reached on the budget boundary: {first}")
    # Resume from exactly the saved probes, then compare with a cold full run.
    resumed = run_agent(binary, early_log, alphabet, None, 1, ["put"], oracle, 100, 10,
                        finish_model=True)
    cold = run_agent(binary, directory / "queue-full.obs", alphabet, None, 1, ["put"], oracle, 100, 10,
                     finish_model=True)
    if not (resumed["states"] == cold["states"] == 3 and resumed["plan"] == cold["plan"] == ["put"]
            and first["queries"] + resumed["queries"] == cold["queries"]):
        raise ValueError(f"Saved goal evidence failed to resume: {resumed}, {cold}")
    empty = run_agent(binary, directory / "empty-prefix.obs", alphabet, None, 0, [], oracle, 1, 10)
    if empty["plan"] != [] or empty["observed"] != 0 or empty["queries"] != 1:
        raise ValueError(f"Missed initial goal: {empty}")
    print(f"Queue without state bound: {provisional}")
    print(f"Queue: {counts[0]} self-selected queries; four shortest plans executed")


def sqlite_readings(trace):
    # Report whether the row survives discarding pending work. Each episode
    # uses a fresh database. The observation reveals no transaction state.
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY)")
        for token in trace:
            if token == "insert":
                connection.execute("INSERT OR IGNORE INTO items VALUES (1)")
            elif token == "delete":
                connection.execute("DELETE FROM items")
            elif token == "commit":
                connection.commit()
            elif token == "rollback":
                connection.rollback()
            else:
                raise ValueError(token)
        visible = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        connection.rollback()
        durable = connection.execute("SELECT COUNT(*) FROM items").fetchone()[0]
        return {"visible": visible, "durable": durable, "pending_change": int(visible != durable)}
    finally:
        connection.close()


def check_sqlite(binary, directory):
    alphabet = ["insert", "delete", "commit", "rollback"]
    oracle = [sys.executable, str(Path(__file__).resolve()), "--sqlite-oracle"]
    log = directory / "sqlite.obs"
    learned = run_agent(binary, log, alphabet, 4, 1, [], oracle, 300, 10)
    undo = run_agent(binary, log, alphabet, 4, 0, ["insert", "commit", "delete", "rollback"],
                     oracle, 0, 10)
    if (learned["states"], learned["plan"], undo["plan"]) != (4, ["insert", "commit"],
                                                               ["delete", "commit"]):
        raise ValueError(f"SQLite transaction plan failed: {learned}, {undo}")
    prefix = ["insert", "commit"]
    trial_log = directory / "sqlite-goal.obs"
    repaired = run_agent(binary, trial_log, alphabet, None, 0, prefix, oracle, 300, 10)
    if repaired["observed"] != 0 or "1 insert commit" not in trial_log.read_text().splitlines():
        raise ValueError(f"Failed to learn from a real rejected SQLite plan: {repaired}")
    shared = directory / "sqlite-sensors.obs"
    oracle = [sys.executable, str(Path(__file__).resolve()), "--sqlite-sensors"]
    run_agent(binary, shared, alphabet, 4, 1, [], oracle, 300, 10, "durable")
    first_goal_log = shared.read_bytes()
    for sensor in ["visible", "pending_change"]:
        shared.write_bytes(first_goal_log)
        prefix = ["insert", "commit"]
        reused = run_agent(binary, shared, alphabet, 4, 1, prefix, oracle, 300, 10, sensor)
        cold = run_agent(binary, directory / (sensor + ".obs"), alphabet, 4, 1, prefix,
                         oracle, 300, 10, sensor)
        expected = [] if sensor == "visible" else ["delete"]
        if reused["plan"] != cold["plan"] or reused["plan"] != expected or reused["queries"] >= cold["queries"]:
            raise ValueError(f"Cross-goal transfer failed: {reused}, {cold}")
        print(f"SQLite {sensor}: {reused['queries']} additional queries vs {cold['queries']} cold")
    print(f"SQLite without state bound: {repaired}")
    print(f"SQLite: {learned['queries']} self-selected queries; "
          f"persisted and removed a row; {undo['queries']} new training queries on restart")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    binary = parser.parse_args().binary.resolve()
    rng = random.Random(5203)
    tasks = [(["tick", "clear"], [[int(s == 3), (s + 1) % 5, 0] for s in range(5)])]
    for size in range(3, 11):
        for _ in range(2):
            alphabet = ["red", "blue", "green"]
            tasks.append((alphabet, [[rng.randrange(2), *(rng.randrange(size) for _ in alphabet)]
                                      for _ in range(size)]))
    with tempfile.TemporaryDirectory() as directory:
        check_queue(binary, Path(directory))
        check_sqlite(binary, Path(directory))
        results = [learn(binary, Path(directory), alphabet, machine) for alphabet, machine in tasks]
        bounded = [learn(binary, Path(directory), alphabet, machine, autonomous=True)
                   for alphabet, machine in tasks[:5]]
    print(f"{len(bounded)} autonomous identifications; {sum(r[0] for r in bounded)} membership queries")
    print(f"{len(results)} equivalent machines; {sum(r[0] for r in results)} membership queries; "
          f"{sum(r[1] for r in results)} counterexamples; {max(r[2] for r in results)} states max")


if __name__ == "__main__":
    if sys.argv[1:] == ["--queue-oracle"]:
        actions = ["put", "take"]
        print(queue_full(tuple(actions.index(token) for token in json.load(sys.stdin))))
    elif sys.argv[1:] == ["--sqlite-oracle"]:
        print(sqlite_readings(json.load(sys.stdin))["durable"])
    elif sys.argv[1:] == ["--sqlite-sensors"]:
        print(json.dumps(sqlite_readings(json.load(sys.stdin))))
    else:
        main()
