# 示例

## 示例 1：学生管理原型（C2D）

### 用户输入

```text
使用 mcp mastergo-magic-mcp 生成一个“学生管理”中保真原型图（后台管理端，1440 宽度）。
页面包含顶部、筛选区、表格区、批量操作、分页。
主色 #1677FF。
链接：https://mastergo.com/prototyping/190126391371865?fileOpenFrom=home&page_id=7%3A69&layer_id=7%3A70
```

### 期望行为

1. 识别为 C2D 任务，调用 `mcp__C2d`
2. 使用页面需求组装 HTML（`data`）
3. 传入 `shortLink`
4. 返回同步结果或错误分流建议

## 示例 2：缺 layer_id 的处理

### 用户输入

```text
https://mastergo.com/prototyping/190126391371865?fileOpenFrom=team&page_id=M
```

### 期望行为

- 不盲目重试
- 明确提示：当前链接缺 `layer_id`
- 引导用户提供：
  - 含 `layer_id` 的链接，或
  - `fileId + layerId`

## 示例 3：设计稿转代码（D2C）

### 用户输入

```text
请基于这个内容生成 Vue 3 代码并落盘资源：
contentId: 176452330285910-2-2845
documentId: 176452330285910
```

### 期望行为

1. 识别为 D2C 任务，调用 `mcp__getD2c`
2. 将返回代码与资源落盘
3. 汇报输出目录与关键文件

