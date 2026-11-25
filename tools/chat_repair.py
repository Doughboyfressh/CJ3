"""Exercise the research repair selector on a named, resettable finite-state target."""
import json
from pathlib import Path
import re
import sqlite3
import sys

from trace_transfer import cost_aware_transfer, predict


def run(name, prefer_library_on_tie):
    if not re.fullmatch("[a-z]+", name):
        raise ValueError("Use a lowercase task name.")
    path = Path(f"out/repair_{name}.json")
    if not path.exists():
        path = Path("examples/repair") / (name + ".json")
    config = json.loads(path.read_text(encoding="utf-8"))
    actions = config["actions"]
    if not isinstance(actions, list) or not actions or len(set(actions)) != len(actions):
        raise ValueError("Provide distinct event names.")
    target = config["target"]
    bound = config["bound"]
    if not 1 <= len(target) <= bound:
        raise ValueError("Target size exceeds the state bound.")
    for table in (target, config["source"]):
        if not table or any(len(row) != len(actions) + 1 or type(row[0]) != int or
                            row[0] not in (0, 1) or any(type(i) != int or not 0 <= i < len(table)
                                                        for i in row[1:]) for row in table):
            raise ValueError("Invalid binary transition table.")
    indices = {action: i for i, action in enumerate(actions)}
    measured = 0

    def observe(trace):
        nonlocal measured
        measured += 1
        return {"goal": predict(target, [indices[action] for action in trace])}

    binary = Path("out/heed.exe" if sys.platform == "win32" else "out/heed").resolve()
    if not binary.is_file():
        raise ValueError("Build examples/native/heed.pi before running repair tasks.")
    result = cost_aware_transfer(binary, config["source"], actions,
                                 [({"goal": 0}, 0), ({"goal": 1}, 1)], observe,
                                 bound, config["budget"], config["patterns"],
                                 "out/repair_history.sqlite", diagnostic=True,
                                 prefer_library_on_tie=prefer_library_on_tie)
    if measured != result["target_episodes"]:
        raise ValueError("Reported experiment count disagrees with the target observer.")
    early = result["early_observation"]
    feedback = "none"
    if early and "predicted" in early:
        feedback = str(int(early["predicted"] != early["value"]))
    print(feedback)
    print(f'{result["strategy"]} repair; {result["status"]}; {measured} target observations; '
          f'{result["prior_tasks"]} prior verified comparisons.')
    if early:
        print("Paid diagnostic:", " ".join(early["trace"]) or "(reset)", "->", early["value"])
    if "paired_costs" in result:
        costs = result["paired_costs"]
        print(f'Repair-only paired costs: ordinary {costs["ordinary"]}, library {costs["library"]}.')


if __name__ == "__main__":
    try:
        run(sys.argv[1], sys.argv[2:] == ["library"])
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        sys.exit(str(exc))
