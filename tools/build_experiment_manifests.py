#!/usr/bin/env python3
"""Write machine-readable provenance records for the three completed runs."""

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save(name: str, payload: dict) -> None:
    folder = ROOT / "experiments" / name
    payload["code"] = {
        "path": f"experiments/{name}/run.py",
        "sha256": sha256(folder / "run.py"),
        "repository_commit": "see enclosing Git commit",
    }
    payload["environment"] = {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "external_model_calls": 0,
        "paid_api_cost_usd": 0,
    }
    payload["outputs"] = [
        {
            "path": f"experiments/{name}/{filename}",
            "sha256": sha256(folder / filename),
            "bytes": (folder / filename).stat().st_size,
        }
        for filename in payload.pop("output_files")
    ]
    (folder / "experiment_manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> None:
    router_dir = ROOT / "experiments" / "acrouter_replay"
    router = json.loads((router_dir / "results.json").read_text(encoding="utf-8"))
    original = router["summaries"]["original_apply_ok_gate"]
    save(
        "acrouter_replay",
        {
            "schema_version": 1,
            "evidence_level": "公开工件回放",
            "command": "python experiments/acrouter_replay/run.py --output-dir <OUTPUT_DIR>",
            "determinism": "无随机数；按发布 ids 顺序确定性遍历",
            "seed": None,
            "input_files": [
                {
                    "path": "experiments/acrouter_replay/data/matrix_acrouter_ood176.json",
                    "sha256": sha256(router_dir / "data" / "matrix_acrouter_ood176.json"),
                    "shape": "176 tasks × 8 model backends",
                }
            ],
            "configuration": router["policy"],
            "expected": {
                "source": "发布工件参考检查",
                "avg_perf_percent_rounded_2": 73.30,
                "cumulative_regret_rounded_1": 15.9,
                "historical_cost_usd_rounded_2": 86.72,
                "escalations": 29,
                "avg_steps_rounded_2": 2.66,
            },
            "actual": {
                "avg_perf_percent": original["avg_perf_percent"],
                "cumulative_regret": original["cumulative_regret"],
                "historical_estimated_total_cost_usd": original["historical_estimated_total_cost_usd"],
                "escalations": original["escalations"],
                "avg_steps": original["avg_steps"],
                "reference_checks": router["reference_checks"],
            },
            "tolerance": "按发布参考口径分别四舍五入到 2、1、2、整数、2 位；逐题字段要求精确",
            "boundary": "固定顺序 cascade 的发布矩阵重放；非跨任务在线学习；数值与论文 v3 Table 3 口径不同",
            "output_files": ["results.json", "decisions.csv", "run.log"],
        },
    )

    evo_dir = ROOT / "experiments" / "evoc2f_scheduler"
    evo = json.loads((evo_dir / "results.json").read_text(encoding="utf-8"))
    save(
        "evoc2f_scheduler",
        {
            "schema_version": 1,
            "evidence_level": "合成机制实验",
            "command": "python experiments/evoc2f_scheduler/run.py --output-dir <OUTPUT_DIR>",
            "determinism": "任务图和故障注入确定；线程计时与冲突交错非完全确定",
            "seed": evo["seed"],
            "input_files": [{"path": "experiments/evoc2f_scheduler/run.py", "sha256": sha256(evo_dir / "run.py")}],
            "configuration": {"repeats": evo["repeats"], "task_graph": evo["task_graph"]},
            "expected": {
                "effect_aware_equivalent_runs": evo["repeats"],
                "dependency_only_equivalent_runs_max": evo["repeats"] - 1,
                "retry_attempts": 2,
                "inventory": 13,
            },
            "actual": {
                "effect_aware_equivalent_runs": evo["modes"]["effect_aware"]["equivalent_runs"],
                "dependency_only_equivalent_runs": evo["modes"]["dependency_only"]["equivalent_runs"],
                "checks": evo["checks"],
                "effect_aware_speedup_vs_serial": evo["effect_aware_speedup_vs_serial"],
            },
            "tolerance": "语义检查精确；墙钟速度只作信息性指标，不设论文指标容差",
            "boundary": "合成 DAG 机制示例，不是 EvoC2F 数据集或端到端论文结果复现",
            "output_files": ["results.json", "runs.csv", "run.log"],
        },
    )

    bias_dir = ROOT / "experiments" / "validation_bias"
    bias = json.loads((bias_dir / "results.json").read_text(encoding="utf-8"))
    save(
        "validation_bias",
        {
            "schema_version": 1,
            "evidence_level": "合成机制实验",
            "command": "python experiments/validation_bias/run.py --output-dir <OUTPUT_DIR>",
            "determinism": "Python random.Random 使用每 trial 固定 seed；单线程确定性",
            "seed": bias["seed"],
            "input_files": [{"path": "experiments/validation_bias/run.py", "sha256": sha256(bias_dir / "run.py")}],
            "configuration": {
                "trials": bias["trials"],
                "rounds": bias["rounds"],
                "candidates_per_round": bias["candidates_per_round"],
                "sample_sizes": bias["sample_sizes"],
            },
            "expected": {
                "checks": {name: True for name in bias["checks"]},
                "numeric_source": "锁定代码与 seed 的已提交结果",
            },
            "actual": {
                "sealed_optimism": bias["sealed_once"]["optimism_reported_minus_final"],
                "reused_optimism": bias["reused_holdout"]["optimism_reported_minus_final"],
                "checks": bias["checks"],
            },
            "tolerance": "同 Python 主版本精确；跨实现比较均值绝对误差 <= 1e-12",
            "boundary": "所有数据均为合成，不对应任一论文数据集",
            "output_files": ["results.json", "round_curve.csv", "run.log"],
        },
    )
    print(json.dumps({"written": 3, "python": sys.version.split()[0]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
