---
name: role-skills
description: >-
  Helps users discover and install agent skills when they ask questions like "how do I do X",
  "can I use a skill for X", "is there a skill that can...", or express interest in extending capabilities.
  This skill should be used when the user is looking for functionality that might exist as an installable skill.
---

# Role Skills

帮助用户发现、查找和安装仓库中的 AI 技能。当用户不知道有哪些技能可用，或想找到特定功能的技能时使用。

## 适用场景

- 用户问"有没有能做 X 的技能？"
- 用户问"怎么画架构图？"（可推荐 drawio-skill）
- 用户问"怎么设计 API？"（可推荐 restful-api-design-skill）
- 用户问"帮我写个 PRD"（可推荐 usecase-prd-skill）
- 用户想了解当前仓库有哪些可用技能
- 用户想了解某个技能的具体用法

## 执行步骤

1. **理解需求**：分析用户想完成什么任务
2. **匹配技能**：从技能清单中查找最匹配的技能
3. **推荐并说明**：告诉用户推荐哪个技能、为什么、怎么用
4. **引导使用**：如果用户确认，加载对应技能继续执行

## 技能清单

### 前端开发

| 技能 | 用途 | 触发词 |
|------|------|--------|
| `stitch-prototype-skill` | 从文本描述生成 UI 原型页面 | stitch、原型图、界面生成、文生页面 |
| `mastergo-magic-skill` | MasterGo 设计稿转代码 / 原型生成 | MasterGo、设计稿转代码、C2D、D2C |
| `drawio-skill` | 生成架构图、流程图、ER 图、UML | 画图、流程图、架构图、可视化 |
| `mermaid-sequence-from-flow` | 自然语言流程转 Mermaid 序列图 | 流程图、序列图、时序图 |

### 后端开发

| 技能 | 用途 | 触发词 |
|------|------|--------|
| `restful-api-design-skill` | RESTful API 设计与校验 | API 设计、接口设计、OpenAPI |
| `task-plan-skill` | PRD 拆解为任务计划与排期 | 任务计划、研发排期、WBS、里程碑 |
| `drawio-skill` | 服务关系图、架构图、流程图 | 架构图、服务图、ER 图 |

### 设计

| 技能 | 用途 | 触发词 |
|------|------|--------|
| `stitch-prototype-skill` | 快速生成界面原型 | 原型图、界面生成 |
| `mastergo-magic-skill` | MasterGo 设计协作 | MasterGo、设计稿 |
| `prd-to-mastergo-interaction-skill` | PRD 转 MasterGo 交互原型 | PRD 转原型、交互图 |
| `drawio-skill` | 用户流程、信息架构可视化 | 用户流程、信息架构 |

### 产品

| 技能 | 用途 | 触发词 |
|------|------|--------|
| `usecase-prd-skill` | 需求转 PRD（用例维度） | 写需求、PRD、产品需求、用例 |
| `task-plan-skill` | 任务分解与排期 | 任务计划、排期、WBS |
| `weekly-report-skill` | 周报/月报结构化输出 | 周报、月报、工作汇报 |
| `prd-to-mastergo-interaction-skill` | PRD 到交互原型过渡 | PRD 转交互 |

### 通用/其他

| 技能 | 用途 | 触发词 |
|------|------|--------|
| `personnel-recruitment` | 结构化招聘（JD、简历筛选、面试设计） | 招聘、岗位画像、JD、面试 |
| `hardware-agent-prompt-skill` | 硬件 AI 智能体提示词生成 | 硬件智能体、设备人格、IoT |
| `elon-musk-perspective` | 马斯克思维模型分析 | 马斯克视角、第一性原理、白痴指数 |
| `find-skills` | 技能发现与推荐（本技能） | 有什么技能、找技能、能做什么 |

## 匹配策略

1. **关键词匹配**：用户输入与技能触发词匹配
2. **语义匹配**：用户描述的任务与技能用途匹配
3. **角色匹配**：根据用户角色（前端/后端/设计/产品）推荐对应技能
4. **组合推荐**：复杂任务可能需要多个技能协作

## 示例对话

```
用户: 我想画一个系统架构图
推荐: 推荐使用 drawio-skill，它可以生成 .drawio 格式的架构图并导出 PNG/SVG。
      需要我加载这个技能帮你画吗？

用户: 帮我写一个用户登录功能的 PRD
推荐: 推荐使用 usecase-prd-skill，它按用例维度输出 PRD，包含用户动作、系统响应和验收标准。
      需要我加载这个技能吗？

用户: 有哪些技能可以用？
回答: 当前仓库共有 12 个技能，按角色分类如下...（列出技能清单）
```
