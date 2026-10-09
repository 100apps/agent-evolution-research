# 环境盘点

检查时间：2026-10-08（UTC）

## 工作区

- 产物根目录：仓库根目录（所有脚本均以自身位置解析，不依赖个人绝对路径）。
- 起始任务目录为空，且不是 Git 仓库。
- 初始任务目录未包含项目级 `AGENTS.md`；当前仓库已补充接续协议。
- 初始只读检索未发现与本项目有关的旧研究记录。

## 硬件

- CPU：Intel Core i9-13900K，24 核 / 32 线程。
- 内存：95.70 GB。
- GPU：NVIDIA GeForce RTX 5060 Ti，16311 MiB；检查时约 12265 MiB 空闲。
- NVIDIA 驱动：617.14；计算能力：12.0。
- C 盘检查时剩余约 113.19 GB；E 盘剩余约 147.30 GB。

## Python 与 GPU 运行时

- 默认 Python：3.14.3（64 位 Windows）。
- 另有 Python 3.13、Python 3.12 和 uv 管理的 Python 3.14.2。
- PyTorch：2.11.0+cu128。
- `torch.cuda.is_available()`：`True`。
- CUDA runtime：12.8；可识别 RTX 5060 Ti。

## 已有关键依赖

可导入：NumPy、SciPy、Pandas、scikit-learn、PyTorch、Transformers、Datasets、NetworkX、pypdf、PyMuPDF、Requests、BeautifulSoup、Jinja2、pytest。

缺失或未检测到：Accelerate、sentence-transformers、Matplotlib、Seaborn、Markdown、Jupyter。

命令行工具：Git、curl、Pandoc、uv、FFmpeg、`pdfinfo` 可用；`pdftotext`、MuPDF CLI、qpdf 未在 PATH 中。Poppler 的 `pdftoppm.exe` 预计可从 Codex bundled runtime 的 `pdfinfo.exe` 同目录调用，需在渲染步骤再核验。

## 实验策略

- 正文提取与轻量机制实验可直接使用现有 Python 3.14 环境。
- 需要第三方仓库或更严格锁定依赖时，优先在本目录创建 Python 3.12 隔离环境，避免污染全局安装。
- 实验不调用付费 API，不创建凭据；GitHub 上传仅在用户明确授权后进行。
- 16 GB 显存适合小模型推理、嵌入和轻量训练；不宣称具备论文中 H800/H100 集群或大规模商业模型实验条件。
