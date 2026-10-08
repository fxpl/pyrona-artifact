"""pyperformance configuration, machine fingerprint, and result stamping.

Shared by the setup step (venv recreate) and the benchmark run so the exclude
list and the result-validity rules live in exactly one place.
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import artifact_config as cfg  # noqa: E402

CONFIG_PATH = cfg.ARTIFACT_ROOT / "benchmarks" / "pyperformance" / "config.toml"
RESULTS_DIR = cfg.ARTIFACT_ROOT / "build" / "results" / "pyperformance"
REFERENCES_DIR = cfg.ARTIFACT_ROOT / "benchmarks" / "pyperformance" / "references"


@dataclass(frozen=True)
class PyperfConfig:
    mode: str
    timeout: int
    online: bool
    exclude: list[str]
    exclude_by_os: dict[str, list[str]]

    def excludes(self) -> list[str]:
        """Platform-effective exclude list."""
        return [*self.exclude, *self.exclude_by_os.get(platform.system(), [])]

    def benchmark_filter(self) -> str:
        """pyperformance ``--benchmarks`` value, e.g. ``-fastapi,-2to3``."""
        return ",".join(f"-{name}" for name in self.excludes())

    def fingerprint(self) -> str:
        """Config identity that invalidates a cached result when it changes."""
        return (
            f"mode={self.mode};timeout={self.timeout};"
            f"online={int(self.online)};exclude={','.join(self.excludes())}"
        )


def load_config(path: Path = CONFIG_PATH) -> PyperfConfig:
    with path.open("rb") as fh:
        data = tomllib.load(fh)["pyperformance"]
    return PyperfConfig(
        mode=data.get("mode", "default"),
        timeout=int(data.get("timeout", 180)),
        online=bool(data.get("online", False)),
        exclude=list(data.get("exclude", [])),
        exclude_by_os={k: list(v) for k, v in data.get("exclude_by_os", {}).items()},
    )


# --- machine fingerprint ----------------------------------------------------

def _read(path: str) -> str | None:
    try:
        return Path(path).read_text().strip()
    except OSError:
        return None


def _cpu_model() -> str:
    system = platform.system()
    if system == "Linux":
        for line in (_read("/proc/cpuinfo") or "").splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    elif system == "Darwin":
        try:
            out = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, check=False,
            ).stdout.strip()
            if out:
                return out
        except OSError:
            pass
    return platform.processor() or platform.machine() or "unknown"


def _cpu_freq() -> str:
    """Governor and current frequency, when the platform exposes them."""
    if platform.system() == "Linux":
        base = "/sys/devices/system/cpu/cpu0/cpufreq"
        gov = _read(f"{base}/scaling_governor") or "unknown"
        freq = _read(f"{base}/scaling_cur_freq") or "unknown"
        return f"{gov}@{freq}"
    return "unknown"


def machine_fingerprint() -> dict[str, str]:
    return {
        "os": platform.system(),
        "arch": platform.machine(),
        "cpu": _cpu_model(),
        "cores": str(os.cpu_count() or 0),
        "freq": _cpu_freq(),
    }


# --- result stamping --------------------------------------------------------

def result_stamp(build: cfg.Build, config: PyperfConfig) -> str | None:
    """Short hash over build + pyperformance config + machine + CPU frequency.

    A cached result is reused only when this stamp matches, so the whole
    measured environment must be identical. Returns None when the build's
    source commit is unknown (snapshots/info.txt missing).
    """
    base = cfg.build_stamp(build)
    if base is None:
        return None
    machine = machine_fingerprint()
    parts = [base, config.fingerprint(), *(f"{k}={v}" for k, v in sorted(machine.items()))]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def result_path(build: cfg.Build, stamp: str) -> Path:
    return RESULTS_DIR / build.id / f"{stamp}.json"
