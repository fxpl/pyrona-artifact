"""Docker-style nested step output for the artifact scripts.

``section()`` groups related steps under a headline; ``run()`` executes a
command under the current section. On an interactive terminal each running
command shows only a short scrolling tail of its output, and a section whose
steps all succeed collapses to a single ``✓`` line. On failure the full
context is kept and the command's complete output is written to ``logs/``.

On a non-interactive stream (CI, ``docker build`` logs) it falls back to plain
indented streaming so the full log is preserved.
"""

from __future__ import annotations

import os
import queue
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Sequence

TAIL_LINES = 6
FAIL_TAIL_LINES = 10
INDENT = "  "
GUTTER = "  │ "
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_EOF = object()

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


# --- styling helpers --------------------------------------------------------

def _interactive() -> bool:
    return sys.stdout.isatty() and os.environ.get("TERM") not in (None, "", "dumb")


def _use_color() -> bool:
    return _interactive() and os.environ.get("NO_COLOR") is None


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _use_color() else text


def _term_width() -> int:
    return shutil.get_terminal_size(fallback=(100, 24)).columns


def _clip(line: str, width: int) -> str:
    line = line.replace("\t", "    ")
    if len(line) > width:
        return line[: max(0, width - 1)] + "…"
    return line


def _write_log(headline: str, lines: list[str], command: str | None = None,
               cwd: object | None = None) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", headline).strip("-") or "step"
    path = LOG_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}_{slug}.log"
    header: list[str] = []
    if command:
        header.append(f"$ {command}")
    if cwd:
        header.append(f"# cwd: {cwd}")
    body = "\n".join([*header, "", *lines]) if header else "\n".join(lines)
    path.write_text(body + "\n", encoding="utf-8")
    return path


# --- renderer ---------------------------------------------------------------

@dataclass
class _Section:
    title: str
    collapse: bool
    children: list[str] = field(default_factory=list)  # rendered summary lines
    failed: bool = False
    baked: bool = False  # already printed permanently (failure path)


@dataclass
class _Active:
    headline: str
    tail: deque[str]


class _Renderer:
    """Owns the terminal's live region: the open sections plus the running command."""

    def __init__(self) -> None:
        self.stack: list[_Section] = []
        self.active: _Active | None = None
        self._frame = 0
        self._drawn = 0
        self._last = 0.0

    @property
    def depth(self) -> int:
        return len(self.stack)

    # live region ----------------------------------------------------------

    def _block(self) -> list[str]:
        width = _term_width()
        spin = _SPINNER[self._frame % len(_SPINNER)]
        lines: list[str] = []
        for d, sec in enumerate(self.stack):
            ind = INDENT * d
            lines.append(f"{ind}{_c('36', '•')} {_c('1', sec.title)}")
            for child in sec.children:
                lines.append(INDENT * (d + 1) + child)
        if self.active is not None:
            ind = INDENT * self.depth
            lines.append(f"{ind}{_c('36', spin)} {self.active.headline}")
            gutter_w = max(10, width - len(ind) - len(GUTTER))
            for raw in self.active.tail:
                lines.append(ind + _c("2", GUTTER) + _c("2", _clip(raw, gutter_w)))
        return lines

    def _erase(self) -> None:
        if self._drawn:
            sys.stdout.write(f"\033[{self._drawn}A\033[0J")
            self._drawn = 0

    def redraw(self, force: bool = False) -> None:
        if not _interactive():
            return
        now = time.monotonic()
        if not force and now - self._last < 0.08:
            return
        self._frame += 1
        self._erase()
        block = self._block()
        if block:
            sys.stdout.write("\n".join(block) + "\n")
            sys.stdout.flush()
        self._drawn = len(block)
        self._last = now

    def _commit(self, lines: list[str]) -> None:
        """Print permanent lines above the live region."""
        if _interactive():
            self._erase()
            if lines:
                sys.stdout.write("\n".join(lines) + "\n")
                sys.stdout.flush()
            self.redraw(force=True)
        else:
            for line in lines:
                print(line, flush=True)

    # standalone messages --------------------------------------------------

    def message(self, mark: str, color: str, msg: str) -> None:
        self._commit([f"{INDENT * self.depth}{_c(color, mark)} {msg}"])

    # sections -------------------------------------------------------------

    def open(self, title: str, collapse: bool) -> None:
        if not _interactive():
            self.message("•", "36", title)
        self.stack.append(_Section(title, collapse))
        self.redraw(force=True)

    def close(self, failed: bool) -> None:
        sec = self.stack.pop()
        if sec.baked:  # failure already printed everything
            if self.stack and (failed or sec.failed):
                self.stack[-1].failed = True
            return

        ok = not failed and not sec.failed
        mark, color = ("✓", "32") if ok else ("✗", "31")
        summary = f"{_c(color, mark)} {_c('1', sec.title)}"
        kept = [] if (ok and sec.collapse) else [INDENT + ch for ch in sec.children]

        if not _interactive():
            self.message(mark, color, sec.title)
        elif self.stack:
            parent = self.stack[-1]
            parent.children.append(summary)
            parent.children.extend(kept)
            parent.failed = parent.failed or not ok
            self.redraw(force=True)
        else:
            self._commit([summary, *kept])

        if self.stack and (failed or sec.failed):
            self.stack[-1].failed = True

    # active command -------------------------------------------------------

    def start(self, headline: str, tail: int) -> None:
        self.active = _Active(headline, deque(maxlen=tail))
        if not _interactive():
            self.message("•", "36", headline)
        self.redraw(force=True)

    def feed(self, line: str) -> None:
        if self.active is None:
            return
        if _interactive():
            self.active.tail.append(line)
            self.redraw()
        else:
            print(INDENT * self.depth + GUTTER + line, flush=True)

    def finish_ok(self) -> None:
        assert self.active is not None
        summary = f"{_c('32', '✓')} {self.active.headline}"
        self.active = None
        if _interactive() and self.stack:
            self.stack[-1].children.append(summary)
            self.redraw(force=True)
        else:
            self._commit([f"{INDENT * self.depth}{summary}"])

    def finish_failed(self, reason: str, log_path: object) -> None:
        """Record the active command as a failed child and keep the section going.

        Used for soft failures (``check=False`` inside a section): the step is
        marked ✗ but the run continues, rather than baking out like ``fail``.
        """
        headline = self.active.headline if self.active else "(step)"
        self.active = None
        lines = [
            f"{_c('31', '✗')} {headline}",
            _c("2", f"{GUTTER}({reason})"),
            _c("2", f"{GUTTER}Full log: {log_path}"),
        ]
        if _interactive() and self.stack:
            self.stack[-1].children.extend(lines)
            self.redraw(force=True)
        else:
            ind = INDENT * self.depth
            self._commit([ind + line for line in lines])

    def child(self, text: str) -> None:
        """Add a standalone child line (e.g. a skipped step) to the section."""
        if _interactive() and self.stack:
            self.stack[-1].children.append(text)
            self.redraw(force=True)
        else:
            depth = self.depth + 1 if self.stack else self.depth
            print(INDENT * depth + text, flush=True)

    def fail(self, detail: list[str]) -> None:
        """Present a failed command and bake the surrounding context permanently."""
        self.active = None
        if _interactive():
            self._erase()
            baked: list[str] = []
            for d, sec in enumerate(self.stack):
                baked.append(f"{INDENT * d}{_c('31', '✗')} {_c('1', sec.title)}")
                for child in sec.children:
                    baked.append(INDENT * (d + 1) + child)
                sec.failed = True
                sec.baked = True
            baked.extend(detail)
            sys.stdout.write("\n".join(baked) + "\n")
            sys.stdout.flush()
            self._drawn = 0
        else:
            for line in detail:
                print(line, flush=True)
            for sec in self.stack:
                sec.failed = True


_R = _Renderer()


# --- public API -------------------------------------------------------------

def info(msg: str) -> None:
    _R.message("•", "36", msg)


def success(msg: str) -> None:
    _R.message("✓", "32", msg)


def error(msg: str) -> None:
    _R.message("✗", "31", msg)


def skip(label: str) -> None:
    """Record a skipped step (a child of the current section, or a plain line)."""
    _R.child(f"{_c('33', '-')} {label}")


class SectionHandle:
    """Yielded by ``section``; call ``fail()`` to mark the section failed."""

    def __init__(self, renderer: "_Renderer") -> None:
        self._renderer = renderer

    def fail(self) -> None:
        if self._renderer.stack:
            self._renderer.stack[-1].failed = True


@contextmanager
def section(title: str, *, collapse: bool = True) -> Iterator[SectionHandle]:
    """Group the steps run inside the block under ``title``.

    A soft failure inside (``console.run(..., check=False)``) renders a ✗ child
    but does not by itself fail the section — call ``handle.fail()`` to mark the
    section failed, so a step that passes on retry still reads as ✓.
    """
    _R.open(title, collapse)
    failed = False
    handle = SectionHandle(_R)
    try:
        yield handle
    except BaseException:
        failed = True
        raise
    finally:
        _R.close(failed)


def _terminate(proc: subprocess.Popen) -> None:
    """Stop a process and its children, escalating SIGTERM -> SIGKILL."""
    if proc.poll() is not None:
        return
    # On POSIX the process runs in its own session (see start_new_session), so we
    # signal the whole group and take any children (make, cc, ...) with it.
    if hasattr(os, "killpg"):
        try:
            pgid = os.getpgid(proc.pid)
        except ProcessLookupError:
            return
        for sig, grace in ((signal.SIGTERM, 5.0), (signal.SIGKILL, None)):
            try:
                os.killpg(pgid, sig)
            except ProcessLookupError:
                return
            try:
                proc.wait(grace)
                return
            except subprocess.TimeoutExpired:
                continue
    else:
        proc.terminate()
        try:
            proc.wait(5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def run(
    headline: str,
    cmd: Sequence[str],
    *,
    cwd: os.PathLike[str] | str | None = None,
    env: dict[str, str] | None = None,
    tail: int = TAIL_LINES,
    fail_tail: int = FAIL_TAIL_LINES,
    timeout: float | None = None,
    check: bool = True,
) -> int:
    """Run ``cmd`` under ``headline`` with a live tail; return the exit code.

    ``timeout`` (seconds) kills the command and its children when exceeded; the
    step then fails like any other (raising ``TimeoutExpired`` when ``check``).
    """
    captured: list[str] = []
    _R.start(headline, tail)

    proc = subprocess.Popen(
        list(cmd),
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,  # own process group so a timeout can kill children
    )

    # Read on a thread so the main loop can enforce the deadline and keep the
    # spinner alive even while the command is silent.
    lines: queue.Queue = queue.Queue()

    def _reader() -> None:
        assert proc.stdout is not None
        for raw in proc.stdout:
            lines.put(raw.rstrip("\n"))
        lines.put(_EOF)

    threading.Thread(target=_reader, daemon=True).start()

    deadline = None if timeout is None else time.monotonic() + timeout
    timed_out = False

    while True:
        if deadline is not None and time.monotonic() >= deadline:
            timed_out = True
            break
        poll = 0.1
        if deadline is not None:
            poll = min(poll, max(0.0, deadline - time.monotonic()))
        try:
            item = lines.get(timeout=poll or 0.01)
        except queue.Empty:
            item = None
        if item is _EOF:
            break
        if item is not None:
            captured.append(item)
            _R.feed(item)
        _R.redraw()

    if timed_out:
        _terminate(proc)
    rc = proc.wait()

    if not timed_out and rc == 0:
        _R.finish_ok()
        return rc

    log_path = _write_log(headline, captured, command=shlex.join(list(cmd)), cwd=cwd)
    reason = f"timed out after {timeout:g}s" if timed_out else f"exit {rc}"

    # Soft failure: inside a section with check disabled, record a ✗ child and
    # let the section keep going instead of baking the whole context out.
    if not check and _R.stack:
        _R.finish_failed(reason, log_path)
        return 124 if timed_out else rc

    ind = INDENT * _R.depth
    detail = [f"{ind}{_c('31', '✗')} {headline} {_c('2', f'({reason})')}"]
    if _interactive():
        shown = captured[-fail_tail:]
        omitted = len(captured) - len(shown)
        if omitted > 0:
            detail.append(ind + _c("2", f"{GUTTER}… {omitted} earlier line(s) in the log"))
        detail += [ind + GUTTER + line for line in shown]
    detail.append(ind + _c("2", f"  full log: {log_path}"))
    _R.fail(detail)

    if check:
        if timed_out:
            raise subprocess.TimeoutExpired(list(cmd), timeout, output="\n".join(captured))
        raise subprocess.CalledProcessError(rc, list(cmd), output="\n".join(captured))

    return 124 if timed_out else rc


def run_main(fn) -> None:
    """Entry-point wrapper: a reported step failure exits cleanly, no traceback."""
    try:
        fn()
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        sys.exit(1)  # console.run already printed the failure and its log path
    except KeyboardInterrupt:
        sys.exit(130)
