---
name: mastergo-magic-skill
description: >-
  Uses MasterGo Magic MCP to generate mid-fidelity prototypes and frontend code
  from design data. Use when users mention MasterGo, mastergo-magic-mcp, 原型图,
  设计稿转代码, C2D, D2C, fileId, layer_id, or short links.
---

# MasterGo Magic MCP 工作流

用于两类任务：
- **原型生成（C2D）**：把页面需求转为 HTML 并同步到 MasterGo 设计稿。
- **设计稿转代码（D2C）**：从 MasterGo 设计稿拉取代码与资源落盘。

## 输入优先级

1. `shortLink`（优先，建议 `goto` 或含 `layer_id` 的链接）
2. `fileId + layerId`
3. 仅 `fileId`（不稳定，通常仍需 `layerId`）

若缺 `layerId`，必须向用户索取含 `layer_id` 的链接或直接索取 `layerId`。

## 执行步骤

1. **先读工具 schema**：调用 MCP 前先确认工具参数要求。
2. **识别任务类型**：
   - 用户说“生成原型图/页面原型” => 用 `mcp__C2d`
   - 用户说“生成前端代码/落盘资源” => 用 `mcp__getD2c`
3. **参数校验**：
   - C2D：至少要 `data`，并尽量带 `shortLink` 或 `fileId`
   - D2C：必须 `contentId + documentId`
4. **错误分流**：
   - `10003`：token 或权限问题（团队版编辑/研发席位、文件编辑权限）
   - `Could not extract layerId from URL`：链接缺 `layer_id`
5. **输出结果**：
   - 说明是否成功
   - 若失败，给最短下一步（补参数或修权限）

## 原型生成默认规范（C2D）

- 目标：中保真后台页面
- 桌面端默认宽度：`1440`
- 默认主色：`#1677FF`
- 结构：页面头部、筛选区、表格区、批量操作、分页
- 组件命名建议：`FilterBar`、`StudentTable`、`StudentFormModal`

## 设计稿转代码默认规范（D2C 后续代码）

- 框架默认：`Vue 3`
- 样式要求：严格遵循设计稿参数，优先 `rem` 适配
- 结构要求：按模块组件化拆分
- 资源要求：图标/图片落到 `assets`
- 兼容目标：Chrome 90+ / Edge 90+ / Safari 14+
- 若设计细节不明确，先问用户再继续

## 参考示例

见同目录 [examples.md](examples.md) 与 [说明.md](说明.md)。

