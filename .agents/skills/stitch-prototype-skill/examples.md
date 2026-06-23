# 示例

## 示例 1：从 0 创建项目并生成首屏

### 用户输入

```text
使用 stitch 设计图 mcp，帮我生成一个“设备监控总览”后台原型图。
要有顶部统计卡片、设备状态趋势图、告警列表、分页表格。风格简洁，蓝色主色。
```

### 期望行为

1. 调用 `create_project` 创建项目（可带 title）
2. 取返回 `projects/{project}` 中的 `{project}` 作为 `projectId`
3. 调用 `generate_screen_from_text`（`deviceType=DESKTOP`）
4. 用 `list_screens` / `get_screen` 补充页面状态并汇报 `projectId + screenId`

## 示例 2：在已有页面上做迭代

### 用户输入

```text
projectId: 4044680601076201931
把当前页面的告警列表改成“未处理/处理中/已关闭”三标签页，表格增加“负责人”和“处理时长”列。
```

### 期望行为

1. 先调用 `list_screens` 获取可编辑页面 ID
2. 选择目标 screen 后调用 `edit_screens`
3. 参数包含 `projectId + selectedScreenIds + prompt`
4. 返回修改结果与后续建议（如是否继续生成多方案）

## 示例 3：多方案探索

### 用户输入

```text
基于当前屏，给我 3 个视觉方向：科技深色、企业浅色、极简灰白。
```

### 期望行为

1. 识别为“多方案”诉求，调用 `generate_variants`
2. 汇总各方案特点和适用场景
3. 引导用户选择一个方案后继续 `edit_screens` 精修

## 示例 4：连接异常后的正确处理

### 用户输入

```text
刚才生成时报错了，你再重试一次。
```

### 期望行为

- 不直接重复调用生成接口
- 提示先用 `get_screen` / `list_screens` 查询是否已在后台生成成功
- 若确实失败，再基于同一 `projectId` 发起新一轮生成
