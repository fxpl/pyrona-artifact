#!/usr/bin/env python3
"""Build GUIDE.md from in-repo Artifact navigation markers.

Supported marker format (can appear in any comment style):

    Artifact[Section Name]: Description text

Example:
    // Artifact[Implementation]: The SCC implementation
    <!-- Artifact[Benchmarking]: PyPerformance Benchmarks -->
"""

from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

MARKER_RE = re.compile(r"Artifact\[([^\]]+)\]\s*:\s*(.+)")
DEFAULT_SECTION_ORDER = ["Benchmarking", "Tests", "Examples", "Implementation"]
GENERATED_START = "<!-- ARTIFACT_GUIDE:START -->"
GENERATED_END = "<!-- ARTIFACT_GUIDE:END -->"

CUSTOM_SKIP_DIRS = {
    ".git",
}
CUSTOM_SKIP_FILES = {
    "GUIDE.md",
    "build_navigation_guide.py",
}


@dataclass(frozen=True)
class IgnoreRules:
    file_paths: set[str]
    dir_paths: set[str]


@dataclass(frozen=True)
class Entry:
    section: str
    text: str
    path: str
    line: int


def _should_skip(path: Path) -> bool:
    if path.name in CUSTOM_SKIP_FILES:
        return True
    return False


def load_simple_gitignore_rules(root: Path) -> IgnoreRules:
    """Parse simple .gitignore lines for fallback scanning.

    Supported forms only:
    - x/.y.z  -> exact file path match
    - x/      -> directory prefix match

    Everything else is intentionally ignored. The git-based file listing path
    handles full .gitignore semantics when git is available.
    """
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return IgnoreRules(file_paths=set(), dir_paths=set())

    file_paths: set[str] = set()
    dir_paths: set[str] = set()

    for raw in gitignore.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue

        normalized = line.lstrip("/")
        if not normalized:
            continue

        if normalized.endswith("/"):
            dir_paths.add(normalized.rstrip("/"))
        else:
            # Keep only path-like exact file entries (e.g. x/.y.z).
            if "/" in normalized:
                file_paths.add(normalized)

    return IgnoreRules(file_paths=file_paths, dir_paths=dir_paths)


def _git_list_candidate_files(root: Path) -> list[Path]:
    """Return non-ignored repo files by delegating ignore rules to git."""
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "--full-name"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []

    files: list[Path] = []
    for rel in result.stdout.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        path = root / rel
        if path.is_file() and not _should_skip(path):
            files.append(path)
    return files


def _fallback_list_candidate_files(root: Path) -> list[Path]:
    ignore_rules = load_simple_gitignore_rules(root)
    files: list[Path] = []

    for path in root.rglob("*"):
        if path.is_dir():
            continue

        if any(part in CUSTOM_SKIP_DIRS for part in path.parts):
            continue
        if _should_skip(path):
            continue

        rel = path.relative_to(root).as_posix()
        if rel in ignore_rules.file_paths:
            continue

        rel_parts = rel.split("/")
        prefixes = ["/".join(rel_parts[:idx]) for idx in range(1, len(rel_parts))]
        if any(prefix in ignore_rules.dir_paths for prefix in prefixes):
            continue

        files.append(path)

    return files


def list_candidate_files(root: Path) -> list[Path]:
    git_files = _git_list_candidate_files(root)
    if git_files:
        return git_files
    return _fallback_list_candidate_files(root)


def find_markers(root: Path) -> list[Entry]:
    entries: list[Entry] = []

    for path in list_candidate_files(root):

        rel_path = path.relative_to(root).as_posix()
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            # Skip binary and non-text files.
            continue
        except OSError:
            continue

        for line_no, line in enumerate(content.splitlines(), start=1):
            match = MARKER_RE.search(line)
            if not match:
                continue

            section = match.group(1).strip()
            text = match.group(2).strip()
            if not section or not text:
                continue

            entries.append(Entry(section=section, text=text, path=rel_path, line=line_no))

    return entries


def ordered_sections(found_sections: Iterable[str]) -> list[str]:
    found = set(found_sections)
    ordered = [name for name in DEFAULT_SECTION_ORDER if name in found]
    extras = sorted(found - set(DEFAULT_SECTION_ORDER), key=str.casefold)
    return ordered + extras


def build_guide_text(entries: list[Entry]) -> str:
    grouped: dict[str, list[Entry]] = {}
    for entry in entries:
        grouped.setdefault(entry.section, []).append(entry)

    # Keep generated output deterministic.
    for section in grouped:
        grouped[section].sort(key=lambda e: (e.path, e.line, e.text.casefold()))

    sections = ordered_sections(grouped.keys())
    if not sections:
        sections = DEFAULT_SECTION_ORDER

    lines: list[str] = []

    for section in sections:
        lines.append(f"## {section}")
        lines.append("")

        for item in grouped.get(section, []):
            lines.append(f"- {item.text}: [./{item.path}#{item.line}](./{item.path}#{item.line})")

        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def replace_generated_block(existing_text: str, generated_text: str) -> str:
    start_idx = existing_text.find(GENERATED_START)
    end_idx = existing_text.find(GENERATED_END)
    if start_idx == -1 or end_idx == -1 or end_idx < start_idx:
        raise ValueError(
            "GUIDE markers not found. Add markers '\n"
            f"{GENERATED_START}\n...\n{GENERATED_END}' to GUIDE.md."
        )

    before = existing_text[: start_idx + len(GENERATED_START)]
    after = existing_text[end_idx:]

    middle = "\n\n" + generated_text.rstrip() + "\n\n"
    return before + middle + after


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root to scan (default: current working directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file path (default: <root>/GUIDE.md)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    output = args.output.resolve() if args.output else root / "GUIDE.md"

    entries = find_markers(root)
    generated_text = build_guide_text(entries)

    if not output.exists():
        raise FileNotFoundError(
            f"{output} does not exist. Create it with {GENERATED_START} and {GENERATED_END} markers."
        )

    existing_text = output.read_text(encoding="utf-8")
    guide_text = replace_generated_block(existing_text, generated_text)

    output.write_text(guide_text, encoding="utf-8")
    print(f"Wrote {output} with {len(entries)} artifact marker(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
