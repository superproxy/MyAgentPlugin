初始化代码开发多 Agent 协作框架（Harness Engineering — Dev 模式）。

使用 `init-dev-harness-agents` skill 执行以下操作：

1. **扫描项目**：读取 package.json、pom.xml、目录结构，识别技术栈与现有 agent 结构
2. **生成 Harness 配置**：创建 `agents/harness.yaml`，定义开发 Agent 角色（orchestrator / executor / reviewer）
3. **生成 Agent 角色定义**：创建 `agents/roles/` 目录，为每个角色生成提示词模板
4. **生成工作流定义**：创建 `agents/workflows/`，定义开发协作流程（开发 / 审查 / 调试）
5. **生成 Harness AGENTS.md**：harness 工程的项目定位、agent 架构拓扑、协作流程、治理规则
6. **生成通信配置**：创建 `agents/communication.yaml`，定义 agent 间消息格式、路由规则
7. **确认并提交**：展示给用户确认后 git commit

如果 Harness 配置已存在，不要覆盖，而是 diff 展示建议改动。

## 触发方式

| 命令 | 类型 | 说明 |
|------|------|------|
| `/init-dev` | 开发 Harness 初始化 | 代码开发领域多 Agent 协作（orchestrator / executor / reviewer） |
