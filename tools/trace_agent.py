"""Learn and plan against a resettable local program with binary observations."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile


def run_agent(binary, log, alphabet, bound, goal, prefix, oracle, budget, timeout, sensor=None):
    if not alphabet or any(not token or any(c.isspace() for c in token) for token in alphabet):
        raise ValueError("Events must be nonempty single tokens")
    if len(set(alphabet)) != len(alphabet) or any(token not in alphabet for token in prefix):
        raise ValueError("Duplicate alphabet entry or unknown prefix event")
    if sensor == "":
        raise ValueError("Sensor name must be nonempty")
    header = ("events " + " ".join(alphabet) if sensor is None else
              json.dumps({"format": "sensors-v1", "events": alphabet})) + "\n"
    try:
        with log.open("x", encoding="utf-8") as handle:
            handle.write(header)
    except FileExistsError:
        contents = log.read_text(encoding="utf-8")
        if not contents.startswith(header) or not contents.endswith("\n"):
            raise ValueError("Existing observation log has a different format, alphabet or incomplete line")
    with tempfile.TemporaryDirectory() as directory:
        projected = log if sensor is None else Path(directory) / "goal.obs"
        previous = {}
        if sensor is not None:
            with projected.open("w", encoding="utf-8") as out:
                print("events", *alphabet, file=out)
                for line in log.read_text(encoding="utf-8").splitlines()[1:]:
                    trace, values = json.loads(line)
                    if not isinstance(trace, list) or any(token not in alphabet for token in trace):
                        raise ValueError("Invalid trace in sensor log")
                    key = tuple(trace)
                    validate_snapshot(values, sensor, previous)
                    if key in previous and previous[key] != values:
                        raise ValueError("Conflicting sensor observations")
                    previous[key] = values
                    print(values[sensor], *trace, file=out)
        return learn_goal(binary, log, projected, alphabet, bound, goal, prefix, oracle,
                          budget, timeout, sensor, previous)


def validate_snapshot(values, sensor, previous):
    if (not isinstance(values, dict) or sensor not in values or
            any(type(value) is not int or value not in (0, 1) for value in values.values())):
        raise ValueError("Expected a JSON object with binary sensor readings including the goal sensor")
    if previous and values.keys() != next(iter(previous.values())).keys():
        raise ValueError("Sensor names changed during learning")


def learn_goal(binary, log, projected, alphabet, bound, goal, prefix, oracle,
               budget, timeout, sensor, previous):
    def heed(*args):
        return subprocess.run([binary, *args], text=True, capture_output=True, check=True,
                              timeout=timeout).stdout.strip()

    def observe(trace):
        # A fresh oracle process starts from its reset state for each query.
        result = subprocess.run(oracle, input=json.dumps(trace) + "\n", text=True,
                                capture_output=True, check=True, timeout=timeout).stdout.strip()
        if sensor is not None:
            values = json.loads(result)
            validate_snapshot(values, sensor, previous)
            key = tuple(trace)
            if key in previous:
                if previous[key] != values:
                    raise ValueError("Conflicting sensor observations")
            else:
                with log.open("a", encoding="utf-8") as handle:
                    print(json.dumps([trace, values]), file=handle)
                previous[key] = values
                with projected.open("a", encoding="utf-8") as handle:
                    print(values[sensor], *trace, file=handle)
            return values[sensor]
        if result not in ("0", "1"):
            raise ValueError(f"Expected one binary observation, received {result!r}")
        return int(result)

    count = 0
    search_bound = 1

    def save_observation(trace):
        nonlocal count
        if count >= budget:
            raise ValueError("Experiment budget reached; observations saved for resumption")
        label = observe(trace)
        if sensor is None:
            with log.open("a", encoding="utf-8") as handle:
                print(label, *trace, file=handle)
        count += 1
        return label

    while True:
        result = heed("states", projected) if bound is None else heed("states-check", projected, str(bound))
        if result.startswith("consistent states "):
            states = int(result.splitlines()[0].split()[-1])
            proposal = heed("states-plan", projected, str(goal), " ".join(prefix))
            if proposal == "Goal unreachable in learned model.":
                if bound is not None:
                    return {"states": states, "queries": count, "plan": None}
                # A provisional model can wrongly predict that a goal is
                # impossible. Seek a distinguishing observation at increasing depth.
                search_bound = max(search_bound, states)
                result = heed("states-check", projected, str(search_bound))
                if result.startswith("consistent states "):
                    search_bound += 1
                    continue
            else:
                fields = proposal.split()
                if not fields or fields[0] != "plan" or any(s not in alphabet for s in fields[1:]):
                    raise ValueError(proposal)
                plan = fields[1:]
                trace = prefix + plan
                if bound is None:
                    label = save_observation(trace)
                    if label != goal:
                        continue
                else:
                    label = observe(trace)
                    if label != goal:
                        raise ValueError("Plan disagreed with the observed outcome on replay")
                return {"states": states, "queries": count, "plan": plan, "observed": label}
        fields = result.split()
        if not fields or fields[0] != "observe" or any(s not in alphabet for s in fields[1:]):
            raise ValueError(result)
        save_observation(fields[1:])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("--events", nargs="+", required=True)
    parser.add_argument("--bound", type=int, help="Optional reachable-state bound for conformance checking")
    parser.add_argument("--goal", choices=(0, 1), type=int, required=True)
    parser.add_argument("--sensor", help="Select a goal field in a JSON object of binary readings")
    parser.add_argument("--prefix", nargs="*", default=[])
    parser.add_argument("--budget", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--oracle", nargs=argparse.REMAINDER, required=True,
                        help="Local executable and arguments; reads a JSON event list on stdin")
    args = parser.parse_args()
    if not args.oracle or (args.bound is not None and args.bound < 1) or args.budget < 0 or args.timeout <= 0:
        parser.error("Supply an oracle command, positive bound and timeout, and nonnegative budget")
    result = run_agent(args.binary.resolve(), args.log, args.events, args.bound, args.goal,
                       args.prefix, args.oracle, args.budget, args.timeout, args.sensor)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
