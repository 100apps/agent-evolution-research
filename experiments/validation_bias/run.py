"""Synthetic demonstration of repeated holdout selection bias in harness search."""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SEED = 20261008
TRIALS = 3000
ROUNDS = 16
CANDIDATES_PER_ROUND = 12
DEV_N = 80
HOLDOUT_N = 80
FINAL_TEST_N = 5000


def binomial_rate(rng: random.Random, probability: float, count: int) -> float:
    # Fast normal approximation to Binomial(n, p), clipped and quantized to 1/n.
    mean = count * probability
    standard_deviation = math.sqrt(count * probability * (1.0 - probability))
    successes = round(rng.gauss(mean, standard_deviation))
    return min(count, max(0, successes)) / count


def candidate_quality(rng: random.Random) -> float:
    # Most changes are neutral/slightly harmful; a minority are useful.
    base = rng.betavariate(24.0, 12.0)
    return min(0.92, max(0.42, base))


@dataclass(frozen=True)
class Candidate:
    round_index: int
    candidate_index: int
    true_quality: float
    dev_score: float
    holdout_score: float
    final_score: float


def generate_trial(seed: int) -> list[list[Candidate]]:
    rng = random.Random(seed)
    rounds: list[list[Candidate]] = []
    for round_index in range(ROUNDS):
        candidates: list[Candidate] = []
        for candidate_index in range(CANDIDATES_PER_ROUND):
            quality = candidate_quality(rng)
            candidates.append(
                Candidate(
                    round_index=round_index,
                    candidate_index=candidate_index,
                    true_quality=quality,
                    dev_score=binomial_rate(rng, quality, DEV_N),
                    holdout_score=binomial_rate(rng, quality, HOLDOUT_N),
                    final_score=binomial_rate(rng, quality, FINAL_TEST_N),
                )
            )
        rounds.append(candidates)
    return rounds


def choose_by_dev(candidates: list[Candidate]) -> Candidate:
    return max(candidates, key=lambda item: (item.dev_score, -item.candidate_index))


def mean_ci95(values: list[float]) -> dict[str, float]:
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    half = 1.96 * sd / math.sqrt(len(values))
    return {"mean": mean, "ci95_low": mean - half, "ci95_high": mean + half, "sd": sd}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    sealed_reported: list[float] = []
    sealed_final: list[float] = []
    reused_reported: list[float] = []
    reused_final: list[float] = []
    sealed_true: list[float] = []
    reused_true: list[float] = []
    curve_bias: dict[int, list[float]] = {round_count: [] for round_count in (1, 2, 4, 8, 16)}

    sample_trial: dict[str, object] | None = None
    for trial in range(TRIALS):
        rounds = generate_trial(SEED + trial)
        flat = [candidate for round_candidates in rounds for candidate in round_candidates]

        # Proper protocol: choose entirely by development data, freeze, then touch holdout once.
        sealed = max(flat, key=lambda item: (item.dev_score, -item.round_index, -item.candidate_index))

        # Leaky protocol: one dev winner per round, then select the round by reused holdout.
        round_winners = [choose_by_dev(candidates) for candidates in rounds]
        reused = max(
            round_winners,
            key=lambda item: (item.holdout_score, -item.round_index, -item.candidate_index),
        )

        sealed_reported.append(sealed.holdout_score)
        sealed_final.append(sealed.final_score)
        reused_reported.append(reused.holdout_score)
        reused_final.append(reused.final_score)
        sealed_true.append(sealed.true_quality)
        reused_true.append(reused.true_quality)

        for round_count in curve_bias:
            prefix_winners = round_winners[:round_count]
            prefix_selected = max(prefix_winners, key=lambda item: item.holdout_score)
            curve_bias[round_count].append(
                prefix_selected.holdout_score - prefix_selected.final_score
            )

        if trial == 0:
            sample_trial = {
                "sealed": sealed.__dict__,
                "reused_holdout": reused.__dict__,
                "round_winners": [candidate.__dict__ for candidate in round_winners],
            }

    sealed_bias = [reported - final for reported, final in zip(sealed_reported, sealed_final)]
    reused_bias = [reported - final for reported, final in zip(reused_reported, reused_final)]
    summary = {
        "experiment": "Independent validation and repeated holdout selection bias",
        "reproduction_level": "机制示例（合成统计模拟，不是论文基准复现）",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "trials": TRIALS,
        "rounds": ROUNDS,
        "candidates_per_round": CANDIDATES_PER_ROUND,
        "sample_sizes": {"development": DEV_N, "holdout": HOLDOUT_N, "final_test": FINAL_TEST_N},
        "sampling_note": "二项准确率使用正态近似并量化到 1/n；全部数据为合成。",
        "sealed_once": {
            "reported_holdout": mean_ci95(sealed_reported),
            "final_test": mean_ci95(sealed_final),
            "true_quality": mean_ci95(sealed_true),
            "optimism_reported_minus_final": mean_ci95(sealed_bias),
        },
        "reused_holdout": {
            "reported_holdout": mean_ci95(reused_reported),
            "final_test": mean_ci95(reused_final),
            "true_quality": mean_ci95(reused_true),
            "optimism_reported_minus_final": mean_ci95(reused_bias),
        },
        "bias_curve": {
            str(round_count): mean_ci95(values) for round_count, values in curve_bias.items()
        },
        "checks": {
            "reused_holdout_more_optimistic": statistics.fmean(reused_bias) > statistics.fmean(sealed_bias),
            "bias_increases_from_1_to_16_rounds": statistics.fmean(curve_bias[16]) > statistics.fmean(curve_bias[1]),
            "final_test_never_used_for_selection": True,
        },
        "sample_trial": sample_trial,
    }
    assert all(summary["checks"].values()), summary["checks"]

    (output_dir / "results.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (output_dir / "round_curve.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["holdout_uses", "mean_optimism", "ci95_low", "ci95_high", "sd"],
        )
        writer.writeheader()
        for round_count, values in curve_bias.items():
            stats = mean_ci95(values)
            writer.writerow({"holdout_uses": round_count, "mean_optimism": stats.pop("mean"), **stats})

    log_lines = [
        f"generated_at={summary['generated_at']}",
        f"seed={SEED}",
        f"trials={TRIALS}",
        f"configuration={json.dumps({k: summary[k] for k in ('rounds', 'candidates_per_round', 'sample_sizes')}, sort_keys=True)}",
        "sealed_once=" + json.dumps(summary["sealed_once"], sort_keys=True),
        "reused_holdout=" + json.dumps(summary["reused_holdout"], sort_keys=True),
        "bias_curve=" + json.dumps(summary["bias_curve"], sort_keys=True),
        "checks=" + json.dumps(summary["checks"], sort_keys=True),
    ]
    (output_dir / "run.log").write_text("\n".join(log_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
