"""Shared build-matrix configuration derived from ``builds.toml``.

This is the single source of truth for every setup/update script and for the
generated ``env.env``. It expands each snapshot across its listed configs into
the corresponding concrete builds.
"""

from __future__ import annotations

import os
import platform
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info < (3, 11):
    sys.exit(
        f"error: Python 3.11+ is required (needs tomllib), got {sys.version.split()[0]}.\n"
        "Set PYTHON to a newer interpreter, e.g. PYTHON=python3.14 scripts/setup/run_all.sh"
    )

import tomllib

ARTIFACT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ARTIFACT_ROOT / "builds.toml"


def _python_bin_suffix() -> str:
    """Mirror env.env: CPython emits ``python.exe`` on Windows and macOS."""
    system = platform.system()
    if system in ("Darwin", "Windows"):
        return ".exe"
    if system.startswith(("CYGWIN", "MINGW", "MSYS")):
        return ".exe"
    return ""


PYTHON_BIN_SUFFIX = _python_bin_suffix()


@dataclass(frozen=True)
class Snapshot:
    name: str
    repo: str
    ref: str
    config: list[str]

    @property
    def src_dir(self) -> Path:
        return ARTIFACT_ROOT / "snapshots" / f"cpython-{self.name}"


@dataclass(frozen=True)
class Build:
    config: str
    snapshot: str
    configure_flags: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.config}-{self.snapshot}"

    @property
    def env_prefix(self) -> str:
        return f"{self.config.upper()}_{self.snapshot.upper()}"

    @property
    def src_dir(self) -> Path:
        return ARTIFACT_ROOT / "snapshots" / f"cpython-{self.snapshot}"

    @property
    def build_dir(self) -> Path:
        return ARTIFACT_ROOT / "build" / f"cpython-{self.id}"

    @property
    def python_bin(self) -> Path:
        return self.build_dir / f"python{PYTHON_BIN_SUFFIX}"

    @property
    def venv_dir(self) -> Path:
        return ARTIFACT_ROOT / "build" / f"venv-{self.id}"

    @property
    def venv_activate(self) -> Path:
        return self.venv_dir / "bin" / "activate"


@dataclass(frozen=True)
class Config:
    snapshots: list[Snapshot]
    configs: dict[str, list[str]]  # config name -> configure flags
    stable_python: str

    @property
    def builds(self) -> list[Build]:
        out: list[Build] = []
        for snapshot in self.snapshots:
            for config in snapshot.config:
                out.append(Build(config, snapshot.name, list(self.configs[config])))
        return out

    def snapshot(self, name: str) -> Snapshot:
        for snapshot in self.snapshots:
            if snapshot.name == name:
                return snapshot
        raise KeyError(f"unknown snapshot: {name}")

    @property
    def stable_venv_dir(self) -> Path:
        return ARTIFACT_ROOT / "build" / "venv-stable"

    @property
    def stable_python_bin(self) -> Path:
        return self.stable_venv_dir / "bin" / "python"

    @property
    def stable_venv_activate(self) -> Path:
        return self.stable_venv_dir / "bin" / "activate"


# Build keys end up in shell variable names (uppercased, joined with `_`),
# so dashes and other punctuation would emit invalid identifiers in env.env.
_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


def _validate_keys(kind: str, keys: list[str]) -> None:
    bad = [k for k in keys if not _KEY_RE.match(k)]
    if bad:
        joined = ", ".join(repr(k) for k in bad)
        sys.exit(
            f"error: invalid {kind} name(s) in builds.toml: {joined}\n"
            "use letters, digits, and underscores only (no dashes)."
        )


def load(manifest_path: Path = MANIFEST_PATH) -> Config:
    with manifest_path.open("rb") as fh:
        data = tomllib.load(fh)

    _validate_keys("snapshot", list(data["snapshot"]))
    _validate_keys("config", list(data["config"]))

    snapshots = [
        Snapshot(
            name=name,
            repo=spec["repo"],
            ref=spec["ref"],
            config=list(spec["config"]),
        )
        for name, spec in data["snapshot"].items()
    ]
    configs = {
        name: list(spec["configure_flags"])
        for name, spec in data["config"].items()
    }
    unknown_configs = [
        f"{snapshot.name}.{name}"
        for snapshot in snapshots
        for name in snapshot.config
        if name not in configs
    ]
    if unknown_configs:
        joined = ", ".join(repr(name) for name in unknown_configs)
        sys.exit(f"error: unknown config(s) in builds.toml: {joined}")
    stable_python = data["stable"]["python"]
    return Config(snapshots=snapshots, configs=configs, stable_python=stable_python)


def snapshot_commit(snapshot: str) -> str | None:
    """The resolved source commit for a snapshot, from snapshots/info.txt."""
    info = ARTIFACT_ROOT / "snapshots" / "info.txt"
    if not info.exists():
        return None
    prefix = f"{snapshot.upper()}_COMMIT="
    for line in info.read_text().splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def build_stamp(build: Build) -> str | None:
    """Identity of a build's inputs (source commit + flags), or None if unknown.

    This is the basis for incremental rebuilds, and the intended basis for
    benchmark result caching once a CPU-frequency fingerprint is appended.
    """
    commit = snapshot_commit(build.snapshot)
    if commit is None:
        return None
    return f"{commit} {' '.join(build.configure_flags)}"


def env_var_names(config: Config) -> list[str]:
    """The variables that env.env exports; the source of truth for the preflight."""
    names = [f"{snapshot.name.upper()}_PYTHON_DIR" for snapshot in config.snapshots]
    for build in config.builds:
        p = build.env_prefix
        names += [
            f"{p}_BUILD_DIR",
            f"{p}_PYTHON_BIN",
            f"{p}_PYTHON_ENV",
            f"{p}_PYTHON_ENV_ACTIVATE",
        ]
    names += ["STABLE_PYTHON_ENV", "STABLE_PYTHON_BIN", "STABLE_PYTHON_ENV_ACTIVATE"]
    return names


def check_env(config: Config | None = None) -> None:
    """Fail fast if env.env has not been sourced into the environment."""
    config = config or load()
    for name in env_var_names(config):
        if not os.environ.get(name):
            sys.exit(f"error: {name} is undefined; run `source env.env` first.")
