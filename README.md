# IDE 初始化脚本使用说明

将 `agents/` 共享配置一键映射到 Cursor / Trae / Codex / OpenCode / Claude / IDEA 等多种 IDE。

> 本文件聚焦**怎么用**。如果想了解仓库的设计思路与治理边界，请看 [AGENTS.md](AGENTS.md)。

---

## 1. 快速开始

```bash
# 1) 复制密钥模板
cp env.example.json env.json

# 2) 编辑 env.json，填入真实 API Key（也可留空，由 OS 环境变量回退）

# 3) 一键全量初始化（生成配置 + 链接所有支持的 IDE）
.\install.cmd      # Windows
./install.sh        # macOS / Linux
```

完成后即可在已支持的 IDE 中使用统一的 rules / mcp / skills 配置。

---

## 2. 脚本与一键命令总览

| 脚本 | 用途 |
|------|------|
| [scripts/init-env.py](file:///c:/Users/59300/Desktop/agent-init-plugin/scripts/init-env.py) | 从 `env.json` / OS 环境变量生成 MCP / Codex / OpenCode 配置 |
| [scripts/init-ide.py](file:///c:/Users/59300/Desktop/agent-init-plugin/scripts/init-ide.py) | 通用 IDE 初始化（创建 Junction、复制 / 生成配置） |
| `init-env.cmd` / `init-env.sh` | 一键生成密钥相关配置 |
| `install.cmd` / `install.sh` | 一键执行环境初始化 + 多 IDE 初始化 |

### 环境要求

- Python 3.10+
- Windows / macOS / Linux 均可
- Windows 下创建 Junction 需以**管理员权限**运行终端

---

## 3. init-env.py 使用手册

### 3.1 常用命令

```bash
# 默认：设置进程环境变量 + 生成所有配置文件
python scripts/init-env.py

# 仅设置环境变量（不生成配置文件）
python scripts/init-env.py -a Env

# 仅生成配置文件
python scripts/init-env.py -a Generate

# 写入用户级环境变量（持久化，跨终端有效）
python scripts/init-env.py -a Env --scope user --force

# 输出 export 语句供 shell 直接 eval
python scripts/init-env.py -a ExportShell
```

### 3.2 切换当前 LLM Provider

仅影响 Codex / Claude（一次只用一个 LLM 的 IDE）。OpenCode 不受影响。

```bash
# 切换到火山引擎（沿用当前协议）
python scripts/init-env.py --provider volcengine

# 同时指定协议
python scripts/init-env.py --provider volcengine --protocol anthropic

# 切换并立即重新生成配置
python scripts/init-env.py --provider deepseek -a Generate
```

支持的 provider 来自 `env.json` 中 `llm.*` 节点（默认包含 `openicu` / `openai` / `openrouter` / `deepseek` / `volcengine`）。

### 3.3 参数速查

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--action` | `-a` | `Env` / `Generate` / `All` / `ExportShell` | `All` |
| `--env-file` | `-f` | 密钥配置文件路径 | `env.json` |
| `--template-file` | — | MCP 模板路径 | `agents/mcp/mcp.template.json` |
| `--output-file` | — | MCP 生成路径 | `agents/mcp/mcp.json` |
| `--scope` | — | `process` / `user` | `process` |
| `--provider` | — | 切换 active provider | — |
| `--protocol` | — | 切换 active protocol（`openai` / `anthropic`） | — |
| `--force` | — | 跳过确认提示 | 否 |

### 3.4 自动生成的文件

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
| `${LLM_<PROVIDER>_<PROTOCOL>_<FIELD>}` | env.json 中**任意 provider** 的字段 | OpenCode（多 provider 并存） |
| `${OPENAI_API_KEY}` / `${ANTHROPIC_*}` | 兼容性标准化键（来自 active provider） | 历史模板 |

### 3.6 密钥清单（MCP / 业务）

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

## 4. init-ide.py 使用手册

### 4.1 常用命令

```bash
# 初始化所有支持的 IDE，写到当前用户主目录
python scripts/init-ide.py

# 强制覆盖已有配置
python scripts/init-ide.py -f

# 仅初始化指定 IDE
python scripts/init-ide.py -i Cursor
python scripts/init-ide.py -i Trae
python scripts/init-ide.py -i trae-cn
python scripts/init-ide.py -i trae-solo-cn
python scripts/init-ide.py -i Codex
python scripts/init-ide.py -i Claude
python scripts/init-ide.py -i WorkBuddy
python scripts/init-ide.py -i Qoder
python scripts/init-ide.py -i OpenClaw
python scripts/init-ide.py -i OpenCode
python scripts/init-ide.py -i IDEA
python scripts/init-ide.py -i Agents

# 指定目标目录（IDE 配置写入位置）
python scripts/init-ide.py -i trae-cn -t $env:USERPROFILE -f
python scripts/init-ide.py -t D:\my-project

# 指定源目录（agents/ 所在目录）
python scripts/init-ide.py --source-dir D:\my-project
```

### 4.2 参数速查

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--target-dir` | `-t` | IDE 配置写入位置 | 用户主目录 |
| `--source-dir` | `-s` | `agents/` 所在目录 | 脚本所在目录的父目录 |
| `--ide` | `-i` | 见下方 IDE 选项 | `All` |
| `--force` | `-f` | 强制覆盖已有配置 | 否 |

### 4.3 支持的 IDE

`Cursor` · `Trae` · `trae-cn` · `trae-solo-cn` · `Codex` · `Claude` · `WorkBuddy` · `Qoder` · `OpenClaw` · `OpenCode` · `IDEA` · `Agents` · `All`

### 4.4 链接 / 生成方式

| 目标 | 链接类型 | 源 |
|------|----------|-----|
| `.agent/rules/` | Junction（目录） | `agents/rules/` |
| `.trae/rules/` 等各 IDE rules 目录 | Junction（目录） | `agents/rules/` |
| `.mcp.json` | Symlink/Copy（文件） | `agents/mcp/mcp.json` |
| `.cursor/mcp.json` | 生成文件 | `agents/mcp/mcp.json`（mcpServers 键） |
| `.codex/config.toml` | 生成文件 | TOML 格式 |
| `.codex/auth.json` | 复制文件 | `ide/codex/auth.json` |
| `.opencode/opencode.json` | 生成文件 | `ide/opencode/opencode.template.json` |
| `*/skills/` | 复制目录 | `agents/skills/` |
| `*/skills/README.md` | 生成文件 | 技能索引 |

---

## 5. 一键脚本

### 5.1 仅生成配置文件

```bash
.\init-env.cmd        # Windows
./init-env.sh          # macOS / Linux
```

等价于 `python scripts/init-env.py -a Generate`。

### 5.2 全量初始化

```bash
.\install.cmd         # Windows
./install.sh           # macOS / Linux
```

依次执行：

1. `init-env`（生成 mcp.json / auth.json / config.toml / opencode.json）
2. `init-ide -i Agents`
3. `init-ide -i trae-cn`
4. `init-ide -i Cursor`
5. `init-ide -i Codex`
6. `init-ide -i OpenCode`
7. `init-ide -i IDEA`
8. `init-ide -i trae-solo-cn`

---

## 6. 典型场景

### 场景 A：新成员第一次使用

```bash
git clone <repo>
cd agent-init-plugin
cp env.example.json env.json
# 编辑 env.json 填密钥
.\install.cmd
```

### 场景 B：切换到火山引擎跑 Codex

```bash
python scripts/init-env.py --provider volcengine -a Generate
# 重启 Codex，base_url / api_key 已自动更新
```

### 场景 C：只想刷新某个 IDE

```bash
python scripts/init-ide.py -i Cursor -f
```

### 场景 D：临时调试，把密钥仅写入当前会话

```bash
python scripts/init-env.py -a Env --scope process
```

### 场景 E：把密钥持久化到用户级环境变量

```bash
python scripts/init-env.py -a Env --scope user --force
```

### 场景 F：在 OpenCode 里新增一个 LLM provider

1. 在 `env.json` 的 `llm` 下加一节：
   ```json
   "groq": { "openai": { "base_url": "https://api.groq.com/openai/v1", "api_key": "..." } }
   ```
2. 在 `ide/opencode/opencode.template.json` 的 `provider` 下新增条目，引用 `${LLM_GROQ_OPENAI_*}` 占位符
3. 重新生成：`python scripts/init-env.py -a Generate`

---

## 7. 版本控制边界

| 文件 | 提交？ | 说明 |
|------|--------|------|
| `env.example.json` | ✅ | 仅占位 |
| `env.json` | ❌ | 含真实密钥（已在 `.gitignore`） |
| `*.template.json` / `*.template.toml` | ✅ | 仅 `${KEY}` 占位符 |
| `agents/mcp/mcp.json` | ❌ | 由脚本生成 |
| `ide/codex/auth.json` | ❌ | 由脚本生成 |
| `ide/codex/config.toml` | ❌ | 由脚本生成 |
| `ide/opencode/opencode.json` | ❌ | 由脚本生成 |

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

> 详细映射由 [`doc/skills-mapping.csv`](file:///c:/Users/59300/Desktop/agent-init-plugin/doc/skills-mapping.csv) 驱动，新增 / 调整 Skill 只需改 CSV。设计原则见 [AGENTS.md](file:///c:/Users/59300/Desktop/agent-init-plugin/AGENTS.md#7-skills-推荐矩阵)。

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

`env.json` 中对应键值为空，且 OS 环境变量也未设置。三种解决方式：

1. 在 `env.json` 填入真实值；
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
python scripts/init-ide.py -i Cursor -f
```

### Q6：Codex / Claude 切到别的 LLM？

```bash
python scripts/init-env.py --provider <provider_name> -a Generate
```

### Q7：OpenCode 里看不到我新加的 provider？

OpenCode 是从 `opencode.json` 的 `provider` 段读取的。新加 provider 需要：
1. `env.json` 加节点
2. `opencode.template.json` 加引用
3. 重新生成
