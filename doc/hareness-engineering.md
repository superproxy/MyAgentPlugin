# Patterns 参考来源

## Loop Engineering
https://github.com/cobusgreyling/loop-engineering

多角色辩论工作流：Collector → Challenger ⇄ Reasoner → Judge → Optimizer

## Harness Engineering
https://openai.com/zh-Hans-CN/index/harness-engineering/

多 Agent 协作框架：通用 Harness / 开发 Harness / 辩论 Harness



Harness 工程可以理解成一套“多 Agent 协作工程化框架”。它的核心特性是把 AI 协作从临时对话，变成有角色、有流程、有质量检查、有交付记录的工作系统。
主要特性：
多 Agent 角色分工
常见角色包括：
coordinator：拆任务、分配工作、做最终决策
analyst：调研、分析、澄清需求、评估风险
creator：生成内容、方案、文档、原型等产物
evaluator：检查质量、一致性、合规性，提出修改意见

标准化工作流
Harness 会把协作过程定义成可复用流程，例如：
标准协作：拆解 → 分析 → 创作 → 评估 → 修订
辩论决策：提出方案 → 批判比较 → 裁决
调研综合：多源分析 → 汇总 → 输出结论

支持顺序、并行、评审、辩论
不同任务可以用不同编排方式：
顺序执行：一步一步推进
并行执行：多个 Agent 同时产出
Review 循环：创作后由评估者检查，再修订
Debate 模式：多方案对比后决策

配置化管理
通常会生成这些文件：
agents/harness.yaml：主配置，定义 Agent、能力、流程
agents/roles/*.md：每个 Agent 的角色说明
agents/workflows/*.yaml：协作流程
agents/communication.yaml：消息格式、超时、重试规则
agents/AGENTS.md：整个 Harness 工程入口说明

通信协议标准化
Agent 之间不是随便“聊天”，而是按统一消息结构传递：
来源 Agent
目标 Agent
消息类型
任务内容
优先级
关联 ID
超时与重试策略

适合复杂任务拆解
尤其适合产品、设计、研究、内容、研发等需要多人协作式思考的任务，比如：
需求分析
PRD 编写
方案评审
原型设计
竞品调研
技术开发拆分
文档生成与质量检查

有治理机制
它强调角色边界、错误处理、决策机制和质量标准，避免多个 Agent 各说各话。

可扩展
可以根据项目增加新角色、新流程、新检查规则。例如研发型 Harness 可以换成：
orchestrator
executor
reviewer

简单说，Harness 工程的价值就是：把 AI 从“一个助手”升级成“一个有组织的协作团队”，并且这个团队的分工、流程和交付标准都能沉淀在项目里。