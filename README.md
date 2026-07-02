# IDE 初始化脚本使用说明

将 `agents/` 共享配置一键映射到 Cursor / Trae / Codex / OpenCode / Claude / IDEA 等多种 IDE。

> 本文件聚焦**怎么用**。如果想了解仓库的设计思路与治理边界，请看 [AGENTS.md](AGENTS.md)。

---

## 1. 快速开始

```bash
# 1) 复制密钥模板（拆分为两个文件）
cp llm-env-example.yaml llm.yaml
cp mcp-env-example.yaml mcp.yaml

# 2) 编辑 llm.yaml / mcp.yaml，填入真实 API Key（也可留空，由 OS 环境变量回退）

# 3) 一键全量初始化（生成配置 + 安装插件 + 同步所有 IDE）
.\install.cmd      # Windows
./install.sh        # macOS / Linux
```

完成后即可在已支持的 IDE 中使用统一的 rules / mcp / skills 配置。

---

## 2. 命令总览

所有功能通过统一 CLI 入口 `scripts/agentctl.py` 提供，合并了原 `init-env.py` / `init-ide.py` / `plugin-manager.py` 三个脚本。

| 命令 | 用途 |
|------|------|
| `agentctl generate` | 从 `llm.yaml` + `mcp.yaml` / OS 环境变量生成 MCP / Codex / OpenCode 配置 |
| `agentctl sync` | 通用 IDE 同步（创建 Junction、复制 / 生成配置） |
| `agentctl plugin install/list` | 插件管理（安装、列出） |
| `agentctl skill list/gen-plugin` | 技能管理（基于 `agents/skills/skills-index.csv`） |
| `agentctl env` | 设置环境变量（process / user 作用域） |
| `agentctl shell` | 输出 `export` 语句供 shell 直接 `eval` |
| `agentctl provider` | 切换 / 查看活跃 LLM provider |
| `agentctl setup` | 一键全流程：generate + plugin install all + sync |
| `install.cmd` / `install.sh` | 端到端安装入口（等价于 `agentctl setup`） |
| `init-env.cmd` / `init-env.sh` | 仅生成运行态配置（等价于 `agentctl generate`） |

### 环境要求

- Python 3.10+
- Windows / macOS / Linux 均可
- Windows 下创建 Junction 需以**管理员权限**运行终端

---

## 3. agentctl 使用手册

### 3.1 generate — 生成运行态配置

```bash
# 默认：生成所有运行态配置
python scripts/agentctl.py generate

# 同时切换 LLM provider
python scripts/agentctl.py generate --provider volcengine

# 同时切换 provider 与协议
python scripts/agentctl.py generate --provider volcengine --protocol anthropic
```

### 3.2 sync — 同步到 IDE

```bash
# 初始化所有支持的 IDE，写到当前用户主目录
python scripts/agentctl.py sync

# 强制覆盖已有配置
python scripts/agentctl.py sync -f

# 仅初始化指定 IDE
python scripts/agentctl.py sync -i Cursor
python scripts/agentctl.py sync -i TraeCN
python scripts/agentctl.py sync -i TraeSoloCN
python scripts/agentctl.py sync -i Codex
python scripts/agentctl.py sync -i Claude
python scripts/agentctl.py sync -i WorkBuddy
python scripts/agentctl.py sync -i Qoder
python scripts/agentctl.py sync -i OpenClaw
python scripts/agentctl.py sync -i OpenCode
python scripts/agentctl.py sync -i IDEA
python scripts/agentctl.py sync -i Agents

# 按技能白名单同步（仅同步列出的技能）
python scripts/agentctl.py sync --skills tdd,mermaid

# 指定同步范围（默认 llm,mcp,skill,rules）
python scripts/agentctl.py sync --scope mcp,rules
```

### 3.3 provider — 切换 / 查看活跃 LLM

仅影响 Codex / Claude（一次只用一个 LLM 的 IDE）。OpenCode 不受影响。

```bash
# 查看当前状态与可用 provider 列表
python scripts/agentctl.py provider

# 切换到火山引擎（沿用当前协议）
python scripts/agentctl.py provider volcengine

# 同时指定协议
python scripts/agentctl.py provider volcengine --protocol anthropic
```

支持的 provider 来自 `llm.yaml` 中 `llm.*` 节点（默认包含 `openicu` / `openai` / `openrouter` / `deepseek` / `volcengine` 等）。

### 3.4 env — 设置环境变量

```bash
# 仅设置当前进程环境变量（默认）
python scripts/agentctl.py env

# 写入用户级环境变量（持久化，跨终端有效）
python scripts/agentctl.py env --scope user --force
```

### 3.5 shell — 导出 shell 语句

```bash
# 输出 export 语句供 shell 直接 eval
eval "$(python scripts/agentctl.py shell)"
```

### 3.6 plugin — 插件管理

```bash
# 列出可用插件
python scripts/agentctl.py plugin list

# 安装单个插件
python scripts/agentctl.py plugin install agents/plugins/core.plugin.yaml

# 模拟安装（不写文件）
python scripts/agentctl.py plugin install agents/plugins/core.plugin.yaml --dry-run
```

### 3.7 skill — 技能管理

```bash
# 列出 agents/skills/skills-index.csv 中的所有技能
python scripts/agentctl.py skill list

# 根据 CSV 生成插件配置
python scripts/agentctl.py skill gen-plugin --name frontend --category 前端
```

### 3.8 setup — 一键全流程

```bash
# 依次执行：generate → plugin install all → sync All
python scripts/agentctl.py setup
```

### 3.9 参数速查

| 命令 | 参数 | 说明 | 默认值 |
|------|------|------|--------|
| `generate` | `--provider` | 切换 LLM provider | — |
| `generate` | `--protocol` | `openai` / `anthropic` | — |
| `sync` | `--ide` / `-i` | 目标 IDE 或 `All` | `All` |
| `sync` | `--force` / `-f` | 强制覆盖 | 否 |
| `sync` | `--scope` | `llm,mcp,skill,rules` 子集 | `llm,mcp,skill,rules` |
| `sync` | `--skills` | 技能白名单（逗号分隔） | 全部 |
| `env` | `--scope` | `process` / `user` | `process` |
| `env` | `--force` | 跳过确认 | 否 |
| `provider` | `name` | provider 名称 | — |
| `provider` | `--protocol` | 同时切换协议 | — |
| `plugin install` | `plugin_file` | `.plugin.yaml` 路径 | — |
| `plugin install` | `--env-file` | 环境变量文件 | `llm.yaml` |
| `plugin install` | `--dry-run` | 模拟运行 | 否 |
| `plugin install` | `--symlink` | 使用 symlink 安装 skill | 否（复制） |
| `plugin list` | `--plugins-dir` | 插件目录 | `agents/plugins` |
| `skill list` | `--csv` | 技能映射文件 | `agents/skills/skills-index.csv` |
| `skill gen-plugin` | `--output` | 输出文件 | `agents/plugins/generated.plugin.yaml` |
| `skill gen-plugin` | `--category` | 按分类过滤 | — |

| 模板 | 生成 | 用途 |
|------|------|------|
| `agents/mcp/mcp.template.json` | `agents/mcp/mcp.json` | MCP 服务密钥（共享） |
| `ide/codex/auth.template.json` | `ide/codex/auth.json` | Codex 当前 LLM 的 API Key |
| `ide/codex/config.template.toml` | `ide/codex/config.toml` | Codex 当前 LLM 的 base_url |
| `ide/opencode/opencode.template.json` | `ide/opencode/opencode.json` | OpenCode 多 provider 列表 |

> ⚙️ **自动剪枝**：模板中如果某个 `provider.*` 或 `mcpServers.*` 子项含有未解析的 `${...}`，整段会被自动移除。这样可以在模板里预先列出所有可能的 provider，未配置的会自动消失，不会产生死配置。

### 3.5 LLM Provider 占位符速查

| 占位符 | 来源 | 用法 |
|--------|------|------|
| `${LLM_ACTIVE_BASE_URL}` / `${LLM_ACTIVE_API_KEY}` | 当前 active provider 的扁平字段 | Codex / Claude 类 IDE |
| `${LLM_ACTIVE_OPENAI_*}` / `${LLM_ACTIVE_ANTHROPIC_*}` | active provider 的指定协议字段 | 需要明确协议时 |
| `${LLM_<PROVIDER>_<PROTOCOL>_<FIELD>}` | llm.yaml 中**任意 provider** 的字段 | OpenCode（多 provider 并存） |
| `${OPENAI_API_KEY}` / `${ANTHROPIC_*}` | 兼容性标准化键（来自 active provider） | 历史模板 |

### 3.6 模型配置说明

#### 模型定义格式

每个 provider 的每个协议下，`models` 字段采用**对象格式**定义多个模型：

```json
"openrouter": {
  "openai": {
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": "sk-xxx",
    "models": {
      "anthropic/claude-opus-4.8-fast": { "name": "Claude Opus 4.8 Fast" },
      "anthropic/claude-sonnet-4":     { "name": "Claude Sonnet 4" },
      "openai/gpt-5.5":               { "name": "GPT-5.5" }
    }
  }
}
```

- **Key**（如 `anthropic/claude-opus-4.8-fast`）：模型 ID，即实际传给 API 的 `model` 参数
- **`name`**：人类可读名称，用于 OpenCode 等 IDE 的 UI 展示
- **默认模型**：`models` 对象的**第一个 Key** 自动作为该协议的默认模型

#### 模型与协议的映射

| 协议 | 环境变量 | 用途 |
|------|---------|------|
| `openai` | `OPENAI_MODEL` | Codex、OpenCode（OpenAI 协议）的 `model` 字段 |
| `anthropic` | `ANTHROPIC_MODEL` | Claude（Anthropic 协议）的 `model` 字段 |

切换 `_active_provider` 后，脚本自动从对应协议的 `models` 中提取第一个 Key 注入到对应环境变量。

#### 当前模型目录

| Provider | 协议 | 模型 ID | 显示名 |
|----------|------|---------|--------|
| **openicu** | openai | `gpt-5.5` | GPT-5.5 |
| | openai | `gpt-5.4` | GPT-5.4 |
| | anthropic | `claude-sonnet-4-20250514` | Claude Sonnet 4 |
| | anthropic | `claude-haiku-4-20250514` | Claude Haiku 4 |
| **openrouter** | openai | `anthropic/claude-opus-4.8-fast` | Claude Opus 4.8 Fast |
| | openai | `anthropic/claude-opus-4.8` | Claude Opus 4.8 |
| | openai | `anthropic/claude-sonnet-4` | Claude Sonnet 4 |
| | openai | `openai/gpt-5.5` | GPT-5.5 |
| | openai | `deepseek/deepseek-v4-pro` | DeepSeek V4 Pro |
| | anthropic | `~anthropic/claude-sonnet-latest` | Claude Sonnet Latest |
| | anthropic | `anthropic/claude-sonnet-4` | Claude Sonnet 4 |
| | anthropic | `anthropic/claude-opus-4.8` | Claude Opus 4 |
| **openai** | openai | `gpt-5.5` | GPT-5.5 |
| | openai | `gpt-5.4` | GPT-5.4 |
| **anthropic** | anthropic | `anthropic/claude-opus-4.8-fast` | Claude Opus 4.8 Fast |
| | anthropic | `anthropic/claude-opus-4.8` | Claude Opus 4.8 |
| **deepseek** | openai | `deepseek/deepseek-v4-pro` | DeepSeek V4 Pro |
| | openai | `deepseek/deepseek-v4-flash` | DeepSeek V4 Flash |
| | anthropic | `deepseek/deepseek-v4-pro` | DeepSeek V4 Pro |
| | anthropic | `deepseek/deepseek-v4-flash` | DeepSeek V4 Flash |
| **volcengine** | openai | `doubao-pro-32k` | Doubao Pro 32K |
| | openai | `doubao-1-5-pro-32k` | Doubao 1.5 Pro 32K |

> 💡 **OpenRouter 模型 ID 前缀**：OpenRouter 的模型 ID 需带 `provider/` 前缀（如 `anthropic/claude-sonnet-4`）。Anthropic 协议下使用 `~` 前缀（如 `~anthropic/claude-sonnet-latest`）表示 OpenRouter 的路由标记。

#### 新增模型

在 `llm.yaml` 对应 provider/protocol 的 `models` 中添加条目即可：

```json
"models": {
  "existing-model": { "name": "Existing Model" },
  "new-model-id":   { "name": "New Model Display Name" }
}
```

重新运行 `python scripts/agentctl.py generate`，新模型会自动注入到 OpenCode 等多模型 IDE 的配置中。如需更改默认模型，将目标模型 Key 移到 `models` 对象的第一位。

---

### 3.7 密钥清单（MCP / 业务）

| 变量名 | 用途 |
|--------|------|
| `AMAP_MAPS_API_KEY` | 高德地图 MCP |
| `WECOM_WEBHOOK_URL` | 企业微信 |
| `BOSS_COOKIE` / `BOSS_BST` | BOSS 直聘 |
| `TAVILY_API_KEY` | Tavily 搜索 |
| `FIRECRAWL_API_KEY` | Firecrawl 爬虫 |
| `YUQUE_TOKEN` | 语雀 |
| `STITCH_API_KEY` | Stitch 原型 |
| `MASTERGO_MAGIC_TOKEN` | MasterGo Magic |
| `CONTEXT7_API_KEY` | Context7 文档 |

---

## 4. 一键脚本

### 4.1 仅生成配置文件

```bash
.\init-env.cmd        # Windows
./init-env.sh          # macOS / Linux
```

等价于 `python scripts/agentctl.py generate`。

### 4.2 全量初始化

```bash
.\install.cmd         # Windows
./install.sh           # macOS / Linux
```

等价于 `python scripts/agentctl.py setup`，依次执行：

1. `plugin install all`（执行各插件 install 脚本 → 下载 skill → 合并 mcp/env 到 `llm.yaml` / `mcp.yaml`）
2. `generate`（生成 `mcp.json` / `auth.json` / `config.toml` / `opencode.json` 等）
3. `sync All`（同步 rules / mcp / skills 到所有 IDE）

---

## 5. Plugin 工作流程

`agentctl setup` / `agentctl plugin install` 涉及的核心流程：

```
┌─────────────────────────────────────────────────────────────┐
│  plugin install（agentctl plugin install <file>）           │
│                                                             │
│  1. 执行插件 install 脚本（scripts.install，如 npm i -g）  │
│  2. 下载 skill 到 agents/skills/<name>/                     │
│  3. 合并 envVars → llm.yaml                                 │
│                                                             │
│  注：plugin.yaml 的 mcpServers 不在此阶段合并，             │
│      保持 mcp.yaml 为用户手写的纯净源                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  generate（agentctl generate）                              │
│                                                             │
│  同时读取 mcp.yaml + agents/plugins/*.plugin.yaml           │
│  → 合并 mcpServers（mcp.yaml 优先，plugin 补充）           │
│  → 生成 mcp.json + 各 IDE 模板（opencode/codex/claude）    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  sync（agentctl sync -i All）                               │
│                                                             │
│  → 同步 mcp.json 到各 IDE（.mcp.json / .cursor/mcp.json …）│
│  → 同步 skills 到各 IDE（复制或 symlink）                  │
└─────────────────────────────────────────────────────────────┘
```

**关键设计**：`mcp.yaml` 与 `plugin.yaml` 中的 `mcpServers` 在 `generate` 阶段一起合并到 `mcp.json`，而不是在 `plugin install` 阶段写入 `mcp.yaml`。这样 `mcp.yaml` 始终是用户手写的纯净源，插件的 mcp 配置作为独立来源参与合并。合并优先级：`mcp.yaml`（用户手写）> `plugin.yaml`（插件默认），同名服务器以 `mcp.yaml` 为准。

### 5.1 单个插件安装

```bash
# 安装一个插件后，再单独执行 generate + sync
python scripts/agentctl.py plugin install agents/plugins/core.plugin.yaml
python scripts/agentctl.py generate
python scripts/agentctl.py sync -i All -f
```

### 5.2 一键全流程

```bash
# 等价于上面三步合并（针对 agents/plugins/*.plugin.yaml 全部插件）
python scripts/agentctl.py setup
```

### 5.3 模拟安装

```bash
# 不写文件，仅打印将要做什么
python scripts/agentctl.py plugin install agents/plugins/core.plugin.yaml --dry-run
```

---

## 6. 典型场景

### 场景 A：新成员第一次使用

```bash
git clone <repo>
cd MyAgentPlugin
cp llm-env-example.yaml llm.yaml
cp mcp-env-example.yaml mcp.yaml
# 编辑 llm.yaml / mcp.yaml 填密钥
./install.sh
```

### 场景 B：切换到火山引擎跑 Codex

```bash
python scripts/agentctl.py provider volcengine
python scripts/agentctl.py generate
# 重启 Codex，base_url / api_key 已自动更新
```

### 场景 C：只想刷新某个 IDE

```bash
python scripts/agentctl.py sync -i Cursor -f
```

### 场景 D：临时调试，把密钥仅写入当前会话

```bash
python scripts/agentctl.py env --scope process
```

### 场景 E：把密钥持久化到用户级环境变量

```bash
python scripts/agentctl.py env --scope user --force
```

### 场景 F：在 OpenCode 里新增一个 LLM provider

1. 在 `llm.yaml` 的 `llm` 下加一节：
   ```json
   "groq": { "openai": { "base_url": "https://api.groq.com/openai/v1", "api_key": "..." } }
   ```
2. 在 `ide/opencode/opencode.template.json` 的 `provider` 下新增条目，引用 `${LLM_GROQ_OPENAI_*}` 占位符
3. 重新生成：`python scripts/agentctl.py generate`

### 场景 G：新增一个插件并同步到所有 IDE

```bash
# 1. 准备 agents/plugins/my.plugin.yaml
# 2. 安装 + 生成 + 同步
python scripts/agentctl.py plugin install agents/plugins/my.plugin.yaml
python scripts/agentctl.py generate
python scripts/agentctl.py sync -i All -f
```

---

## 7. 版本控制边界

| 文件 | 提交？ | 说明 |
|------|--------|------|
| `llm-env-example.yaml` / `mcp-env-example.yaml` | ✅ | 仅占位 |
| `llm.yaml` / `mcp.yaml` | ❌ | 含真实密钥（已在 `.gitignore`） |
| `*.template.json` / `*.template.toml` | ✅ | 仅 `${KEY}` 占位符 |
| `agents/mcp/mcp.json` | ❌ | 由 `agentctl generate` 生成 |
| `ide/codex/auth.json` | ❌ | 由 `agentctl generate` 生成 |
| `ide/codex/config.toml` | ❌ | 由 `agentctl generate` 生成 |
| `ide/opencode/opencode.json` | ❌ | 由 `agentctl generate` 生成 |
| `agents/plugins/*.plugin.yaml` | ✅ | 插件定义（无密钥） |

---

## 8. 不同 IDE 的格式差异

| 项目 | Cursor | Trae | Codex | OpenCode |
|------|--------|------|-------|----------|
| MCP 键名 | `mcpServers` | `mcpServers` | TOML 表 | `mcp` |
| MCP 位置 | `.cursor/mcp.json` | `.mcp.json` | `.codex/config.toml` | `.opencode/opencode.json` |
| Rules 目录 | `.cursor/rules/` | `.trae/rules/` | `.codex/rules/` | `.opencode/skills/` |
| Rules 扩展名 | `.mdc` | `.md` | `.md` | — |
| 项目指令 | — | `AGENTS.md` | — | — |

---

## 9. Skill 推荐速查

> 详细映射由 [`agents/skills/skills-index.csv`](agents/skills/skills-index.csv) 驱动，新增 / 调整 Skill 只需改 CSV。设计原则见 [AGENTS.md](AGENTS.md#7-skills-推荐矩阵)。

| 角色 | 推荐 Skill |
|------|-----------|
| 前端 | `stitch-prototype-skill` · `mastergo-magic-skill` · `drawio-skill` · `mermaid-sequence-from-flow` |
| 后端 | `restful-api-design-skill` · `task-plan-skill` · `drawio-skill` |
| 设计 | `stitch-prototype-skill` · `mastergo-magic-skill` · `prd-to-mastergo-interaction-skill` · `drawio-skill` |
| 产品 | `usecase-prd-skill` · `task-plan-skill` · `weekly-report-skill` · `prd-to-mastergo-interaction-skill` |
| 通用安装 | `find-skills` · `personnel-recruitment` · `hardware-agent-prompt-skill` · `elon-musk-perspective` |

---

## 10. 常见问题

### Q1：`[WARN] Unresolved placeholders ...`？

`llm.yaml` / `mcp.yaml` 中对应键值为空，且 OS 环境变量也未设置。三种解决方式：

1. 在 `llm.yaml` / `mcp.yaml` 填入真实值；
2. `setx OPENAI_API_KEY xxx`（Windows） / `export OPENAI_API_KEY=xxx`（*nix）后重跑；
3. 若该占位符不需要，确认它是否在 `provider.*` / `mcpServers.*` 容器键下——是的话脚本会**自动移除**该子项；不是的话从模板里删掉。

### Q2：Windows 下提示"需要管理员权限"？

Junction 创建需要管理员权限。右键终端 → "以管理员身份运行"。

### Q3：已有配置被覆盖了怎么办？

脚本默认不覆盖已有配置。要覆盖，加 `--force` / `-f`。

### Q4：修改 `agents/rules/` 后需要重新运行脚本吗？

不需要。Junction 是目录链接，会自动同步。

### Q5：如何只刷新某个 IDE？

```bash
python scripts/agentctl.py sync -i Cursor -f
```

### Q6：Codex / Claude 切到别的 LLM？

```bash
python scripts/agentctl.py provider <provider_name>
python scripts/agentctl.py generate
```

### Q7：OpenCode 里看不到我新加的 provider？

OpenCode 是从 `opencode.json` 的 `provider` 段读取的。新加 provider 需要：
1. `llm.yaml` 加节点
2. `ide/opencode/opencode.template.json` 加引用
3. 重新生成：`python scripts/agentctl.py generate`
