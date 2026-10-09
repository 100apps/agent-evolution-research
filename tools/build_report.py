#!/usr/bin/env python3
"""Build the self-contained offline HTML report from verified local artifacts."""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Template
from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "index.html"


def load_json(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


ANNOTATIONS = {
    1: ("Harness / 编排", "外部状态", "把提示、检索、记忆和代码 harness 作为可改写整体。", "分类、数学与 TerminalBench-2；完整轨迹搜索优于压缩反馈。", "TB2 搜索/评估同 89 题，成本和强 proposer 贡献未充分拆开。"),
    2: ("技能 / 记忆", "外部状态", "从强模型轨迹构建规划—功能—原子三级技能库。", "BFCL-v3 与 AppWorld 多模型对照，公开部分技能与代码。", "按测试集性能停止迭代会引入选择偏差，跨环境迁移仍有限。"),
    3: ("技能 / 记忆", "外部状态", "把长篇技能压缩为带 AVOID 的策略 Gene。", "45 个科学编程场景；Flash 提升而 Pro 基本不变。", "checkpoint 分不等于整题成功，等预算和信息量控制不完整。"),
    4: ("技能 / 记忆", "外部状态", "从成功/失败轨迹并行归纳可携带技能目录。", "v5 使用独立进化/留出切分，电子表格资产已发布。", "最大单项提升不能代表平均；跨模型迁移也存在负例。"),
    5: ("技能 / 记忆", "外部状态", "在多用户会话之间创建、修订、验证并同步共享技能。", "8 个模拟用户、6 轮演化，四类任务报告 best-skill。", "缺独立未见用户/任务协议；best-so-far 曲线含选择效应与隐私风险。"),
    6: ("权重 / 训练", "更新权重", "训练时逐步撤去技能，让策略参数内化其作用。", "Qwen2.5-VL 3B/7B 在 ALFWorld、Search-QA、WebShop 上评测。", "需要 4×H800；视觉压缩与训练收益混杂，并非免训练上下文学习。"),
    7: ("权重 / 训练", "权重 + 外部库", "联合学习技能检索、执行与轨迹蒸馏。", "ALFWorld 有多种子显著性；WebShop 增益仅 0.6pp。", "8×H800 全参 RL；信用分配是代理信号而非无偏因果贡献。"),
    8: ("Harness / 编排", "外部状态", "以可下钻轨迹、manifest 和文件级回滚演化 coding harness。", "TB2 69.7→77.0；迁移 SWE-Verified 只提升 0.4pp 但降 token。", "同基准搜索评测且仅一轮 campaign；回归预测 recall 很低。"),
    9: ("Harness / 编排", "外部为主；可选权重", "在同一未重置 episode 内持续更新提示、子代理、技能和记忆。", "Pokémon 阶段性里程碑、导航技能与共同训练案例。", "弱模型反而退化；接口、teacher 和更多交互时间的贡献未拆开。"),
    10: ("技能 / 记忆", "外部状态", "从每份长上下文自出题、自评并形成可回放技能。", "CL-bench 500 上下文/1899 任务，多代 GPT 均有提升。", "约 3 万美元探索成本；共享上下文和 LLM judge 使因果归因复杂。"),
    11: ("权重 / 训练", "更新权重 + 数据", "依据当前策略弱点动态合成并验证新训练任务。", "对 GRPO 的直接增量在 AppWorld/BFCL 上为数个百分点。", "强探索模型与可执行环境是关键资源，完整训练代码尚未核实可用。"),
    12: ("技能 / 记忆", "外部状态", "把技能文件、测试、经验和长期记忆纳入完整生命周期。", "SkillsBench 75 任务与 SkillLearnBench；覆盖率按全分母报告。", "同题成功轨迹蒸馏再重跑易乐观，官方实现未验证。"),
    13: ("技能 / 记忆", "外部状态", "从客服工单诊断失败并最小增量修改领域技能。", "1,883 工单按时间分片，五场景留出评测。", "私有数据/模型且 LLM judge 口径复杂；领域与通用基线信息不等价。"),
    14: ("Harness / 编排", "外部状态", "用资源协议与 Reflect→Select→Improve→Evaluate→Commit 管理可回滚演化。", "GPQA/AIME、GAIA/HLE 和 LeetCode 上报告多类结果。", "协议兼容多优化器不等于都验证过；安全依赖 Accept 判定。"),
    15: ("Harness / 编排", "外部状态", "让 meta-agent 修改搜索机制或内层 agent 代码。", "Terminal-Bench、ARC-AGI-2 与开放优化任务。", "每轮成本约基线 3 倍、Best@3 且代码资产缺失，因果与稳定性有限。"),
    16: ("提示 / 反馈", "外部状态", "聚合不同客户端本地优化后的文本提示。", "同构/异构客户端及 11B→3B 迁移对照。", "提示不是数学梯度；隐私、恶意客户端与长度预算未解决。"),
    17: ("提示 / 反馈", "外部状态", "用语言批评提出方向，再以 beam/bandit 搜索离散提示。", "四个分类任务及同预算搜索消融。", "可能以测试分数择优；错误反馈会改窄任务或翻转标签。"),
    18: ("提示 / 反馈", "外部文本变量", "在计算图上传播语言反馈并改写提示、答案或代码。", "推理、代码、多模态和科学优化多域实验。", "强反馈模型与额外调用是重要资源；版本表格存在口径差异。"),
    19: ("工程案例", "外部软件状态", "把专家修正、可追溯生产日志和回归测试接入工程改进闭环。", "官方案例报告 7000 份申报、吞吐与字段完成率变化。", "非论文、无随机对照；有人审查且不同百分比口径不可拼接。"),
    20: ("综述 / 评论", "不适用", "把 vibe coding 与 Agent 自进化统一为反馈驱动工程循环。", "观点视频，用于连接合集概念。", "没有一一对应的独立论文或可核验实验，报告不把它计入论文结果。"),
    21: ("提示 / 反馈", "提示 + 奖励模型权重", "进化跨任务系统提示，并用训练过的奖励模型排序。", "42 个域内任务与 5 个外域基准；系统/任务提示组合。", "完整规模含 9000 组件与 10 万偏好对；组合对 ProTeGi 的 p=0.053。"),
    22: ("权重 / 训练", "权重 + 外部记忆", "先把轨迹蒸馏为原则记忆，再以 GRPO 更新策略。", "七个 QA 集；3B/7B 模型及记忆消融。", "无检索性能下降说明未完全内化；原则效用是相关而非因果。"),
    23: ("预测 / 筛选", "训练预测器，不改目标模型", "用 100 步 probe 与静态特征预测完整微调结果。", "1300+ 完整 LoRA 运行，MMLU R²=.99。", "预测器本身依赖大量历史真值；跨目标模型需重新训练。"),
    24: ("权重 / 训练", "权重 + 外部技能", "把通用技能内化，把场景技能保留在检索库。", "ALFWorld/WebShop 的 ID/OOD 分层训练。", "OOD 测试仍提供新专项技能；人工技能分层和 rollout 噪声限制外推。"),
    25: ("权重 / 训练", "更新权重", "把真实奖励规则写入训练 prompt 以引导 RL 探索。", "Knights & Knaves 与数学基准的 GRPO 对照。", "冻结模型提示对照不等于训练收益；弱模型提升仍有限。"),
    26: ("预测 / 筛选", "不改目标模型", "用 SAE 特征预测微调影响幅度。", "三类 7B–9B 模型跨域相关约 .77–.81。", "只预测变化大小、不预测正负；需要白盒激活和匹配 SAE。"),
    27: ("权重 / 训练", "更新权重", "分别学习计划可执行性与执行遵循度。", "ALFWorld/ScienceWorld 五次运行，并主动报告短任务负面结果。", "数据收集需数十小时多 rollout；协调分是代理指标。"),
    28: ("路由 / 选择", "外部状态 + 小路由器", "基于任务、记忆、成本与反馈选择后端模型。", "论文 v3 与最新仓库制品都可核验；本报告做了 OOD176 独立回放。", "最新 JSON 混合模型版本；工件级级联不等于论文在线 0.8B+kNN 全闭环。"),
    29: ("GUI / 记忆", "权重 + 外部记忆", "把 GUI 轨迹、规则和成功摘要用于检索，并以 SFT/GRPO 训练。", "ScreenSpot、AndroidControl、GUIOdyssey、AndroidWorld。", "表内 75.8/73.8 冲突；默认仓库配置不等于论文设置。"),
    30: ("Harness / 编排", "外部状态", "把工具调用编译为带依赖、效应、重试和幂等性的 Plan IR。", "StableToolBench、ShortcutsBench 与 ToolSeq-500。", "正确性依赖保守效应标注；真实 API 与完整训练预算门槛高。"),
    31: ("综述 / 评论", "补充：外部状态", "视频综述 Agent 自进化难点，并在 06:15 引用 SkVM。", "补充下载 SkVM v3，研究技能能力适配、AOT/JIT 与回退。", "视频本身无核心论文；SkVM 单列补充，不能当作第 42 个视频。"),
    32: ("运行时 / 系统", "外部运行时状态", "以可逆 effect 与 reactive coeffect 管理组件生命周期。", "形式化定理、TypeScript 实现及 Koishi 生态案例。", "逆操作正确性由作者承担，语言代理不是恶意代码沙箱。"),
    33: ("技能 / 记忆", "外部非参数记忆", "从相似状态经验估计动作优势并重加权冻结模型策略。", "WebArena、Jericho 与跨任务记忆对照。", "公开代码概率加法/argmax 与论文 logit-softmax 公式不一致。"),
    34: ("Harness / 编排", "外部状态", "用 clade 未来潜力估计与 Thompson sampling 搜索 agent 后代。", "SWE/Polyglot 的相关、成功率和 CPU-hour。", "理论依赖真实 CMP oracle；实际估计与约 5000 美元实验不能证明全局最优。"),
    35: ("Harness / 编排", "生成器权重 + 外部 archive", "训练按任务生成/修复 harness 的模型，部署时冻结并积累 archive。", "9 基准、多执行模型与成本/延迟比较。", "公开 27B 是蒸馏初始版本，训练数据与预算细节不足。"),
    36: ("技能 / 记忆", "外部状态", "把不可改轨迹编译为持续 wiki，再生成经验证的技能。", "五模型五基准、三次演化与 bootstrap。", "小验证集反复选择会过拟合；存在明显负迁移。"),
    37: ("技能 / 记忆", "外部状态", "跨重复 episode 演化提示、记忆、超参和 Python 工具。", "六个 Jericho 游戏、50 episode 与同模型控制。", "固定任务策略性过拟合，且依赖强 evolver；不是跨任务持续学习。"),
    38: ("拓扑 / 多代理", "外部状态", "分阶段优化单代理提示、系统拓扑和联合提示。", "8 个混合指标任务与开放模型补表。", "未确认官方实现，主表任务子集小且不同方法优化器不完全可比。"),
    39: ("Harness / 编排", "外部状态", "大规模自动研究筛出 Action Fusion、上下文压缩和证据保留机制。", "535 环境、3000+ run；能力—token—费用多 operating point。", "省 token 伴随分数下降；51 题中 11 题用于接受决定，不能称全未见。"),
    40: ("运行时 / 系统", "基础设施状态", "按需加载沙盒层、资源回收和 CPU QoS 提升训练吞吐。", "10 节点 8192 容器与存储/内存/QoS 指标。", "未含 RL 框架端到端质量，且只公开部分存储组件。"),
    41: ("权重 / 训练", "权重 + 可执行技能库", "在连续任务中生成可执行函数，并用 skill-integrated reward 训练复用。", "AppWorld Test-Normal/Challenge 与 reward、检索、任务链消融。", "完整训练 32×H100 且前置闭源教师；不适合普通单机原数复现。"),
}


THEME_COLORS = {
    "Harness / 编排": "violet",
    "技能 / 记忆": "cyan",
    "权重 / 训练": "orange",
    "提示 / 反馈": "green",
    "预测 / 筛选": "blue",
    "路由 / 选择": "pink",
    "GUI / 记忆": "cyan",
    "拓扑 / 多代理": "violet",
    "运行时 / 系统": "slate",
    "工程案例": "green",
    "综述 / 评论": "slate",
}

ALIASES = {
    1: "Meta Harness",
    6: "SkillZero Skill 0",
    8: "AHE Agentic Harness Engineering",
    10: "Ctx2Skill Context to Skills",
    12: "MUSE Autoskill",
    15: "AEvo Harnessing Agentic Evolution",
    16: "FedTextGrad",
    17: "ProTeGi APO Automatic Prompt Optimization",
    18: "TextGrad",
    21: "SPRIG",
    22: "EvolveR",
    25: "MeRF Motivation RL",
    26: "STS SAE Crystal Ball",
    28: "ACRouter Agent as a Router",
    30: "EvoC2F",
    31: "SkVM",
    33: "JitRL JIT RL",
    34: "HGM Huxley Godel Machine",
    35: "JIT-Agent JIT Agent",
    39: "SoL-Pi SoL Pi",
    40: "DSec DeepSeek Elastic Compute",
    41: "SAGE",
}


NOTE_META = [
    ("harness.md", "Harness、在线适应、搜索机制与运行时", [1, 8, 9, 14, 15, 32, 34, 35, 37, 39]),
    ("skills.md", "技能库、技能表示与技能内化", [2, 3, 4, 5, 6, 7, 10]),
    ("skillforge_muse.md", "MUSE、SkillForge、WikiSkill、SAGE", [12, 13, 36, 41]),
    ("prompts.md", "提示优化、文本反馈与多智能体设计", [16, 17, 18, 19, 21, 38]),
    ("training_routing.md", "训练、迁移预测与 ACRouter", [11, 22, 23, 24, 25, 26, 27, 28]),
    ("jitrl.md", "JitRL 深入核验", [33]),
    ("systems_gui.md", "SE-GA、EvoC2F 与 DSec", [29, 30, 40]),
    ("skvm_supplemental.md", "SkVM 补充论文", [31]),
]


def build_cards(inventory, sources, manifest):
    core_by_index = {int(item["index"]): item for item in sources["core"]}
    supplement_by_index = {
        int(item["related_to_index"]): item for item in sources["supplemental"]
    }
    manifest_by_filename = {item["filename"]: item for item in manifest["records"]}
    no_core = {int(item["index"]): item["reason"] for item in sources["no_core_pdf"]}
    cards = []
    for entry in inventory["entries"]:
        idx = int(entry["index"])
        theme, update, claim, evidence, limitation = ANNOTATIONS[idx]
        core = core_by_index.get(idx)
        supplemental = supplement_by_index.get(idx)
        download = core or supplemental
        record = manifest_by_filename.get(download["filename"]) if download else None
        if core:
            status = "核心 PDF 已下载并校验"
        elif supplemental:
            status = "视频无核心论文；补充 PDF 已下载并校验"
        else:
            status = "无核心 PDF（官方文章/评论视频）"
        cards.append(
            {
                **entry,
                "theme": theme,
                "color": THEME_COLORS[theme],
                "aliases": ALIASES.get(idx, ""),
                "update": update,
                "claim": claim,
                "evidence": evidence,
                "limitation": limitation,
                "status": status,
                "no_core_reason": no_core.get(idx),
                "download": download,
                "record": record,
                "local_pdf": f"../{record['path']}" if record else None,
            }
        )
    return cards


def build_notes(md):
    notes = []
    for filename, label, indices in NOTE_META:
        path = ROOT / "research_notes" / filename
        text = path.read_text(encoding="utf-8")
        notes.append(
            {
                "filename": filename,
                "label": label,
                "indices": indices,
                "html": md.render(text),
                "bytes": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
    return notes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=REPORT_PATH)
    parser.add_argument("--experiment-root", type=Path, default=ROOT / "experiments")
    parser.add_argument("--analysis-output", type=Path, default=ROOT / "metadata" / "paper_analysis.json")
    args = parser.parse_args()
    report_path = args.output.resolve()
    experiment_root = args.experiment_root.resolve()
    analysis_output = args.analysis_output.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    analysis_output.parent.mkdir(parents=True, exist_ok=True)
    inventory = load_json("metadata/inventory.json")
    sources = load_json("metadata/download_sources.json")
    manifest = load_json("metadata/pdf_manifest.json")
    evo = json.loads((experiment_root / "evoc2f_scheduler" / "results.json").read_text(encoding="utf-8"))
    bias = json.loads((experiment_root / "validation_bias" / "results.json").read_text(encoding="utf-8"))
    router = json.loads((experiment_root / "acrouter_replay" / "results.json").read_text(encoding="utf-8"))

    if len(inventory["entries"]) != 41 or set(ANNOTATIONS) != set(range(1, 42)):
        raise SystemExit("41-item inventory or annotation coverage is incomplete")
    if manifest["status_counts"] != {"ok": 39}:
        raise SystemExit(f"unexpected PDF manifest status: {manifest['status_counts']}")
    if not all(router["reference_checks"].values()):
        raise SystemExit("ACRouter reference checks failed")

    md = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})
    cards = build_cards(inventory, sources, manifest)
    notes = build_notes(md)
    themes = Counter(card["theme"] for card in cards)
    update_counts = Counter(card["update"] for card in cards)

    analysis_export = {
        str(card["index"]): {
            key: card[key]
            for key in ("primary_title", "theme", "update", "claim", "evidence", "limitation", "status")
        }
        for card in cards
    }
    analysis_output.write_text(
        json.dumps(analysis_export, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    router_summaries = router["summaries"]
    router_rows = [
        router_summaries[name]
        for name in [
            "single::gpt-5.4",
            "single::claude-opus-4-6",
            "cheap_chain",
            "original_apply_ok_gate",
            "cheap_chain_then_opus_no_gate",
        ]
    ]
    bias_curve = [
        {"round": int(key), **value} for key, value in sorted(bias["bias_curve"].items(), key=lambda x: int(x[0]))
    ]

    total_pages = sum(record.get("pages", 0) for record in manifest["records"])
    total_chars = sum(record.get("text_chars", 0) for record in manifest["records"])
    panorama_path = ROOT / "assets" / "Agent_自进化论文全景图.png"
    panorama_bytes = panorama_path.read_bytes()
    panorama_data_uri = "data:image/png;base64," + base64.b64encode(panorama_bytes).decode("ascii")
    template = Template(TEMPLATE)
    rendered = template.render(
        generated_at=datetime.now(timezone.utc).isoformat(),
        cards=cards,
        notes=notes,
        themes=themes,
        update_counts=update_counts,
        manifest=manifest,
        total_pages=total_pages,
        total_chars=total_chars,
        evo=evo,
        bias=bias,
        bias_curve=bias_curve,
        router=router,
        router_rows=router_rows,
        panorama_data_uri=panorama_data_uri,
        panorama_bytes=len(panorama_bytes),
        panorama_sha256=file_sha256(panorama_path),
    )
    repo_prefix = Path(os.path.relpath(ROOT, report_path.parent)).as_posix()
    rendered = rendered.replace('href="../', f'href="{repo_prefix}/')
    report_path.write_text(rendered, encoding="utf-8")
    print(
        json.dumps(
            {
                "report": Path(os.path.relpath(report_path, ROOT)).as_posix(),
                "bytes": report_path.stat().st_size,
                "sha256": file_sha256(report_path),
                "cards": len(cards),
                "notes": len(notes),
                "pdfs": len(manifest["records"]),
                "pages": total_pages,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


TEMPLATE = r'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark light">
<title>Agent 自动优化 / Agent 进化：41 项论文地图、复现与审计报告</title>
<style>
:root{--bg:#081019;--panel:#0e1824;--panel2:#132131;--text:#eaf2f8;--muted:#9fb1c3;--line:#243548;--cyan:#50d5d2;--violet:#a78bfa;--orange:#fbad5c;--green:#73d69c;--blue:#68a8ff;--pink:#f08cc8;--slate:#91a4b7;--danger:#ff8f8f;--shadow:0 12px 40px #0006}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:radial-gradient(circle at 10% -10%,#16344d 0,transparent 35%),var(--bg);color:var(--text);font:15.5px/1.72 system-ui,-apple-system,"Segoe UI","Noto Sans SC",sans-serif}a{color:var(--cyan);text-decoration:none}a:hover{text-decoration:underline}code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;background:#07101a;border:1px solid var(--line);border-radius:5px;padding:.08em .32em}pre{overflow:auto;background:#07101a;border:1px solid var(--line);padding:14px;border-radius:10px}pre code{border:0;padding:0}.wrap{width:min(1500px,calc(100% - 32px));margin:auto}.hero{padding:72px 0 42px}.eyebrow{color:var(--cyan);letter-spacing:.12em;text-transform:uppercase;font-weight:800;font-size:12px}.hero h1{font-size:clamp(34px,5vw,72px);line-height:1.06;max-width:1080px;margin:.25em 0}.hero p{max-width:900px;color:var(--muted);font-size:18px}.metrics{display:grid;grid-template-columns:repeat(5,minmax(150px,1fr));gap:12px;margin-top:28px}.metric,.panel,.paper,.experiment{background:linear-gradient(180deg,#132132dd,#0d1722dd);border:1px solid var(--line);border-radius:16px;box-shadow:var(--shadow)}.metric{padding:18px}.metric b{font-size:30px;display:block}.metric span{color:var(--muted)}nav{position:sticky;top:0;z-index:10;backdrop-filter:blur(14px);background:#081019dd;border-block:1px solid var(--line)}nav .wrap{display:flex;gap:18px;overflow:auto;padding:11px 0;white-space:nowrap}nav a{color:var(--muted);font-weight:700}.section{padding:54px 0}.section h2{font-size:32px;margin:0 0 10px}.lead{color:var(--muted);max-width:1000px;margin:0 0 24px}.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.panel{padding:24px}.panel h3{margin-top:0}.callout{border-left:4px solid var(--cyan);padding:14px 18px;background:#0c1c29;border-radius:8px}.warning{border-left-color:var(--orange)}.danger{border-left-color:var(--danger)}.pipeline{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;counter-reset:step}.pipeline div{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:22px}.pipeline div:before{counter-increment:step;content:counter(step);display:grid;place-items:center;width:30px;height:30px;border-radius:50%;background:var(--cyan);color:#042029;font-weight:900;margin-bottom:10px}.tag{display:inline-flex;align-items:center;gap:6px;border:1px solid var(--line);border-radius:999px;padding:3px 9px;font-size:12px;color:#d8e4ee;background:#0a141f}.dot{width:7px;height:7px;border-radius:50%;background:var(--slate)}.dot.cyan{background:var(--cyan)}.dot.violet{background:var(--violet)}.dot.orange{background:var(--orange)}.dot.green{background:var(--green)}.dot.blue{background:var(--blue)}.dot.pink{background:var(--pink)}.dot.slate{background:var(--slate)}table{width:100%;border-collapse:collapse;display:block;overflow:auto}th,td{padding:10px 12px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}th{color:#cfe0ec;background:#0b1621;position:sticky;top:0}td{color:#dce6ee}.small{font-size:13px;color:var(--muted)}.experiment{padding:25px;margin:16px 0}.experiment h3{margin:0 0 4px}.result{font-size:28px;font-weight:850;color:var(--cyan)}.bar{height:9px;background:#09111a;border-radius:99px;overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--violet),var(--cyan));border-radius:99px}.filters{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}.filters input,.filters select{background:#0b1520;color:var(--text);border:1px solid var(--line);border-radius:10px;padding:10px 12px;min-width:220px}.papers{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.paper{padding:20px}.paper h3{font-size:18px;line-height:1.35;margin:8px 0}.paper .idx{font:800 13px/1 ui-monospace;color:var(--cyan)}.paper dl{display:grid;grid-template-columns:74px 1fr;gap:6px 10px;margin:14px 0}.paper dt{color:var(--muted);font-weight:700}.paper dd{margin:0}.links{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}.links a{border:1px solid var(--line);border-radius:9px;padding:6px 9px}.note{border:1px solid var(--line);border-radius:14px;background:var(--panel);margin:14px 0;overflow:hidden}.note>summary{cursor:pointer;padding:17px 20px;font-weight:800;background:#122130}.note article{padding:24px;max-width:1000px}.note article h1{font-size:27px}.note article h2{margin-top:34px}.note article blockquote{border-left:3px solid var(--violet);margin-left:0;padding-left:14px;color:var(--muted)}footer{border-top:1px solid var(--line);padding:40px 0 70px;color:var(--muted)}@media(max-width:900px){.metrics{grid-template-columns:repeat(2,1fr)}.grid2,.grid3,.papers,.pipeline{grid-template-columns:1fr}.hero{padding-top:42px}}@media print{nav,.filters{display:none}.paper,.panel,.experiment{break-inside:avoid}body{background:white;color:#111}.panel,.paper,.experiment,.metric,.note{box-shadow:none;background:white;border-color:#ccc}a{color:#0645ad}}
.panel,.paper,.experiment,.note,.note article,.pipeline>div{min-width:0}
.panel,.paper,.experiment,.note article,p,li,dd{overflow-wrap:anywhere;word-break:break-word}
a,code{overflow-wrap:anywhere;word-break:break-all}
table{max-width:100%}
.filters input,.filters select{max-width:100%}
.paper dl{grid-template-columns:74px minmax(0,1fr)}
.note>summary{overflow-wrap:anywhere}
.note article{max-width:100%}
.panorama{margin:24px 0 0}.panorama button{display:block;width:100%;padding:0;border:1px solid var(--line);border-radius:18px;overflow:hidden;background:#fff;cursor:zoom-in;box-shadow:var(--shadow)}.panorama img{display:block;width:100%;height:auto}.panorama figcaption{color:var(--muted);margin-top:10px}.lightbox{position:fixed;inset:0;z-index:99;background:#02060bea;display:none;overflow:auto;padding:20px}.lightbox.open{display:block}.lightbox img{display:block;max-width:none;width:max(1200px,96vw);height:auto;margin:auto}.lightbox button{position:fixed;right:22px;top:18px;z-index:100;border:1px solid #ffffff55;background:#081019;color:white;border-radius:999px;padding:10px 16px;font-weight:800;cursor:pointer}
@media(max-width:900px){.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.grid2,.grid3,.papers,.pipeline{grid-template-columns:minmax(0,1fr)}nav .wrap{flex-wrap:wrap;white-space:normal;gap:8px 14px;padding:9px 0}}
</style>
</head>
<body>
<header class="hero wrap">
  <div class="eyebrow">证据优先 · 可离线打开 · 2026-10-09</div>
  <h1>Agent 自动优化 / Agent 进化<br>41 项论文地图、复现与审计报告</h1>
  <p>从合集视频到 38 篇核心 PDF、1 篇补充论文、8 份全文核验笔记和 3 项本地实跑。本报告把“论文作者报告”“发布工件回放”“合成机制示例”和“待执行计划”严格分开。</p>
  <div class="metrics">
    <div class="metric"><b>41</b><span>合集视频完整覆盖</span></div>
    <div class="metric"><b>38 + 1</b><span>核心 + 补充 PDF</span></div>
    <div class="metric"><b>{{ total_pages }}</b><span>本地校验页数</span></div>
    <div class="metric"><b>3</b><span>实际运行实验</span></div>
    <div class="metric"><b>0</b><span>付费 API 调用</span></div>
  </div>
</header>
<nav><div class="wrap"><a href="#panorama">39 篇全景</a><a href="#takeaways">结论</a><a href="#framework">统一框架</a><a href="#experiments">真实实验</a><a href="#map">41 项地图</a><a href="#notes">全文核验</a><a href="#limits">边界与复现路线</a><a href="#files">文件与校验</a></div></nav>

<main>
<section id="panorama" class="section wrap">
  <h2>39 篇论文全景：经验最终改变了什么？</h2>
  <p class="lead">38 篇合集核心论文与补充 SkVM 按主要作用位置归类。它是概念地图，不是时间谱系或已经验证过的联合架构。点击图像进入原尺寸查看；图像以 data URI 内嵌，因此只保存本 HTML 也能离线显示。</p>
  <figure class="panorama">
    <button id="open-panorama" type="button" aria-label="放大全景图"><img src="{{ panorama_data_uri }}" width="3600" height="3320" alt="Agent 自进化 39 篇论文全景图"></button>
    <figcaption>3600×3320 · {{ '{:,}'.format(panorama_bytes) }} bytes · SHA-256 <code>{{ panorama_sha256 }}</code> · <a href="../assets/Agent_自进化论文全景图.png">仓库原图</a> · <a href="../metadata/agent_evolution_map.json">主题地图源数据</a></figcaption>
  </figure>
</section>

<section id="takeaways" class="section wrap">
  <h2>结论先行</h2>
  <p class="lead">“Agent 自进化”不是一种算法，而是一组更新对象、反馈源与门禁机制的组合。最关键的问题不是它有没有修改，而是修改了什么、谁提供反馈、什么时候更新、如何防止对验证集过拟合，以及总成本是否完整核算。</p>
  <div class="grid3">
    <div class="panel"><h3>多数工作不改基础模型权重</h3><p>提示、技能、记忆、harness、拓扑、路由、代码和运行时状态都能在冻结模型时改变系统行为。只有 SKILL0/1、CoEvolve、EvolveR、Skill0.5、MeRF、CoPE、SE-GA、SAGE 等明确包含参数训练。</p></div>
    <div class="panel"><h3>独立评测比“自我反思”更重要</h3><p>同题反复择优、复用小 holdout、best-of-N 与 LLM 自评都可能制造乐观偏差。真正可靠的闭环需要只读评测器、封存测试、版本化候选、回归检查和负面结果。</p></div>
    <div class="panel"><h3>收益必须和成本同账</h3><p>外层 proposer、critic、judge、候选执行、沙盒、训练与线上额外 token 都是成本。相同轮数不等于相同预算；“无梯度”也不等于免费。</p></div>
  </div>
  <div class="callout" style="margin-top:18px"><b>推荐落地顺序：</b>先建立独立测试与可回放轨迹；再做低风险、可回滚的技能/记忆/harness 更新；只有当外部状态改造无法达到目标、数据和算力足够且收益能独立验证时，才进行昂贵的权重训练。若把它用于购物/评论类 Agent，可先从“错误归因 → 规则或技能补丁 → 封存商品/评论留出集 → 回归门禁”开始，而不是直接让系统自改模型或评分器。</div>
</section>

<section id="framework" class="section wrap">
  <h2>统一分析框架</h2>
  <div class="grid2">
    <div class="panel"><h3>六个问题</h3><ol><li><b>优化对象</b>：prompt、skill、memory、harness、topology、router、weights 还是 runtime？</li><li><b>反馈源</b>：环境奖励、文本批评、执行证据、人工修正、成本还是类型/编译约束？</li><li><b>时间尺度</b>：每步、每回合、测试时跨回合、离线搜索还是训练阶段？</li><li><b>搜索空间</b>：文本、代码、DAG、图拓扑、模型选择或训练数据？</li><li><b>评测门禁</b>：独立验证、回归、可执行 verifier、人工审核，还是仅 LLM 自评？</li><li><b>实际成本</b>：是否含所有角色、候选评估、失败、judge、沙盒和部署开销？</li></ol></div>
    <div class="panel"><h3>外部状态与权重更新必须分开</h3><p>外部状态的优点是可审计、可回滚、易做灰度；缺点是上下文、检索与运行时依赖会持续存在。权重更新可减少推理时依赖，但数据、训练和灾难性回归成本更高，且需要更强隔离与独立测试。</p><table><tr><th>层级</th><th>典型对象</th><th>主要风险</th></tr><tr><td>外部</td><td>prompt / skill / memory / harness / topology / route</td><td>验证过拟合、上下文污染、错误技能和副作用</td></tr><tr><td>权重</td><td>SFT / GRPO / DPO / KTO / LoRA</td><td>训练成本、遗忘、不可逆回归、数据污染</td></tr><tr><td>运行时</td><td>compiler / sandbox / storage / scheduler</td><td>语义标注错误、隔离不足、性能数字外推</td></tr></table></div>
  </div>
  <div class="pipeline" style="margin-top:18px"><div><h3>证据与门禁</h3><p>先固定任务、版本、只读评分器和最终测试；轨迹保留原始证据。</p></div><div><h3>可回滚外部改进</h3><p>限制修改面，逐个候选验证，报告覆盖率、失败和成本。</p></div><div><h3>权重训练</h3><p>仅在数据、算力和对照齐全时做；独立报告外部记忆是否仍是必要条件。</p></div></div>
</section>

<section id="experiments" class="section wrap">
  <h2>本次实际运行：三种证据等级</h2>
  <p class="lead">这里的数字来自本机保存的代码和日志；论文中建议的其余实验没有运行。完整论文结果复现：0；缩小规模论文方法复现：0；公开工件回放：1；合成机制示例：2。</p>
  <div class="experiment">
    <span class="tag"><span class="dot pink"></span>公开发布工件的离线回放</span>
    <h3>ACRouter OOD176 独立标准库重放与一致性审计</h3>
    <div class="result">73.30% · CumReg 15.9 · $86.72（历史估算）</div>
    <p>固定 commit <code>{{ router.source.commit }}</code> 与矩阵 SHA-256 <code>{{ router.source.sha256 }}</code>。本次只读 JSON，没有实时模型调用和费用；未执行作者脚本。176 个任务中成功 129 个、升级 29 次、平均 2.6648 步，6 项官方参考检查全部通过。</p>
    <table><tr><th>策略</th><th>成功率</th><th>累计 regret</th><th>历史估算成本</th><th>升级</th><th>平均步</th></tr>{% for row in router_rows %}<tr><td>{{ row.name }}</td><td>{{ '%.2f'|format(row.avg_perf_percent) }}%</td><td>{{ '%.2f'|format(row.cumulative_regret) }}</td><td>${{ '%.2f'|format(row.historical_estimated_total_cost_usd) }}</td><td>{{ row.escalations }}</td><td>{{ '%.2f'|format(row.avg_steps) }}</td></tr>{% endfor %}</table>
    <p class="small">无门控升级得到 78.41% 但成本 $144.98；原门控是性能—成本折中。廉价链 71.02% / $46.07，且其 regret 略低于原门控，说明额外成功不一定抵消成本惩罚。176 行混合 old112/new64，并含模型版本别名映射，不能据此建立当前模型排名。</p>
    <div class="links"><a href="../experiments/acrouter_replay/README.md">说明</a><a href="../experiments/acrouter_replay/run.py">源码</a><a href="../experiments/acrouter_replay/results.json">结果 JSON</a><a href="../experiments/acrouter_replay/decisions.csv">逐题轨迹</a><a href="../experiments/acrouter_replay/run.log">真实日志</a></div>
  </div>
  <div class="experiment">
    <span class="tag"><span class="dot violet"></span>合成机制示例，不是论文基准复现</span>
    <h3>EvoC2F：依赖与副作用感知调度</h3>
    <div class="result">1.68× 加速，12 / 12 语义等价</div>
    <p>同一合成 DAG 上比较串行、只看数据依赖的并行和 effect-aware 并行。只看依赖平均 0.1071s、近 1.99×，但 0/12 最终状态等价；effect-aware 平均 0.1268s、12/12 等价。故“更并行”不能取代副作用冲突分析。重试在提交后故障场景中确实发生，幂等键保持库存状态正确。</p>
    <table><tr><th>模式</th><th>平均秒</th><th>等价运行</th><th>平均冲突</th></tr>{% for name, row in evo.modes.items() %}<tr><td>{{ name }}</td><td>{{ '%.4f'|format(row.timing_seconds.mean) }}</td><td>{{ row.equivalent_runs }}/{{ row.total_runs }}</td><td>{{ '%.1f'|format(row.mean_observed_conflicts) }}</td></tr>{% endfor %}</table>
    <div class="links"><a href="../experiments/evoc2f_scheduler/README.md">说明</a><a href="../experiments/evoc2f_scheduler/run.py">源码</a><a href="../experiments/evoc2f_scheduler/results.json">结果</a><a href="../experiments/evoc2f_scheduler/run.log">真实日志</a></div>
  </div>
  <div class="experiment">
    <span class="tag"><span class="dot orange"></span>合成统计机制示例，不是论文基准复现</span>
    <h3>反复使用 holdout 的选择偏差</h3>
    <div class="result">16 轮复用后乐观偏差 +5.58pp</div>
    <p>3000 次合成试验、每轮 12 候选、16 轮。只在最后使用一次封存 holdout 时，报告值减最终大测试的均值为 {{ '%.5f'|format(bias.sealed_once.optimism_reported_minus_final.mean) }}；反复用 holdout 选 best-so-far 后为 {{ '%.5f'|format(bias.reused_holdout.optimism_reported_minus_final.mean) }}，95% CI [{{ '%.5f'|format(bias.reused_holdout.optimism_reported_minus_final.ci95_low) }}, {{ '%.5f'|format(bias.reused_holdout.optimism_reported_minus_final.ci95_high) }}]。二项准确率使用正态近似并量化到 1/n，所有数据均为合成。</p>
    <table><tr><th>选择轮数</th><th>乐观偏差均值</th><th>95% CI</th></tr>{% for row in bias_curve %}<tr><td>{{ row.round }}</td><td>{{ '%.4f'|format(row.mean) }}</td><td>[{{ '%.4f'|format(row.ci95_low) }}, {{ '%.4f'|format(row.ci95_high) }}]</td></tr>{% endfor %}</table>
    <div class="links"><a href="../experiments/validation_bias/README.md">说明</a><a href="../experiments/validation_bias/run.py">源码</a><a href="../experiments/validation_bias/results.json">结果</a><a href="../experiments/validation_bias/run.log">真实日志</a></div>
  </div>
</section>

<section id="map" class="section wrap">
  <h2>41 项视频—论文地图</h2>
  <p class="lead">每张卡片同时保留 B 站视频、公开来源、本地 PDF 状态、优化对象、核心主张、证据与局限。第 19 项是官方行业文章，第 20/31 项是评论视频；第 31 项另下载 SkVM 作为补充文献。</p>
  <div class="filters"><input id="q" type="search" placeholder="搜索标题、主张、局限…"><select id="theme"><option value="">全部主题</option>{% for theme,count in themes.items()|sort %}<option value="{{ theme }}">{{ theme }}（{{ count }}）</option>{% endfor %}</select><select id="state"><option value="">全部更新对象</option>{% for state,count in update_counts.items()|sort %}<option value="{{ state }}">{{ state }}（{{ count }}）</option>{% endfor %}</select></div>
  <div id="papers" class="papers">
  {% for p in cards %}<article class="paper" data-theme="{{ p.theme|e }}" data-state="{{ p.update|e }}" data-search="{{ (p.primary_title ~ ' ' ~ p.aliases ~ ' ' ~ p.claim ~ ' ' ~ p.evidence ~ ' ' ~ p.limitation ~ ' ' ~ (p.arxiv_ids|join(' ')))|lower|e }}">
    <div class="idx">#{{ '%02d'|format(p.index) }}</div><span class="tag"><span class="dot {{ p.color }}"></span>{{ p.theme }}</span>
    <h3>{{ p.primary_title }}</h3>
    <div class="small">{{ p.status }}{% if p.record %} · {{ p.record.pages }} 页 · SHA-256 {{ p.record.sha256[:12] }}…{% endif %}</div>
    <dl><dt>更新</dt><dd>{{ p.update }}</dd><dt>主张</dt><dd>{{ p.claim }}</dd><dt>证据</dt><dd>{{ p.evidence }}</dd><dt>局限</dt><dd>{{ p.limitation }}</dd></dl>
    <div class="links"><a href="{{ p.video_url }}">对应视频</a>{% if p.local_pdf %}<a href="{{ p.local_pdf }}">本地 PDF</a>{% endif %}{% for url in p.primary_source_urls %}<a href="{{ url }}">公开来源{% if loop.index>1 %} {{ loop.index }}{% endif %}</a>{% endfor %}</div>
  </article>{% endfor %}
  </div>
</section>

<section id="notes" class="section wrap">
  <h2>8 份全文核验笔记</h2>
  <p class="lead">以下内容来自完整 PDF、附录与官方仓库核验，保留精确版本、表格页码、百分点/相对值、代码状态、成本与复现建议。建议实验均是计划，不是本次已执行结果。</p>
  {% for note in notes %}<details class="note"><summary>{{ note.label }} · <code>{{ note.filename }}</code> · 涵盖 #{{ note.indices|join(', #') }}</summary><article>{{ note.html|safe }}<hr><p class="small">本地原文：<a href="../research_notes/{{ note.filename }}">{{ note.filename }}</a> · {{ note.bytes }} bytes · SHA-256 {{ note.sha256 }}</p></article></details>{% endfor %}
</section>

<section id="limits" class="section wrap">
  <h2>复现等级、缺失项与建议路线</h2>
  <div class="grid2">
    <div class="panel"><h3>本次证据等级</h3><table><tr><th>等级</th><th>数量</th><th>说明</th></tr><tr><td>完整论文结果复现</td><td>0</td><td>没有原模型、全数据、预算和同协议端到端重跑。</td></tr><tr><td>缩小规模方法复现</td><td>0</td><td>本机无合适已部署文本 LLM，且未安装/运行第三方外部代码。</td></tr><tr><td>发布工件离线重放</td><td>1</td><td>ACRouter OOD176；固定 commit、SHA 与独立实现。</td></tr><tr><td>合成机制示例</td><td>2</td><td>EvoC2F 调度、反复 holdout 选择偏差。</td></tr><tr><td>计划/静态核验</td><td>其余</td><td>论文全文、源码状态、建议实验与边界。</td></tr></table></div>
    <div class="panel"><h3>为什么没有冒充“完整复现”</h3><ul><li>许多论文依赖闭源模型、付费 API、多张 H100/H800/A100、专用沙盒、商业 ROM 或私有工单。</li><li>公开仓库可能晚于论文、只含部分组件，或默认参数与论文不一致。</li><li>本机虽有 RTX 5060 Ti 16GB 和 CUDA PyTorch，但没有已部署的通用文本模型服务；临时下载大模型与安装外部代码不在本次授权范围。</li><li>更换模型、数据、judge 或任务切分会改变问题，应标为迁移/缩小实验。</li></ul></div>
  </div>
  <div class="callout warning" style="margin-top:18px"><b>下一阶段优先级：</b>① Cordis / ObservationPack / JitRL 公式等纯 CPU 确定性测试；② 复用公开技能与评分器做小型留出对照；③ 在明确授权后部署一个本地 3B–8B 量化模型，做 TextGrad/ProTeGi 或 WikiSkill 的真实小规模实验；④ 最后才考虑 RL 或 27B+ harness 生成器。所有阶段固定最终测试、记录失败与总 token/时间。</div>
</section>

<section id="files" class="section wrap">
  <h2>文件、校验与离线使用</h2>
  <div class="grid2">
    <div class="panel"><h3>论文资料</h3><p>{{ manifest.actual_core }} 份核心 PDF + {{ manifest.actual_supplemental }} 份补充 PDF，状态全部为 <code>ok</code>，共 {{ total_pages }} 页、{{ '{:,}'.format(total_chars) }} 个提取字符。每份记录含来源、大小、SHA-256、页数、加密状态和文本路径。</p><div class="links"><a href="../metadata/inventory.json">41 项清单</a><a href="../metadata/download_sources.json">下载来源</a><a href="../metadata/pdf_manifest.csv">PDF 清单 CSV</a><a href="../metadata/pdf_manifest.json">PDF 清单 JSON</a><a href="../metadata/paper_registry.json">稳定论文索引</a><a href="../metadata/paper_analysis.json">结构化分析</a></div></div>
    <div class="panel"><h3>环境与可运行性</h3><p>Windows；i9-13900K，约 95.7GB RAM，RTX 5060 Ti 16GB；PyTorch 2.11.0+cu128 可见 CUDA。Python 3.12/3.13/3.14 可用。未发现 Ollama/llama.cpp/LM Studio/vLLM 等通用文本服务。</p><div class="links"><a href="../metadata/environment.md">环境记录</a><a href="../experiments/README.md">实验索引</a><a href="../README.md">项目说明</a></div></div>
  </div>
  <p class="small">本 HTML 不依赖网络资源，可直接双击离线打开；本地 PDF、代码、结果和日志使用相对链接。公开来源链接仅作为联网时的回退。生成时间：{{ generated_at }}。</p>
</section>
</main>
<footer><div class="wrap">Agent 自动优化 / Agent 进化研究归档 · 本地离线报告 · 本次实验不含付费 API 调用或凭据。</div></footer>
<div id="panorama-lightbox" class="lightbox" role="dialog" aria-modal="true" aria-label="全景图放大"><button id="close-panorama" type="button">关闭 ×</button></div>
<script>
const q=document.querySelector('#q'),theme=document.querySelector('#theme'),state=document.querySelector('#state'),papers=[...document.querySelectorAll('.paper')];
function filter(){const needle=q.value.trim().toLowerCase();for(const p of papers){const ok=(!needle||p.dataset.search.includes(needle))&&(!theme.value||p.dataset.theme===theme.value)&&(!state.value||p.dataset.state===state.value);p.hidden=!ok}}q.addEventListener('input',filter);theme.addEventListener('change',filter);state.addEventListener('change',filter);
const panorama=document.querySelector('#open-panorama img'),lightbox=document.querySelector('#panorama-lightbox'),closePanorama=document.querySelector('#close-panorama');
function closeLightbox(){lightbox.classList.remove('open');lightbox.querySelector('img')?.remove()}
document.querySelector('#open-panorama').addEventListener('click',()=>{const clone=panorama.cloneNode();clone.removeAttribute('width');clone.removeAttribute('height');lightbox.appendChild(clone);lightbox.classList.add('open')});
closePanorama.addEventListener('click',closeLightbox);lightbox.addEventListener('click',event=>{if(event.target===lightbox)closeLightbox()});document.addEventListener('keydown',event=>{if(event.key==='Escape')closeLightbox()});
</script>
</body></html>'''


if __name__ == "__main__":
    main()
