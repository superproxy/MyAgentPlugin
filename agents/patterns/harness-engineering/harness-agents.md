## Harness 模式总览

| 模式 | 命令 | Skill | 角色 | 适用场景 |
|------|------|-------|------|---------|
| 通用 Harness | `/init` | `init-harness-agents` | coordinator / analyst / creator / evaluator | 产品、设计、研究 |
| 开发 Harness | `/init-dev` | `init-dev-harness-agents` | orchestrator / executor / reviewer | 代码开发 |
| 辩论 Harness | `/loop` | `init-loop-agents` | collector / challenger / reasoner / judge / optimizer | 求真辨伪、方案辩论 |

---

# Harness Engineering — Agent 框架初始化

为项目搭建 AI Agent 协作框架（Harness），定义 Agent 角色、工作流、通信协议与治理规则。

## 通用 / 开发 Harness

使用 `init-harness-agents` 或 `init-dev-harness-agents` skill 执行以下操作：

1. **扫描项目**：读取 package.json、pom.xml、目录结构，识别技术栈与现有 agent 结构
2. **生成 Harness 配置**：创建 `agents/harness.yaml`，定义 agent 角色清单、能力边界、通信协议（A2A / MCP / 直接调用）
3. **生成 Agent 角色定义**：创建 `agents/roles/` 目录，为每个角色生成提示词模板（system prompt + 能力声明 + 输入输出契约）
4. **生成工作流定义**：创建 `agents/workflows/`，定义多 agent 协作流程（顺序 / 并行 / 辩论 / 评审）
5. **生成 Harness AGENTS.md**：harness 工程的项目定位、agent 架构拓扑、协作流程、治理规则、skill 依赖
6. **生成通信配置**：创建 `agents/communication.yaml`，定义 agent 间消息格式、路由规则、超时与重试策略
7. **确认并提交**：展示给用户确认后 git commit

如果 Harness 配置已存在，不要覆盖，而是 diff 展示建议改动。

## Harness 工程目录结构

```
agents/
├── harness.yaml           # Harness 主配置：角色清单、能力矩阵、协议声明
├── communication.yaml     # Agent 间通信配置：消息格式、路由、超时
├── roles/                 # Agent 角色定义
│   ├── orchestrator.md    # 编排者：任务分发、上下文管理
│   ├── executor.md        # 执行者：具体任务实施
│   ├── reviewer.md        # 评审者：代码/方案审查
│   └── ...
├── workflows/             # 多 Agent 协作流程
│   ├── code-review.yaml   # 代码审查流程
│   ├── prd-to-code.yaml   # PRD → 代码 流程
│   └── ...
└── AGENTS.md              # Harness 工程入口文档
```

## Harness 配置模板（harness.yaml）

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
    instances: 3  # 可并行实例数

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

## 与标准 init 的区别

| 维度 | 标准 init | Harness init |
|------|----------|-------------|
| 目标 | 单项目开发流程 | 多 Agent 协作框架 |
| 产出 | AGENTS.md + docs/ | harness.yaml + roles/ + workflows/ |
| 适用 | 常规前后端项目 | 需要多 Agent 协作的复杂项目 |
| Agent 模型 | 单一 Agent | 多角色 Agent 集群 |
| 触发 | `/init` | `/init-dev` |

## 辩论 Harness（Loop Engineering）

基于 [loop-engineering](https://github.com/cobusgreyling/loop-engineering)，提供一个**通用的多角色工作流执行引擎**。不绑定任何特定角色或领域——角色和工作流由项目自行定义。

### 核心思路

```
agents/
├── debate-workflow.yaml   # 工作流定义（步骤、角色、依赖、条件、循环）
└── roles/                 # 角色定义（每个角色一个 .md 文件）
    ├── role-a.md
    └── role-b.md
```

引擎只做通用的事：解析 YAML → 拓扑排序 → 化身角色执行 → 保存结果。角色人格和能力来自项目自己的 `roles/*.md`。

### 示例：求真辨伪工作流

`agents/patterns/loop-enginerring/` 中提供了一个完整示例：

| 角色 | 职责 |
|------|------|
| Collector | 搜集争议话题，八维度打分筛选 |
| Challenger | 质疑者：找漏洞、红旗信号、异常聚类 |
| Reasoner | 推理者：建立最强解释、证据分级 |
| Judge | 裁判者：比较证据强度、分层结论 |
| Optimizer | 优化者：沉淀方法论、同步角色能力 |

### 自动化流程

```
/loop 触发
    │
    ▼
解析 debate-workflow.yaml → 拓扑排序
    │
    ▼
按步骤化身角色执行（支持依赖、条件、循环）
    │
    ▼
全部输出保存到 debates/{工作流名称}-{日期}/
    │
    ▼
检查是否需要更新角色武器库
```

### 触发方式

| 命令 | 说明 |
|------|------|
| `/loop` | 运行当前项目的工作流 |
| `/loop --resume` | 从上次中断处继续 |
