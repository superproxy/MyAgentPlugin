---
name: init-dev-harness-agents
description: Use when initializing a code-development multi-agent collaboration framework (Harness Engineering) - generates harness.yaml with orchestrator/executor/reviewer roles, dev workflows, and communication config
---

# Init Dev Harness Agents — 代码开发多 Agent 协作框架初始化

## Overview

为代码开发项目搭建 AI Agent 协作框架（Harness Engineering），定义开发专用 Agent 角色（orchestrator / executor / reviewer）、开发工作流、通信协议与治理规则。

**核心原则**: 每个 Agent 角色职责单一、输入输出契约明确、通信协议标准化。面向代码生成、审查、调试等开发场景。

## When to Use

- 新代码项目需要多 Agent 开发协作框架
- 已有代码项目接入 Harness Engineering（开发模式）
- `/init --harness --dev` 命令触发
- 需要定义开发 Agent 角色分工与协作流程（orchestrator / executor / reviewer）

## Boot Agents 流程

收到 `/init-dev` 指令后，执行以下步骤：

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

创建 `agents/harness.yaml`，定义：

```yaml
name: {项目名}-harness
version: 1.0.0

agents:
  - id: orchestrator
    role: orchestrator.md
    capabilities: [task-decomposition, context-management, agent-routing]
    protocol: direct

  - id: executor
    role: executor.md
    capabilities: [code-generation, file-operation, command-execution]
    protocol: direct
    instances: 3

  - id: reviewer
    role: reviewer.md
    capabilities: [code-review, security-scan, quality-check]
    protocol: direct

workflows:
  - name: standard-dev
    steps:
      - agent: orchestrator
        action: decompose
      - agent: executor
        action: implement
        parallel: true
      - agent: reviewer
        action: review
      - agent: executor
        action: fix
        condition: review.failed

communication:
  format: json
  timeout_ms: 30000
  retry: 3
```

### Step 3: 生成 Agent 角色定义

创建 `agents/roles/` 目录，为每个角色生成提示词模板：

**orchestrator.md** — 编排者：
- 职责：任务分解、上下文管理、Agent 路由
- 输入：用户需求 / 上游 Agent 输出
- 输出：任务分配指令

**executor.md** — 执行者：
- 职责：代码生成、文件操作、命令执行
- 输入：任务分配指令
- 输出：代码变更 / 执行结果

**reviewer.md** — 评审者：
- 职责：代码审查、安全扫描、质量检查
- 输入：代码变更
- 输出：审查报告

### Step 4: 生成工作流定义

创建 `agents/workflows/` 目录，定义多 Agent 协作流程：

- `code-review.yaml` — 代码审查流程
- `prd-to-code.yaml` — PRD → 代码流程
- `debug-workflow.yaml` — 调试协作流程

工作流类型：
- **顺序（sequential）**：Agent 按序执行
- **并行（parallel）**：多个 Agent 同时执行
- **辩论（debate）**：多 Agent 讨论达成共识
- **评审（review）**：执行 → 评审 → 修复循环

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

## Skill 依赖
| Skill | 用途 |
|---|---|
| init-dev-harness-agents | Harness 框架初始化 |
| brainstorming | 需求澄清 |
| writing-plans | 实施计划 |
| subagent-driven-development | 逐任务实施 |
| systematic-debugging | 排查 bug |
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
  default_ms: 30000
  review_ms: 60000

retry:
  max_attempts: 3
  backoff: exponential

message:
  schema: |
    {
      "from": "agent_id",
      "to": "agent_id",
      "type": "task | review | response",
      "payload": {},
      "correlation_id": "uuid"
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
│   ├── orchestrator.md
│   ├── executor.md
│   └── reviewer.md
├── workflows/             # 多 Agent 协作流程
│   ├── code-review.yaml
│   ├── prd-to-code.yaml
│   └── debug-workflow.yaml
└── AGENTS.md              # Harness 工程入口文档
```

## 依赖 Skill 声明

init-dev-harness-agents 本身不依赖其他 skill 执行，但生成的 AGENTS.md 中会声明 Harness 工程所需的 skill 链：

```
Harness 开发 skill 链:
  brainstorming → writing-plans → subagent-driven-development → verification-before-completion

多 Agent 协作:
  orchestrator → executor (parallel) → reviewer → executor (fix)

调试:
  systematic-debugging

验证:
  verification-before-completion
```

## 模板变量

| 变量 | 来源 | 示例 |
|---|---|---|
| `{项目名}` | 目录名或 package.json name | stock-analysis |
| `{技术栈}` | 扫描依赖文件 | Java 17 + Spring Boot + Vue3 + Vite |
| `{Agent 数量}` | 根据项目复杂度 | 3（orchestrator + executor + reviewer） |
| `{工作流数量}` | 根据项目需求 | 3（dev / review / debug） |

## 与 init-harness-agents 的区别

| 维度 | init-harness-agents（通用） | init-dev-harness-agents（开发） |
|------|--------------------------|-------------------------------|
| 目标 | 通用多 Agent 协作 | 代码开发多 Agent 协作 |
| 角色 | coordinator / analyst / creator / evaluator | orchestrator / executor / reviewer |
| 适用 | 产品、设计、研究等非代码领域 | 前后端代码开发 |
| 工作流 | 协作、辩论、调研 | 开发、审查、调试 |
| 触发 | `/init` | `/init-dev` |

## 注意事项

- 如果 Harness 配置已存在，不要覆盖，而是 diff 展示建议改动
- 角色定义保持单一职责，避免一个角色承担过多能力
- 工作流定义优先覆盖核心流程（dev / review / debug），后续按需扩展
- 通信配置中的超时和重试策略根据实际 Agent 响应时间调整
- 必须记录用户的询问，放在 `docs/interaction-changes/`，并在 AGENTS.md 中说明位置
