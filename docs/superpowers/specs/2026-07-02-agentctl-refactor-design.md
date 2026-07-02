# agentctl 重构设计：三脚本合并为统一入口

- 日期：2026-07-02
- 状态：待实现
- 范围：`scripts/init-env.py` + `scripts/init-ide.py` + `scripts/plugin-manager.py` 合并为 `scripts/agentctl.py`，并更新所有调用方

---

## 1. 背景与目标

### 1.1 现状

仓库现有三个脚本，职责存在重叠：

| 脚本 | 行数 | 主要职责 |
|------|------|----------|
| `init-env.py` | 1004 | 从 `llm.yaml` + `mcp.yaml` 生成运行态配置（mcp.json、各 IDE 模板填充）；设置环境变量 |
| `init-ide.py` | 1538 | 把 `agents/`（rules/skills/mcp.json）分发同步到各 IDE 目录，含 MCP 格式转换 |
| `plugin-manager.py` | 778 | 解析 `plugin.json`，安装 skills 到 `.agents/skills`，合并 mcp 到 `mcp.yaml` |

### 1.2 职责重叠点

1. **工具函数重复**：`load_env_config_file` / `save_env_config_file` / `_load_yaml_module` 在三个脚本各自实现一遍
2. **mcp.yaml 读写交叉**：`plugin-manager` 写（`update_mcp_template`）、`init-env` 读
3. **mcp.json 流转**：`init-env` 生成 → `init-ide` 消费
4. **skill 安装/同步**：`plugin-manager` 装到 `.agents/skills`、`init-ide` 同步到 IDE
5. **占位符/剪枝逻辑**：`init-env` 和 `init-ide`(opencode 注入) 各有一套

### 1.3 目标

- 合并为单一 CLI 入口 `agentctl.py`，消除职责重叠
- 配置源统一为：`llm.yaml` + `mcp.yaml` + `plugin.json`（plugin.json 是 mcp+skills 打包，未来含 llm）+ UI 选中的 skills
- 提取公共库 `scripts/lib/`，消除重复代码
- 更新所有调用方，删除旧脚本

### 1.4 非目标

- 不改变配置文件格式（llm.yaml / mcp.yaml / plugin.json 结构不变）
- 不改变 IDE 目标目录布局
- 不改变 UI（config_ui.html）行为，仅后端调用入口替换

---

## 2. 子命令设计

统一入口 `agentctl.py`，argparse 子命令组织，按"动作"映射：

| 子命令 | 对应旧脚本动作 | 作用 |
|--------|---------------|------|
| `agentctl env` | `init-env Env` | 设置环境变量（`--scope process/user`，`--force`） |
| `agentctl shell` | `init-env ExportShell` | 输出 shell 环境变量赋值语句 |
| `agentctl generate` | `init-env Generate` | 从 llm.yaml+mcp.yaml 生成运行态配置（mcp.json、各 IDE 模板填充、opencode 模型注入） |
| `agentctl provider` | `init-env --provider/--protocol` | 切换 active provider/protocol 并保存 |
| `agentctl sync` | `init-ide` | 同步 rules/skills/mcp 到各 IDE |
| `agentctl plugin install` | `plugin-manager install` | 安装插件（skills+mcp 合并） |
| `agentctl plugin list` | `plugin-manager list` | 列出可用插件 |
| `agentctl skill list` | `plugin-manager list-skills` | 列出 skills（从 csv） |
| `agentctl skill gen-plugin` | `plugin-manager generate-plugin` | 从 csv 生成 plugin.json |
| `agentctl setup` | install.sh 全流程 | 一键：generate → plugin install(全部) → sync |

### 2.1 关键参数映射

`agentctl sync` 参数（原 init-ide）：
- `--ide <name>` / `-i`：目标 IDE，默认 `All`
- `--force` / `-f`：强制覆盖
- `--scope <llm,mcp,skill,plugin,rules>`：同步范围
- `--skills <name1,name2>`：仅同步勾选的技能（白名单过滤）
- `--target <dir>` / `-t`：IDE 配置根目录
- `--source-dir <dir>`：源 agents 目录

`agentctl generate` 参数（原 init-env Generate）：
- `--scope <process/user>`（env 子命令用）
- `--force`（env 子命令用）

`agentctl plugin install` 参数（原 plugin-manager install）：
- `<plugin-file>`：插件配置路径
- `--symlink`：用 symlink 而非复制
- `--copy`：强制复制（默认，沙箱友好）

---

## 3. 模块结构

```
scripts/
  agentctl.py              # 唯一 CLI 入口（argparse 子命令分发）
  lib/
    __init__.py
    config_io.py           # yaml/json 读写（消除三处重复）
    placeholder.py         # 占位符替换 + 未解析块剪枝（prune_unresolved_blocks）
    logging.py             # 颜色日志（COLOR_* 常量 + print 包装）
    paths.py               # 项目根 / IDE 路径解析 / junction-symlink-copy 工具
    llm.py                 # llm.yaml 加载 / flatten / switch provider / active protocols
    mcp.py                 # mcp.yaml 加载 + mcp.json 生成 + 各 IDE MCP 格式转换
    skills.py              # skills 安装(npx) / 复制 / 索引生成 / 白名单过滤
    plugins.py             # plugin.json 解析 / 安装 / mcp 合并到 mcp.yaml / envVars 更新
    ide/
      __init__.py
      base.py              # IDE 抽象基类（init_rules/init_mcp/init_skills/init_manifest）
      cursor.py            # Cursor 分发
      codex.py             # Codex 分发（config.toml TOML 转换）
      opencode.py          # OpenCode 分发（多 provider + 模型注入）
      trae.py              # Trae / trae-cn / trae-solo-cn 分发
      claude.py            # Claude 分发
      workbuddy.py         # WorkBuddy 分发
      qoder.py             # Qoder 分发
      openclaw.py          # OpenClaw 分发
      idea.py              # IDEA 分发
      agents.py            # Agents 分发
```

### 3.1 模块职责边界

- `config_io`：唯一负责 yaml/json 读写，统一 encoding（utf-8-sig 读、utf-8 写）、sort_keys、ensure_ascii
- `placeholder`：占位符解析（`${LLM_ACTIVE_*}` 等 4 类命名约定）、`_has_unresolved_placeholder`、`prune_unresolved_blocks`（仅对 provider/providers/mcpServers/mcp 容器键剪枝）
- `mcp`：`mcp.yaml` → `mcp.json` 生成；`mcp.json` → 各 IDE 格式（cursor json / codex toml / opencode json / trae json）。**init-env 和 init-ide 的 MCP 逻辑合并到此**
- `skills`：`copy_skills_safe`（含白名单过滤 `INCLUDE_SKILLS`）、`write_skills_index`、`install_skill`(npx skills add)。**plugin-manager 和 init-ide 的 skill 逻辑合并到此**
- `plugins`：`load_plugin_config`、`validate_plugin_config`、`update_mcp_template`（合并到 mcp.yaml）、`update_env_file`、`install_plugin`(编排)
- `ide/base`：定义 `IdeTarget` 抽象（`name`、`rules_dir`、`mcp_file`、`skills_dir`、`init_rules/init_mcp/init_skills/init_manifest`），各 IDE 子类实现差异

---

## 4. 数据流

```
┌─────────────┐
│ plugin.json │──┐
└─────────────┘  │  agentctl plugin install
                 ├──→ mcp.yaml（合并 mcpServers）
┌─────────────┐  │  ├──→ .agents/skills/（安装 skills）
│ llm.yaml ───┤  │
│ mcp.yaml ───┤  │  agentctl generate
│ skills 选中 ┘  │  ├──→ agents/mcp/mcp.json（运行态）
└─────────────┘  │  ├──→ .codex/config.toml / opencode.json（模板填充+剪枝）
                 │  └──→ opencode 模型注入
                 │
                 │  agentctl sync --skills <选中>
                 └──→ 各 IDE 目录（rules/skills/mcp/manifest）
```

`agentctl setup` = `generate` → `plugin install`(全部插件) → `sync --ide All`

---

## 5. 兼容性与迁移

### 5.1 调用方更新清单

| 调用方 | 旧调用 | 新调用 |
|--------|--------|--------|
| `install.sh` | `plugin-manager.py install` × N + `init-env.py -a Generate` + `init-ide.py -i All -f` | `agentctl setup` |
| `install.cmd` | 同上 | `agentctl setup` |
| `init-env.cmd` | `init-env.py -a Generate` | `agentctl generate` |
| `run.sh` | `init-ide.py`（如有） | `agentctl sync` |
| `app.py` / `config_server.py` | `_script_run_shell_cmd("init-ide", ...)` | `_script_run_shell_cmd("agentctl", ["sync", ...])` |
| `tests/test_init_env.py` | 测 `init-env.py` | 测 `agentctl generate` |
| `README.md` | 旧命令示例 | 新命令示例 |
| `AGENTS.md` | 旧脚本引用 | 新脚本引用 |

### 5.2 旧脚本处理

- 删除 `scripts/init-env.py`、`scripts/init-ide.py`、`scripts/plugin-manager.py`
- 删除 `scripts/skills-mapping.csv` 相关逻辑迁移到 `agentctl skill` 子命令（若仍需要）

### 5.3 向后不兼容说明

- 旧 CLI 参数不再可用（`-a Generate` / `--ide` 等改为子命令形式）
- 文档与脚本同步更新，不留兼容包装

---

## 6. 测试策略

- 保留并改造 `tests/test_init_env.py` → `tests/test_agentctl.py`
- 测试覆盖：
  - `agentctl generate`：生成 mcp.json、config.toml、opencode.json 内容正确
  - `agentctl sync`：各 IDE 目录文件生成、白名单过滤生效
  - `agentctl plugin install`：mcp 合并、skill 安装
  - `agentctl provider`：切换 provider 后 generate 输出变化
- 手动验证：`agentctl setup` 端到端在干净环境下产出与旧流程一致

---

## 7. 风险与对策

| 风险 | 对策 |
|------|------|
| 重构面大，易引入回归 | 分阶段：先建 lib + agentctl 骨架 → 逐子命令迁移并测试 → 更新调用方 → 删旧脚本 |
| IDE 分发器差异多（11 个 IDE） | `ide/base.py` 抽象统一接口，子类只覆写差异方法；先迁移已有逻辑不改行为 |
| opencode 模型注入逻辑复杂 | 单独成 `mcp._inject_opencode_models`，保持现有实现 |
| 沙箱环境 symlink 失败 | `paths.py` 统一 junction→symlink→copy 降级链，默认 copy |

---

## 8. 实现阶段（供 writing-plans 细化）

1. 建 `scripts/lib/` 公共库（config_io / placeholder / logging / paths），从三脚本提取
2. 建 `scripts/lib/llm.py` + `mcp.py`，迁移 init-env 的 generate 逻辑
3. 建 `scripts/lib/skills.py` + `plugins.py`，迁移 plugin-manager 逻辑
4. 建 `scripts/lib/ide/`，迁移 init-ide 各 IDE 分发器
5. 建 `scripts/agentctl.py` 入口，串联子命令
6. 改造 `tests/`，验证 agentctl 各子命令
7. 更新调用方（install.sh/cmd、run.sh、app.py、config_server.py）
8. 更新文档（README.md、AGENTS.md）
9. 删除旧脚本
