"""A results directory that archives every run and publishes the latest good one.

Shared by experiments that produce a set of output files per run. ``start()``
clears the root of the previous run's (regenerable) files and opens a fresh
``<root>/.archive/<run timestamp>/`` to write into, so a partial or failed run
leaves the root empty rather than mixed. ``publish()`` copies the completed
run's files up next to ``.archive``, so the root always holds exactly the latest
successful run — and the archive keeps every run tagged with the time it ran.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path


class RunOutput:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.archive = root / ".archive"
        self.run_dir = self.archive / datetime.now().strftime("%Y%m%d-%H%M%S")

    def start(self) -> Path:
        """Clear the root of regenerable files and open this run's archive dir."""
        if self.root.exists():
            for path in self.root.iterdir():
                if path == self.archive:
                    continue
                shutil.rmtree(path) if path.is_dir() else path.unlink()
        self.run_dir.mkdir(parents=True, exist_ok=True)
        return self.run_dir

    def publish(self) -> None:
        """Copy this run's files up to the root, next to the archive."""
        for path in self.run_dir.iterdir():
            shutil.copy2(path, self.root / path.name)
