#!/usr/bin/env python3
"""Render the 39-paper panorama from repository-relative source data.

This is a maintained local renderer derived from the original project drawing
script. It does not execute paper or third-party repository code.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = ROOT / "metadata" / "agent_evolution_map.json"
DEFAULT_OUTPUT = ROOT / "assets" / "Agent_自进化论文全景图.png"


def font_candidates(bold: bool) -> list[Path]:
    names = (
        ["msyhbd.ttc", "simhei.ttf", "msyh.ttc"]
        if bold
        else ["msyh.ttc", "simsun.ttc", "simhei.ttf"]
    )
    roots = [
        Path("C:/Windows/Fonts"),
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        Path("/usr/share/fonts/opentype/noto"),
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/share/fonts/truetype/dejavu"),
    ]
    linux_names = (
        ["NotoSansCJK-Bold.ttc", "NotoSansCJK-Bold.otf", "DejaVuSans-Bold.ttf"]
        if bold
        else ["NotoSansCJK-Regular.ttc", "NotoSansCJK-Regular.otf", "DejaVuSans.ttf"]
    )
    return [root / name for root in roots for name in names + linux_names]


def resolve_font(explicit: str | None, bold: bool) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"font not found: {path}")
        return path
    for path in font_candidates(bold):
        if path.is_file():
            return path
    raise SystemExit("No usable TrueType/OpenType font found; pass --font and --bold-font")


def validate_source(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    papers = [paper for group in data["groups"] for paper in group["papers"]]
    if data.get("count") != 39 or len(papers) != 39:
        raise SystemExit("topic-map source must contain exactly 39 unique papers")
    keys = [str(paper["inventory_index"]) for paper in papers]
    if len(keys) != len(set(keys)):
        raise SystemExit("topic-map source contains duplicate inventory_index values")
    return data


def render(output: Path, preview: Path | None, regular: Path, bold: Path) -> None:
    width, height = 3600, 3320
    image = Image.new("RGB", (width, height), "#F4F6FA")
    draw = ImageDraw.Draw(image)

    def font(size: int, is_bold: bool = False):
        return ImageFont.truetype(str(bold if is_bold else regular), size)

    def text(x, y, value, size=32, color="#26364A", is_bold=False):
        draw.text((x, y), value, font=font(size, is_bold), fill=color)

    def box(x, y, w, h, fill="#FFFFFF", outline=None, radius=26):
        draw.rounded_rectangle(
            (x, y, x + w, y + h), radius=radius, fill=fill, outline=outline, width=2
        )

    def line(points, color="#7B8CA5", line_width=5):
        draw.line(points, fill=color, width=line_width)

    def arrow(points, color="#7B8CA5", line_width=6):
        line(points, color, line_width)
        a, b = points[-2:]
        theta = math.atan2(b[1] - a[1], b[0] - a[0])
        length = 18
        draw.polygon(
            [
                b,
                (
                    b[0] - length * math.cos(theta - 0.5),
                    b[1] - length * math.sin(theta - 0.5),
                ),
                (
                    b[0] - length * math.cos(theta + 0.5),
                    b[1] - length * math.sin(theta + 0.5),
                ),
            ],
            fill=color,
        )

    def centered(x, y, w, value, size=32, color="#26364A", is_bold=False):
        bounds = draw.textbbox((0, 0), value, font=font(size, is_bold))
        text(x + (w - (bounds[2] - bounds[0])) / 2, y, value, size, color, is_bold)

    def row(x, y, name, description, color, tag=None):
        draw.ellipse((x, y + 14, x + 10, y + 24), fill=color)
        text(x + 25, y, name, 34, "#172B42", True)
        text(x + 25, y + 49, description, 27, "#5A6A7E")
        if tag:
            text(x + 25, y + 86, tag, 23, color)

    def card(x, y, w, h, title, subtitle, color):
        box(x, y, w, h)
        box(x, y, w, 116, color, radius=25)
        draw.rectangle((x, y + 80, x + w, y + 116), fill=color)
        text(x + 32, y + 18, title, 39, "white", True)
        text(x + 32, y + 72, subtitle, 25, "#FFFFFF")

    text(100, 48, "Agent 自进化：39 篇论文到底在改哪里？", 70, "#132840", True)
    text(104, 151, "先看执行闭环，再看四种改变：改外部状态、改模型参数、预测训练收益、改运行底座。", 34, "#576B83")
    text(100, 229, "01  运行现场", 36, "#0C7383", True)
    text(390, 233, "每次任务都在这里发生；下面的优化最终必须回到这里验证", 29, "#62738A")
    y = 302
    nodes = [
        (100, 440, "用户任务", "目标 / 约束 / 环境"),
        (600, 570, "选择模型", "ACRouter · 反馈驱动路由"),
        (1230, 940, "Agent 决策与执行", "模型 θ + Prompt + Skill + Memory + Harness"),
        (2230, 640, "工具 / 环境", "动作、观察、状态与副作用"),
        (2930, 570, "任务结果", "成功率 / 成本 / 延迟 / 风险"),
    ]
    for x, w, title, subtitle in nodes:
        box(x, y, w, 170, "#E6F2F5")
        centered(x, y + 24, w, title, 40, "#0B5261", True)
        centered(x, y + 92, w, subtitle, 25, "#345C6B")
    for index in range(4):
        arrow(
            [
                (nodes[index][0] + nodes[index][1] + 10, y + 83),
                (nodes[index + 1][0] - 12, y + 83),
            ],
            "#2C8794",
        )
    box(1230, 500, 440, 104, "#DDEDF7")
    text(1250, 514, "JIT-Agent", 32, "#1D5679", True)
    text(1250, 557, "按任务生成专用 Harness", 24)
    box(2230, 500, 640, 104, "#DDEDF7")
    text(2260, 514, "EvoC2F", 32, "#1D5679", True)
    text(2260, 557, "编译工具计划，安全并行", 27)
    box(1730, 500, 440, 104, "#DDEDF7")
    text(1750, 514, "SkVM · 补充", 32, "#1D5679", True)
    text(1750, 557, "技能适配目标模型与框架", 24)
    text(100, 511, "推理时适配：4 篇", 31, "#0C7383", True)
    text(100, 557, "路由 / 临时框架 / 工具计划 / 技能编译", 25, "#57728A")
    arrow([(3215, 472), (3215, 630)], "#2C8794")
    box(100, 648, 3400, 131, "#142D47")
    centered(125, 666, 790, "轨迹 + 成败 + 成本", 36, "#FFFFFF", True)
    centered(945, 666, 690, "诊断：错在哪一层？", 36, "#FFFFFF", True)
    centered(1675, 666, 780, "生成候选改变", 36, "#FFFFFF", True)
    centered(2500, 666, 960, "独立验证 → 发布 / 回滚", 36, "#F6C777", True)
    for x in [905, 1640, 2465]:
        arrow([(x, 710), (x + 32, 710)], "#89ADC4", 4)
    text(144, 727, "共同证据：真实任务反馈；共同门槛：锁定测试集、成本匹配、版本追踪与回归检查", 26, "#B8CEDF")
    arrow([(3505, 710), (3550, 710), (3550, 265), (1700, 265), (1700, 290)], "#A9BBCD", 4)

    text(100, 825, "02  改外部系统：22 篇", 43, "#126B67", True)
    text(104, 885, "改变可加载的指令、技能、记忆与编排；部分方法另含辅助训练，主位置不等于唯一机制。", 29, "#65738A")
    y, card_width = 958, 1080
    x1, x2, x3 = 100, 1260, 2420
    card(x1, y, card_width, 888, "指令 / 拓扑 / 记忆", "给模型更好的指令、协作方式和经验", "#337AA7")
    rows = [
        ("APO / ProTeGi", "用文本反馈 + 搜索改提示词"),
        ("TextGrad", "把语言反馈沿计算图反向传递"),
        ("FedTextGrad", "跨客户端聚合文本梯度"),
        ("SPRIG", "用遗传搜索优化系统提示词"),
        ("MASS", "联合优化提示词与多 Agent 拓扑"),
        ("JitRL", "检索经验，按动作优势调整输出"),
    ]
    for index, (name, desc) in enumerate(rows):
        row(x1 + 32, y + 137 + index * 109, name, desc, "#337AA7")
    text(x1 + 58, y + 817, "JitRL：测试时非参数策略改进", 25, "#337AA7")
    card(x2, y, card_width, 888, "可复用 Skill", "把任务经验变成可创建、维护、验证的技能资产", "#278777")
    rows = [
        ("SkillX", "成功轨迹 → 分层技能知识库"),
        ("Trace2Skill", "局部轨迹教训 → 可迁移技能"),
        ("SkillClaw", "聚合多用户轨迹，协同更新技能"),
        ("Ctx2Skill", "上下文规则 → 自博弈提炼技能"),
        ("MUSE-Autoskill", "创建、测试、修补与管理技能生命周期"),
        ("SkillForge", "领域知识 + 失败归因 → 最小技能修复"),
        ("WikiSkill", "用持久知识层支持技能演化"),
        ("Strategy Genes / EvoMap", "把经验编码成可执行的策略控制信号"),
    ]
    for index, (name, desc) in enumerate(rows):
        row(x2 + 32, y + 134 + index * 91, name, desc, "#278777")
    card(x3, y, card_width, 888, "Harness 与搜索机制", "改模型外层系统；有些还会改“怎么进化”", "#7062A8")
    rows = [
        ("Meta-Harness", "端到端搜索模型外壳"),
        ("AHE", "可观测轨迹驱动组件修改与回滚"),
        ("Continual Harness", "连续任务中在线改写外层系统"),
        ("Autogenesis", "把自进化组织成可审计协议"),
        ("AEvo", "让元 Agent 改进演化机制"),
        ("HGM", "按后代潜力选择自修改分支"),
        ("EvoTest", "测试时复盘配置，用 UCB 探索"),
        ("SoL-Pi", "设能力门槛，搜索更省 token 的框架"),
    ]
    for index, (name, desc) in enumerate(rows):
        row(x3 + 32, y + 134 + index * 91, name, desc, "#7062A8")

    text(100, 1900, "03  改模型参数：9 篇", 43, "#AF6131", True)
    text(104, 1960, "经验不只留在文件里，还通过 SFT / RL / 偏好优化改变 θ；很多方法同时维护外部技能与记忆。", 29, "#65738A")
    card(100, 2028, 2260, 671, "参数训练：把反馈变成策略能力", "任务轨迹 / 奖励 / 技能 → 训练更新 → 新模型版本", "#B87743")
    rows = [
        ("SKILL0", "逐步撤去技能提示，让技能内化"),
        ("Skill1", "联合学习技能选择、使用与蒸馏"),
        ("Skill0.5", "通用技能内化，任务技能继续调用"),
        ("SAGE", "训练 Agent 生成与复用技能"),
        ("EvolveR", "原则记忆 + GRPO 联合改进"),
        ("SE-GA", "GUI 层级记忆 + 记忆感知训练"),
        ("CoEvolve", "让训练任务分布与策略共同进化"),
        ("CoPE", "按规划—执行协调性加权训练"),
        ("MeRF", "在训练提示中显式表达奖励规则"),
    ]
    for index, (name, desc) in enumerate(rows):
        column, item_row = divmod(index, 3)
        row(135 + column * 735, 2178 + item_row * 157, name, desc, "#B87743")
    text(142, 2630, "跨层：Skill1 / Skill0.5 / SAGE / EvolveR / SE-GA 同时涉及外部状态；这里只按主要机制定位。", 25, "#85572E")
    card(2420, 2028, 1080, 671, "训练前的预测与筛选：2 篇", "帮助决定“值不值得训”，本身不是自进化闭环", "#758345")
    row(2457, 2181, "TuneAhead", "用数据特征 + 100 步探针预测微调收益", "#758345")
    text(2482, 2272, "依赖历史完整训练结果，不是零成本预测", 25, "#6D765C")
    row(2457, 2350, "STS / SAE as a Crystal Ball", "用可解释激活特征预测跨域影响幅度", "#758345")
    text(2482, 2441, "不等于预测所有能力都会上升", 25, "#6D765C")
    box(2457, 2536, 1006, 104, "#F1F3E6")
    text(2485, 2556, "预测 / 筛选 → 训练决策", 31, "#657536", True)
    arrow([(2330, 1870), (2330, 1998)], "#B87743", 5)
    text(1390, 1871, "技能 / 经验可进一步进入参数学习", 28, "#AF6131")

    text(100, 2761, "04  运行底座：2 篇", 42, "#526078", True)
    text(565, 2770, "为上面所有层提供可组合、可恢复、可扩展的执行环境", 29, "#65738A")
    box(100, 2847, 1660, 190, "#E4EAF2")
    text(135, 2870, "Cordis", 38, "#384C65", True)
    text(135, 2935, "组件、状态与生命周期的时空可组合性", 30)
    text(135, 2980, "解决系统怎么可靠拼装；不是直接训练 Agent 更聪明", 25, "#607087")
    box(1810, 2847, 1690, 190, "#E4EAF2")
    text(1845, 2870, "DSec", 38, "#384C65", True)
    text(1845, 2935, "隔离沙盒、按需镜像与大规模训练执行资源", 30)
    text(1845, 2980, "解决实验怎么跑得起、跑得稳；不是策略学习算法", 25, "#607087")
    box(100, 3091, 3400, 125, "#FFFFFF")
    text(136, 3110, "一眼读懂：做任务 → 留证据 → 找薄弱环节 → 改外部系统或参数 → 独立验证 → 再做任务", 35, "#152F49", True)
    text(139, 3165, "这些论文是同一闭环里的不同零件，不是 39 套互相替代的完整 Agent。", 30, "#63728A")
    text(104, 3252, "覆盖：38 篇核心研究 + SkVM 补充论文。Tax AI 案例与两条观点视频不计入论文数。", 23, "#718094")
    text(104, 3286, "按主要机制定位，跨层方法已标注；箭头表示可组合的概念关系，不代表所有论文已经联合验证。依据本次逐篇原文分析 · 2026-10-08", 22, "#718094")

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output, optimize=True)
    if preview:
        preview.parent.mkdir(parents=True, exist_ok=True)
        image.resize((1200, 1107), Image.Resampling.LANCZOS).save(preview, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preview", type=Path)
    parser.add_argument("--font")
    parser.add_argument("--bold-font")
    args = parser.parse_args()
    data = validate_source(args.data.resolve())
    regular = resolve_font(args.font, False)
    bold = resolve_font(args.bold_font, True)
    render(args.output.resolve(), args.preview.resolve() if args.preview else None, regular, bold)
    print(json.dumps({
        "output": str(args.output.resolve()),
        "size": [3600, 3320],
        "papers": data["count"],
        "font": str(regular),
        "bold_font": str(bold),
        "python": sys.version.split()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
