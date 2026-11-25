"""Use a learned Heed transition table to propose plans in a renamed environment."""
import argparse
from collections import deque
from math import factorial
import json
from pathlib import Path
from itertools import chain, islice, permutations, product
import sqlite3
import subprocess
import tempfile


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

def distinguish(reference, hypothesis, starts=(0, 0)):
    """Shortest differing output trace, or None if all reachable outputs agree."""
    pending = deque([(*starts, ())])
    seen = {starts}
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


def repair_transfer(table, actions, examples, observe, budget, allow_split=False):
    """Identify target behavior within all bijections and zero/one edge changes."""
    sensor = goal_sensor(examples)
    n, k = len(table), len(actions)
    if not n or not k or len(set(actions)) != k or any(len(row) != k + 1 for row in table):
        raise ValueError("Repair requires matching source and target alphabet sizes")
    if k > 6 or factorial(k) * (1 + n * k * (n - 1 + int(allow_split))) > 10000:
        raise ValueError("Repair exceeds the 10000-candidate search limit")
    if budget < 0:
        raise ValueError("Expected a nonnegative episode budget")
    candidates = {}
    for order in permutations(range(1, k + 1)):
        base = tuple((row[0], *(row[i] for i in order)) for row in table)
        candidates[base] = 0
        for state, row in enumerate(base):
            for col in range(1, k + 1):
                if allow_split:
                    # Enter a copy of this state on this action. Its next
                    # action follows the original row, including self-loops.
                    fork = row[:col] + (n,) + row[col + 1:]
                    variant = base[:state] + (fork,) + base[state + 1:] + (row,)
                    candidates.setdefault(variant, 1)
                for target in range(n):
                    if row[col] != target:
                        changed = row[:col] + (target,) + row[col + 1:]
                        variant = base[:state] + (changed,) + base[state + 1:]
                        candidates.setdefault(variant, 1)

    return identify_candidates(candidates, actions, sensor, observe, budget)


def identify_candidates(candidates, actions, sensor, observe, budget):
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


def composed_candidates(source, actions, log):
    """Compose an old-state redirect and a split, filtering on target evidence."""
    n, k = len(source), len(actions)
    edges = n * k
    if factorial(k) * edges * (edges - 1) * (n - 1) > 50000:
        return {}
    indices = {action: i for i, action in enumerate(actions)}
    evidence = [(tuple(indices[a] for a in trace), value) for trace, value in log.items()]
    candidates = {}
    for order in permutations(range(1, k + 1)):
        base = tuple((row[0], *(row[i] for i in order)) for row in source)
        for state, row in enumerate(base):
            for col in range(1, k + 1):
                for target in range(n):
                    if target == row[col]:
                        continue
                    redirect = row[:col] + (target,) + row[col + 1:]
                    edited = base[:state] + (redirect,) + base[state + 1:]
                    for parent, original in enumerate(edited):
                        for event in range(1, k + 1):
                            if (parent, event) == (state, col):
                                continue
                            fork = original[:event] + (n,) + original[event + 1:]
                            model = edited[:parent] + (fork,) + edited[parent + 1:] + (original,)
                            if all(predict(model, trace) == y for trace, y in evidence):
                                candidates[model] = 2
    return candidates


def access_paths(table, actions):
    paths = {0: ()}
    queue = deque([0])
    while queue:
        state = queue.popleft()
        for action, successor in zip(actions, table[state][1:]):
            if successor not in paths:
                paths[successor] = paths[state] + (action,)
                queue.append(successor)
    return paths


def check_proposal(table, actions, bound, measurement):
    """State cover plus distinguishing suffixes, for complete resettable machines."""
    paths = access_paths(table, range(len(actions)))
    if len(paths) != len(table) or len(table) > bound:
        return False
    suffixes = {()}
    for left in range(len(table)):
        for right in range(left):
            probe = distinguish(table, table, (left, right))
            if probe is None:
                return False
            suffixes.add(probe)
    suffixes = sorted(suffixes)
    # Every prefix, followed by up to bound - n + 1 inputs and a suffix.
    for depth in range(bound - len(table) + 2):
        for word in product(range(len(actions)), repeat=depth):
            for prefix in paths.values():
                for tail in suffixes:
                    trace = prefix + word + tail
                    observed = measurement(tuple(actions[i] for i in trace))
                    if observed is None:
                        return None
                    if predict(table, trace) != observed:
                        return False
    return True


def extract_pattern(result):
    """Abstract a verified split by an access trace and observable preconditions."""
    if not result.get("local_model_verified") or result.get("local_edits") != 1 or not result.get("split"):
        raise ValueError("Saving a pattern requires a verified single split")
    split = result["split"]
    events = result["events"]
    table = result["table"]
    parent, clone = split["state"], split["new_state"]
    prefix = split["histories"][0]
    event = split["event"]
    # Bind by first occurrence, so neither environment names nor state IDs persist.
    roles = list(dict.fromkeys([*prefix, event]))
    successor = table[clone][1 + events.index(event)]
    return {"format": "split-v1", "access": [roles.index(a) for a in prefix],
            "event": roles.index(event), "before": table[parent][0], "after": table[successor][0]}


def instantiate_pattern(pattern, source, actions):
    if not isinstance(pattern, dict) or pattern.get("format") != "split-v1":
        raise ValueError("Unknown repair pattern format")
    prefix, event = pattern.get("access"), pattern.get("event")
    if not isinstance(prefix, list) or any(type(x) is not int or x < 0 for x in [*prefix, event]):
        raise ValueError("Invalid repair pattern roles")
    roles = list(dict.fromkeys([*prefix, event]))
    if roles != list(range(len(roles))) or any(pattern.get(k) not in (0, 1) for k in ("before", "after")):
        raise ValueError("Invalid repair pattern conditions")
    k = len(actions)
    if k > 6 or len(roles) > k:
        return {}
    if factorial(k) * min(len(source) * k, factorial(k) // factorial(k - len(roles))) > 10000:
        return {}
    candidates = {}
    seen = set()
    for binding in permutations(range(1, k + 1), len(roles)):
        state = 0
        for role in prefix:
            state = source[state][binding[role]]
        col = binding[event]
        row = source[state]
        if row[0] != pattern["before"] or source[row[col]][0] != pattern["after"]:
            continue
        if (state, col) in seen:
            continue
        seen.add((state, col))
        copied = [tuple(r) for r in source]
        copied[state] = (*row[:col], len(source), *row[col + 1:])
        copied.append(tuple(row))
        for order in permutations(range(1, k + 1)):
            model = tuple((r[0], *(r[i] for i in order)) for r in copied)
            candidates[model] = 1
    return candidates


def grow_transfer(binary, source, actions, examples, observe, bound, budget, pattern=None):
    """Reuse repair probes; learn a larger table and verify a lower-bound witness."""
    if bound < len(source) or budget < 0:
        raise ValueError("Expected a bound at least the source size and a nonnegative budget")
    if any(not token or any(c.isspace() for c in token) for token in actions):
        raise ValueError("Native event names must be nonempty single tokens")
    sensor = goal_sensor(examples)
    log = {}

    def measurement(trace):
        key = tuple(trace)
        if key not in log:
            value = observe(list(key))[sensor]
            if value not in (0, 1):
                raise ValueError("Expected a binary target observation")
            log[key] = int(value)
        return log[key]

    def bounded_measurement(trace):
        if trace not in log and len(log) >= budget:
            return None
        return measurement(trace)

    if any(len(row) != len(actions) + 1 for row in source) or len(set(actions)) != len(actions):
        raise ValueError("Expected distinct actions and matching source alphabet")
    def probe(trace):
        return {sensor: measurement(trace)}

    reused = False
    matches = []
    if pattern is not None and bound > len(source):
        patterns = pattern if isinstance(pattern, list) else [pattern]
        origins = {}
        for index, saved in enumerate(patterns):
            for model in instantiate_pattern(saved, source, actions):
                origins.setdefault(model, []).append(index)
                if len(origins) > 10000:
                    raise ValueError("Pattern collection exceeds 10000 candidate models")
        # Vote once per distinct table. A repeated pattern must not change probe order.
        candidates = dict.fromkeys(sorted(origins), 1)
        prior = identify_candidates(candidates, actions, sensor, probe, budget)
        table = prior.get("table")
        reused = table is not None and check_proposal(table, actions, bound, bounded_measurement)
        if reused:
            matches = sorted({index for model, indices in origins.items()
                              if distinguish(table, model) is None for index in indices})
        if reused is None:
            return {"status": "budget exhausted", "target_episodes": len(log)}
    if reused:
        repair = prior
    else:
        repair = repair_transfer(source, actions, examples, probe, budget - len(log),
                                 allow_split=bound > len(source))
    initial = len(log)
    table = repair.get("table")
    local = reused or (table is not None and check_proposal(table, actions, bound, bounded_measurement))
    if local is None:
        return {"status": "budget exhausted", "target_episodes": len(log)}
    edits = repair.get("minimum_edits") if local else None
    if not local and bound > len(source) and len(log) < budget:
        candidates = composed_candidates(source, actions, log)
        combined = identify_candidates(candidates, actions, sensor, lambda tr: {sensor: measurement(tr)},
                                       budget - len(log))
        table = combined.get("table")
        local = table is not None and check_proposal(table, actions, bound, bounded_measurement)
        if local is None:
            return {"status": "budget exhausted", "target_episodes": len(log)}
        if local:
            edits = 2
    if not local:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations"
            with path.open("w", encoding="utf-8") as out:
                print("events", *actions, file=out)
                for trace, value in log.items():
                    print(value, *trace, file=out)
            while True:
                reply = subprocess.check_output([binary, "states-check", path, str(bound)],
                                                text=True, timeout=30).splitlines()
                fields = reply[0].split()
                if fields[:2] == ["consistent", "states"]:
                    table = [tuple(map(int, row.split())) for row in reply[1:]]
                    break
                if fields[:1] != ["observe"]:
                    return {"status": reply[0], "target_episodes": len(log)}
                trace = tuple(fields[1:])
                if trace in log:
                    raise ValueError("Repeated native query")
                if len(log) == budget:
                    return {"status": "budget exhausted", "target_episodes": len(log)}
                value = measurement(trace)
                with path.open("a", encoding="utf-8") as out:
                    print(value, *trace, file=out)

    paths = access_paths(table, actions)
    # For each pair, execute the same continuation from both histories.
    # Different measured bits certify that the two histories require distinct states.
    witnesses = []
    if len(table) > len(source):
        states = list(paths)[:len(source) + 1]
        for i, left in enumerate(states):
            for right in states[i+1:]:
                suffix = distinguish(table, table, (left, right))
                if suffix is None:
                    raise ValueError("Inferred states are observationally equivalent")
                tail = tuple(actions[a] for a in suffix)
                traces = (paths[left] + tail, paths[right] + tail)
                if len(log) + len(set(traces) - log.keys()) > budget:
                    return {"status": "budget exhausted", "target_episodes": len(log)}
                bits = [measurement(trace) for trace in traces]
                if bits[0] == bits[1]:
                    raise ValueError("Target refuted proposed state distinction")
                witnesses.append([paths[left], paths[right], tail, bits])
    split = None
    if local and len(table) == len(source) + 1:
        copy = len(source)
        parent, event = next((state, event) for state, row in enumerate(table[:copy])
                             for event, successor in zip(actions, row[1:]) if successor == copy)
        split = {"state": parent, "event": event, "new_state": copy,
                 "histories": [paths[parent], paths[copy]]}
    return {"status": "checked under supplied bound", "events": actions, "table": table,
            "source_states": len(source), "target_states": len(table), "witnesses": witnesses,
            "local_model_verified": local, "pattern_verified": reused, "matching_patterns": matches, "local_edits": edits, "split": split, "repair_status": repair["status"],
            "repair_episodes": initial, "target_episodes": len(log)}


def choose_diagnostic(records):
    """Compare the empirical cost of one paid probe to the best unconditional policy."""
    if not records:
        return None
    tasks = sum(r[3] for r in records)
    best = min(sum(r[i] for r in records) for i in (1, 2))
    choice = None
    for index in range(len(records[0][0])):
        groups = [[r for r in records if r[0][index] == bit] for bit in "01"]
        if any(sum(r[3] for r in group) < 2 for group in groups):
            continue
        totals = [(sum(r[1] for r in group), sum(r[2] for r in group)) for group in groups]
        cost = tasks + sum(min(pair) for pair in totals)
        if cost < best:
            best = cost
            choice = index, [library < ordinary for ordinary, library in totals]
    return choice


def cost_aware_transfer(binary, source, actions, examples, observe, bound, budget, patterns, history, diagnostic=False,
                        *, prefer_library_on_tie=False):
    """Choose from prior paired costs, then measure both policies on the verified table."""
    sensor = goal_sensor(examples)
    # Action names and target outcomes are deliberately absent. Keep baseline
    # column order: probe tie-breaking can affect the costs being predicted.
    key = json.dumps([1, source, bound, budget, sorted(json.dumps(p, sort_keys=True) for p in patterns)])
    probes = list(islice(chain.from_iterable(product(range(len(actions)), repeat=n)
                                            for n in range(4)), 256)) if diagnostic else []
    records = []
    with sqlite3.connect(history) as db:
        db.execute("CREATE TABLE IF NOT EXISTS costs "
                   "(context TEXT PRIMARY KEY, tasks INTEGER, ordinary INTEGER, library INTEGER)")
        row = db.execute("SELECT tasks, ordinary, library FROM costs WHERE context=?", (key,)).fetchone()
        if diagnostic:
            db.execute("CREATE TABLE IF NOT EXISTS diagnostic_cases "
                       "(context TEXT, bits TEXT, ordinary INTEGER, library INTEGER, tasks INTEGER, "
                       "PRIMARY KEY(context,bits))")
            records = db.execute("SELECT bits, ordinary, library, tasks FROM diagnostic_cases WHERE context=?",
                                 (key,)).fetchall()
    consult = row is not None and (row[2] < row[1] or (row[2] == row[1] and prefer_library_on_tie))
    choice = choose_diagnostic(records) if budget > 0 else None
    early = None
    if choice is not None:
        index, policies = choice
        trace = [actions[i] for i in probes[index]]
        bit = observe(trace)[sensor]
        if bit not in (0, 1):
            raise ValueError("Expected binary diagnostic observation")
        consult = policies[int(bit)]
        early = {"trace": trace, "value": int(bit)}
        ones = sum(count for bits, _, _, count in records if bits[index] == "1")
        total = sum(r[3] for r in records)
        if 2 * ones != total:
            early["predicted"] = int(2 * ones > total)
    repair_budget = budget - int(early is not None)
    used = patterns if consult else None
    result = grow_transfer(binary, source, actions, examples, observe, bound, repair_budget, used)
    repair_cost = result["target_episodes"]
    result["target_episodes"] += int(early is not None)
    if diagnostic:
        result["early_observation"] = early
    result["strategy"] = "library" if consult else "ordinary"
    result["prior_tasks"] = row[0] if row else 0
    if "table" not in result:
        return result
    indices = {action: i for i, action in enumerate(actions)}
    def replay(trace):
        return {sensor: predict(result["table"], [indices[a] for a in trace])}
    other = grow_transfer(binary, source, actions, examples, replay, bound, budget,
                          None if consult else patterns)
    # An unfinished alternative has unknown completion cost. Its cost so
    # far is a lower bound; leave this pair out of the historical averages.
    if "table" not in other:
        return result
    actual, alternate = repair_cost, other["target_episodes"]
    ordinary, library = (alternate, actual) if consult else (actual, alternate)
    with sqlite3.connect(history) as db:
        db.execute("INSERT INTO costs VALUES (?,1,?,?) ON CONFLICT(context) DO UPDATE SET "
                   "tasks=tasks+1, ordinary=ordinary+excluded.ordinary, library=library+excluded.library",
                   (key, ordinary, library))
        if diagnostic:
            bits = "".join(str(predict(result["table"], trace)) for trace in probes)
            db.execute("INSERT INTO diagnostic_cases VALUES (?,?,?,?,1) ON CONFLICT(context,bits) "
                       "DO UPDATE SET tasks=tasks+1, ordinary=ordinary+excluded.ordinary, "
                       "library=library+excluded.library", (key, bits, ordinary, library))
    result["paired_costs"] = {"ordinary": ordinary, "library": library}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("source_log", type=Path, help="Single-output native Heed log")
    parser.add_argument("examples", type=Path, help="JSON array of [target sensor object, success bit]")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--grow-bound", type=int, help="Check for additional states under a supplied target bound")
    mode.add_argument("--repair", action="store_true", help="Identify a renamed table with up to one changed transition")
    parser.add_argument("--save-pattern", type=Path, help="Write a verified single-split pattern to a new file")
    parser.add_argument("--use-pattern", action="append", type=Path, help="Try a saved pattern on the current source table")
    parser.add_argument("--events", nargs="+", required=True)
    parser.add_argument("--diagnostic", action="store_true", help="Learn whether to buy one observation before choosing a strategy")
    parser.add_argument("--cost-history", type=Path, help="Choose whether to use saved patterns from previous experiment counts")
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--budget", type=int, default=100)
    parser.add_argument("--oracle", nargs=argparse.REMAINDER, required=True)
    args = parser.parse_args()
    if (args.use_pattern or args.save_pattern) and args.grow_bound is None:
        parser.error("Repair patterns require --grow-bound")
    if args.diagnostic and not args.cost_history:
        parser.error("--diagnostic requires --cost-history")
    if args.cost_history and not args.use_pattern:
        parser.error("--cost-history requires --use-pattern")
    if not args.oracle:
        parser.error("Supply a resettable local oracle command")
    examples = json.loads(args.examples.read_text(encoding="utf-8"))

    def observe(trace):
        result = subprocess.run(args.oracle, input=json.dumps(trace), capture_output=True,
                                text=True, timeout=30, check=True)
        return json.loads(result.stdout)

    table = read_table(args.binary.resolve(), args.source_log)
    if args.grow_bound is not None:
        pattern = [json.loads(path.read_text()) for path in args.use_pattern] if args.use_pattern else None
        params = (args.binary.resolve(), table, args.events, examples, observe, args.grow_bound, args.budget)
        if args.cost_history:
            result = cost_aware_transfer(*params, pattern, args.cost_history, args.diagnostic)
        else:
            result = grow_transfer(*params, pattern)
        if args.save_pattern:
            learned = extract_pattern(result)
            with args.save_pattern.open("x", encoding="utf-8") as out:
                print(json.dumps(learned), file=out)
        print(json.dumps(result))
        return
    if args.repair:
        print(json.dumps(repair_transfer(table, args.events, examples, observe, args.budget)))
        return
    plan, episodes = try_transfer(table, args.events, examples, observe, args.depth, args.budget)
    print(json.dumps({"plan": plan, "target_episodes": episodes}))


if __name__ == "__main__":
    main()
