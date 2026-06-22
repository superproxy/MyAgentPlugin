---
name: init-loop-agents
description: Use when running a loop-engineering multi-agent workflow - parses debate-workflow.yaml, executes steps by role, handles dependencies/conditions/loops, saves results
---

# Init Loop Agents — 多角色工作流执行引擎

## Overview

基于 [loop-engineering](https://github.com/cobusgreyling/loop-engineering) 模式，提供一个**通用的多角色工作流执行引擎**。不绑定任何特定角色或领域——角色和工作流由项目自行定义。

**核心原则**: 引擎只负责解析、调度、执行、保存。角色人格和能力来自项目自己的 `agents/roles/*.md`，工作流结构来自 `agents/debate-workflow.yaml`。

## When to Use

- 项目已定义 `agents/debate-workflow.yaml` 和 `agents/roles/`
- 需要按工作流定义自动执行多步骤、多角色协作
- `/loop` 命令触发
- 需要自动处理步骤依赖、条件分支、循环控制

## 执行流程

收到 `/loop` 指令后，按以下通用流程执行：

### Step 1: 解析工作流

读取 `agents/debate-workflow.yaml`，提取：

```yaml
name: "工作流名称"
inputs:
  - name: xxx
    required: true/false
    default: "..."
steps:
  - id: step_id
    role: "角色文件名（不含 .md）"
    depends_on: ["上游 step_id"]
    condition: "表达式"
    loop:
      back_to: "step_id"
      max_iterations: N
      exit_condition: "表达式"
    task: "任务描述，支持 {{变量}}"
    output: "输出变量名"
```

### Step 2: 收集输入

- `required: true` → 必须由用户提供
- 有 `default` → 使用默认值
- 无默认值的可选输入 → 空字符串

### Step 3: 构建执行顺序

按 `depends_on` 拓扑排序：
- 无依赖的步骤 → 同一层级，可并行
- 有依赖的步骤 → 等待上游完成

### Step 4: 执行步骤

对每个步骤：

1. 读取 `agents/roles/{role}.md`，提取角色人格
2. 将 `{{变量}}` 替换为上下文值
3. 评估 `condition`（如设置），不满足则跳过
4. **完全化身该角色**执行任务
5. 输出存入上下文变量（如有 `output` 字段）
6. 检查 `loop`：退出条件未满足则跳回 `loop.back_to`（最多 `loop.max_iterations` 轮）

### Step 5: 保存结果

```
debates/{工作流名称}-{日期}/
├── steps/
│   ├── 1-{step_id}.md
│   └── ...
├── summary.md
└── metadata.json
```

### Step 6: 同步检查

工作流结束后，检查是否需要更新角色能力（按 RULES.md 第 8 节）。

## 项目结构约定

```
agents/
├── debate-workflow.yaml   # 工作流定义
└── roles/                 # 角色定义
    ├── role-a.md          # 角色人格 + 方法论武器库
    └── role-b.md

debates/                   # 输出目录（自动创建）
└── {工作流名称}-{日期}/
```

## 工作流 YAML 规范

### 步骤字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `id` | ✅ | 步骤唯一标识 |
| `role` | ✅ | 角色文件名（不含 .md），对应 `agents/roles/{role}.md` |
| `name` | - | 步骤显示名称 |
| `task` | ✅ | 任务描述，支持 `{{变量}}` 模板 |
| `depends_on` | - | 上游步骤 id 列表 |
| `depends_on_mode` | - | `all`（默认）或 `any_completed` |
| `condition` | - | 执行条件，运算符：`contains`/`equals`/`not_contains`/`not_equals` |
| `loop` | - | 循环配置：`back_to`/`max_iterations`/`exit_condition` |
| `output` | - | 输出变量名，供下游步骤引用 |
| `emoji` | - | 步骤图标 |

### 输入字段

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | ✅ | 输入变量名 |
| `required` | - | 是否必填（默认 false） |
| `default` | - | 默认值 |
| `description` | - | 输入说明 |

## 角色文件规范

每个 `agents/roles/{name}.md`：

```markdown
---
name: 角色名称
description: 角色描述
emoji: 🔴
---

# 角色名称

角色人格描述...

## 方法论武器库

角色专属的方法论、检查清单、判断标准...
```

## 重要规则

- 每个步骤必须真正化身所分配的角色——禁止通用回复
- 禁止跳过或合并步骤；严格按拓扑顺序执行
- 角色文件缺失时告知用户安装路径
- 条件不满足的步骤标记为"已跳过"并继续
- `depends_on_mode: "any_completed"` 时任意一个上游完成即可继续
- 工作流结束后记录到 `docs/inquiry-log.md`

## 示例

参考 `agents/patterns/loop-enginerring/` 中的求真辨伪示例：

- 工作流：`debate-workflow.yaml`（Collector → Challenger ⇄ Reasoner → Judge → Optimizer）
- 角色：`roles/collector.md`、`roles/challenger.md`、`roles/reasoner.md`、`roles/judge.md`、`roles/optimizer.md`
- 规则：`RULES.md`

## 注意事项

- 引擎不绑定任何领域——产品评审、代码审查、架构辩论都可以用
- 工作流和角色完全由项目自定义，引擎只负责调度执行
- 如果工作流文件不存在，提示用户先创建 `agents/debate-workflow.yaml`
- 步骤失败时支持从失败步骤恢复继续
