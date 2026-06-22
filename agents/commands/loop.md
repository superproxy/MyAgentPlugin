启动多角色辩论工作流（Loop Engineering），自动解析工作流定义、执行步骤、保存结果。

使用 `init-loop-agents` skill 自动执行以下操作：

1. **解析工作流**：读取 `agents/debate-workflow.yaml`，提取名称、输入、步骤、依赖关系、条件和循环
2. **收集输入**：`required: true` 的输入由用户提供，可选输入使用默认值
3. **构建执行顺序**：按 `depends_on` 拓扑排序，无依赖步骤并行执行
4. **执行步骤**：读取 `agents/roles/{role}.md`，化身该角色执行任务，变量替换、条件评估、循环控制
5. **保存结果**：全部输出保存到 `debates/{工作流名称}-{日期}/`
6. **同步能力**：辩论结束后检查是否需要更新角色武器库

## 触发方式

| 命令 | 说明 |
|------|------|
| `/loop` | 运行当前项目的工作流 |
| `/loop --resume` | 从上次中断处继续 |

## 工作流驱动

loop-engineering 本身不绑定任何特定角色。角色和工作流由项目自行定义：

```
agents/
├── debate-workflow.yaml   # 工作流定义（步骤、角色、依赖、条件、循环）
└── roles/                 # 角色定义（每个角色一个 .md 文件）
    ├── role-a.md
    ├── role-b.md
    └── ...
```

执行引擎只做通用的事：解析 YAML → 拓扑排序 → 化身角色执行 → 保存结果。

## 相关资源

- 执行规则：`agents/patterns/loop-enginerring/agents/RULES.md`
- 示例工作流：`agents/patterns/loop-enginerring/agents/debate-workflow.yaml`（求真辨伪）
- 示例角色：`agents/patterns/loop-enginerring/agents/roles/`
- 参考项目：https://github.com/cobusgreyling/loop-engineering
