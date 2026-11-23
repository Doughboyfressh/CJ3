"""Compare transferred and fresh plans across all action renamings of a file store."""
import argparse
import json
import subprocess
from itertools import permutations, product
from pathlib import Path
import sys
import tempfile

from trace_agent import run_agent
from trace_transfer import distinguish, grow_transfer, goal_sensor, predict, read_table, repair_transfer, try_transfer
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
    adapted = fresh = 0
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
        if (result.get("target_states") != 5 or len(result["witnesses"]) != 10
                or distinguish(reference, result["table"]) is not None):
            raise AssertionError(result)
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
    control = grow_transfer(binary, source, actions, examples,
                            lambda tr: file_readings(tr, roles), 5, 1000)
    if control.get("target_states") != 4 or control["witnesses"]:
        raise AssertionError(control)
    print(f"24 confirmation stores: {adapted} target episodes vs {fresh} fresh; "
          "240 pairwise witnesses replayed; unchanged control has 4 states")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("--repair-only", action="store_true")
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
