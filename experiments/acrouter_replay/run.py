#!/usr/bin/env python3
"""Replay the public ACRouter OOD matrix without executing author code.

This is an artifact replay over historical cells, not a live agent rollout.
Only the Python standard library is used.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "matrix_acrouter_ood176.json"
EXPECTED_SHA256 = "f0fe49db24cf2c1d5552a1dd512544676825e0e4f34e136f194fecd9c022c15a"
CHEAP_CHAIN = ["MiniMax-M2.7", "kimi-k2.5", "gpt-5.4", "glm-5"]
ESCALATION_MODEL = "claude-opus-4-6"


@dataclass
class Decision:
    task_id: str
    chosen_model: str
    resolved: bool
    attempts: list[str]
    apply_ok_count: int
    escalated: bool
    total_cost_usd: float
    oracle_model: str
    oracle_utility: float
    achieved_utility: float
    regret: float


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def oracle(row: dict[str, dict[str, Any]]) -> tuple[str, float]:
    scored = [
        (model, float(cell["resolved"]) - 0.1 * float(cell["cost_usd"]))
        for model, cell in row.items()
    ]
    return max(scored, key=lambda item: (item[1], item[0]))


def make_decision(
    task_id: str,
    row: dict[str, dict[str, Any]],
    attempts: list[str],
    chosen_model: str,
    resolved: bool,
    apply_ok_count: int,
    escalated: bool,
) -> Decision:
    total_cost = sum(float(row[model]["cost_usd"]) for model in attempts)
    oracle_model, oracle_utility = oracle(row)
    achieved_utility = float(resolved) - 0.1 * total_cost
    return Decision(
        task_id=task_id,
        chosen_model=chosen_model,
        resolved=resolved,
        attempts=attempts,
        apply_ok_count=apply_ok_count,
        escalated=escalated,
        total_cost_usd=total_cost,
        oracle_model=oracle_model,
        oracle_utility=oracle_utility,
        achieved_utility=achieved_utility,
        regret=oracle_utility - achieved_utility,
    )


def replay_chain(
    task_id: str,
    row: dict[str, dict[str, Any]],
    escalation: str,
) -> Decision:
    attempts: list[str] = []
    apply_ok_count = 0
    chosen_model = CHEAP_CHAIN[-1]
    resolved = False
    for model in CHEAP_CHAIN:
        attempts.append(model)
        cell = row[model]
        apply_ok_count += int(bool(cell["apply_ok"]))
        chosen_model = model
        resolved = bool(cell["resolved"])
        if resolved:
            break

    escalated = False
    chain_failed = not resolved and len(attempts) == len(CHEAP_CHAIN)
    should_escalate = chain_failed and (
        escalation == "always" or (escalation == "gated" and apply_ok_count >= 2)
    )
    if should_escalate:
        escalated = True
        attempts.append(ESCALATION_MODEL)
        if bool(row[ESCALATION_MODEL]["resolved"]):
            chosen_model = ESCALATION_MODEL
            resolved = True
        # If escalation fails, the specified policy retains glm-5 as chosen_model.

    return make_decision(
        task_id,
        row,
        attempts,
        chosen_model,
        resolved,
        apply_ok_count,
        escalated,
    )


def replay_single(task_id: str, row: dict[str, dict[str, Any]], model: str) -> Decision:
    cell = row[model]
    return make_decision(
        task_id,
        row,
        [model],
        model,
        bool(cell["resolved"]),
        int(bool(cell["apply_ok"])),
        False,
    )


def summarize(name: str, decisions: list[Decision]) -> dict[str, Any]:
    n = len(decisions)
    resolved = sum(decision.resolved for decision in decisions)
    total_cost = sum(decision.total_cost_usd for decision in decisions)
    return {
        "name": name,
        "tasks": n,
        "resolved_tasks": resolved,
        "avg_perf_percent": 100.0 * resolved / n,
        "cumulative_regret": sum(decision.regret for decision in decisions),
        "historical_estimated_total_cost_usd": total_cost,
        "escalations": sum(decision.escalated for decision in decisions),
        "avg_steps": sum(len(decision.attempts) for decision in decisions) / n,
        "mean_cost_usd": total_cost / n,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    actual_sha256 = sha256(DATA_PATH)
    if actual_sha256 != EXPECTED_SHA256:
        raise SystemExit(
            f"matrix SHA256 mismatch: expected {EXPECTED_SHA256}, got {actual_sha256}"
        )

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    ids: list[str] = payload["ids"]
    matrix: dict[str, dict[str, dict[str, Any]]] = payload["matrix"]
    models: list[str] = payload["models"]
    if len(ids) != 176 or set(ids) != set(matrix):
        raise SystemExit("matrix task count or IDs do not match the public artifact")

    policies: list[tuple[str, Callable[[str, dict[str, dict[str, Any]]], Decision]]] = []
    for model in models:
        policies.append((f"single::{model}", lambda task_id, row, m=model: replay_single(task_id, row, m)))
    policies.extend(
        [
            ("cheap_chain", lambda task_id, row: replay_chain(task_id, row, "never")),
            ("cheap_chain_then_opus_no_gate", lambda task_id, row: replay_chain(task_id, row, "always")),
            ("original_apply_ok_gate", lambda task_id, row: replay_chain(task_id, row, "gated")),
        ]
    )

    summaries: dict[str, dict[str, Any]] = {}
    all_decisions: dict[str, list[Decision]] = {}
    for name, policy in policies:
        decisions = [policy(task_id, matrix[task_id]) for task_id in ids]
        all_decisions[name] = decisions
        summaries[name] = summarize(name, decisions)

    original = summaries["original_apply_ok_gate"]
    reference_checks = {
        "tasks_176": original["tasks"] == 176,
        "avg_perf_rounds_to_73_30": round(original["avg_perf_percent"], 2) == 73.30,
        "cumulative_regret_rounds_to_15_9": round(original["cumulative_regret"], 1) == 15.9,
        "historical_cost_rounds_to_86_72": round(
            original["historical_estimated_total_cost_usd"], 2
        )
        == 86.72,
        "escalations_29": original["escalations"] == 29,
        "avg_steps_rounds_to_2_66": round(original["avg_steps"], 2) == 2.66,
    }

    result = {
        "experiment_type": "公开历史矩阵的离线制品回放（不是实时 Agent 运行）",
        "implementation": "独立 Python 标准库实现；未执行作者仓库脚本",
        "randomness": "none; deterministic iteration in published ids order",
        "source": {
            "repository": "https://github.com/LanceZPF/agent-as-a-router",
            "commit": "e43839edb0d5d0a9feec2f7078019406ab4d64bd",
            "artifact": "data/matrices/phase2_ood/unified/matrix_acrouter_ood176.json",
            "sha256": actual_sha256,
            "artifact_summary": payload.get("summary", {}),
        },
        "policy": {
            "cheap_chain": CHEAP_CHAIN,
            "escalation_model": ESCALATION_MODEL,
            "gate": "only after all four cheap models fail and apply_ok count >= 2",
            "utility": "resolved - 0.1 * total_attempt_cost_usd",
            "oracle": "per-task max over one-model utilities",
        },
        "summaries": summaries,
        "reference_checks": reference_checks,
        "audit_boundaries": [
            "Costs are historical estimates stored in the public matrix; this run made no model API calls and incurred no API charges.",
            "The 176 rows combine old112 and new64 source batches; new64 aliases model labels and does not form a same-version live leaderboard.",
            "This replay implements the published artifact's ID/source/dimension grouping path, not online 0.8B embedding plus k-NN memory voting.",
            "The artifact reference AvgPerf 73.30 is separate from the arXiv v3 Table 3 OOD result 62.50.",
        ],
    }
    (output_dir / "results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    with (output_dir / "decisions.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "policy",
                "task_id",
                "chosen_model",
                "resolved",
                "attempts",
                "apply_ok_count",
                "escalated",
                "total_cost_usd",
                "oracle_model",
                "oracle_utility",
                "achieved_utility",
                "regret",
            ],
        )
        writer.writeheader()
        for policy_name, decisions in all_decisions.items():
            for decision in decisions:
                row = asdict(decision)
                row["policy"] = policy_name
                row["attempts"] = " -> ".join(decision.attempts)
                writer.writerow(row)

    print(json.dumps({"original": original, "checks": reference_checks}, ensure_ascii=False, indent=2))
    if not all(reference_checks.values()):
        raise SystemExit("one or more public-reference checks failed")


if __name__ == "__main__":
    main()
