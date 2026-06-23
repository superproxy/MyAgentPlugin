---
name: mermaid-sequence-from-flow
description: >-
  Converts natural-language business flows in 主题/背景/流程 structure into valid
  Mermaid sequenceDiagram. Use when the user asks for 流程图、序列图、时序图、Mermaid
  sequence diagrams, or writes flows matching 流程图绘制.md format (主题, 背景, 流程).
---

# 流程 → Mermaid 序列图

将用户按「主题 / 背景 / 流程」书写的业务步骤，转为 **`sequenceDiagram`**（不用 flowchart）。

## 用户输入模板（对齐项目内 `流程图绘制.md`）

```markdown
主题：<一句话概括>

背景：
<可选，多行上下文、系统边界、网络或依赖>

流程：
<步骤 1，自然语言>
<步骤 2>
...
```

若用户未显式分段，将正文视为「流程」；「主题」可用首句或用户标题代替。

## Agent 执行步骤

1. **解析三段**：识别 `主题`、`背景`、`流程`；背景可空。
2. **抽取参与者**：从每句主语、系统名（PMS、小程序、API、平台、设备等）归纳 `participant`，控制在可读数量；合并同义词（如「管理端」「管理端小程序」→ 一个 participant）。
3. **保序映射**：流程自上而下顺序对应消息时间顺序。每行可映射为一条或多条 `A->>B: 简短标签`；一句含多个连续动作用多条消息，避免塞成过长标签。
4. **背景落地**：将 `背景` 压缩为 `Note right of...` / `Note over A,B: ...`（或图前一两句说明），不重复全流程。
5. **分支**：仅当用户明确「如果 / 否则 / 可选 / 或者（互斥路径）」时使用 `alt` / `opt`；并行用 `par` 仅当输入明确并行。
6. **输出**：一个 markdown 围栏代码块，语言为 `mermaid`，首行 `sequenceDiagram`；可选 `autonumber` 以匹配步骤序号需求。

## Mermaid 序列图语法要点

- **参与者**：`participant Id as 显示名`。`Id` 仅用字母数字下划线，无空格；中文放在 `as` 后。
- **消息**：同步实线箭头 `->>`，异步/返回可用 `-->>`（按需）。
- **标签**：尽量短；含 `:`、括号或与语法冲突时，尝试改写短句或拆消息。
- **注释**：`Note left of Id: ...`、`Note right of Id: ...`、`Note over Id1,Id2: ...`（具体兼容以 [Mermaid 序列图语法](https://mermaid.js.org/syntax/sequenceDiagram.html) 为准）。
- **禁用**：不要用 `flowchart`/`graph TD` 替代本 skill 的主输出。

## 示例与完整对照

见同目录 [examples.md](examples.md)。
