# agentctl 三脚本合并重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `init-env.py` + `init-ide.py` + `plugin-manager.py` 合并为单一 CLI 入口 `agentctl.py`，提取公共库消除职责重叠，更新所有调用方。

**Architecture:** `scripts/agentctl.py` 作 argparse 入口分发子命令；`scripts/lib/` 存公共库（config_io/placeholder/logging/paths/llm/mcp/skills/plugins/ide/*）；数据流：plugin.json + llm.yaml + mcp.yaml + 选中 skills → generate → sync → 各 IDE。

**Tech Stack:** Python 3 + PyYAML + argparse + Flask(调用方) + Vue3(UI 不变)

**Spec:** [docs/superpowers/specs/2026-07-02-agentctl-refactor-design.md](file:///Users/yangxuezeng/Desktop/MyAgentPlugin/docs/superpowers/specs/2026-07-02-agentctl-refactor-design.md)

---

## 迁移原则（所有 Task 通用）

1. **迁移而非重写**：从旧脚本搬运函数到 lib，保持行为不变；遇到重复实现以本计划指定的为准
2. **先迁移后验证**：每完成一个 lib 模块，立即用现有测试或新测试验证
3. **颜色常量统一**：所有 `COLOR_*` 常量集中到 `lib/logging.py`，其他模块 `from lib.logging import *`
4. **路径基准**：`PROJECT_ROOT = Path(__file__).resolve().parents[1]`（agentctl.py 在 scripts/ 下，故 parents[1] 是项目根）

---

## Task 1: 建 lib 公共库基础设施

**Files:**
- Create: `scripts/lib/__init__.py`
- Create: `scripts/lib/logging.py`
- Create: `scripts/lib/config_io.py`
- Create: `scripts/lib/paths.py`
- Create: `scripts/lib/placeholder.py`

- [ ] **Step 1: 创建 lib 包与 logging.py**

创建 `scripts/lib/__init__.py`（空文件）。

创建 `scripts/lib/logging.py`，从 `scripts/init-env.py:23-33`（COLOR_* 常量）迁移：

```python
"""统一颜色日志。所有模块 from lib.logging import * 即可。"""
import sys

COLOR_CYAN = "\033[96m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_RED = "\033[91m"
COLOR_MAGENTA = "\033[95m"
COLOR_WHITE = "\033[97m"
COLOR_DARKGRAY = "\033[90m"
COLOR_RESET = "\033[0m"


def info(msg): print(f"{COLOR_GREEN}{msg}{COLOR_RESET}")
def warn(msg): print(f"{COLOR_YELLOW}{msg}{COLOR_RESET}", file=sys.stderr)
def error(msg): print(f"{COLOR_RED}{msg}{COLOR_RESET}", file=sys.stderr)
def hint(msg): print(f"{COLOR_DARKGRAY}{msg}{COLOR_RESET}")
```

- [ ] **Step 2: 创建 config_io.py**

从 `scripts/init-env.py:40-71`（`_load_yaml_module`/`load_env_config_file`/`save_env_config_file`）迁移到 `scripts/lib/config_io.py`，函数签名不变。删除三脚本里各自的重复实现（此步只建库，旧脚本暂不删，后续 Task 9 删）。

```python
"""统一 yaml/json 读写。消除三脚本重复的 load/save 函数。"""
import json
from pathlib import Path

def _load_yaml_module():
    try:
        import yaml
        return yaml
    except ImportError:
        raise SystemExit("PyYAML is required. Install: pip install pyyaml")

def load_env_config_file(path: Path) -> dict:
    with open(path, "r", encoding="utf-8-sig") as f:
        if path.suffix.lower() in (".yaml", ".yml"):
            return _load_yaml_module().safe_load(f)
        return json.load(f)

def save_env_config_file(path: Path, data: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        if path.suffix.lower() in (".yaml", ".yml"):
            _load_yaml_module().safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
```

- [ ] **Step 3: 创建 paths.py**

从 `scripts/init-ide.py`（junction/symlink/copy 降级链）迁移目录链接工具。关键函数：`make_dir_link(src, dst)`（junction→symlink→copy 降级，沙箱默认 copy）。

```python
"""路径与目录链接工具。junction→symlink→copy 降级链。"""
import os
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # scripts/lib/ → scripts/ → 项目根

def make_dir_link(src: Path, dst: Path, prefer_copy: bool = True) -> str:
    """创建目录链接，降级链：junction(mac不支持)→symlink→copy。返回使用的方式。"""
    if dst.exists() or dst.is_symlink():
        if dst.is_dir() and not dst.is_symlink():
            shutil.rmtree(dst)
        else:
            dst.unlink()
    if prefer_copy:
        shutil.copytree(src, dst)
        return "copy"
    try:
        os.symlink(src, dst)
        return "symlink"
    except (OSError, NotImplementedError):
        shutil.copytree(src, dst)
        return "copy"
```

- [ ] **Step 4: 创建 placeholder.py**

从 `scripts/init-env.py:633-674`（`_has_unresolved_placeholder`/`prune_unresolved_blocks`）迁移到 `scripts/lib/placeholder.py`，函数签名不变。容器键剪枝逻辑保持：仅对 `provider/providers/mcpServers/mcp` 子项剪枝。

- [ ] **Step 5: 验证 lib 可导入**

Run: `.venv/bin/python -c "from scripts.lib import config_io, logging, paths, placeholder; print('lib import OK')"`
Expected: `lib import OK`（在项目根运行；若 scripts 非 package，改用 `cd scripts && python -c "from lib import config_io; print('OK')"`）

- [ ] **Step 6: Commit**

```bash
git add scripts/lib/
git commit -m "feat(agentctl): 建 lib 公共库（config_io/logging/paths/placeholder）"
```

---

## Task 2: 建 lib/llm.py（LLM 配置处理）

**Files:**
- Create: `scripts/lib/llm.py`
- 源函数位置：`scripts/init-env.py:73-531`（load_split_env_config / flatten_env_config / switch_provider / get_active_provider 等）

- [ ] **Step 1: 迁移 llm.yaml 加载与 flatten 逻辑**

将 `init-env.py` 的以下函数迁移到 `scripts/lib/llm.py`，保持签名与行为不变：
- `load_split_env_config`（line 73）
- `save_split_env_config`（line 123）
- `read_env_config`（line 149）
- `build_proxy_model_list`（line 170）
- `_is_flat_provider`（line 223）
- `flatten_env_config`（line 227）
- `get_active_provider`（line 469）
- `get_active_protocols`（line 476）
- `list_providers`（line 484）
- `list_protocols`（line 491）
- `switch_provider`（line 499）
- `get_env_entries`（line 447）
- `mask_value`（line 463）

模块内 `from lib.config_io import load_env_config_file, save_env_config_file`、`from lib.logging import *`。

- [ ] **Step 2: 迁移环境变量导出逻辑**

将以下函数迁移到 `scripts/lib/llm.py`：
- `invoke_env_step`（line 532）
- `_detect_shell_rc`（line 589）
- `_write_shell_rc`（line 601）
- `invoke_export_shell`（line 626）

- [ ] **Step 3: 验证现有测试仍通过**

Run: `.venv/bin/python -m pytest tests/test_init_env.py -v`
Expected: 现有 `FlattenEnvConfigTests` 全部 PASS（此阶段旧脚本仍存在且未改，测试导入旧脚本路径，应通过）

- [ ] **Step 4: Commit**

```bash
git add scripts/lib/llm.py
git commit -m "feat(agentctl): 迁移 llm.yaml 加载/flatten/switch 逻辑到 lib/llm.py"
```

---

## Task 3: 建 lib/mcp.py（MCP 配置生成与格式转换）

**Files:**
- Create: `scripts/lib/mcp.py`
- 源函数位置：`init-env.py:746-828`（invoke_mcp_generate_step / _inject_opencode_models）+ `init-ide.py` 各 IDE 的 MCP 格式转换函数

- [ ] **Step 1: 迁移 mcp.json 生成逻辑**

将 `init-env.py` 的以下函数迁移到 `scripts/lib/mcp.py`：
- `invoke_mcp_generate_step`（line 746）：从 mcp.yaml 生成 agents/mcp/mcp.json
- `_inject_opencode_models`（line 829）：opencode 模型注入
- `invoke_generate_step`（line 676）：模板填充 + 占位符替换 + 剪枝（调用 `lib.placeholder.prune_unresolved_blocks`）

模块内 `from lib.config_io import *`、`from lib.placeholder import prune_unresolved_blocks, _has_unresolved_placeholder`、`from lib.logging import *`。

- [ ] **Step 2: 迁移各 IDE MCP 格式转换**

从 `init-ide.py` 迁移 MCP 格式转换函数到 `scripts/lib/mcp.py`（保持函数名）：
- Cursor: `mcp.json` 提取 `mcpServers` 键
- Codex: 转 TOML（`init-ide.py` 约 line 394 附近的 TOML 生成）
- OpenCode: `opencode.json` 格式
- Trae/Claude/其他: 直接复制 `mcp.json` 或提取 `mcpServers`

具体函数名参照 `init-ide.py` 内各 `init_<ide>_mcp` 实现，迁移为独立纯函数 `convert_mcp_to_<ide>(mcp_json_data) -> str/bytes`。

- [ ] **Step 3: 验证 generate 可生成 mcp.json**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'scripts'); from lib import mcp; mcp.invoke_mcp_generate_step(<构造 flat_config>, Path('mcp.yaml'), Path('/tmp/test_mcp.json')); print('OK')"`
Expected: `/tmp/test_mcp.json` 生成且内容含 mcpServers（用真实 mcp.yaml 测试）

- [ ] **Step 4: Commit**

```bash
git add scripts/lib/mcp.py
git commit -m "feat(agentctl): 迁移 MCP 生成与各 IDE 格式转换到 lib/mcp.py"
```

---

## Task 4: 建 lib/skills.py（技能安装与同步）

**Files:**
- Create: `scripts/lib/skills.py`
- 源函数位置：`init-ide.py`（copy_skills_safe / write_skills_index / INCLUDE_SKILLS 过滤）+ `plugin-manager.py:134-372`（parse_shorthand / build_install_command / install_skill）

- [ ] **Step 1: 迁移 skill 同步逻辑**

将 `init-ide.py` 的以下函数迁移到 `scripts/lib/skills.py`，保持白名单过滤逻辑（`INCLUDE_SKILLS` 改为函数参数 `include_skills: set | None`）：
- `copy_skills_safe(src, dst, label, force, include_skills=None)`：复制 .agents/skills → IDE skills 目录，按白名单过滤
- `write_skills_index(skills_source_dir, target_file, ide_name, force, include_skills=None)`：生成 README.md 索引

- [ ] **Step 2: 迁移 skill 安装逻辑**

将 `plugin-manager.py` 的以下函数迁移到 `scripts/lib/skills.py`：
- `parse_shorthand`（line 134）
- `build_install_command`（line 172）
- `install_skill`（line 263）：执行 `npx skills add` 安装到 `.agents/skills/`

- [ ] **Step 3: 验证 skill 安装与同步**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'scripts'); from lib import skills; skills.copy_skills_safe(Path('.agents/skills'), Path('/tmp/test_skills'), 'test', True, include_skills={'tdd'}); print('OK')"`
Expected: `/tmp/test_skills/tdd/` 存在（假设 .agents/skills/tdd 存在）

- [ ] **Step 4: Commit**

```bash
git add scripts/lib/skills.py
git commit -m "feat(agentctl): 迁移 skill 安装/同步/白名单过滤到 lib/skills.py"
```

---

## Task 5: 建 lib/plugins.py（插件解析与安装）

**Files:**
- Create: `scripts/lib/plugins.py`
- 源函数位置：`plugin-manager.py:51-432`（load_plugin_config / validate_plugin_config / update_env_file / update_mcp_template / install_plugin / install_skills / run_plugin_scripts）

- [ ] **Step 1: 迁移插件配置解析**

将 `plugin-manager.py` 的以下函数迁移到 `scripts/lib/plugins.py`：
- `load_plugin_config`（line 51）
- `validate_plugin_config`（line 61）
- `update_env_file`（line 71）
- `update_mcp_template`（line 100）：合并插件 mcpServers 到 mcp.yaml

- [ ] **Step 2: 迁移插件安装编排**

将以下函数迁移到 `scripts/lib/plugins.py`，内部调用 `lib.skills.install_skill`：
- `install_skills`（line 373）
- `run_plugin_scripts`（line 334）
- `install_plugin`（line 384）：编排 = 更新 env + 更新 mcp 模板 + 安装 skills + 运行脚本
- `list_plugins`（line 433）

- [ ] **Step 3: 迁移 csv 相关（list-skills / generate-plugin）**

将 `plugin-manager.py:547-778` 的 csv 逻辑迁移到 `scripts/lib/plugins.py`：
- `load_skills_mapping`（line 547）
- `generate_plugin_from_csv`（line 562）
- `list_skills_from_csv`（line 614）

- [ ] **Step 4: 验证插件 list**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'scripts'); from lib import plugins; plugins.list_plugins(Path('agents/plugins'))"`
Expected: 列出 7 个插件（core/frontend-design/productivity/dev-tools/computer-use 等）

- [ ] **Step 5: Commit**

```bash
git add scripts/lib/plugins.py
git commit -m "feat(agentctl): 迁移插件解析/安装/csv 逻辑到 lib/plugins.py"
```

---

## Task 6: 建 lib/ide/ 分发器

**Files:**
- Create: `scripts/lib/ide/__init__.py`
- Create: `scripts/lib/ide/base.py`
- Create: `scripts/lib/ide/cursor.py` `codex.py` `opencode.py` `trae.py` `claude.py` `workbuddy.py` `qoder.py` `openclaw.py` `idea.py` `agents.py`（共 11 个，对应 init-ide.py 的 init_<ide> 函数）

- [ ] **Step 1: 建 base.py 抽象基类**

```python
"""IDE 分发器基类。各 IDE 子类实现差异。"""
from pathlib import Path
from lib.logging import *
from lib.skills import copy_skills_safe, write_skills_index

class IdeTarget:
    name: str = ""
    rules_dir: str = ""        # 相对项目根的目录，如 ".cursor/rules"
    mcp_file: str = ""         # 如 ".cursor/mcp.json"
    skills_dir: str = ""       # 如 ".cursor/skills"
    manifest_files: list = []  # 额外复制文件

    def __init__(self, project_root: Path, force: bool = False, include_skills=None):
        self.root = project_root
        self.force = force
        self.include_skills = include_skills

    def init_rules(self, source_rules: Path):
        if self.rules_dir:
            make_dir_link(source_rules, self.root / self.rules_dir, prefer_copy=True)

    def init_mcp(self, mcp_json: Path):
        if self.mcp_file:
            # 默认复制 mcp.json，子类可覆写做格式转换
            shutil.copy(mcp_json, self.root / self.mcp_file)

    def init_skills(self, skills_source: Path):
        if self.skills_dir:
            copy_skills_safe(skills_source, self.root / self.skills_dir, self.name, self.force, self.include_skills)
            write_skills_index(skills_source, self.root / self.skills_dir / "README.md", self.name, self.force, self.include_skills)

    def init_manifest(self):
        for f in self.manifest_files:
            shutil.copy(self.root / "AGENTS.md", self.root / f)

    def run(self, source_rules, mcp_json, skills_source):
        self.init_rules(source_rules)
        self.init_mcp(mcp_json)
        self.init_skills(skills_source)
        self.init_manifest()
```

- [ ] **Step 2: 迁移 Cursor 分发器**

创建 `scripts/lib/ide/cursor.py`，将 `init-ide.py` 的 `init_cursor()` 逻辑迁移为 `CursorTarget(IdeTarget)` 子类。覆写 `init_mcp`（提取 mcpServers 到 `.cursor/mcp.json`）。

- [ ] **Step 3: 迁移 Codex 分发器**

创建 `scripts/lib/ide/codex.py`，迁移 `init_codex()`。覆写 `init_mcp`（生成 TOML 格式 `.codex/config.toml`，调用 `lib.mcp.convert_mcp_to_codex`）。

- [ ] **Step 4: 迁移 OpenCode 分发器**

创建 `scripts/lib/ide/opencode.py`，迁移 `init_opencode()`。覆写 `init_mcp`（生成 `opencode.json`，调用 `lib.mcp._inject_opencode_models`）。

- [ ] **Step 5: 迁移 Trae 分发器（含 trae-cn / trae-solo-cn）**

创建 `scripts/lib/ide/trae.py`，迁移 `init_trae()` / `init_trae_cn()` / `init_trae_solo_cn()`。三个子类或一个类 + name 参数。

- [ ] **Step 6: 迁移其余 6 个 IDE 分发器**

按相同模式创建：`claude.py` `workbuddy.py` `qoder.py` `openclaw.py` `idea.py` `agents.py`。每个迁移对应 `init_<ide>()` 逻辑。WorkBuddy 额外生成 `models.json`。

- [ ] **Step 7: 建 ide/__init__.py 注册表**

```python
from .cursor import CursorTarget
from .codex import CodexTarget
# ... 其余
IDE_REGISTRY = {
    "Cursor": CursorTarget, "Codex": CodexTarget, "OpenCode": OpenCodeTarget,
    "Trae": TraeTarget, "TraeCN": TraeCNTarget, "TraeSoloCN": TraeSoloCNTarget,
    "Claude": ClaudeTarget, "WorkBuddy": WorkBuddyTarget, "Qoder": QoderTarget,
    "OpenClaw": OpenClawTarget, "IDEA": IdeATarget, "Agents": AgentsTarget,
}
def get_ide(name, **kw):
    if name == "All":
        return [cls(**kw) for cls in IDE_REGISTRY.values()]
    return [IDE_REGISTRY[name](**kw)]
```

- [ ] **Step 8: 验证各 IDE 分发器可实例化**

Run: `.venv/bin/python -c "import sys; sys.path.insert(0,'scripts'); from lib.ide import IDE_REGISTRY; [c(Path('.')) for c in IDE_REGISTRY.values()]; print('all IDE targets OK')"`
Expected: `all IDE targets OK`

- [ ] **Step 9: Commit**

```bash
git add scripts/lib/ide/
git commit -m "feat(agentctl): 迁移 11 个 IDE 分发器到 lib/ide/"
```

---

## Task 7: 建 agentctl.py 统一入口

**Files:**
- Create: `scripts/agentctl.py`

- [ ] **Step 1: 写 argparse 子命令骨架**

```python
#!/usr/bin/env python3
"""agentctl - 统一 AI 智能体配置 CLI。

子命令：env / shell / generate / provider / sync / plugin / skill / setup
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.logging import *
from lib import llm, mcp, skills, plugins
from lib.ide import get_ide

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def cmd_generate(args):
    """从 llm.yaml + mcp.yaml 生成运行态配置。"""
    env_config = llm.load_split_env_config(PROJECT_ROOT)
    if args.provider:
        env_config = llm.switch_provider(env_config, args.provider, args.protocol, PROJECT_ROOT / "llm.yaml")
    flat = llm.flatten_env_config(env_config, llm.get_active_provider(env_config), llm.get_active_protocols(env_config))
    mcp.invoke_generate_step(flat, PROJECT_ROOT / "templates/...", PROJECT_ROOT / "...")  # 按原 init-env 逻辑
    mcp.invoke_mcp_generate_step(flat, PROJECT_ROOT / "mcp.yaml", PROJECT_ROOT / "agents/mcp/mcp.json")


def cmd_sync(args):
    """同步 rules/skills/mcp 到各 IDE。"""
    include = set(s.strip() for s in args.skills.split(",") if s.strip()) if args.skills.strip() else None
    if include is not None:
        hint(f"Skills filter: {len(include)} skill(s) selected")
    targets = get_ide(args.ide, project_root=PROJECT_ROOT, force=args.force, include_skills=include)
    for t in targets:
        info(f"==> {t.name}")
        t.run(PROJECT_ROOT / "agents/rules", PROJECT_ROOT / "agents/mcp/mcp.json", PROJECT_ROOT / ".agents/skills")
    print("[DONE]")


def cmd_plugin_install(args):
    """安装插件。"""
    plugins.install_plugin(Path(args.plugin_file), PROJECT_ROOT / ".agents/skills", use_symlink=args.symlink)


def cmd_plugin_list(args):
    plugins.list_plugins(PROJECT_ROOT / "agents/plugins")


def cmd_setup(args):
    """一键：generate → plugin install(全部) → sync。"""
    # generate
    ns = argparse.Namespace(provider=None, protocol=None)
    cmd_generate(ns)
    # install all plugins
    for p in (PROJECT_ROOT / "agents/plugins").glob("*.plugin.json"):
        plugins.install_plugin(p, PROJECT_ROOT / ".agents/skills", use_symlink=False)
    # sync
    ns2 = argparse.Namespace(ide="All", force=True, skills="")
    cmd_sync(ns2)


def main():
    parser = argparse.ArgumentParser(prog="agentctl", description="AI 智能体配置统一 CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_gen = sub.add_parser("generate", help="生成运行态配置")
    p_gen.add_argument("--provider"); p_gen.add_argument("--protocol")
    p_gen.set_defaults(func=cmd_generate)

    p_sync = sub.add_parser("sync", help="同步到 IDE")
    p_sync.add_argument("--ide", "-i", default="All")
    p_sync.add_argument("--force", "-f", action="store_true")
    p_sync.add_argument("--scope", default="llm,mcp,skill,plugin,rules")
    p_sync.add_argument("--skills", default="", help="逗号分隔技能名，仅同步这些")
    p_sync.add_argument("--target", "-t")
    p_sync.set_defaults(func=cmd_sync)

    p_pi = sub.add_parser("plugin", help="插件管理")
    p_pi_sub = p_pi.add_subparsers(dest="sub", required=True)
    p_ins = p_pi_sub.add_parser("install"); p_ins.add_argument("plugin_file"); p_ins.add_argument("--symlink", action="store_true")
    p_ins.set_defaults(func=cmd_plugin_install)
    p_lst = p_pi_sub.add_parser("list"); p_lst.set_defaults(func=cmd_plugin_list)

    p_setup = sub.add_parser("setup", help="一键全流程")
    p_setup.set_defaults(func=cmd_setup)

    # env / shell / provider / skill 子命令类似，按 spec §2 补全
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 补全 env / shell / provider / skill 子命令**

参照 `init-env.py:865-1004` 的 main 逻辑，补全：
- `cmd_env(args)`：调用 `llm.invoke_env_step(flat, args.scope, args.force)`
- `cmd_shell(args)`：调用 `llm.invoke_export_shell(flat)`
- `cmd_provider(args)`：调用 `llm.switch_provider` 并保存
- `cmd_skill_list(args)`：调用 `plugins.list_skills_from_csv`
- `cmd_skill_gen_plugin(args)`：调用 `plugins.generate_plugin_from_csv`

- [ ] **Step 3: 验证 agentctl 可运行**

Run: `.venv/bin/python scripts/agentctl.py --help`
Expected: 显示子命令列表（generate/sync/plugin/setup/env/...）

Run: `.venv/bin/python scripts/agentctl.py plugin list`
Expected: 列出 7 个插件

- [ ] **Step 4: 验证 sync 带白名单**

Run: `.venv/bin/python scripts/agentctl.py sync --ide Cursor --skills tdd,mermaid-sequence-from-flow`
Expected: 输出 `Skills filter: 2 skill(s) selected`，仅复制这 2 个技能到 `.cursor/skills/`

- [ ] **Step 5: Commit**

```bash
git add scripts/agentctl.py
git commit -m "feat(agentctl): 建统一 CLI 入口，子命令 generate/sync/plugin/setup"
```

---

## Task 8: 改造测试

**Files:**
- Modify: `tests/test_init_env.py` → 重命名/改为 `tests/test_agentctl.py`

- [ ] **Step 1: 改测试导入路径**

将 `tests/test_init_env.py` 中 `SCRIPT_PATH = .../init-env.py` 改为导入 `scripts/lib/llm.py`：

```python
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from lib import llm

# 原 init_env.flatten_env_config → llm.flatten_env_config
```

- [ ] **Step 2: 跑测试验证迁移正确**

Run: `.venv/bin/python -m pytest tests/test_agentctl.py -v`
Expected: 所有 `FlattenEnvConfigTests` 用例 PASS（行为不变）

- [ ] **Step 3: 新增 sync 白名单测试**

在 `tests/test_agentctl.py` 新增：

```python
import tempfile, shutil
from lib import skills

class SkillsFilterTests(unittest.TestCase):
    def test_include_skills_filters_copy(self):
        with tempfile.TemporaryDirectory() as td:
            src = pathlib.Path(td) / "src"; src.mkdir()
            (src / "keep").mkdir(); (src / "keep/SKILL.md").write_text("x")
            (src / "skip").mkdir(); (src / "skip/SKILL.md").write_text("y")
            dst = pathlib.Path(td) / "dst"
            skills.copy_skills_safe(src, dst, "test", True, include_skills={"keep"})
            self.assertTrue((dst / "keep").exists())
            self.assertFalse((dst / "skip").exists())
```

Run: `.venv/bin/python -m pytest tests/test_agentctl.py::SkillsFilterTests -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test(agentctl): 改造测试导入 lib，新增 skill 白名单过滤测试"
```

---

## Task 9: 更新调用方 + 删旧脚本 + 更新文档

**Files:**
- Modify: `install.sh` `install.cmd` `init-env.cmd` `run.sh` `app.py` `tools/config_server.py` `README.md` `AGENTS.md`
- Delete: `scripts/init-env.py` `scripts/init-ide.py` `scripts/plugin-manager.py`

- [ ] **Step 1: 更新 install.sh**

将 `install.sh:8-43` 的多行命令替换为：
```bash
python3 scripts/agentctl.py setup
```
删除 `plugin-manager.py install` × N + `init-env.py -a Generate` + `init-ide.py -i All -f`。

- [ ] **Step 2: 更新 install.cmd**

将 `install.cmd` 同样替换为 `python scripts\agentctl.py setup`。

- [ ] **Step 3: 更新 init-env.cmd**

`init-env.cmd:1` 改为：`python scripts/agentctl.py generate`

- [ ] **Step 4: 更新 config_server.py 的 _script_run_shell_cmd 调用**

在 `tools/config_server.py` 的 `/api/init-ide` 路由，将 `_script_run_shell_cmd("init-ide", cmd_args)` 改为：
```python
cmd_args = ["sync", "--ide", ide, "--force", "--scope", scope_arg]
if safe_skills:
    cmd_args += ["--skills", safe_skills]
cmd = _script_run_shell_cmd("agentctl", cmd_args)
```

- [ ] **Step 5: 更新 app.py / run.sh（如有 init-ide 调用）**

搜索 `app.py` 和 `run.sh` 中的 `init-ide` / `init-env` / `plugin-manager` 引用，替换为 `agentctl` 对应子命令。

- [ ] **Step 6: 删除旧脚本**

```bash
git rm scripts/init-env.py scripts/init-ide.py scripts/plugin-manager.py
```

- [ ] **Step 7: 更新 README.md**

将 `README.md:32-33` 的脚本说明表、`45-78` 的 init-env 用法、`209-239` 的 init-ide 用法，替换为 agentctl 子命令用法：
- `python scripts/agentctl.py generate`（原 init-env Generate）
- `python scripts/agentctl.py sync -i Cursor -f`（原 init-ide -i Cursor -f）
- `python scripts/agentctl.py plugin install <file>`（原 plugin-manager install）
- `python scripts/agentctl.py setup`（原 install.sh 全流程）

- [ ] **Step 8: 更新 AGENTS.md**

更新 `AGENTS.md:58`（init-env.py 引用）、`103-114`（init-ide.py 引用）、`192-202`（plugin-manager.py 引用），改为 agentctl 对应说明。脚本路径引用统一为 `scripts/agentctl.py`。

- [ ] **Step 9: 端到端验证**

Run: `.venv/bin/python scripts/agentctl.py setup`
Expected: 全流程成功——生成 mcp.json、安装插件、同步所有 IDE，输出 `[DONE]`

Run: 启动 UI 服务，在 Skills 配置页勾选技能点"同步到 IDE"
Expected: 后端日志显示 `agentctl sync --skills=...`，仅同步勾选技能

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "refactor(agentctl): 更新调用方，删除旧脚本，更新文档"
```

---

## Self-Review 结果

**Spec 覆盖：**
- §1 背景目标：Task 1-9 整体覆盖 ✓
- §2 子命令设计：Task 7 实现 generate/sync/plugin/setup/env/shell/provider/skill ✓
- §3 模块结构：Task 1-6 建全部 lib 模块 ✓
- §4 数据流：Task 7 cmd_setup 编排 generate→plugin→sync ✓
- §5 兼容性迁移：Task 9 更新全部调用方 + 删旧脚本 ✓
- §6 测试：Task 8 改造 + 新增 ✓
- §7 风险对策：分阶段（Task 1-9）+ 先迁移后验证 ✓

**占位符扫描：** Task 7 Step 1 的 cmd_generate 中 `templates/...` 路径需在实现时对照 init-env.py 的真实模板路径填入。其余无 TBD/TODO。

**类型一致性：** `include_skills` 参数在 skills.py / ide/base.py / agentctl.py 一致（`set | None`）；`IdeTarget.run` 签名在 base.py 与 agentctl.py cmd_sync 调用一致。
