"""Run paired cold and transferred door episodes against a compiled Heed binary."""

import argparse
from pathlib import Path
import re
import subprocess
import tempfile
import time


RULES = {
    "follow": "current switch",
    "latch": "switch-on events >= 1",
    "rearm": "last 1 of [2, 4] opens for [[4]]",
    "retry": "first-door attempts >= 1",
    "delay": "elapsed actions >= 3",
    "sequence": "first-door attempt occurred before the first switch-on; both occurred",
}


def run_episode(binary, layout, mechanism, observations=None):
    args = [binary, "explore", layout, mechanism]
    if observations is not None:
        args.append(observations)
    output = subprocess.check_output(args, text=True, timeout=30).strip()
    result = re.fullmatch(
        re.escape(layout) + r" exit; rule (.+); experiments (\d+); actions (\d+)", output
    )
    if result is None:
        raise ValueError(f"{layout} ({mechanism}): {output}")
    return result[1], int(result[2]), int(result[3])


def rearm_histories(limit):
    """Enumerate legal hall walks and label each possible first-door crossing."""
    pending = [(0, False, False, ())]
    records = {}
    while pending:
        pos, switch, armed, events = pending.pop()
        if pos in (1, 2):
            records[events] = int(armed)
        if len(events) == limit:
            continue
        if pos in (0, 4):
            pending.append((pos, not switch, armed if switch else False,
                            events + ((3 if switch else 2),)))
        passage = {0: 1, 1: 0, 2: 4, 4: 2}[pos]
        pending.append((passage, switch, armed, events + (1,)))
        if pos in (1, 2):
            pending.append((3 - pos if armed else pos, switch, True, events + (4,)))
        if pos == 2 and switch:
            pending.append((pos, switch, armed, events + (5,)))
    return records


def check_context_memory(binary, directory, layouts):
    history = directory / "rearm.obs"
    withheld = directory / "withheld.obs"
    rule, trials, actions = run_episode(binary, "hall", "rearm", history)
    if rule != RULES["rearm"] or trials == 0:
        raise ValueError(f"Cold learner failed to identify the reset: {rule}")
    observations = history.read_text()
    training = set()
    contradiction = False
    for line in observations.splitlines():
        _, sequence, label = line.split()
        events = tuple(map(int, sequence.split(",")))
        training.add(events)
        if 4 in events and label == "0":
            contradiction = True
    if not contradiction:
        raise ValueError("Cold learner never falsified the once-attempted rule")
    records = rearm_histories(9)
    unseen = records.keys() - training

    withheld.write_text("".join(
        f"door2 {','.join(map(str, events))} {records[events]}\n"
        for events in sorted(unseen)
    ))
    score = subprocess.check_output([binary, "explore-score", history, withheld],
                                    text=True, timeout=30).strip()
    if score != f"{len(unseen)}/{len(unseen)} correct; 0 disputed":
        raise ValueError(f"Unseen rearm predictions: {score}")
    for layout in layouts:
        # Restore the original cold-training log before every layout.
        history.write_text(observations)
        rule, trials, _ = run_episode(binary, layout, "rearm", history)
        if (rule, trials) != ("last 1 of [2, 4] opens for [[4]]", 0):
            raise ValueError(f"{layout}: unexpected rearm result {(rule, trials)}")
    print(f"rearm: {actions} cold training actions; {score}; {len(layouts)} transferred layouts")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, help="Path to the Heed executable")
    binary = parser.parse_args().binary.resolve()
    layouts = ["annex"] + [
        f"corridor-{size}-{door}"
        for size in range(4, 13)
        for door in range(1, size - 2)
    ]
    # Same location, switch and event counts; only the ordering differs.
    with tempfile.TemporaryDirectory() as directory:
        history = Path(directory) / "ordered.obs"
        history.write_text("door2 2,1,4,1,1 0\ndoor2 1,4,1,2,1 1\n")
        rule, trials, _ = run_episode(binary, "hall", "sequence", history)
        if rule != RULES["sequence"] or trials == 0:
            raise ValueError("The equal-count histories need a further experiment")
        if run_episode(binary, "annex", "sequence", history)[:2] != (rule, 0):
            raise ValueError("The order rule did not transfer across restart")
    print("mechanism  training_trials  layouts  transferred_actions  cold_actions  wins")
    with tempfile.TemporaryDirectory() as directory:
        check_context_memory(binary, Path(directory), layouts)
        start = time.perf_counter()
        for mechanism, expected in RULES.items():
            observations = Path(directory) / (mechanism + ".benchmark")
            rule, trials, _ = run_episode(binary, "hall", mechanism, observations)
            if rule != expected:
                raise ValueError(f"{mechanism}: learned {rule!r}")
            transferred = cold = wins = 0
            for layout in layouts:
                rule, extra, actions = run_episode(binary, layout, mechanism, observations)
                if rule != expected or extra:
                    raise ValueError(f"{layout}: unexpected transfer result for {mechanism}")
                _, _, baseline = run_episode(binary, layout, mechanism)
                transferred += actions
                cold += baseline
                wins += int(actions < baseline)
            print(mechanism, trials, len(layouts), transferred, cold, wins)
    print(f"Wall time for {len(RULES) * (1 + 2 * len(layouts))} processes: "
          f"{time.perf_counter() - start:.3f} s")


if __name__ == "__main__":
    main()
