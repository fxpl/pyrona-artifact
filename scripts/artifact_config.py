"""Shared build-matrix configuration derived from ``builds.toml``.

This is the single source of truth for every setup/update script and for the
generated ``env.env``. It expands the three variants (baseline, immutability,
regions) across the two configs (gil, nogil) into six concrete builds.
"""

from __future__ import annotations

import os
import platform
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
class Variant:
    name: str
    repo: str
    ref: str
    resolve: str | None  # None or "merge-base"

    @property
    def src_dir(self) -> Path:
        return ARTIFACT_ROOT / "snapshots" / f"cpython-{self.name}"


@dataclass(frozen=True)
class Build:
    config: str
    variant: str
    configure_flags: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        return f"{self.config}-{self.variant}"

    @property
    def env_prefix(self) -> str:
        return f"{self.config.upper()}_{self.variant.upper()}"

    @property
    def src_dir(self) -> Path:
        return ARTIFACT_ROOT / "snapshots" / f"cpython-{self.variant}"

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
    variants: list[Variant]
    configs: dict[str, list[str]]  # config name -> configure flags
    stable_python: str

    @property
    def builds(self) -> list[Build]:
        out: list[Build] = []
        for config, flags in self.configs.items():
            for variant in self.variants:
                out.append(Build(config, variant.name, list(flags)))
        return out

    def variant(self, name: str) -> Variant:
        for v in self.variants:
            if v.name == name:
                return v
        raise KeyError(f"unknown variant: {name}")

    @property
    def stable_venv_dir(self) -> Path:
        return ARTIFACT_ROOT / "build" / "venv-stable"

    @property
    def stable_python_bin(self) -> Path:
        return self.stable_venv_dir / "bin" / "python"

    @property
    def stable_venv_activate(self) -> Path:
        return self.stable_venv_dir / "bin" / "activate"


def load(manifest_path: Path = MANIFEST_PATH) -> Config:
    with manifest_path.open("rb") as fh:
        data = tomllib.load(fh)

    variants = [
        Variant(
            name=name,
            repo=spec["repo"],
            ref=spec["ref"],
            resolve=spec.get("resolve"),
        )
        for name, spec in data["variant"].items()
    ]
    configs = {
        name: list(spec["configure_flags"])
        for name, spec in data["config"].items()
    }
    stable_python = data["stable"]["python"]
    return Config(variants=variants, configs=configs, stable_python=stable_python)


def variant_commit(variant: str) -> str | None:
    """The resolved snapshot commit for a variant, from snapshots/info.txt."""
    info = ARTIFACT_ROOT / "snapshots" / "info.txt"
    if not info.exists():
        return None
    prefix = f"{variant.upper()}_COMMIT="
    for line in info.read_text().splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return None


def build_stamp(build: Build) -> str | None:
    """Identity of a build's inputs (source commit + flags), or None if unknown.

    This is the basis for incremental rebuilds, and the intended basis for
    benchmark result caching once a CPU-frequency fingerprint is appended.
    """
    commit = variant_commit(build.variant)
    if commit is None:
        return None
    return f"{commit} {' '.join(build.configure_flags)}"


def env_var_names(config: Config) -> list[str]:
    """The variables that env.env exports; the source of truth for the preflight."""
    names = [f"{v.name.upper()}_PYTHON_DIR" for v in config.variants]
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
