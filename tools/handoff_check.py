#!/usr/bin/env python3
"""Check whether a newcomer Agent can locate the required continuation facts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def contains(path: str, *needles: str) -> bool:
    text = (ROOT / path).read_text(encoding="utf-8")
    return all(needle in text for needle in needles)


def main() -> None:
    checks = {
        "purpose_found": contains("README.md", "Agent 自动优化 / Agent 进化研究", "41 个视频条目"),
        "scope_found": contains("README.md", "38 份核心论文 PDF", "1 份补充论文 SkVM"),
        "evidence_boundaries_found": contains(
            "RESEARCH_STATUS.md", "完整论文复现：0", "缩小真实实验：0", "公开发布工件回放"
        ),
        "next_questions_found": contains(
            "BACKLOG.md", "P1：ACRouter", "P2：JitRL", "P3：记忆", "验收", "费用/模型"
        ),
        "rerun_command_found": contains(
            "README.md", "python tools/research.py all --output-dir run_outputs/clean-run"
        ),
        "agent_first_steps_found": contains(
            "AGENTS.md", "首次打开必须按此顺序", "git status --short", "核验输入哈希"
        ),
        "stable_registry_found": (ROOT / "metadata" / "paper_registry.json").is_file(),
        "templates_found": all(
            (ROOT / "templates" / name).is_file()
            for name in ("paper_analysis.md", "experiment_record.md", "finding.md")
        ),
    }
    result = {
        "perspective": "陌生 Agent 仅从仓库文档开始",
        "can_find_purpose_scope_status_next_steps_and_rerun": all(checks.values()),
        "checks": checks,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not all(checks.values()):
        raise SystemExit("handoff contract incomplete")


if __name__ == "__main__":
    main()
