---
name: init-harness-agents
description: Use when initializing a general-purpose multi-agent collaboration framework (Harness Engineering) - generates harness.yaml, agent role definitions, workflow definitions, and communication config for any domain
---

# Init Harness Agents — 通用多 Agent 协作框架初始化

## Overview

为项目搭建通用 AI Agent 协作框架（Harness Engineering），定义 Agent 角色、工作流、通信协议与治理规则。适用于产品、设计、研究等非代码开发领域的多 Agent 协作。

**核心原则**: Agent 角色按能力域划分，工作流按业务场景编排，通信协议标准化。

## When to Use

- 新项目需要通用多 Agent 协作框架
- 产品 / 设计 / 研究等非代码领域接入 Harness
- `/init` 命令触发（通用 Harness 模式）
- 需要定义跨领域 Agent 角色分工与协作流程

## Boot Agents 流程

收到 `/init` 指令后，执行以下步骤：

### Step 1: 扫描项目

```
扫描内容：
├── package.json / pom.xml / Cargo.toml → 技术栈
├── src/ / app/ / lib/ → 目录结构
├── agents/ → 现有 agent 结构（如有）
├── .git/ → 是否 git 仓库
├── existing harness.yaml → 是否已有 Harness 配置
└── docs/ → 已有文档
```

### Step 2: 生成 Harness 配置

创建 `agents/harness.yaml`，定义通用 Agent 角色：

```yaml
name: {项目名}-harness
version: 1.0.0

agents:
  - id: coordinator
    role: coordinator.md
    capabilities: [task-decomposition, context-management, agent-routing, decision-making]
    protocol: direct

  - id: analyst
    role: analyst.md
    capabilities: [research, data-analysis, requirement-clarification, risk-assessment]
    protocol: direct

  - id: creator
    role: creator.md
    capabilities: [content-generation, design-output, document-writing, prototyping]
    protocol: direct
    instances: 2

  - id: evaluator
    role: evaluator.md
    capabilities: [quality-check, consistency-review, compliance-verification]
    protocol: direct

workflows:
  - name: standard-collaboration
    steps:
      - agent: coordinator
        action: decompose
      - agent: analyst
        action: analyze
      - agent: creator
        action: create
        parallel: true
      - agent: evaluator
        action: evaluate
      - agent: creator
        action: revise
        condition: evaluator.failed

  - name: debate-decision
    steps:
      - agent: analyst
        action: present-options
      - agent: evaluator
        action: critique
      - agent: coordinator
        action: decide

communication:
  format: json
  timeout_ms: 60000
  retry: 3
```

### Step 3: 生成 Agent 角色定义

创建 `agents/roles/` 目录，为每个角色生成提示词模板：

**coordinator.md** — 协调者：
- 职责：任务分解、上下文管理、Agent 路由、决策仲裁
- 输入：用户需求 / 上游 Agent 输出
- 输出：任务分配指令 / 决策结论

**analyst.md** — 分析者：
- 职责：调研分析、数据解读、需求澄清、风险评估
- 输入：待分析问题 / 数据源
- 输出：分析报告 / 需求文档

**creator.md** — 创作者：
- 职责：内容生成、设计输出、文档编写、原型制作
- 输入：创作指令 / 参考素材
- 输出：创作产物

**evaluator.md** — 评估者：
- 职责：质量检查、一致性审查、合规验证
- 输入：待评估产物
- 输出：评估报告 / 改进建议

### Step 4: 生成工作流定义

创建 `agents/workflows/` 目录，定义多 Agent 协作流程：

- `standard-collaboration.yaml` — 标准协作流程（分析→创作→评估）
- `debate-decision.yaml` — 辩论决策流程（多方案→批判→裁决）
- `research-synthesis.yaml` — 调研综合流程

工作流类型：
- **顺序（sequential）**：Agent 按序执行
- **并行（parallel）**：多个 Agent 同时执行
- **辩论（debate）**：多 Agent 讨论达成共识
- **评审（review）**：创作 → 评估 → 修订循环

### Step 5: 生成 Harness AGENTS.md

按以下模板生成：

```markdown
# {项目名} — Harness 工程

## 项目定位
[一句话]

## Agent 架构拓扑
（引用 harness.yaml 中的角色关系）

## 协作流程
（引用 agents/workflows/）

## 治理规则
### 角色边界
### 通信协议
### 错误处理
### 决策机制

## Skill 依赖
| Skill | 用途 |
|---|---|
| init-harness-agents | Harness 框架初始化 |
| brainstorming | 需求澄清 |
| writing-plans | 实施计划 |
| subagent-driven-development | 逐任务实施 |
| verification-before-completion | 完成前验证 |

## 启动命令
## 当前优先级
```

### Step 6: 生成通信配置

创建 `agents/communication.yaml`：

```yaml
format: json
routing:
  default: direct
  fallback: mcp

timeout:
  default_ms: 60000
  analysis_ms: 120000

retry:
  max_attempts: 3
  backoff: exponential

message:
  schema: |
    {
      "from": "agent_id",
      "to": "agent_id",
      "type": "task | analysis | creation | evaluation | decision",
      "payload": {},
      "correlation_id": "uuid",
      "priority": "normal | high | low"
    }
```

### Step 7: 确认并提交

- 展示生成的 Harness 配置给用户确认
- 用户确认后 git commit

## Harness 工程目录结构

```
agents/
├── harness.yaml           # Harness 主配置
├── communication.yaml     # Agent 间通信配置
├── roles/                 # Agent 角色定义
│   ├── coordinator.md
│   ├── analyst.md
│   ├── creator.md
│   └── evaluator.md
├── workflows/             # 多 Agent 协作流程
│   ├── standard-collaboration.yaml
│   ├── debate-decision.yaml
│   └── research-synthesis.yaml
└── AGENTS.md              # Harness 工程入口文档
```

## 依赖 Skill 声明

init-harness-agents 本身不依赖其他 skill 执行，但生成的 AGENTS.md 中会声明 Harness 工程所需的 skill 链：

```
通用 Harness 协作链:
  brainstorming → writing-plans → subagent-driven-development → verification-before-completion

多 Agent 协作:
  coordinator → analyst → creator (parallel) → evaluator → creator (revise)

辩论决策:
  analyst (options) → evaluator (critique) → coordinator (decide)
```

## 模板变量

| 变量 | 来源 | 示例 |
|---|---|---|
| `{项目名}` | 目录名或 package.json name | product-research |
| `{领域}` | 项目类型 | 产品 / 设计 / 研究 |
| `{Agent 数量}` | 根据项目复杂度 | 4（coordinator + analyst + creator + evaluator） |
| `{工作流数量}` | 根据项目需求 | 3（collaboration / debate / research） |

## 与 init-dev-harness-agents 的区别

| 维度 | init-harness-agents（通用） | init-dev-harness-agents（开发） |
|------|--------------------------|-------------------------------|
| 目标 | 通用多 Agent 协作 | 代码开发多 Agent 协作 |
| 角色 | coordinator / analyst / creator / evaluator | orchestrator / executor / reviewer |
| 适用 | 产品、设计、研究等非代码领域 | 前后端代码开发 |
| 工作流 | 协作、辩论、调研 | 开发、审查、调试 |
| 触发 | `/init` | `/init-dev` |

## 注意事项

- 如果 Harness 配置已存在，不要覆盖，而是 diff 展示建议改动
- 角色定义保持单一职责，按能力域划分而非按任务划分
- 工作流定义优先覆盖核心协作模式，后续按需扩展
- 通信配置中的超时策略根据领域特点调整（分析类任务通常需要更长超时）
- 必须记录用户的询问，放在 `docs/interaction-changes/`，并在 AGENTS.md 中说明位置
