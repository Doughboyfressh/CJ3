"""Compare transferred and fresh plans across all action renamings of a file store."""
import argparse
import json
import subprocess
from itertools import permutations
from pathlib import Path
import sys
import tempfile

from trace_agent import run_agent
from trace_transfer import goal_sensor, read_table, try_transfer


def file_readings(trace, roles):
    # A draft bit is copied to or restored from a separate published file.
    with tempfile.TemporaryDirectory() as directory:
        draft, published = (Path(directory) / name for name in ("draft", "published"))
        draft.write_bytes(b"0")
        published.write_bytes(b"0")
        for token in trace:
            role = roles[token]
            if role == "mark":
                draft.write_bytes(b"1")
            elif role == "erase":
                draft.write_bytes(b"0")
            elif role == "publish":
                published.write_bytes(draft.read_bytes())
            elif role == "restore":
                draft.write_bytes(published.read_bytes())
        left, right = int(draft.read_bytes()), int(published.read_bytes())
        return {"s0": left != right, "s1": left, "s2": right}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    binary = parser.parse_args().binary.resolve()
    actions = ["ka", "zu", "mi", "vo"]
    examples = [({"s0": 1, "s1": 1, "s2": 0}, 0),
                ({"s0": 1, "s1": 0, "s2": 1}, 1)]
    with tempfile.TemporaryDirectory() as directory:
        log = Path(directory) / "source.obs"
        source = run_agent(binary, log, ["insert", "delete", "commit", "rollback"], 4,
                           1, [], [sys.executable, str(Path(__file__).with_name("trace_inference.py")),
                                   "--sqlite-oracle"], 200, 10)
        table = read_table(binary, log)
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
    if sys.argv[1:2] in (["--oracle"], ["--sensors"]):
        roles = dict(zip(["ka", "zu", "mi", "vo"], sys.argv[2:6]))
        snapshot = file_readings(json.load(sys.stdin), roles)
        print(json.dumps(snapshot) if sys.argv[1] == "--sensors" else int(snapshot[sys.argv[6]]))
    else:
        main()
