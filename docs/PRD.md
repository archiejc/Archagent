# PRD: 多利益相关者建筑协商 Agent 系统（研究工具版 v0.2）

- 项目代号: Archagent
- 文档版本: v0.2（研究工具导向）
- 日期: 2026-03-11
- 状态: Draft for review

## 1. 产品目标与问题定义

### 1.1 背景
建筑概念设计阶段通常涉及开发商、居民、规划部门、环保组织等多方博弈。当前协商过程高度依赖人工会议，存在沟通成本高、方案迭代慢、利益冲突难显式量化的问题。

### 1.2 产品目标
构建一个多智能体协商系统，作为研究者的实验平台，模拟多方在建筑概念设计中的谈判过程，产出可复现实验材料，用于量化博弈分析与“好的设计”定义检验。

### 1.3 研究目标（Methodology Fit）
本系统服务于“心智与行为耦合运算”研究，核心是让每个 agent 的内部偏好、冲突策略与外显协商行为形成可计算映射，并通过多轮实验回答以下问题：

1. 不同 TKI 组合如何影响协商成功率与死锁率。
2. 何种策略配置更可能产生公平、帕累托改进且社会总福利更高的设计结果。
3. 协商过程中的让步路径是否可解释、可复现。

### 1.4 成功标准（研究层）
1. 在给定轮次预算内达成可行方案的比例显著高于随机/无策略基线。
2. 能稳定复现实验：同配置多次运行结果方差可控。
3. 结果可解释：每次妥协均可追溯到约束、让步与收益变化。
4. 可支持论文级实验材料导出（逐轮状态、效用轨迹、策略参数、结果指标）。

### 1.5 “好的设计”操作化定义（研究假设）
系统将“好的设计”定义为可计算的多目标判据，而非单一审美判断。候选方案 `x` 需同时考察：

1. 个体理性（Fairness baseline）: 对所有主体 `i`，`u_i(x) >= d_i`，其中 `d_i` 为谈判破裂收益（disagreement payoff）。
2. 帕累托效率: 方案到估计帕累托前沿的距离最小化。
3. 社会总福利: `W(x) = sum_i w_i * u_i(x)` 最大化（`w_i` 可等权或政策加权）。
4. 协商可达性: 达成协议率高、死锁/流产率低。
5. 可生成性: 协商结果可被参数化生成器（Grasshopper）稳定映射为具备空间坐标的候选方案集。

## 2. 范围与非目标

### 2.1 MVP 范围
1. 概念设计级别协商，不做施工图级别细化。
2. 先支持 4-6 个典型角色。
3. 协商对象先聚焦可量化指标：容积率、绿化率、公共空间占比、停车位、预算。
4. 输出文本结论 + 结构化方案 JSON + 审计日志。
5. 输出研究材料：逐轮效用、分歧点、让步路径、死锁原因、反事实对照结果。
6. `final_plan.json` 必须可被下游可视化/生成 app 消费（含 Grasshopper 参数与工件引用）。

### 2.2 非目标
1. 不替代法定审批流程。
2. 不直接生成 BIM 全量模型。
3. 不在 MVP 阶段处理真实个人隐私数据。
4. 不将“视觉草图理解”作为主决策输入（MVP 仅作辅助提取）。

## 3. 智能体角色与心智建模（主题一）

### 3.1 角色集合（MVP）
1. 开发商（Developer）
2. 居民代表（Residents）
3. 城市规划部门（Planner）
4. 环保组织（Environment NGO）
5. 可选: 交通部门（Transport）

### 3.2 TKI 参数化方案（核心）
以两轴参数控制冲突风格，映射为可执行策略：

- `assertiveness`（坚定性，0-1）
- `cooperativeness`（合作性，0-1）

并叠加谈判控制参数：

- `reservation_utility`（底线效用，0-1）
- `concession_rate`（让步速度，0-1）
- `walkaway_threshold`（退出阈值，0-1）
- `package_search_weight`（是否偏好打包交易，0-1）

| TKI策略 | assertiveness | cooperativeness | concession_rate | walkaway_threshold | 行为说明 |
|---|---:|---:|---:|---:|---|
| 竞争 Competing | 0.85-1.00 | 0.00-0.35 | 0.05-0.20 | 0.75-0.95 | 强底线，少让步，优先单项最大化 |
| 合作 Collaborating | 0.70-0.95 | 0.70-0.95 | 0.30-0.60 | 0.40-0.70 | 强目标+强协同，偏好多议题打包优化 |
| 妥协 Compromising | 0.40-0.65 | 0.40-0.65 | 0.50-0.75 | 0.35-0.60 | 追求中间解，时间效率较高 |
| 回避 Avoiding | 0.00-0.30 | 0.00-0.30 | 0.00-0.15 | 0.20-0.45 | 低参与，倾向延迟或退出 |
| 顺应 Accommodating | 0.10-0.35 | 0.75-1.00 | 0.65-0.90 | 0.15-0.40 | 高让步，优先关系与整体推进 |

### 3.3 Persona 注入规范
每个 agent 使用统一 persona schema：

- `role_name`
- `socioeconomic_profile`（收入、产权关系、风险偏好、公共压力）
- `hard_constraints`（不可违反）
- `soft_preferences`（可交易）
- `utility_weights`（目标权重向量）
- `public_narrative_style`（发言风格）

### 3.4 推理框架
1. 采用 ReAct-lite，而非暴露完整 CoT。
2. 每轮发言前执行私有评估步骤：约束校验、对手提议影响评估、候选动作打分。
3. 对外仅输出 `reason_summary`（简化理由），不输出完整内部推理细节。

## 4. 协商协议与通信机制（主题二）

### 4.1 协议选择
采用“SAOP + 轮次同步”的混合协议：

1. 任一 agent 可在开放窗口提交新提议（SAOP特征）。
2. 每个回合末执行一次固定顺序澄清发言与接受/拒绝表态（Roundtable特征）。
3. 触发条件满足即成交：全体一致或达到预设超多数（可配置）。

### 4.2 消息层双通道
1. 自然语言通道: 用于解释、说服、叙事。
2. 结构化通道: JSON payload，用于消歧与可计算执行。

消息 schema（简化）：

```json
{
  "message_type": "proposal|accept|reject|query|inform",
  "proposal_id": "P-20260311-001",
  "issue_deltas": {
    "far": -0.1,
    "green_ratio": 0.05,
    "public_space_ratio": 0.03,
    "budget_delta_million": 12
  },
  "rationale": "用提高绿化换取停车位调整",
  "conditions": ["Developer ROI >= 8%", "Green ratio >= 35%"],
  "confidence": 0.73
}
```

### 4.3 黑板架构
设置共享黑板（shared state）+ 私有内存（private state）：

- 黑板公开: 当前设计状态、已提交提议、历史投票、公共指标。
- 私有保留: 各方真实效用权重、最低可接受阈值、隐藏策略。

## 5. 环境本体与动作空间（主题三）

### 5.1 本体（Ontology）
MVP 本体对象：

- `Parcel` 地块
- `BuildingMass` 建筑体量
- `OpenSpace` 公共开放空间
- `Mobility` 交通与停车
- `Budget` 预算
- `Regulation` 规划与法规约束

关键指标：

- `FAR`（容积率）
- `green_ratio`（绿化率）
- `public_space_ratio`
- `parking_count`
- `total_cost`
- `expected_roi`
- `carbon_proxy`

### 5.2 设计感知与表示（重点）
原则：协商核心引擎消费结构化“设计状态”，而不是直接消费草图像素。  
建议采用 `Design State Graph (DSG)` 作为统一中间表示，草图/文本概念仅作为输入源，经解析后写入 DSG。

输入适配层（MVP 到 V2）：

1. 文本概念输入（MVP主路径）：研究者直接提供结构化参数与约束。
2. 草图解析输入（V2增强）：VLM/OCR/CV 抽取几何与功能线索，输出带置信度的结构化候选。
3. 人工确认闸门：当解析置信度低于阈值时，必须人工确认后入库。

Agent 看到的关键信息（最小充分集）：

1. 地块与法定约束：地块面积、边界、退线、限高、容积率上限、日照/消防约束。
2. 体量与功能：建筑占地、层数/高度、功能配比、可建设面积。
3. 公共与生态：绿化率、公共开放空间面积、可达性代理、碳排代理指标。
4. 交通与基础设施：停车位、出入口容量、慢行系统连接度。
5. 经济信息：成本基线、预算上限、收益预期、敏感性参数。
6. 不确定性信息：每个字段的来源、置信度、是否需人工复核。

DSG 最小 schema（示意）：

```json
{
  "site": {
    "area_m2": 24000,
    "zoning": "R2/C1",
    "far_max": 3.2,
    "height_limit_m": 80
  },
  "program": {
    "residential_gfa_m2": 38000,
    "commercial_gfa_m2": 9000
  },
  "public_env": {
    "green_ratio": 0.34,
    "public_space_ratio": 0.18,
    "carbon_proxy_tco2e": 1200
  },
  "mobility": {
    "parking_count": 520,
    "transit_access_score": 0.71
  },
  "economics": {
    "cost_million": 860,
    "roi_expected": 0.094
  },
  "uncertainty": {
    "source": "text_spec|sketch_parser",
    "confidence": 0.87,
    "needs_human_review": false
  }
}
```

### 5.3 动作空间
MVP 采用“参数化动作”，每个动作可计算、可校验：

- `propose_delta(issue, value)`
- `bundle_trade([issue_deltas])`
- `accept(proposal_id)`
- `reject(proposal_id, reason_code)`
- `request_simulation(proposal_id)`

V2 扩展到“空间动作”：

- `add_park(x,y,area)`
- `shift_building(zone_id,dx,dy)`

### 5.4 环境反馈
环境模拟器在每个候选方案上返回：

- 合规性（法规通过/失败原因）
- 经济性（成本、ROI变化）
- 环境性（绿化、碳代理指标）
- 社会性（公共空间可达性代理分）

### 5.5 Grasshopper 中间生成层（Rhino 桥接）
设计原则：协商层先达成“参数约束合约”，再由 Grasshopper 在约束空间内演化多个可视化候选方案。

闭环流程：

1. 协商层输出宏观参数区间与目标权重（如 FAR 区间、绿化率下限、预算上限）。
2. Grasshopper 适配器读取参数并执行 `ghx/gh`，生成 `N` 个具备空间坐标的候选方案。
3. 每个候选方案输出：
   - Rhino 几何工件（`.3dm` 或等效格式）
   - 人类可读图像工件（鸟瞰图、总平图）
   - 机器可读 sidecar（`design_options.jsonl`，逐方案一行）
4. 仿真与评估引擎对候选方案计算 KPI 并回写黑板，供 agent 继续协商或收敛。

机器可读 sidecar（每行一个候选）建议字段：

```json
{
  "variant_id": "v_017",
  "source_plan_id": "plan_20260311_001",
  "gh_definition": "tower_mix_v3.ghx",
  "param_vector": {"far": 2.95, "green_ratio": 0.36, "podium_height_m": 18},
  "geometry_ref": {"rhino_3dm": "artifacts/v_017.3dm"},
  "preview_ref": {"birdview_png": "artifacts/v_017_birdview.png", "siteplan_png": "artifacts/v_017_siteplan.png"},
  "kpi": {"roi": 0.091, "carbon_proxy": 1180, "public_space_ratio": 0.19},
  "constraint_pass": true
}
```

约束：agent 默认不直接解析 Rhino 几何本体，而是消费 sidecar JSONL 与 KPI 结果，确保可重复与可审计。
每个几何对象需保留稳定 `object_guid`，并在 sidecar 中维护 `object_guid -> 语义构件` 映射。

## 6. 记忆机制与上下文管理（主题四）

### 6.1 三层记忆
1. 工作记忆: 最近 N 轮逐条消息（建议 N=6）。
2. 情景记忆: 每 3 轮自动总结一次的“让步与分歧摘要”。
3. 语义记忆: 稳定规则（角色人设、法规、底线参数）。

### 6.2 抗指令衰减
每轮推理前注入 `system reminder`：

- 当前关键分歧 Top-K
- 该 agent 不可违反的 hard constraints
- 当前采用的 TKI 策略参数
- 剩余轮次与时间压力

### 6.3 上下文压缩策略
1. 对历史对话做结构化摘要，替代原文回灌。
2. 保留“转折点事件”原文引用（首次重大让步、规则冲突、临近破裂）。
3. 所有摘要写入审计日志，支持复盘。

## 7. 评估体系与审计（主题五）

### 7.1 结果指标
1. `agreement_rate`: 达成协议的实验占比。
2. `deadlock_rate`: 超轮次/超时未达成协议的占比（流产率）。
3. `individual_rationality_rate`: 各方获得收益不低于破裂收益 `d_i` 的比例。
4. `pareto_frontier_distance`: 最终方案到估计帕累托前沿的归一化距离（越小越好）。
5. `social_welfare`: 群体效用 `W(x)=sum_i w_i*u_i(x)`（越大越好）。
6. `utility_balance_index`: 各方效用均衡度（建议 `1-Gini`）。

### 7.2 指标计算定义（用于论文复现）
1. 公平性（个体理性）: 对方案 `x`，若 `u_i(x) >= d_i` 对所有 `i` 成立，则记为公平可接受。
2. 帕累托边界距离: `PFD(x)=min_{y in ParetoSet} ||u(y)-u(x)||_2`，并做 [0,1] 归一化。
3. 社会总福利: 默认等权 `w_i=1/N`，支持政策权重配置。
4. 协议率与流产率: 分母均为总实验次数，保证可横向比较。
5. 死锁强度: 额外记录僵局轮次长度与“最后可行提议”距离。

### 7.3 过程指标
1. 让步曲线斜率（按 agent）。
2. 提议被采纳率。
3. 发言份额均衡性。
4. 无效提议率（被规则引擎拒绝）。
5. 约束触碰频次（触底线次数）。
6. 策略漂移度（实际行为与设定 TKI 参数的偏离）。

### 7.4 LLM-as-a-judge（辅助层，不替代量化指标）
可引入双裁判机制作为补充解释：

1. Judge-A: 评空间公平性（Spatial Justice Rubric）。
2. Judge-B: 评利益分配合理性与叙事一致性。
3. 当两者分歧超过阈值时触发人工复核。
4. 量化指标为主判据，LLM 评分只作为质性解释，不作为单一结论来源。

## 8. 系统架构与安全脚手架（主题六）

### 8.1 框架选型结论
MVP 推荐：`LangGraph + 自定义模拟器 + 规则引擎`。

原因：

1. 需要强状态机、可恢复执行、可审计回放，LangGraph 适配度高。
2. AutoGen 可用于多 agent 对话，但其官方已提示新项目可优先考虑 Microsoft Agent Framework，技术路线存在迁移成本。
3. AgentSociety更偏大规模社会仿真，启动成本高，建议作为 V2/V3 环境层增强，而非 MVP 依赖。

### 8.2 防御式 Harness（四层）
1. Schema 层: 严格 JSON Schema/Pydantic 校验。
2. 规则层: 规划法规、预算上限、物理约束校验器。
3. 仿真层: 对候选提议运行快速可行性评估。
4. 策略层: 违规提议拒绝并返回机器可读错误码。

### 8.3 审计与可追溯
1. 事件溯源（event sourcing）记录每次动作。
2. 全量版本化：`state_t`、`proposal_t`、`metrics_t`。
3. 支持回放：任意轮次重建协商现场。

### 8.4 Rhino/Grasshopper 适配器
1. 适配器职责：接收 `final_plan` 或中间协商约束，调用 Grasshopper 生成候选方案并输出 sidecar JSONL。
2. 运行模式：
   - MVP: 批处理模式（每轮或每阶段触发一次生成）。
   - V2: 交互式模式（支持准实时增量生成与回写）。
3. 接口要求：
   - 输入：`generation_recipe + parameter_bounds + seed`
   - 输出：`design_options.jsonl + geometry artifacts + preview artifacts`
4. 可靠性要求：任一生成失败要返回机器可读错误码，不得静默失败。

## 9. 功能需求清单（MVP）

### 9.1 核心功能
1. 创建协商会话（角色、地块、初始约束）。
2. 运行多轮谈判（可设最大轮次、超时）。
3. 实时黑板状态展示。
4. 对提议执行规则校验与仿真反馈。
5. 达成/破裂判定与报告导出。
6. 研究实验编排器（批量运行策略组合与随机种子）。
7. 设计输入适配器（文本结构化输入为主，草图解析为辅）。
8. Grasshopper 方案生成器（基于参数约束批量生成空间候选）。
9. Rhino sidecar 抽取器（将模型工件映射为 JSONL 机器可读材料）。

### 9.2 输出物
1. `final_plan.json`
2. `negotiation_log.jsonl`
3. `evaluation_report.json`
4. `utility_trajectory.csv`（逐轮效用轨迹）
5. `experiment_manifest.json`（参数、种子、模型版本）
6. `pareto_analysis.json`（前沿估计与距离）
7. `design_options.jsonl`（Grasshopper 候选方案 sidecar）
8. `artifacts/`（`.3dm`、鸟瞰图、总平图等可视化工件）
9. 人类可读摘要报告（Markdown/PDF）

### 9.3 `final_plan.json` 数据契约（高层）
`final_plan.json` 需包含三层信息，确保既可研究复现也可驱动可视化 app：

1. `semantic_plan`: 协商达成的目标、约束、KPI 与公平性结论。
2. `generation_recipe`: Grasshopper 定义、参数边界、采样策略、随机种子、候选数量。
3. `selected_variant`: 入选方案 ID、工件路径、关键空间指标与评分。

## 10. 非功能需求

1. 可复现实验: 固定随机种子时，关键指标方差在可控区间。
2. 性能: 6 agent、30轮以内协商在单次任务可接受时延内完成。
3. 稳定性: 失败可恢复，支持断点续跑。
4. 安全性: 无 schema 合法性即拒绝执行。

## 11. 里程碑

1. M1（2周）: 本体、DSG 结构、规则引擎最小闭环，单回合校验跑通。
2. M2（2周）: 多 agent 协商循环 + 黑板 + 日志回放 + 逐轮效用计算。
3. M3（2周）: Rhino/Grasshopper 适配器 + sidecar JSONL + 方案工件输出。
4. M4（2周）: 研究指标体系（公平/PFD/总福利/协议率）+ 对比实验脚本 + LLM Judge 辅助评审。

## 12. 待确认决策（必须）

1. 法规基准地域: 中国国标/地方法规，还是国际化抽象规则集。
2. 协议成交条件: 全体一致，还是 2/3 超多数。
3. 主优化目标优先级: 经济收益优先，还是环境公平/空间正义优先。
4. LLM 预算上限: 每次会话可接受 token 成本区间。
5. 是否引入真人在环审批节点（例如最终一票否决）。
6. 设计输入策略: MVP 是否仅允许结构化输入，草图解析放入 V2。
7. 社会总福利权重 `w_i` 设定: 等权、人口加权或政策加权。
8. Grasshopper 执行模式: 本地 Rhino/Grasshopper、Rhino.Compute，或混合模式。
9. 每轮候选生成规模: 固定 `N`，还是按不确定性自适应 `N`。

## 13. 验收标准（MVP）

1. 至少 3 组冲突策略组合（竞争型、合作型、混合型）可重复跑完 30 次实验。
2. 每次实验输出完整结构化日志、最终方案与逐轮效用轨迹。
3. 非法提议拦截率达到 100%（规则已覆盖范围内）。
4. 能清晰比较不同策略组合对协议率、流产率、公平性、帕累托边界距离、社会总福利的影响。
5. 固定种子重跑时关键指标误差在预设容忍区间内。
6. 任一 `final_plan.json` 可驱动 Grasshopper 生成候选方案并产出 `.3dm + 预览图 + JSONL sidecar`。
7. 候选方案 sidecar 与工件一一对应，且可被可视化 app 直接消费。

---

## 参考资料（用于选型与协议定义）

1. LangGraph 文档（持久化状态、检查点与工作流能力）: https://docs.langchain.com/oss/python/langgraph/overview
2. LangGraph durable execution: https://langchain-ai.github.io/langgraph/concepts/durable_execution/
3. AutoGen 仓库（新项目路线提示）: https://github.com/microsoft/autogen
4. Microsoft Agent Framework（与 AutoGen 关系与迁移）: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/
5. AgentSociety 论文（社会仿真定位）: https://aclanthology.org/2024.findings-emnlp.400/
6. AgentSociety 文档（城市空间与经济活动仿真能力）: https://agentsociety.readthedocs.io/en/latest/
7. SAOP（ANAC 竞赛常见协议说明）: https://ii.tudelft.nl/nego/node/14
8. TKI 手册（五种冲突处理模式）: https://shop.themyersbriggs.com/en/thomas-kilmann-conflict-mode-instrument-tki
9. ReAct 方法论文: https://arxiv.org/abs/2210.03629
10. IFC（建筑信息模型开放标准）: https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/
