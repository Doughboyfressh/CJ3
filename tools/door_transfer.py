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
    start = time.perf_counter()
    print("mechanism  training_trials  layouts  transferred_actions  cold_actions  wins")
    with tempfile.TemporaryDirectory() as directory:
        for mechanism, expected in RULES.items():
            observations = Path(directory) / mechanism
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
