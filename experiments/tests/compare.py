import argparse
import re
from dataclasses import dataclass


TESTS_PREFIX = "Total tests:"


@dataclass
class TestRunSummary:
    duration_seconds: int
    total_tests_run: int


def parse_user_time_to_seconds(line: str) -> int:
    match = re.match(r"^user\s+(.+)$", line, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Unable to parse user time line: '{line}'")

    duration_text = match.group(1).strip()
    total_seconds = 0.0
    has_value = False

    for value_text, unit in re.findall(r"(\d+(?:\.\d+)?)([hms])", duration_text, flags=re.IGNORECASE):
        has_value = True
        value = float(value_text)
        unit_lower = unit.lower()
        if unit_lower.startswith("h"):
            total_seconds += value * 3600
        elif unit_lower.startswith("m"):
            total_seconds += value * 60
        elif unit_lower.startswith("s"):
            total_seconds += value

    if not has_value:
        raise ValueError(f"Unable to parse user duration text: '{duration_text}'")

    return int(round(total_seconds))


def format_seconds(total_seconds: int) -> str:
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


def parse_total_tests_run(line: str) -> int:
    match = re.search(r"run\s*=\s*([\d,]+)", line, flags=re.IGNORECASE)
    if not match:
        raise ValueError(f"Unable to parse executed test count from line: '{line}'")
    return int(match.group(1).replace(",", ""))


def parse_make_test_output(path: str) -> TestRunSummary:
    user_time_line = None
    tests_line = None

    with open(path, "r", encoding="utf-8", errors="replace") as file_obj:
        for raw_line in file_obj:
            line = raw_line.strip()
            if re.match(r"^user\s+", line, flags=re.IGNORECASE):
                user_time_line = line
            elif line.startswith(TESTS_PREFIX):
                tests_line = line

    if user_time_line is None:
        raise ValueError(f"{path}: missing 'user' time line")
    if tests_line is None:
        raise ValueError(f"{path}: missing '{TESTS_PREFIX}' line")

    duration_seconds = parse_user_time_to_seconds(user_time_line)
    total_tests_run = parse_total_tests_run(tests_line)

    return TestRunSummary(duration_seconds=duration_seconds, total_tests_run=total_tests_run)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare CPython make test benchmark results")
    parser.add_argument("--baseline", required=True, help="Path to baseline make test output")
    parser.add_argument("--patched", required=True, help="Path to patched make test output")
    args = parser.parse_args()

    baseline = parse_make_test_output(args.baseline)
    patched = parse_make_test_output(args.patched)

    delta_seconds = patched.duration_seconds - baseline.duration_seconds
    abs_delta_seconds = abs(delta_seconds)

    if baseline.duration_seconds == 0:
        delta_percent_display = "n/a"
    else:
        delta_percent = (delta_seconds / baseline.duration_seconds) * 100
        delta_percent_display = f"{delta_percent:+.2f}%"

    if delta_seconds < 0:
        verdict = "patched is faster"
    elif delta_seconds > 0:
        verdict = "patched is slower"
    else:
        verdict = "same runtime"

    tests_delta = patched.total_tests_run - baseline.total_tests_run

    print("[done] make test comparison")
    print(f"    baseline user time: {format_seconds(baseline.duration_seconds)} ({baseline.duration_seconds} sec)")
    print(f"    patched user time:  {format_seconds(patched.duration_seconds)} ({patched.duration_seconds} sec)")
    print(f"    delta user time (patched - baseline): {delta_seconds:+d} sec")
    print(f"    absolute delta user time: {abs_delta_seconds} sec")
    print(f"    delta percent: {delta_percent_display}")
    print(f"    verdict: {verdict}")
    print(f"    baseline tests executed: {baseline.total_tests_run:,}")
    print(f"    patched tests executed:  {patched.total_tests_run:,}")
    print(f"    test execution delta (patched - baseline): {tests_delta:+,}")


if __name__ == "__main__":
    main()
