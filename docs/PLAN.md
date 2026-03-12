# Archagent 多智能体系统详细开发计划（落盘目标：`docs/DEVELOPMENT_PLAN.md`）

## 摘要
1. 文档策略：将以下内容作为唯一主计划写入 `docs/DEVELOPMENT_PLAN.md`，后续迭代只更新此文件，避免计划分叉。  
2. 开发主线：按“Agent 内核优先”推进，先完成协商引擎闭环，再接入真实 GH 生成，再做实验编排与评估。  
3. 目标定义：10 周内把当前 phase-1 合约原型升级为可重复实验的多智能体协商系统，满足 4-6 agent、30 轮协商、可回放、可对比实验。  

## 实施计划（10 周，决策已锁定）
1. 第 1-2 周：协商运行时内核。交付会话状态机、回合协议（提议/校验/表态/结算）、黑板状态、事件溯源日志、断点恢复。  
2. 第 3-4 周：规则与效用引擎。交付 hard/soft 约束校验、agent 效用函数、让步与退出机制、无效提议拦截、deadlock 判定。  
3. 第 5-6 周：生成与选择闭环。交付“协商结果 -> 生成候选 -> 评估 KPI -> 3 judge 选择 -> final_plan”自动链路；保留 mock 适配器并新增真实适配器入口。  
4. 第 7-8 周：研究实验层。交付批量实验编排器（策略组合 × 随机种子）、指标计算（agreement/deadlock/fairness/pareto/social welfare）、对照实验报告输出。  
5. 第 9-10 周：稳定化与发布。交付性能基线、失败注入回归、契约兼容性检查、最小可用 CLI 与文档闭环。  

## 公开接口与数据契约变更
1. 新增会话输入契约：`session_input`（角色配置、TKI 参数、初始 DSG、回合预算、seed、成交规则）。  
2. 新增过程事件契约：`negotiation_event`（proposal/accept/reject/query/inform、规则校验结果、效用变化、时间戳、轮次）。  
3. 新增评估结果契约：`evaluation_report`（协议率、死锁率、个体理性、PFD、社会福利、过程指标）。  
4. 稳定接口定义：  
   `NegotiationEngine.run(session_input) -> SessionResult`  
   `RuleEngine.validate(proposal, state) -> ValidationResult`  
   `UtilityEngine.score(agent_id, state) -> UtilitySnapshot`  
   `GeneratorAdapter.generate(generation_recipe, constraints) -> DesignOptions`  
   `SelectionEngine.select(candidates) -> SelectionResult`  
5. 兼容性策略：`final_plan.v1` 保持向后兼容；新增研究输出文件（`negotiation_log.jsonl`、`utility_trajectory.csv`、`evaluation_report.json`、`experiment_manifest.json`、`pareto_analysis.json`）不破坏现有消费端。  

## 测试与验收方案
1. 单元测试：规则校验、效用函数、让步策略、投票选择、坐标映射、错误码覆盖。  
2. 集成测试：单会话 30 轮内收敛或正确死锁；无效提议拦截率 100%；输出工件与 sidecar 一一对应。  
3. 端到端测试：固定 seed 重跑两次，关键结果一致（允许时间戳差异）；`final_plan + design_options` 合约校验通过。  
4. 失败注入测试：LLM 不可用、生成器失败、工件缺失、坐标缺项、候选全 infeasible，系统均返回机器可读错误并可恢复。  
5. 性能验收：4-6 agent、30 轮会话在目标机器满足可接受时延；批量实验支持至少 3 组策略 × 30 次重跑。  

## 已锁定假设与默认值
1. 主线优先级：Agent 内核优先。  
2. 成交规则：默认 2/3 超多数。  
3. 法规基线：MVP 先用抽象规则集。  
4. 输入策略：MVP 仅结构化输入，草图解析放 V2。  
5. 研究权重：社会福利默认等权，可在实验配置中覆盖。  
6. 风险兜底：真实 GH 适配未就绪时，mock 适配持续可用，保证实验与契约链路不断。  
