"""Compare transferred and fresh plans across all action renamings of a file store."""
import argparse
import json
import subprocess
from itertools import permutations, product
from pathlib import Path
import sys
import tempfile

from trace_agent import run_agent
from trace_transfer import cost_aware_transfer, extract_pattern, distinguish, grow_transfer, goal_sensor, predict, read_table, repair_transfer, try_transfer
from trace_inference import learn


def file_readings(trace, roles, consume=False, confirm=False):
    # A draft bit is copied to or restored from a separate published file.
    with tempfile.TemporaryDirectory() as directory:
        draft, published = (Path(directory) / name for name in ("draft", "published"))
        draft.write_bytes(b"0")
        published.write_bytes(b"0")
        awaiting_confirmation = False
        for token in trace:
            role = roles[token]
            if role != "publish":
                awaiting_confirmation = False
            if role == "mark":
                draft.write_bytes(b"1")
            elif role == "erase":
                draft.write_bytes(b"0")
            elif role == "publish":
                if (confirm and not awaiting_confirmation and
                        draft.read_bytes() == b"1" and published.read_bytes() == b"0"):
                    awaiting_confirmation = True
                else:
                    published.write_bytes(draft.read_bytes())
                    awaiting_confirmation = False
            elif role == "restore":
                move = consume and draft.read_bytes() == b"0" and published.read_bytes() == b"1"
                draft.write_bytes(published.read_bytes())
                if move:
                    published.write_bytes(b"0")
        left, right = int(draft.read_bytes()), int(published.read_bytes())
        return {"s0": left != right, "s1": left, "s2": right}


def reference_table(names, consume):
    # Independent specification using state bits (draft, published).
    result = []
    for state in range(4):
        draft, published = divmod(state, 2)
        successors = {"mark": (1, published), "erase": (0, published),
                      "publish": (draft, draft), "restore": (published, published)}
        if consume and state == 1:
            successors["restore"] = (1, 0)
        result.append((published, *(2 * successors[n][0] + successors[n][1] for n in names)))
    return result


def check_repair(binary, directory, table, actions, examples):
    adapted = cold = unchanged = heldout = 0
    for names in permutations(["mark", "erase", "publish", "restore"]):
        roles = dict(zip(actions, names))
        for consume in (False, True):
            samples = set()

            def observe(trace):
                samples.add(tuple(trace))
                return file_readings(trace, roles, consume)

            result = repair_transfer(table, actions, examples, observe, 100)
            reference = reference_table(names, consume)
            if result["status"] != "identified within family" or result["minimum_edits"] != int(consume):
                raise AssertionError(result)
            if distinguish(reference, result["table"]) is not None:
                raise AssertionError("Identified table diverges from target specification")
            if consume:
                adapted += result["target_episodes"]
                cost, _, _ = learn(binary, directory, actions, reference, autonomous=True,
                                   observe=lambda tr: file_readings([actions[i] for i in tr], roles, True)["s2"])
                cold += cost
                # Exercise the changed edge, then republish; both probes use
                # real files independently of the transition-table reference.
                prefix = tuple(actions[names.index(role)] for role in ("mark", "publish", "erase", "restore"))
                for suffix in product(actions, repeat=3):
                    trace = prefix + suffix
                    if trace not in samples:
                        actual = file_readings(trace, roles, True)["s2"]
                        if predict(result["table"], [actions.index(a) for a in trace]) != actual:
                            raise AssertionError("Held-out file behavior differs")
                        heldout += 1
                if file_readings(prefix, roles, True)["s2"] != 0:
                    raise AssertionError("Changed restore should consume the published bit")
                # Choose a recovery action by prediction, then execute it.
                plan = next(a for a in actions if predict(result["table"],
                            [actions.index(e) for e in (*prefix, a)]))
                if file_readings((*prefix, plan), roles, True)["s2"] != 1:
                    raise AssertionError("Learned recovery plan failed")
            else:
                unchanged += result["target_episodes"]
    if heldout == 0:
        raise AssertionError("No held-out queries tested")
    print(f"24 changed stores: repair {adapted}, fresh bounded Heed {cold} episodes; "
          f"{heldout} held-out file checks; 24 unchanged controls: {unchanged} episodes")


def check_growth(binary, directory, source, actions, examples):
    adapted = fresh = combined_total = combined_fresh = 0
    for names in permutations(["mark", "erase", "publish", "restore"]):
        roles = dict(zip(actions, names))
        def observe(trace):
            return file_readings(trace, roles, confirm=True)
        reference = reference_table(names, False)
        publish = 1 + names.index("publish")
        reference[4:] = [reference[2]]
        row = list(reference[2])
        row[publish] = 4
        reference[2] = tuple(row)
        result = grow_transfer(binary, source, actions, examples, observe, 5, 1000)
        if (not result.get("local_model_verified") or result.get("target_states") != 5 or len(result["witnesses"]) != 10
                or distinguish(reference, result["table"]) is not None):
            raise AssertionError(result)
        split = result["split"]
        if roles[split["event"]] != "publish":
            raise AssertionError("The split should distinguish a publication attempt")
        predictions = [observe(history + (split["event"],))["s2"] for history in split["histories"]]
        if predictions != [0, 1]:
            raise AssertionError("Reported split failed on the target")
        for left, right, tail, bits in result["witnesses"]:
            if bits != [observe(left + tail)["s2"], observe(right + tail)["s2"]] or bits[0] == bits[1]:
                raise AssertionError("State-count witness failed independent replay")
        target_actions = [actions[names.index(a)] for a in ("mark", "publish", "publish")]
        for length, expected in enumerate([0, 0, 0, 1]):
            trace = target_actions[:length]
            if predict(result["table"], [actions.index(a) for a in trace]) != expected:
                raise AssertionError("Incorrect confirmation plan")
        adapted += result["target_episodes"]
        cost, _, _ = learn(binary, directory, actions, reference, autonomous=True,
                           observe=lambda tr: observe([actions[i] for i in tr])["s2"])
        fresh += cost
        combined = grow_transfer(binary, source, actions, examples,
                                 lambda tr: file_readings(tr, roles, consume=True, confirm=True), 5, 1000)
        both = reference_table(names, True)
        both.append(both[2])
        row = list(both[2])
        row[publish] = 4
        both[2] = tuple(row)
        if combined.get("local_edits") != 2 or distinguish(both, combined["table"]) is not None:
            raise AssertionError("Failed to identify both changes")
        sequence = ["mark", "publish", "publish", "erase", "restore", "publish", "publish"]
        trace = []
        for role, expected in zip(sequence, (0, 0, 1, 1, 0, 0, 1)):
            trace.append(actions[names.index(role)])
            predicted = predict(combined["table"], [actions.index(a) for a in trace])
            if predicted != expected or file_readings(trace, roles, True, True)["s2"] != expected:
                raise AssertionError("Combined publish, restore and recovery failed")
        combined_total += combined["target_episodes"]
        cost, _, _ = learn(binary, directory, actions, both, autonomous=True,
                           observe=lambda tr: file_readings([actions[i] for i in tr], roles, True, True)["s2"])
        combined_fresh += cost
    control = grow_transfer(binary, source, actions, examples,
                            lambda tr: file_readings(tr, roles), 5, 1000)
    if control.get("target_states") != 4 or control["witnesses"]:
        raise AssertionError(control)
    # Inverted outputs lie outside both local edit families.
    def inverted(trace):
        return {"s2": 1 - file_readings(trace, roles)["s2"]}
    fallback = grow_transfer(binary, source, actions, examples, inverted, 5, 1000)
    flipped = [(1 - row[0], *row[1:]) for row in reference_table(names, False)]
    if fallback.get("local_model_verified") is not False or distinguish(flipped, fallback["table"]) is not None:
        raise AssertionError("Out-of-family target failed full inference")
    print(f"24 combined stores: {combined_total} target episodes vs {combined_fresh} fresh")
    print(f"24 confirmation stores: {adapted} target episodes vs {fresh} fresh; "
          "240 pairwise witnesses replayed; unchanged control has 4 states")


def check_pattern(binary, directory, actions, examples):
    # Generate and serialize the donor pattern in a separate CLI process.
    labels = directory / "donor-labels.json"
    labels.write_text(json.dumps(examples))
    saved = directory / "split.json"
    names = ["restore", "mark", "publish", "erase"]
    command = [sys.executable, str(Path(__file__).with_name("trace_transfer.py")), binary,
               directory / "source.obs", labels, "--grow-bound", "5", "--budget", "300",
               "--save-pattern", saved, "--events", *actions, "--oracle", sys.executable,
               __file__, "--confirm-sensors", *names]
    donor = json.loads(subprocess.check_output(command, text=True, timeout=60))
    pattern = json.loads(saved.read_text())
    if pattern != extract_pattern(donor):
        raise AssertionError("Pattern did not survive serialization")

    replay = command.copy()
    pos = replay.index("--save-pattern")
    replay[pos:pos+2] = ["--use-pattern", saved, "--use-pattern", saved]
    duplicate = json.loads(subprocess.check_output(replay, text=True, timeout=60))
    if duplicate["matching_patterns"] != [0, 1]:
        raise AssertionError("Equivalent saved patterns must remain ambiguous")

    # An independent ticket dispenser has no draft, published bit, or rollback.
    symbols = ["a", "b", "c"]
    goal = [({"ticket": 0}, 0), ({"ticket": 1}, 1)]
    base = [(0, 1, 0, 0), (0, 1, 2, 0), (1, 2, 2, 0)]
    learn(binary, directory, symbols, base, autonomous=True)
    learned_base = read_table(binary, directory / "observations")
    # A four-state lamp requires two shutdown commands when fully lit.
    # Its dim state and fourth command are absent from the ticket dispenser.
    lamp_actions = ["power", "light", "off", "dim"]
    lamp = [(0, 1, 0, 0, 0), (0, 1, 2, 0, 1), (1, 2, 2, 0, 3), (0, 3, 2, 0, 2)]
    confirmed_lamp = [*lamp[:2], (1, 2, 2, 4, 3), lamp[3], lamp[2]]
    learn(binary, directory, lamp_actions, lamp, autonomous=True)
    lamp_source = read_table(binary, directory / "observations")
    def lamp_observe(trace):
        return {"lit": predict(confirmed_lamp, [lamp_actions.index(a) for a in trace])}
    lamp_result = grow_transfer(binary, lamp_source, lamp_actions, [({"lit": 0}, 0), ({"lit": 1}, 1)],
                                lamp_observe, 5, 300)
    library = [pattern, extract_pattern(lamp_result)]
    policy_totals = [0, 0, 0]
    strategies = []
    heldout = [0, 0, 0]
    selected = generic = prior_known = none = none_generic = 0
    warm = cold = wins = 0
    for names in permutations(["load", "issue", "clear"]):
        def observe(trace, confirm=True, delayed_clear=False):
            loaded = issued = pending = False
            for token in trace:
                op = names[symbols.index(token)]
                if op == "clear":
                    if issued and delayed_clear and not pending:
                        pending = True
                    else:
                        loaded = issued = pending = False
                elif op == "load":
                    loaded, pending = True, False
                elif loaded and not issued:
                    issued = pending or not confirm
                    pending = not issued
                else:
                    pending = False
            return {"ticket": int(issued)}

        reference = [(0, 1, 0, 0), (0, 1, 3, 0), (1, 2, 2, 0), (0, 1, 2, 0)]
        order = [["load", "issue", "clear"].index(name) + 1 for name in names]
        expected = [(r[0], *(r[i] for i in order)) for r in reference]
        result = grow_transfer(binary, learned_base, symbols, goal, observe, 4, 300, pattern)
        baseline = grow_transfer(binary, learned_base, symbols, goal, observe, 4, 300)
        if (not result["pattern_verified"] or distinguish(expected, result["table"]) is not None
                or distinguish(expected, baseline["table"]) is not None):
            raise AssertionError("Incorrect ticket dispenser model")
        warm += result["target_episodes"]
        cold += baseline["target_episodes"]
        wins += result["target_episodes"] < baseline["target_episodes"]
        retract = [*base[:2], (1, 2, 2, 3), base[2]]
        for idx, ref in enumerate([reference, retract, base]):
            oracle = lambda trace: observe(trace, idx == 0, idx == 1)
            candidates = list(reversed(library)) if names[0] == "clear" else library
            multi = grow_transfer(binary, learned_base, symbols, goal, oracle, 4, 300, candidates)
            target = [(r[0], *(r[i] for i in order)) for r in ref]
            expected_matches = [candidates.index(library[idx])] if idx < 2 else []
            if multi["matching_patterns"] != expected_matches or distinguish(target, multi["table"]) is not None:
                raise AssertionError((names, idx, expected_matches, multi))
            ordinary = grow_transfer(binary, learned_base, symbols, goal, oracle, 4, 300)
            observed = []
            def counted(trace):
                observed.append(tuple(trace))
                return oracle(trace)
            policy = cost_aware_transfer(binary, learned_base, symbols, goal, counted, 4, 300,
                                         candidates, directory / "costs.sqlite")
            if (policy["paired_costs"] != {"ordinary": ordinary["target_episodes"], "library": multi["target_episodes"]}
                    or len(observed) != policy["target_episodes"]
                    or distinguish(target, policy["table"]) is not None
                    or policy["prior_tasks"] != len(strategies)):
                raise AssertionError("Cost history or strategy replay disagrees with direct measurement")
            strategies.append(policy["strategy"])
            for j, run in enumerate((policy, multi, ordinary)):
                policy_totals[j] += run["target_episodes"]
                if len(strategies) > 9:
                    heldout[j] += run["target_episodes"]
            if idx == 2:
                none_generic += ordinary["target_episodes"]
                none += multi["target_episodes"]
                continue
            known = grow_transfer(binary, learned_base, symbols, goal, oracle, 4, 300, library[idx])
            selected += multi["target_episodes"]
            prior_known += known["target_episodes"]
            generic += ordinary["target_episodes"]
    print(f"Last 9 first-seen tasks: {heldout} (adaptive, library, ordinary)")
    print(f"18 sequential targets: {policy_totals[0]} adaptive, {policy_totals[1]} always library, "
          f"{policy_totals[2]} always ordinary; {strategies.count('library')} library choices")
    print(f"12 applicable targets: {selected} library, {prior_known} preselected, {generic} generic; "
          f"6 immediate controls rejected both ({none} vs {none_generic} generic); lamp donor {lamp_result['target_episodes']}")
    control = grow_transfer(binary, learned_base, symbols, goal, lambda tr: observe(tr, False),
                            4, 300, pattern)
    unchanged = [(r[0], *(r[i] for i in order)) for r in base]
    if control["pattern_verified"] or distinguish(unchanged, control["table"]) is not None:
        raise AssertionError("Inapplicable pattern accepted")
    print(f"File donor {donor['target_episodes']} episodes; 6 ticket dispensers: "
          f"{warm} with pattern vs {cold} existing search; {wins} wins; negative control passed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--repair-only", action="store_true")
    parser.add_argument("--pattern-only", action="store_true")
    parser.add_argument("--growth-only", action="store_true")
    args = parser.parse_args()
    binary = args.binary.resolve()
    actions = ["ka", "zu", "mi", "vo"]
    examples = [({"s0": 1, "s1": 1, "s2": 0}, 0),
                ({"s0": 1, "s1": 0, "s2": 1}, 1)]
    with tempfile.TemporaryDirectory() as directory:
        log = Path(directory) / "source.obs"
        source = run_agent(binary, log, ["insert", "delete", "commit", "rollback"], 4,
                           1, [], [sys.executable, str(Path(__file__).with_name("trace_inference.py")),
                                   "--sqlite-oracle"], 200, 10)
        table = read_table(binary, log)
        if args.pattern_only or not (args.growth_only or args.repair_only):
            check_pattern(binary, Path(directory), actions, examples)
        if args.pattern_only:
            return
        if args.growth_only or not args.repair_only:
            check_growth(binary, Path(directory), table, actions, examples)
        if args.growth_only:
            return
        check_repair(binary, Path(directory), table, actions, examples)
        if args.repair_only:
            return
        labels = Path(directory) / "goal.json"
        labels.write_text(json.dumps(examples), encoding="utf-8")
        demo = subprocess.check_output(
            [sys.executable, str(Path(__file__).with_name("trace_transfer.py")), binary, log, labels,
             "--events", *actions, "--oracle", sys.executable, __file__, "--sensors",
             "restore", "publish", "erase", "mark"], text=True, timeout=30)
        if json.loads(demo)["plan"] != ["vo", "zu"]:
            raise AssertionError("Unexpected plan through the transfer CLI")
        totals = [0, 0, 0]
        wins = 0
        for index, names in enumerate(permutations(["mark", "erase", "publish", "restore"])):
            roles = dict(zip(actions, names))

            def observe(trace):
                return file_readings(trace, roles)

            guided, cost = try_transfer(table, actions, examples, observe, 3, 85)
            direct, cold = try_transfer(None, actions, examples, observe, 3, 85)
            fresh = run_agent(binary, Path(directory) / f"fresh-{index}", actions, None, 1, [],
                              [sys.executable, __file__, "--oracle", *names, goal_sensor(examples)],
                              200, 10)
            if not (guided and direct and fresh["observed"] == 1 and observe(guided)["s2"] == 1):
                raise AssertionError("Failed plan")
            totals = [a + b for a, b in zip(totals, (cost, cold, fresh["queries"]))]
            wins += int(cost < cold)
        # Mismatched dynamics: a positive single-action outcome unsupported
        # by every source mapping must still be discoverable.
        plan, _ = try_transfer(table, actions, examples,
                               lambda trace: {"s2": int(trace == ["vo"])}, 2, 21)
        if plan != ["vo"] or wins != 24:
            raise AssertionError((plan, wins))
        print(f'Source: {source["queries"]} training episodes plus one replay')
        print(f"24 renamings: transferred {totals[0]}, fresh direct search {totals[1]}, "
              f"fresh Heed {totals[2]} target episodes; {wins} wins over direct search")


if __name__ == "__main__":
    if sys.argv[1:2] in (["--oracle"], ["--sensors"], ["--confirm-sensors"]):
        roles = dict(zip(["ka", "zu", "mi", "vo"], sys.argv[2:6]))
        snapshot = file_readings(json.load(sys.stdin), roles, confirm=sys.argv[1] == "--confirm-sensors")
        print(json.dumps(snapshot) if sys.argv[1] != "--oracle" else int(snapshot[sys.argv[6]]))
    else:
        main()
