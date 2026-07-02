# AGENTS.md

## 1. 项目定位

这是一个面向公司内部 **前端、后端、设计、产品** 人员使用的 AI 智能体工程仓库，核心资产包括：

- **技能库**：`agents/skills/*/SKILL.md`
- **MCP 配置参考**：`agents/mcp/mcp_config.yaml`
- **本地运行态 MCP 配置**：`agents/mcp/mcp.json`
- **MCP 指令说明**：`agents/mcp/mcp-codex.md`

本文件作为仓库级总入口，负责定义：

- 角色如何选择
- Git 管理和协作边界
- Rules 规则
- MCP 推荐使用方式
- Skills 推荐矩阵

> 说明：当前以本仓库已有结构为主进行治理整理。若后续需要严格适配 Trae 的 Rules / MCP / Skills 官方格式，请再按官方文档补齐语法细节；不要在未验证前提下臆造官方字段。

> 想直接看怎么用脚本？请看 [README.md]。本文件聚焦**为什么这么设计**与**协作边界**。

---

## 1.5 设计思路

### 1.5.1 单一数据源（Single Source of Truth）

`agents/` 是仓库的**唯一数据源**：

```
agents/
  ├── rules/              # 团队共识的规则（产品 / 设计 / 前端 / 后端 / 安全 / 测试 / API）
  ├── mcp/                # MCP 配置模板与运行态
  └── skills/*/SKILL.md   # 技能定义
```

各 IDE 不重复维护一份配置，而是通过下面三种映射方式指向 `agents/`：

| 映射方式 | 用途 | 示例 |
|----------|------|------|
| **Junction / Symlink** | 目录级链接，源文件改动自动可见 | `.trae/rules/` ⟶ `agents/rules/` |
| **生成产物**（脚本输出） | 不同 IDE 格式不同，需要按规则转换 | `agents/mcp/mcp.json` ⟶ `.codex/config.toml`（TOML） |
| **复制（fallback）** | Junction 不可用时退化为复制 | `.workbuddy/skills/` |

> ✅ 所以**绝不要**在 `.trae/rules/` 等链接目标里直接编辑文件——改动会被链接源覆盖；要改请回到 `agents/rules/`。

### 1.5.2 三层配置分离

```
模板（提交，无密钥）   →  本地密钥（不提交）   →  运行态产物（不提交，由脚本生成）
*.template.json/toml      llm.yaml + mcp.yaml      mcp.json / auth.json / config.toml / opencode.json
```

- **模板层**：列出占位符 `${KEY}`，可以安全提交，作为"团队共识结构"。
- **密钥层**：`llm.yaml` + `mcp.yaml` 由开发者本地填写，**绝不提交**。
- **运行态产物**：由 `agentctl generate`（见 [scripts/agentctl.py](scripts/agentctl.py)）在本地组合两者后生成；**绝不提交**。

这样模板可以演化（新增 provider / MCP 服务）而不需要每次改密钥；密钥可以轮换而不影响共享结构。

### 1.5.3 LLM Provider 双轨

不同 IDE 的 LLM 加载语义不同，本仓库用 `llm.yaml` + `mcp.yaml` 两份数据，按需扁平化为不同形态的环境变量：

| IDE | 语义 | 占位符前缀 | 切换方式 |
|-----|------|-----------|---------|
| **Codex / Claude** | 一次只用一个 active provider | `${LLM_ACTIVE_*}` / `${OPENAI_API_KEY}` | 改 `llm.yaml._active_provider` |
| **OpenCode** | 多 provider 并存，UI 内选择 | `${LLM_<PROVIDER>_<PROTOCOL>_*}` | 在 `llm.yaml.llm` 中维护 |

**设计意图**：

- 用户填一份 `llm.yaml` + `mcp.yaml` 同时满足多个 IDE，不需要为每个 IDE 各自维护一份密钥
- 切换 active provider 只需一条命令，Codex 的 base_url / api_key 自动跟随
- OpenCode 列出哪些 provider 由模板文件决定，与具体密钥解耦

### 1.5.4 自动剪枝（Conditional Generation）

模板里可以**预先列出所有可能的 provider / MCP 服务**，没填的不会污染最终配置：

> 在 `provider.*` / `providers.*` / `mcpServers.*` / `mcp.*` 这几个**容器键**下，如果某个子项含未解析的 `${...}` 占位符，整段会被自动移除。

**为什么只对这些容器键剪枝？**

- 它们的子项天然是"可插拔"的——一个 provider 缺失不影响其他
- 顶层字段（如 `model_provider`）即使有占位符也通常意味着配置错误，需要显性报警

这套机制让模板可以扮演"目录"的角色，未启用项自动隐形。

### 1.5.5 占位符命名约定

| 模式 | 含义 | 用途 |
|------|------|------|
| `${LLM_ACTIVE_<FIELD>}` | 当前 active provider 的扁平字段 | 通用引用 |
| `${LLM_ACTIVE_<PROTOCOL>_<FIELD>}` | active provider 的指定协议字段 | 区分 OpenAI / Anthropic 协议 |
| `${LLM_<PROVIDER>_<PROTOCOL>_<FIELD>}` | llm.yaml 中**任意 provider** 的字段 | 多 provider 并存 |
| `${OPENAI_API_KEY}` / `${ANTHROPIC_*}` | 兼容性标准化键 | 历史代码、第三方 SDK |

新增占位符时优先沿用现有命名约定，不引入第四种风格。

### 1.5.6 IDE 抽象层级

`scripts/agentctl.py sync`（由 `scripts/lib/ide/` 分发器实现）把所有 IDE 抽象成相同的初始化步骤：

```
[Rules]    源 agents/rules/ → 目标 IDE rules 目录（Junction 优先，复制 fallback）
[MCP]      源 agents/mcp/mcp.json → 目标 IDE 期望的 MCP 配置（按 IDE 格式转换）
[Skills]   源 agents/skills/ → 目标 IDE skills 目录（复制） + 索引 README.md
[Manifest] 复制 AGENTS.md 等项目级指令
```

新增一个 IDE 通常只需：

1. 在 `scripts/lib/ide/` 加一个 `<name>.py`，继承 `IdeTarget`
2. 在 `scripts/lib/ide/__init__.py` 的 `IDE_REGISTRY` 注册
3. 如果 IDE 有特殊 MCP 格式，在分发器中实现 `init_mcp`

**核心约束**：不要为单个 IDE 创建平行的 `agents/` 副本；所有差异都应在生成层处理，而非数据层。

### 1.5.7 一键脚本的语义

所有入口都收敛到 `agentctl` 子命令：

| 子命令 | 含义 | 适用场景 |
|------|------|---------|
| `agentctl generate` | 只刷新密钥相关产物（mcp.json + 各 IDE 模板） | 轮换密钥、切换 provider |
| `agentctl sync` | 同步 rules/mcp/skills 到各 IDE | 改完共享源后同步 |
| `agentctl plugin install` | 安装单个插件（install 脚本 + skill 下载 + 合并 mcp/env） | 安装新插件 |
| `agentctl setup` | 一键全流程：plugin install all → generate → sync | 新机器、新成员、大版本升级 |

### 1.5.8 插件系统（Plugin System）

插件系统用于模块化管理技能库和 MCP 配置，支持本地备份和远程安装两种方式。

#### 目录结构与数据流向
```
agents/skills/              → 原始源，备份，不直接修改（提交到 Git）
  └── {skill-name}/SKILL.md
.agents/skills/             → 开发环境，可以在这里更新，然后同步到 IDE（不提交）
agents/plugins/             → 插件配置目录
  ├── core.plugin.yaml          → 核心插件（基础技能）
  ├── frontend-design.plugin.yaml  → 前端设计插件
  ├── productivity.plugin.yaml     → 生产力插件
  ├── dev-tools.plugin.yaml        → 开发工具插件
  └── computer-use.plugin.yaml     → 电脑操作插件
```

#### 数据流向
1. **插件安装**（`agentctl plugin install`）：执行 install 脚本 → 下载 skill 到 `agents/skills/` → 合并 envVars 到 `llm.yaml`
   - 注：plugin.yaml 的 `mcpServers` 不在此阶段合并，保持 `mcp.yaml` 为用户手写的纯净源
2. **配置生成**（`agentctl generate`）：同时读取 `mcp.yaml` + `agents/plugins/*.plugin.yaml` 的 `mcpServers`，合并生成 `mcp.json` + 各 IDE 模板
   - 合并优先级：`mcp.yaml`（用户手写）> `plugin.yaml`（插件默认）
3. **IDE 同步**（`agentctl sync`）：同步 `mcp.json` 到各 IDE + 同步 skills 到各 IDE

#### 插件配置格式
插件配置支持两种 skill 格式，默认都是远程安装，优先检查本地缓存：

```yaml
name: plugin-name
version: 1.0.0
description: 描述
mcpServers: {}
skills:
  - skill-name
  - name: skill-name
    source: owner/repo
    skill: skill-name
    url: 第三方市场URL（可选）
    description: 描述
```

支持三种安装格式：
1. **直接名称**：`"skill-name"` → `npx skills add skill-name -g`
2. **owner/repo**：`"owner/repo"` → `npx skills add owner/repo --skill skill-name -g`
3. **完整URL**：`"https://github.com/owner/repo"` → `npx skills add https://github.com/owner/repo --skill skill-name -g`

安装流程：
1. 优先检查 `.agents/skills/` 是否已存在该技能，存在则跳过
2. 检查 `agents/skills/` 缓存，存在则复制到 `.agents/skills/`
3. 缓存不存在时从远程安装

> 注：插件安装阶段不合并 `mcpServers` 到 `mcp.yaml`。`mcp.yaml` + `plugin.yaml` 的 `mcpServers` 在 `agentctl generate` 阶段一起合并到 `mcp.json`，保持 `mcp.yaml` 为用户手写的纯净源。

#### 目录优先级
```
agents/skills/              → 源/备份（提交到 Git）
.agents/skills/             → 开发环境（不提交，优先使用）
各 IDE 的 skills 目录        → 运行时（从 .agents/skills 同步）
```

#### 使用方式
```bash
# 列出可用插件
python scripts/agentctl.py plugin list

# 安装单个插件
python scripts/agentctl.py plugin install agents/plugins/frontend-design.plugin.yaml

# 完整安装（含 core 和 computer-use 插件）
install.cmd  # Windows
./install.sh  # Linux/Mac

# 日常：在 .agents/skills 更新后同步到 IDE
python scripts/agentctl.py sync --ide All --force
```

#### 设计理念
- **优先本地**：内置技能全部用 `local` 类型，避免网络问题
- **开发更新**：`.agents/skills` 作为开发环境，可以更新和调试
- **IDE 同步**：通过 `agentctl sync` 将最新技能同步到各 IDE

---

## 2. 指令优先级与使用方式

### 指令优先级

1. 当前任务的用户明确要求
2. 本文件（`AGENTS.md`）中的仓库级规则
3. 角色模板：`templates/agents/*.txt`
4. 技能说明：`agents/skills/*/SKILL.md`

### 使用原则

- 优先复用已有模板、skills、MCP 组织方式，不随意新建平行体系。
- `AGENTS.md` 只负责**顶层治理与路由**，不复制角色长提示词与 skill 详细执行步骤。
- 需要详细角色能力时，回到对应模板；需要详细技能流程时，回到对应 `SKILL.md`。

---

## 3. Git 管理规则

### 基本原则

- 修改范围只聚焦当前任务，避免无关重构。
- 优先修改已有文件，避免新增重复文档或平行配置。
- 新增规则、说明、映射时，尽量保持短小、可扫描、可审查。
- 提交内容必须适合团队协作，不把本机临时状态当成共享规范。

### 禁止提交的内容

- Token、API Key、Cookie、账号密钥
- 带敏感参数的 MCP 配置
- 本机绝对路径、个人环境变量值
- 临时导出文件、调试日志、无说明的生成物

### MCP 相关 Git 边界

- `config/mcp_config.yaml` 用于表达**共享参考结构**。
- `.mcp.json` 属于**本地运行态配置**，可能包含密钥或机器相关参数。
- 不要把 `.mcp.json` 中的真实密钥、Header、Token 复制到共享文档、模板或提交说明中。
- 当前仓库中旧的 `mcp.json` 已被 `.mcp.json` 替代；后续继续维护时，以“共享结构”和“本地私有配置”分离为原则。

---

## 4. 角色路由

### Product

**适用场景**：需求澄清、PRD、功能拆解、Story、验收标准、范围界定。

**优先复用模板**：`templates/agents/product_manager.txt`

**工作重点**：

- 把业务目标转成可评审的需求文档
- 明确用户故事、交互流程、优先级
- 产出可直接交付设计与开发的需求结构

### Design

**适用场景**：用户流程、界面结构、状态设计、设计系统、原型方案。

**优先复用模板**：`templates/agents/ux_designer.txt`

**工作重点**：

- 基于需求设计用户流程和关键界面
- 覆盖空态、错误态、加载态、权限态等关键状态
- 产出可供评审和开发衔接的原型/交互说明

### Frontend

**适用场景**：页面实现、组件拆分、状态管理、接口联调、设计落地。

**说明**：仓库当前没有独立的 `frontend` 角色模板；前端工作默认综合参考设计模板与前端相关 skills。

**工作重点**：

- 关注组件边界、页面状态、交互反馈、接口依赖
- 优先保证设计稿、原型、接口契约三者一致
- 输出要便于工程落地，而不是只停留在视觉描述

### Backend

**适用场景**：API 设计、服务端实现、数据库建模、集成、测试。

**优先复用模板**：`templates/agents/backend_dev.txt`

**工作重点**：

- 关注 RESTful API、业务逻辑、数据结构
- 明确鉴权、错误模型、日志监控、测试建议
- 输出可直接用于研发与联调

### Architect（跨角色补充）

**适用场景**：跨前后端/产品/设计的系统边界、架构取舍、迁移方案。

**优先复用模板**：`templates/agents/architect.txt`

---

## 5. Rules 规则

### 5.1 Product Rules

- 需求默认按 **用户动作 -> 系统响应 -> 验收标准** 组织。
- 必须明确：范围边界、假设、待确认项、不做项。
- 默认给出 **P0 / P1 / P2** 优先级。
- 需求输出要能直接衔接设计和开发，避免只写抽象目标。

### 5.2 Design Rules

- 必须覆盖：`loading / empty / error / permission / offline` 等关键状态。
- 原型或界面说明要能回溯到需求故事和关键流程。
- 默认考虑多端适配、可访问性、一致性。
- 优先描述“用户如何完成任务”，而不是只描述页面长相。

### 5.3 Frontend Rules

- 默认输出组件边界、页面状态、交互反馈、接口依赖。
- 至少补齐：`loading / empty / error / success` 四类状态。
- 优先组件复用、模块分层、低耦合实现。
- 不擅自扩展接口语义；与设计和后端契约保持一致。

### 5.4 Backend Rules

- 优先做 RESTful 资源建模，而不是动作堆叠。
- 明确状态码、错误结构、鉴权、分页、过滤、排序。
- 输出建议包含：API 文档、数据结构、测试建议。
- 默认考虑日志、监控、容错、安全与合规。

---

## 6. MCP 推荐与配置说明

### 6.1 使用原则

- 优先按本仓库现有 MCP 组织方式接入。
- 仓库级共享参考优先看：`config/mcp_config.yaml`
- 本地真实可运行配置优先看：`.mcp.json`
- 若需适配 Trae，请按官方文档补齐语法细节，不在本仓库中伪造未证实的官方格式。

### 6.2 推荐 MCP 按角色映射

| 角色 | 推荐 MCP | 典型用途 |
| --- | --- | --- |
| Frontend | `context7` | 查开发文档、框架/库上下文 |
| Frontend | `stitch` | 快速生成页面原型 |
| Frontend | `mastergo-magic-mcp` | 设计稿/原型到实现协作 |
| Frontend | `drawio` | 模块结构图、流程图 |
| Frontend | `mermaid` | 序列图、状态图、用户流程图 |
| Backend | `context7` | 查开发文档、依赖用法 |
| Backend | `yuque-mcp` | 读写知识库、接口说明、协作文档 |
| Backend | `drawio` | 架构图、数据流图 |
| Backend | `mermaid` | 时序图、状态图、流程图 |
| Design | `stitch` | 界面原型生成 |
| Design | `mastergo-magic-mcp` | MasterGo 相关设计流程 |
| Design | `drawio` | 信息架构、用户流程可视化 |
| Design | `mermaid` | 交互流程、状态说明 |
| Design | `yuque-mcp` | 设计说明沉淀与共享 |
| Product | `yuque-mcp` | PRD、协作文档、知识沉淀 |
| Product | `stitch` | 需求快速转原型 |
| Product | `mastergo-magic-mcp` | PRD 到交互设计协作 |
| Product | `drawio` | 业务流程图、依赖图 |
| Product | `mermaid` | 用户流程、状态流程 |

### 6.3 配置边界

- **共享层**：描述“推荐接什么 MCP、分别做什么事、角色如何映射”。
- **本地层**：保存真实地址、密钥、Header、凭据。
- 文档中只放占位符和说明，不放真实值。

---

## 7. Skills 推荐矩阵

### 7.1 Frontend 推荐 Skills

| Skill | 典型用途 |
| --- | --- |
| `stitch-prototype-skill` | 快速生成界面原型与页面方案 |
| `mastergo-magic-skill` | 设计稿/原型到实现协作 |
| `drawio-skill` | 界面流程、模块关系、说明图 |
| `mermaid-sequence-from-flow` | 把流程转为序列图/交互图 |
| `design-taste-frontend` | 提升 UI 审美质量与设计品味 |
| `high-end-visual-design` | 高端视觉表现与页面设计 |
| `redesign-existing-projects` | 已有项目页面重构与改进 |
| `ui-ux-pro-max` | 强化 UX 设计规范与交互一致性 |

### 7.2 Backend 推荐 Skills

| Skill | 典型用途 |
| --- | --- |
| `restful-api-design-skill` | RESTful API 设计与接口契约 |
| `task-plan-skill` | 开发拆解、里程碑与实施计划 |
| `drawio-skill` | 服务关系图、流程图、架构图 |

### 7.3 Design 推荐 Skills

| Skill | 典型用途 |
| --- | --- |
| `stitch-prototype-skill` | 原型生成 |
| `mastergo-magic-skill` | MasterGo 相关设计流程 |
| `prd-to-mastergo-interaction-skill` | 从 PRD 到交互原型 |
| `drawio-skill` | 用户流程与信息架构可视化 |
| `design-taste-frontend` | 提升 UI 审美质量与设计品味 |
| `high-end-visual-design` | 高端视觉表现与页面设计 |
| `ui-ux-pro-max` | 强化 UX 设计规范与交互一致性 |

### 7.4 Product 推荐 Skills

| Skill | 典型用途 |
| --- | --- |
| `usecase-prd-skill` | 从需求到 PRD |
| `task-plan-skill` | 任务分解与排期 |
| `weekly-report-skill` | 周报/月报结构化输出 |
| `prd-to-mastergo-interaction-skill` | 推动需求向交互稿过渡 |

### 7.5 通用 Skills

| Skill | 典型用途 |
| --- | --- |
| `find-skills` | 技能发现与推荐，帮助用户找到适合当前任务的技能 |
| `personnel-recruitment` | 结构化招聘（JD 优化、简历筛选、面试设计） |
| `hardware-agent-prompt-skill` | 硬件 AI 智能体提示词与角色设定 |
| `elon-musk-perspective` | 马斯克思维模型分析（第一性原理、五步算法等） |

---

## 8. 详细资料入口


### 技能目录

- `agents/skills/find-skills/SKILL.md`
- `agents/skills/stitch-prototype-skill/SKILL.md`
- `agents/skills/mastergo-magic-skill/SKILL.md`
- `agents/skills/prd-to-mastergo-interaction-skill/SKILL.md`
- `agents/skills/restful-api-design-skill/SKILL.md`
- `agents/skills/task-plan-skill/SKILL.md`
- `agents/skills/usecase-prd-skill/SKILL.md`
- `agents/skills/weekly-report-skill/SKILL.md`
- `agents/skills/drawio-skill/SKILL.md`
- `agents/skills/mermaid-sequence-from-flow/SKILL.md`
- `agents/skills/personnel-recruitment/SKILL.md`
- `agents/skills/hardware-agent-prompt-skill/SKILL.md`
- `agents/skills/elon-musk-perspective/SKILL.md`
- `agents/skills/design-taste-frontend/SKILL.md`
- `agents/skills/high-end-visual-design/SKILL.md`
- `agents/skills/redesign-existing-projects/SKILL.md`
- `agents/skills/ui-ux-pro-max/SKILL.md`

### MCP 参考

- `agents/mcp/mcp_config.yaml`
- `agents/mcp/mcp.json`（本地运行态，注意敏感信息）
- `agents/mcp/mcp-codex.md`（本地/外部工具接入说明）

---

## 9. 维护约定

- 角色有新增或调整时，优先更新对应模板，再回到 `AGENTS.md` 更新路由摘要。
- Skill 新增时，优先保持与现有 `SKILL.md` 一致的结构风格。
- MCP 新增时，先判断它属于“共享参考”还是“本地私有配置”，再决定写入哪个文件。
- 若后续补齐 Trae 官方语法适配，应在不破坏当前仓库共享结构的前提下增量调整。
