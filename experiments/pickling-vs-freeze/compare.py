import argparse
import json
from statistics import geometric_mean, mean, stdev


EXPECTED_EXPERIMENTS = ["dict-int", "dict-student", "tuple", "binary-tree"]


def summarize(durations_ms):
    if not durations_ms:
        raise ValueError("Cannot summarize empty measurements")

    return {
        "mean": mean(durations_ms),
        "gmean": geometric_mean(durations_ms),
        "std": stdev(durations_ms) if len(durations_ms) > 1 else 0.0,
        "min": min(durations_ms),
        "max": max(durations_ms),
    }


def print_summary_row(experiment_name, bench_type, summary, relative_to_fastest):
    rel_display = "" if abs(relative_to_fastest - 1.0) < 1e-9 else f"{relative_to_fastest:2.1f}x"
    print(
        f"| {experiment_name:23} | {bench_type:8} | {summary['mean']:7.2f} | {rel_display:4} | {summary['gmean']:7.2f} | "
        f"{summary['std']:7.2f} | {summary['min']:7.2f} | {summary['max']:7.2f} |"
    )


def load_results(path):
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if payload.get("benchmark") != "pickling-vs-freeze":
        raise ValueError(f"{path} is not a pickling-vs-freeze benchmark result file")

    mode = payload.get("mode")
    if mode not in {"freeze", "pickle"}:
        raise ValueError(f"{path} has invalid mode '{mode}'")

    return payload


def validate_compatibility(freeze_payload, pickle_payload):
    for key in ["dict_size", "num_trials", "value_length"]:
        if freeze_payload.get(key) != pickle_payload.get(key):
            raise ValueError(
                f"Input files are incompatible: '{key}' differs "
                f"({freeze_payload.get(key)} vs {pickle_payload.get(key)})"
            )


def main():
    parser = argparse.ArgumentParser("Compare freezing and pickling benchmark data")
    parser.add_argument("--freeze", required=True, help="Path to JSON generated with --collect freeze")
    parser.add_argument("--pickle", required=True, help="Path to JSON generated with --collect pickle")
    args = parser.parse_args()

    freeze_payload = load_results(args.freeze)
    pickle_payload = load_results(args.pickle)

    if freeze_payload["mode"] != "freeze":
        raise ValueError(f"{args.freeze} is mode '{freeze_payload['mode']}', expected 'freeze'")
    if pickle_payload["mode"] != "pickle":
        raise ValueError(f"{args.pickle} is mode '{pickle_payload['mode']}', expected 'pickle'")

    validate_compatibility(freeze_payload, pickle_payload)

    print("| Experiment              | Type     | Mean    | Rel  | GeoMean | StdDev  | Min     | Max     |")
    print("| ----------------------- | -------- | ------- | ---- | ------- | ------- | ------- | ------- |")

    freeze_results = freeze_payload.get("results", {})
    pickle_results = pickle_payload.get("results", {})

    for experiment_name in EXPECTED_EXPERIMENTS:
        freeze_ms = freeze_results.get(experiment_name, {}).get("freeze_ms")
        pickle_ms = pickle_results.get(experiment_name, {}).get("pickle_ms")
        unpickle_ms = pickle_results.get(experiment_name, {}).get("unpickle_ms")

        if freeze_ms is None:
            raise ValueError(f"Missing freeze_ms for experiment '{experiment_name}'")
        if pickle_ms is None:
            raise ValueError(f"Missing pickle_ms for experiment '{experiment_name}'")
        if unpickle_ms is None:
            raise ValueError(f"Missing unpickle_ms for experiment '{experiment_name}'")

        pickling_ms = [x + y for x, y in zip(pickle_ms, unpickle_ms)]

        summaries = {
            "freeze": summarize(freeze_ms),
            "pickle": summarize(pickle_ms),
            "unpickle": summarize(unpickle_ms),
            "pickling": summarize(pickling_ms),
        }

        fastest_mean = min(summary["mean"] for summary in summaries.values())

        for bench_type in ["freeze", "pickle", "unpickle", "pickling"]:
            summary = summaries[bench_type]
            relative_to_fastest = summary["mean"] / fastest_mean
            print_summary_row(experiment_name, bench_type, summary, relative_to_fastest)

    print()
    print(f"Items per data structure: {freeze_payload['dict_size']}")
    print(f"Trials per structure: {freeze_payload['num_trials']}")
    print(f"Freeze seed: {freeze_payload['initial_seed']}")
    print(f"Pickle seed: {pickle_payload['initial_seed']}")
    print(f"Time in MS")


if __name__ == "__main__":
    main()
