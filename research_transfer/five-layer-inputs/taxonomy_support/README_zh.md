# 五层 AI 论文分类接入包

版本：ai-cake-research-v1.0.0-proposed（待用户/独立人工审阅）。

最短接入步骤：
1. 读取 taxonomy.json。5 个 L1 / 17 个 L2 / 59 个 L3；ID 已冻结。仅 L1 来自 NVIDIA，其他是项目研究扩展。
2. 以 master_csv_schema.json 的字段语义组织主表。自动首轮明确 candidate + automated；给逐字段来源、逐标签证据及规则命中跨度。
3. 仅把有证据 L3 交给 classifier_reference.category_fields() 补祖先。不要按产业依赖让 Applications 自动继承其余四层。
4. 使用 classifier_reference.validate_record() 校验记录；用 validate_boundary_prediction() 连接真正的分类器跑 adversarial_tests.json。
5. Explorer 依 taxonomy 构树，同时保留状态、facet、覆盖和审核筛选。paper 与 occurrence 分母分别报告。

文件：
- taxonomy.json：冻结语义树、词表与规则
- taxonomy_nodes.csv：供人工查看/表格导入的节点表
- classification_guide_zh.md：中文边界、方法、来源、全叶子定义
- master_csv_schema.json / master_csv_template.csv：43 字段契约与空模板
- adjudicated_examples.json / .csv：17 个本地真实标题+摘要示例与 1 个真实缺摘要例；AI 判定，不是人工金标准
- adversarial_tests.json：24 个合成反例/正例；不是实际论文或准确率数据
- classifier_reference.py：仅标准库的闭包、证据跨度、记录/测试校验工具；没有冒充语义分类器
- validation.json：结构和证据跨度校验结果；真实分类器语义测试与人工验证尚未运行

运行本包自检：python classifier_reference.py

如需重建，顺序为 build_taxonomy.py → build_examples_schema.py → build_tests_guide.py → classifier_reference.py。构建脚本读取原 conference 数据；分发给无原数据的环境只需使用成品文件与 classifier_reference.py，不必重建。

冻结 taxonomy.json SHA-256：
e3289464ff67fd7cf470c1525a880eaa7d3a6e8a44837dc5acd75844aa2248eb

没有生成或发布任何网站、写入任何仓库，也没有运行 89,530 行的全语料分类。
