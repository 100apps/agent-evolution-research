# 报告目录

- `index.html`：最终单文件离线中文报告，包含内嵌样式与交互筛选。
- 报告靠前位置以内嵌 data URI 展示 3600×3320 的 39 论文全景图，点击可放大；单独复制 HTML 仍能显示。
- `report_preview.png`：早期本机 Edge 无头渲染首屏截图。
- `qa_desktop.png`：修复后 1440×1000 桌面首屏。
- `qa_interaction.png`：搜索“ACRouter”后的唯一匹配卡片。
- `qa_note_expanded.png`：桌面端研究笔记展开状态。
- `qa_mobile.png`：390×844 窄屏首屏。
- `qa_mobile_note.png`：390×844 窄屏研究笔记展开状态。
- `qa_desktop_panorama.png`：桌面端内嵌全景图。
- `qa_panorama_lightbox.png`：点击放大后的原尺寸浏览状态。
- `qa_mobile_panorama.png`：390×844 窄屏内嵌全景图。

构建断言：41 个条目、8 份研究笔记、3 个实验区块、39 份 PDF；当前 71 个本地相对链接全部存在。验证日志位于 `../logs/build_report.log` 与 `../logs/validate_report.log`。实际浏览器验收日志位于本目录 `visual_qa.log`，覆盖全景图内嵌/放大、桌面/窄屏、搜索、主题筛选、卡片/笔记展开及横向溢出检查。

HTML 中所有本地 PDF、代码、结果和日志使用相对路径；整个 `agent_evolution_research` 文件夹移动或解压后仍可离线使用。公开网页仅作为联网回退。
