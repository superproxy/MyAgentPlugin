---
name: stitch-prototype-skill
description: >-
  Uses Stitch MCP to create and iterate UI prototypes from text prompts.
  Use when users mention stitch, 设计图 mcp, 原型图, 界面生成, 文生页面,
  交互原型, 设计迭代.
---

# Stitch 原型工作流

用于通过 Stitch MCP 从自然语言快速生成、迭代和扩展原型页面。

## 触发场景

- 用户提到：`stitch`、`设计图 mcp`、`原型图`、`界面生成`、`文生页面`、`交互原型`
- 用户希望：先出页面草图，再根据反馈持续修改

## 执行步骤

1. **先读工具 schema**：调用 MCP 前，先确认工具参数与必填字段。
2. **确认项目上下文**：
   - 有 `projectId`：直接复用。
   - 无 `projectId`：先调用 `create_project` 创建项目。
3. **首屏生成**：
   - 调用 `generate_screen_from_text`，必须传 `projectId + prompt`。
   - 默认 `deviceType` 建议：后台管理端 `DESKTOP`，移动端 `MOBILE`。
4. **结果核验**：
   - 使用 `list_screens` / `get_screen` 获取页面与状态。
   - 若 `outputComponents` 有 `text` 或 `suggestion`，需回传给用户并引导下一步。
5. **迭代编辑**：
   - 用户要求改版时，调用 `edit_screens`。
   - 必填：`projectId + selectedScreenIds + prompt`。
6. **多方案扩展（可选）**：
   - 需要多个视觉方向时调用 `generate_variants`。
7. **收尾输出**：
   - 明确返回：`projectId`、关键 `screenId`、本轮生成/编辑结果摘要、下一步建议。

## 参数与约束

- `create_project`
  - 常用：`title`
  - 返回值中的 `name` 形如 `projects/{project}`，后续接口通常只要 `{project}` 这段 ID。
- `generate_screen_from_text`
  - 必填：`projectId`、`prompt`
  - 可选：`deviceType`、`modelId`
  - 该调用可能较慢，**不要重复重试**。
- `edit_screens`
  - 必填：`projectId`、`selectedScreenIds`、`prompt`
  - `selectedScreenIds` 只传纯 ID，不带 `screens/` 前缀。

## 错误分流

- 参数缺失：提示缺少的必填字段并给出最小补充示例。
- 连接中断：提示用户稍后用 `get_screen` / `list_screens` 查结果，不盲目重试生成。
- `projectId` 或 `screenId` 无效：先列项目/页面，再让用户确认目标。

## 默认提示词模板

- 页面生成模板：
  - `请生成一个{端类型}的{页面名称}，包含{核心模块}，风格{风格关键词}，主色{颜色}。`
- 页面编辑模板：
  - `请在保留现有布局结构的前提下，将{目标区域}改为{改动要求}，并强化{可用性目标}。`

## 输出规范

- 用 3-5 条要点汇报结果，不贴冗长原始返回。
- 必须包含：`projectId`、涉及的 `screenId`、是否成功、建议下一步。

## 参考示例

见同目录 [examples.md](examples.md) 与 [说明.md](说明.md)。

## 实操流程沉淀（PRD -> Stitch -> 交互流程图）

用于“先按 PRD 生成 Stitch 原型，再输出评审图”的标准执行。

1. 准备输入
   - 读取 PRD，提取：页面清单、主成功流、异常流、设计原则（配色/去 AI 风格）。
   - 先整理成一段可执行提示词，避免模糊描述。
2. 创建项目
   - 调用 `create_project` 创建专用项目，记录 `projects/{project}`。
   - 后续调用统一使用纯 `projectId`（不带 `projects/` 前缀）。
3. 首轮生成
   - 调用 `generate_screen_from_text(projectId, prompt, deviceType=MOBILE)`。
   - 提示词必须包含：页面数、页面命名、主链路、异常分支、配色、去 AI 风格约束。
4. 结果解析
   - 提取 `sessionId`、页面数量、关键 `screen name/title`。
   - 若返回含 `outputComponents.text` 或 `outputComponents.suggestion`，要回传并给出下一步操作建议。
5. 页面核验
   - 调用 `list_screens(projectId)` 或解析输出中的 `design.screens`。
   - 核验最少项：P0 页面齐全、至少 2 个异常态、关键回退路径存在。
6. 生成评审图
   - 基于 screen 列表生成流程图（建议 `.drawio` + `.png`），表达：
     - 主链路：权限 -> 扫描 -> 连接 -> 设备首页 -> 功能页；
     - 异常链路：连接失败、设备离线及重试/重连返回路径。
7. 输出给用户
   - 返回：`projectId`、`sessionId`、关键 `screenId/title`、图文件路径、下一轮迭代建议。

### 可复用提示词骨架

`请生成一个移动端中保真交互原型，包含{页面清单}，主链路{主流程}，异常分支{异常流程}；遵守配色{主色+状态色}，支持深浅主题，禁止AI炫技视觉（大渐变/玻璃拟态/过度阴影），并保证每个关键页面有状态反馈与返回路径。`
