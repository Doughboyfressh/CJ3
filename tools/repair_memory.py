"""Locate repair history and import legacy SQLite data into an active profile."""
from contextlib import closing
import os
from pathlib import Path
import sqlite3
import tempfile


def repair_history():
    legacy = Path("out/repair_history.sqlite")
    profile = Path(".pi-profile")
    if not (profile / "active").is_file():
        return legacy
    target = profile / legacy.name
    if target.exists() or not legacy.is_file():
        return target

    # Snapshot committed data, including WAL pages. Publish only a complete
    # database and leave an already installed history intact on a racing launch.
    with tempfile.TemporaryDirectory(dir=profile) as directory:
        snapshot = Path(directory) / legacy.name
        with closing(sqlite3.connect(legacy.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(snapshot)) as dest:
                source.backup(dest)
        try:
            os.link(snapshot, target)
        except FileExistsError:
            pass
    return target
