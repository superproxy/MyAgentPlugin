初始化项目开发流程和 AGENTS.md。

使用 `init-dev-agents` skill 执行以下操作：

1. **扫描项目**：读取 package.json、pom.xml、目录结构，识别技术栈
2. **生成 AGENTS.md**：项目定位、工程结构、开发流程、skill 依赖、约定、启动命令
3. **生成需求收集流程**：创建 `docs/requirement-workflow.md`（如不存在）
4. **生成交互调整目录**：创建 `docs/interaction-changes/` + README 索引
5. **确认并提交**：展示给用户确认后 git commit

如果 AGENTS.md 已存在，不要覆盖，而是 diff 展示建议改动。
