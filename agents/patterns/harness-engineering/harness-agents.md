# Harness Engineering — Agent 框架初始化

为项目搭建 AI Agent 协作框架（Harness），定义 Agent 角色、工作流、通信协议与治理规则。

使用 `init-dev-harness-agents` skill 执行以下操作：

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
