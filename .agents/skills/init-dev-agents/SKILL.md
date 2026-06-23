---
name: init-dev-agents
description: Use when initializing a new project or bootstrapping development workflow - generates AGENTS.md, defines skill dependencies, sets up requirement collection process
---

# Init Agents — 项目开发流程初始化

## Overview

为新项目（或已有项目首次接入智能体协作）生成 `AGENTS.md`，定义开发流程、声明依赖 skill、建立需求收集机制。

**核心原则**: AGENTS.md 只做地图和入口，细节进入 skill/docs/cases。

## When to Use

- 新项目首次创建 AGENTS.md
- 已有项目接入智能体协作
- `/init` 命令触发
- 开发流程需要重新定义或重大调整

## Boot Agents 流程

收到 `/init` 或"初始化开发流程"指令后，执行以下步骤：

### Step 1: 扫描项目

```
扫描内容：
├── package.json / pom.xml / Cargo.toml → 技术栈
├── src/ / app/ / lib/ → 目录结构
├── Makefile / docker-compose.yml → 构建入口
├── .git/ → 是否 git 仓库
├── existing AGENTS.md → 是否已有
├── docs/ → 已有文档
└── tests/ → 测试框架
```

### Step 2: 生成 AGENTS.md

按以下模板生成（根据扫描结果填充）：

```markdown
# [项目名]

## 项目定位
[一句话]

## 工程结构
### 1. [主要目录]
### 2. [后端/前端]
### 3. [数据/文档]

## 开发流程
（引用 docs/requirement-workflow.md）

## Skill 依赖
| Skill | 用途 |
|---|---|
| brainstorming | 需求澄清 |
| openspec-explore | 探索模式 |
| openspec-propose | 生成提案 |
| writing-plans | 实施计划 |
| subagent-driven-development | 逐任务实施 |
| systematic-debugging | 排查 bug |
| verification-before-completion | 完成前验证 |

## 约定
### 代码约定
### 数据约定
### 交互调整约定

## 启动命令
## 当前优先级
```

### Step 3: 生成需求收集流程

创建 `docs/requirement-workflow.md`（如不存在），定义：
- 需求分类规则（交互调整 / 功能需求 / 架构改动）
- 每类对应的 skill 链
- 产出文件位置
- 自动化要点

### Step 4: 生成交互调整目录

创建 `docs/interaction-changes/` 目录：
- `README.md` 索引
- 模板说明

### Step 5: 确认并提交

- 展示生成的 AGENTS.md 给用户确认
- 用户确认后 git commit

## 依赖 Skill 声明

init-agents 本身不依赖其他 skill 执行，但生成的 AGENTS.md 中会声明项目开发所需的 skill 链：

```
日常开发 skill 链:
  brainstorming → openspec-explore → openspec-propose → writing-plans → subagent-driven-development

交互调整快速通道:
  brainstorming → 直接实现 → interaction-changes 记录

调试:
  systematic-debugging

验证:
  verification-before-completion
```

## AGENTS.md 模板变量

| 变量 | 来源 | 示例 |
|---|---|---|
| `{项目名}` | 目录名或 package.json name | 股票分析 |
| `{技术栈}` | 扫描依赖文件 | Java 17 + Spring Boot + Vue3 + Vite |
| `{构建命令}` | Makefile 或 scripts | `make start` |
| `{测试命令}` | Makefile 或 package.json | `make test` |
| `{数据目录}` | 扫描 data/ | `data/daily/` |
| `{API 前缀}` | 扫描 controller | `/api/` |

## 注意事项

- 如果 AGENTS.md 已存在，不要覆盖，而是 diff 展示建议改动
- 保持 AGENTS.md 简洁（< 300 行），细节引到 docs/
- skill 依赖表只列实际用到的，不列全部
- 需求收集流程引用 `docs/requirement-workflow.md`，不内联
- 必须记录用户的询问，放在 `docs/interaction-changes/`，并在 AGENTS.md 中说明位置
