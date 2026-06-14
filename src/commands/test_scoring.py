"""Scoring and reporting helpers for test suite commands."""
import click
from dataclasses import dataclass
import json
import os
import statistics


@dataclass
class SuiteRunResult:
    case: str
    passed: bool
    runtime: float
    error: str
    output: str


@dataclass
class AggregatedSuiteResult:
    case: str
    passed: bool
    runtime: float
    error: str
    output: str
    runs: int
    passed_runs: int
    score_mean: float | None
    score_stdev: float
    numeric_runs: int


@dataclass
class PairResult:
    case: str
    valid: bool
    error: str
    score_a: float | None
    score_b: float | None
    diff: float | None


def aggregate_suite_results(raw_results, runs):
    grouped = {}
    for result in raw_results:
        grouped.setdefault(result.case, []).append(result)

    aggregate_results = []
    for case, case_results in grouped.items():
        numeric_outputs = []
        for result in case_results:
            try:
                numeric_outputs.append(parse_numeric_output(result.output))
            except ValueError:
                pass

        mean_output = statistics.mean(numeric_outputs) if numeric_outputs else None
        output = f"{mean_output}\n" if mean_output is not None else ""
        failed_runs = [result for result in case_results if not result.passed]
        aggregate_results.append(AggregatedSuiteResult(
            case=case,
            passed=not failed_runs and len(case_results) == runs,
            runtime=statistics.mean(result.runtime for result in case_results),
            error=_format_aggregate_error(failed_runs, len(case_results), runs),
            output=output,
            runs=len(case_results),
            passed_runs=len(case_results) - len(failed_runs),
            score_mean=mean_output,
            score_stdev=statistics.stdev(numeric_outputs) if len(numeric_outputs) > 1 else 0.0,
            numeric_runs=len(numeric_outputs),
        ))
    return aggregate_results


def _format_aggregate_error(failed_runs, actual_runs, expected_runs):
    if actual_runs != expected_runs:
        return f"expected {expected_runs} run(s), got {actual_runs}"
    if not failed_runs:
        return ""
    first_error = failed_runs[0].error
    return f"{len(failed_runs)}/{actual_runs} run(s) failed: {first_error}"


def format_suite_result_line(status, result, runs):
    if runs == 1:
        return f"{status} {result.case} ({result.runtime:.3f}s)"
    return (
        f"{status} {result.case} "
        f"({result.passed_runs}/{result.runs} runs, avg {result.runtime:.3f}s)"
    )


def report_noise_summary(results, runs):
    click.echo("\n--- Noise Summary ---")
    for result in results:
        if result.numeric_runs == runs:
            click.echo(
                f"{result.case}: mean={format_score(result.score_mean)} "
                f"stdev={result.score_stdev:.6f}"
            )
        else:
            click.echo(f"{result.case}: N/A ({result.numeric_runs}/{runs} numeric run(s))")


def load_best_known(best_known_file):
    if not os.path.exists(best_known_file):
        return {}
    with open(best_known_file, 'r') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise click.ClickException("--best-known must contain a JSON object")
    return data


def write_best_known(best_known_file, best_known):
    parent_dir = os.path.dirname(best_known_file)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    with open(best_known_file, 'w') as f:
        json.dump(best_known, f, indent=2, sort_keys=True)
        f.write("\n")


def report_relative_scores(results, best_known, score_mode, relative_scale, relative_round):
    click.echo("\n--- Relative Score ---")
    total = 0.0
    scored = 0
    scored_cases = []
    for result in results:
        case = result.case
        try:
            your_score = parse_numeric_output(result.output)
        except ValueError as exc:
            click.echo(f"{case}: N/A ({exc})")
            continue

        best_score = best_known.get(case)
        if best_score is None:
            click.echo(f"{case}: N/A (no best-known value)")
            continue

        try:
            relative_score = _relative_score(your_score, float(best_score), score_mode, relative_scale)
        except ValueError as exc:
            click.echo(f"{case}: N/A ({exc})")
            continue

        total += relative_score
        scored += 1
        points = round(relative_score) if relative_round else relative_score
        max_points = round(relative_scale) if relative_round else relative_scale
        scored_cases.append({
            "case": case,
            "points": points,
            "max_points": max_points,
            "loss": max(0, max_points - points),
        })
        click.echo(
            f"{case}: your={format_score(your_score)} "
            f"best={format_score(float(best_score))} "
            f"relative={relative_score:.6f}"
        )

    click.echo(f"Total relative score: {total:.6f} / {(scored * relative_scale):.6f}")
    _report_contest_score(scored_cases, relative_round)


def _report_contest_score(scored_cases, relative_round):
    if not scored_cases:
        return

    total_points = sum(case["points"] for case in scored_cases)
    max_points = sum(case["max_points"] for case in scored_cases)
    percent = total_points / max_points * 100 if max_points else 0.0
    if relative_round:
        click.echo(f"Contest score: {total_points} / {max_points} ({percent:.2f}% of max, rounded per case)")
    else:
        click.echo(f"Contest score: {total_points:.6f} / {max_points:.6f} ({percent:.2f}% of max)")

    click.echo("\n--- Relative Loss Ranking ---")
    for case in sorted(scored_cases, key=lambda item: item["loss"], reverse=True):
        if relative_round:
            click.echo(f"{case['case']}: loss={case['loss']} point(s)")
        else:
            click.echo(f"{case['case']}: loss={case['loss']:.6f} point(s)")


def update_best_known(results, best_known, score_mode):
    updated = 0
    for result in results:
        try:
            your_score = parse_numeric_output(result.output)
        except ValueError:
            continue

        current_best = best_known.get(result.case)
        if current_best is None or _is_better(your_score, float(current_best), score_mode):
            best_known[result.case] = your_score
            updated += 1
    return updated


def parse_numeric_output(output):
    tokens = output.strip().split()
    if not tokens:
        raise ValueError("empty output")
    try:
        return float(tokens[0])
    except ValueError as exc:
        raise ValueError("first output token is not numeric") from exc


def _relative_score(your_score, best_score, score_mode, relative_scale):
    if your_score <= 0 or best_score <= 0:
        raise ValueError("relative score requires positive numeric values")
    if score_mode == "min":
        return relative_scale * best_score / your_score
    return relative_scale * your_score / best_score


def _is_better(candidate, current_best, score_mode):
    if score_mode == "min":
        return candidate < current_best
    return candidate > current_best


def report_compare_results(pair_results, score_mode):
    pair_results.sort(key=lambda result: result.case)
    valid_results = [result for result in pair_results if result.valid]

    click.echo("\n--- Paired A/B Results ---")
    for result in pair_results:
        if not result.valid:
            click.echo(f"{result.case}: N/A ({result.error})")
            continue
        winner = _compare_winner(result.score_a, result.score_b, score_mode)
        click.echo(
            f"{result.case}: "
            f"A={format_score(result.score_a)} "
            f"B={format_score(result.score_b)} "
            f"diff(A-B)={result.diff:.6f} "
            f"winner={winner}"
        )

    if not valid_results:
        click.echo("\nSummary: 0 valid paired run(s)")
        return

    diffs = [result.diff for result in valid_results]
    a_wins = sum(1 for result in valid_results if _compare_winner(result.score_a, result.score_b, score_mode) == "A")
    b_wins = sum(1 for result in valid_results if _compare_winner(result.score_a, result.score_b, score_mode) == "B")
    ties = len(valid_results) - a_wins - b_wins

    click.echo(
        "\nSummary: "
        f"A wins {a_wins}/{len(valid_results)}, "
        f"B wins {b_wins}/{len(valid_results)}, "
        f"ties {ties}/{len(valid_results)}"
    )
    click.echo(f"Mean diff(A-B): {statistics.mean(diffs):.6f}")
    if len(diffs) > 1:
        click.echo(f"Diff stdev: {statistics.stdev(diffs):.6f}")
    else:
        click.echo("Diff stdev: 0.000000")


def report_noise_floor_results(pair_results):
    pair_results.sort(key=lambda result: result.case)
    valid_results = [result for result in pair_results if result.valid]

    click.echo("\n--- Noise Floor ---")
    for result in pair_results:
        if not result.valid:
            click.echo(f"{result.case}: N/A ({result.error})")
            continue
        click.echo(
            f"{result.case}: "
            f"run1={format_score(result.score_a)} "
            f"run2={format_score(result.score_b)} "
            f"abs-diff={abs(result.diff):.6f}"
        )

    if not valid_results:
        click.echo("\nSummary: 0 valid self-pair(s)")
        return

    diffs = [result.diff for result in valid_results]
    abs_diffs = [abs(diff) for diff in diffs]
    click.echo(f"\nSummary: {len(valid_results)} valid self-pair(s)")
    click.echo(f"Mean absolute diff: {statistics.mean(abs_diffs):.6f}")
    click.echo(f"Max absolute diff: {max(abs_diffs):.6f}")
    if len(diffs) > 1:
        click.echo(f"Signed diff stdev: {statistics.stdev(diffs):.6f}")
    else:
        click.echo("Signed diff stdev: 0.000000")


def _compare_winner(score_a, score_b, score_mode):
    if score_a == score_b:
        return "tie"
    if score_mode == "min":
        return "A" if score_a < score_b else "B"
    return "A" if score_a > score_b else "B"


def format_score(score):
    if score.is_integer():
        return str(int(score))
    return f"{score:.6f}"
