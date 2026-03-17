import subprocess
import os
import tempfile
import streamlit as st
import re
import copy
import signal
import threading
from typing import Callable
from code_editor import code_editor

EXPECTED_ENV = [
    "BASELINE_PYTHON_ENV_ACTIVATE",
    "PATCHED_PYTHON_ENV_ACTIVATE",
    "STABLE_PYTHON_ENV_ACTIVATE",
]

PATCHED_PYTHON_BIN = "PATCHED_PYTHON_BIN"
STABLE_PYTHON_BIN = "STABLE_PYTHON_BIN"
MAX_COMMAND_OUTPUT_LINES = 100
OUTPUT_REFRESH_RATE = "250ms"

def _append_command_output(state: dict, chunk: str) -> None:
    output_lines = state.setdefault("output_lines", [])
    output_lines.extend(chunk.splitlines(keepends=True) or [chunk])

    if len(output_lines) > MAX_COMMAND_OUTPUT_LINES:
        state["output_lines"] = output_lines[-MAX_COMMAND_OUTPUT_LINES:]
        state["output_truncated"] = True

    state["output"] = "".join(state["output_lines"])

def validate_required_envs(env_names: list[str], env_files: list[str]) -> bool:
    """
    Check whether required environment variables are set.
    """

    missing_envs = [name for name in env_names if not os.getenv(name)]
    unset_file_envs = [name for name in env_files if not os.getenv(name)]
    invalid_file_envs = []

    for name in env_files:
        path = os.getenv(name)
        if path and not os.path.isfile(path):
            invalid_file_envs.append(f"{name} -> {path}")

    if missing_envs or unset_file_envs or invalid_file_envs:
        problems = []
        if missing_envs:
            problems.append("Missing required environment variables:\n- " + "\n- ".join(missing_envs))
        if unset_file_envs:
            problems.append("Environment variables for required files are not set:\n- " + "\n- ".join(unset_file_envs))
        if invalid_file_envs:
            problems.append("Environment variables do not point to a valid file:\n- " + "\n- ".join(invalid_file_envs))
        st.error("\n\n".join(problems))
        return False

    st.success("All required environment variables are set and file paths are valid.")
    return True

_BUTTON_STYLE = {
    "border": "1px solid gray",
    "top": "0rem"
}
_BUTTON_SETTINGS = {
    "primary": True,
    "hasText": True,
    "alwaysOn": True,
    "showWithIcon": True,
}
_CODE_BLOCK_BUTTONS = [
    {
        **_BUTTON_SETTINGS,
        "name": "Copy",
        "feather": "Copy",
        "commands": ["copyAll"],
        "style": {**_BUTTON_STYLE, "right": "4.5em"}
    },{
        **_BUTTON_SETTINGS,
        "name": "Run",
        "feather": "Play",
        "commands": ["submit"],
        "style": {**_BUTTON_STYLE, "right": 0}
    }
]
_CODE_BLOCK_INFO_CSS = """
background-color: #bee1e5;

body > #root .ace-streamlit-dark~& {
   background-color: #262830;
}
"""
_CODE_BLOCK_INFO_BAR_BASE = {
        "name": "language info",
        "css": _CODE_BLOCK_INFO_CSS,
        "style": {
                    "order": "1",
                    "display": "flex",
                    "flexDirection": "row",
                    "alignItems": "center",
                    "width": "100%",
                    "height": "2.5rem",
                    "padding": "0rem 0.75rem",
                    "borderRadius": "8px 8px 0px 0px",
                    "zIndex": "9993"
                },
        "info": [{
                    "name": "python",
                    "style": {"width": "100px"}
                }]
    }

def _info_bar(title: str) -> dict:
    return {
        **_CODE_BLOCK_INFO_BAR_BASE,
        "info": [{
            "name": title,
            "style": {"width": "100px"}
        }]
    }
_CODE_BLOCK_INFO_BAR_PYTHON = _info_bar("python")
_CODE_BLOCK_INFO_BAR_BASH = _info_bar("bash")

# Command execution model:
# - A background worker thread owns subprocess lifecycle and appends output into
#   st.session_state[command_state_<run_id>].
# - The Streamlit script thread never does blocking process IO; it only renders
#   status/output from that shared state.
# - While running, a fragment refreshes just the output panel on a short timer.
# - "Kill Process" sets stop_requested and sends SIGTERM to the process group.
# - Temp files (for python snippets) are cleaned up by the worker in finally.

def _process_state_key(run_id: str) -> str:
    return f"command_state_{run_id}"


def _get_command_state(run_id: str) -> dict | None:
    return st.session_state.get(_process_state_key(run_id))


def _terminate_process_group(pgid: int | None) -> bool:
    if not pgid:
        return False

    try:
        os.killpg(pgid, signal.SIGTERM)
        return True
    except (ProcessLookupError, PermissionError):
        return False

def _is_new_id(id: str) -> bool:
    handled_ids = st.session_state.setdefault("handled_ids", set())

    if id in handled_ids:
        return False

    handled_ids.add(id)
    return True

def _stop_running_process(run_id: str) -> bool:
    state = _get_command_state(run_id)
    if not state:
        return False

    state["stop_requested"] = True
    pgid = state.get("pgid")
    return _terminate_process_group(pgid)


def _run_command_worker(commands: list[str], state: dict, cwd: str = ".") -> None:
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    proc = None

    try:
        proc = subprocess.Popen(
            commands,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            env=env,
            cwd=cwd,
            start_new_session=True,
        )
        state["pid"] = proc.pid
        state["pgid"] = proc.pid

        assert proc.stdout is not None
        for line in proc.stdout:
            if state.get("stop_requested") and state.get("pgid"):
                _terminate_process_group(state["pgid"])
                break
            _append_command_output(state, line)

        rc = proc.wait()
        state["returncode"] = rc
        state["status"] = "stopped" if state.get("stop_requested") else "finished"
    except BaseException as exc:
        state["status"] = "failed"
        state["error"] = str(exc)
        if proc is not None and proc.poll() is None:
            _terminate_process_group(proc.pid)
    finally:
        state["running"] = False
        state["pgid"] = None
        cleanup_paths = state.get("cleanup_paths", [])
        for path in cleanup_paths:
            if os.path.exists(path):
                os.remove(path)


def _render_command_panel(
    title: str,
    run_id: str,
    output_lines: int = 10,
    on_finished: Callable[[str, dict], None] | None = None,
) -> None:
    state = _get_command_state(run_id)
    if not state:
        return

    with st.expander(title, expanded=True):
        if state.get("running"):
            if st.button(f"Kill Process", key=f"stop-button-{run_id}"):
                _stop_running_process(run_id)
        else:
            if state.get("status") == "stopped":
                st.error("Command was interrupted")
            elif state.get("status") == "failed":
                st.error(f"Command failed: {state.get('error', 'unknown error')}")
            elif state.get("returncode", 1) != 0:
                st.error(f"Command exited with code {state.get('returncode')}")
            else:
                st.success("Command exited with code 0")

        if state.get("output_truncated"):
            st.caption(f"Showing last {MAX_COMMAND_OUTPUT_LINES} lines of output.")

        at_max_lines = len(state.get("output_lines", [])) >= output_lines
        height = 21 * output_lines + 32 if at_max_lines else None
        st.code(state.get("output", ""), language=None, height=height)

    if not state.get("running") and on_finished is not None:
        on_finished(run_id, state)


@st.fragment(run_every=OUTPUT_REFRESH_RATE)
def _render_command_panel_fragment(
    title: str,
    run_id: str,
    output_lines: int = 10,
    on_finished: Callable[[str, dict], None] | None = None,
) -> None:
    _render_command_panel(title, run_id, output_lines, on_finished=on_finished)

def _render_command_output(
    title: str,
    run_id: str,
    output_lines: int = 10,
    on_finished: Callable[[str, dict], None] | None = None,
) -> None:
    state = _get_command_state(run_id)
    if state:
        if state.get("running"):
            _render_command_panel_fragment(title, run_id, output_lines, on_finished=on_finished)
        else:
            _render_command_panel(title, run_id, output_lines, on_finished=on_finished)

def run_command(
    commands: list[str],
    run_id: str,
    cleanup_paths: list[str] | None = None,
    cwd: str = ".",
) -> None:
    state = _get_command_state(run_id)
    if state and state.get("running"):
        return

    working_dir = os.path.abspath(cwd)

    state = {
        "running": True,
        "status": "running",
        "output": "",
        "output_lines": [],
        "output_truncated": False,
        "returncode": None,
        "error": "",
        "pid": None,
        "pgid": None,
        "stop_requested": False,
        "cleanup_paths": cleanup_paths or [],
        "working_dir": working_dir,
    }
    st.session_state[_process_state_key(run_id)] = state

    worker = threading.Thread(target=_run_command_worker, args=(commands, state, working_dir), daemon=True)
    worker.start()

def editable_bash_block(
    code: str,
    run_id: str,
    output_lines: int = 10,
    on_finished: Callable[[str, dict], None] | None = None,
) -> None:
    # create info bar dictionary
    response_dict = code_editor(code, lang="sh", buttons=_CODE_BLOCK_BUTTONS, info=_CODE_BLOCK_INFO_BAR_BASH)
    if response_dict['type'] == "submit" and _is_new_id(response_dict["id"]) and len(response_dict['text']) != 0:
        run_command(["bash", "-lc", response_dict['text']], run_id)
    _render_command_output("Bash Output", run_id, output_lines, on_finished=on_finished)


def make_pdf_display_callback(
    pdf_path: str,
    label: str = "Generated Plot",
    viewer_height: int = "stretch",
) -> Callable[[str, dict], None]:
    """Return a callback that shows a button to display a PDF when it exists."""

    def _on_finished(run_id: str, state: dict) -> None:
        if state.get("returncode", 1) != 0:
            return
        working_dir = state.get("working_dir") or os.getcwd()
        resolved_pdf_path = pdf_path if os.path.isabs(pdf_path) else os.path.join(working_dir, pdf_path)

        path_key = re.sub(r"[^a-zA-Z0-9_-]", "-", pdf_path)

        if not os.path.isfile(resolved_pdf_path):
            st.error(f"PDF not found at: {resolved_pdf_path}")
            return

        with st.expander(label, expanded=True):
            st.pdf(
                resolved_pdf_path,
                height=viewer_height,
                key=f"pdf-viewer-{run_id}-{path_key}",
            )

    return _on_finished

def _trim_outer_empty_lines(text: str) -> str:
    lines = text.splitlines()
    if lines and not lines[0].strip():
        lines = lines[1:]
    if lines and not lines[-1].strip():
        lines = lines[:-1]
    return "\n".join(lines)

def editable_python_block(code:str, run_id: str, python_env=PATCHED_PYTHON_BIN, output_lines=10) -> None:
    code = _trim_outer_empty_lines(code)
    # create info bar dictionary
    response_dict = code_editor(code, lang="python", buttons=_CODE_BLOCK_BUTTONS, info=_CODE_BLOCK_INFO_BAR_PYTHON)
    # each button press causes the `response_dict` to be returned. However, the ID changes, we can use this
    if response_dict['type'] == "submit" and _is_new_id(response_dict["id"]) and len(response_dict['text']) != 0:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as temp_script:
            temp_script.write(response_dict['text'])
            temp_script_path = temp_script.name
        python_path = os.getenv(python_env)
        if python_path and os.path.isfile(python_path):
            run_command([python_path, "-u", temp_script_path], run_id, cleanup_paths=[temp_script_path])
        else:
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)
            st.error(f"Unable to find the python binary. Used environment value `{python_env}`")
    _render_command_output("Python Output", run_id, output_lines)

