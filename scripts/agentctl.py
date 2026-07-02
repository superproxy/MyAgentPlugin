#!/usr/bin/env python3
"""agentctl - AI 智能体配置统一 CLI。

合并 init-env.py + init-ide.py + plugin-manager.py 为单一入口。

子命令：
  generate  生成运行态配置（mcp.json + 各 IDE 模板配置）
  sync      同步 rules/mcp/skills 到各 IDE
  plugin    插件管理（install/list）
  skill     技能管理（list-skills/generate-plugin from CSV）
  env       设置环境变量（process/user 作用域）
  shell     导出 shell 环境变量语句
  provider  切换活跃 LLM provider/protocol
  setup     一键全流程（generate + plugin install all + sync）

用法示例：
  python scripts/agentctl.py generate
  python scripts/agentctl.py sync --ide Cursor --force
  python scripts/agentctl.py sync --ide All --skills tdd,mermaid
  python scripts/agentctl.py plugin install agents/plugins/core.plugin.yaml
  python scripts/agentctl.py plugin list
  python scripts/agentctl.py provider openai
  python scripts/agentctl.py setup
"""
import argparse
import sys
from pathlib import Path

# 确保 scripts/ 在 sys.path 中，以便导入 lib 包
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.logging import (
    COLOR_CYAN, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_DARKGRAY, COLOR_RESET,
    info, warn, error, hint, header,
)
from lib import llm, mcp, skills, plugins
from lib.ide import get_ide, IDE_REGISTRY

PROJECT_ROOT = Path(__file__).resolve().parents[1]


# ============================================================
# 子命令实现
# ============================================================

def cmd_generate(args):
    """生成运行态配置：mcp.json + 各 IDE 模板配置（opencode/codex/claude/proxy）。"""
    env_config = llm.load_split_env_config(PROJECT_ROOT)

    # 切换 provider/protocol（如指定）
    if args.provider or args.protocol:
        if args.provider:
            env_config = llm.switch_provider(
                env_config, args.provider, args.protocol,
                PROJECT_ROOT / "llm.yaml"
            )
        elif args.protocol:
            active = llm.get_active_provider(env_config)
            available = llm.list_protocols(env_config, active)
            current = llm.get_active_protocols(env_config)
            new_protocols = list(set(current + [args.protocol]))
            new_protocols = [p for p in new_protocols if p in available]
            if not new_protocols:
                new_protocols = [args.protocol] if args.protocol in available else available
            env_config["llm"]["_active_protocol"] = "|".join(new_protocols)
            llm.save_split_env_config(PROJECT_ROOT, env_config)
            print(f"{COLOR_GREEN}[OK] Protocol updated: {active}/{'|'.join(new_protocols)}{COLOR_RESET}")

    active_provider = llm.get_active_provider(env_config)
    active_protocols = llm.get_active_protocols(env_config)
    flat_config = llm.flatten_env_config(env_config, active_provider, active_protocols)

    header("Generate Runtime Configs")
    print(f"  {COLOR_GREEN}Active LLM: {active_provider}/{'|'.join(active_protocols)}{COLOR_RESET}")
    print()

    # 1. 生成 mcp.json（从 mcp.yaml + plugins/*.plugin.yaml 合并 mcpServers）
    mcp_yaml_file = PROJECT_ROOT / "mcp.yaml"
    mcp_output = PROJECT_ROOT / "agents" / "mcp" / "mcp.json"
    plugins_dir = PROJECT_ROOT / "agents" / "plugins"
    mcp.invoke_mcp_generate_step(flat_config, mcp_yaml_file, mcp_output, plugins_dir=plugins_dir)

    # 2. 生成 opencode.json（从模板 + 注入模型）
    opencode_template = PROJECT_ROOT / "ide" / "opencode" / "opencode.template.json"
    opencode_output = PROJECT_ROOT / "ide" / "opencode" / "opencode.json"
    if opencode_template.exists():
        mcp.invoke_generate_step(flat_config, opencode_template, opencode_output)
        mcp._inject_opencode_models(opencode_output, env_config)

    # 3. 生成 codex auth.json + config.toml（从模板）
    codex_auth_template = PROJECT_ROOT / "ide" / "codex" / "auth.template.json"
    codex_auth_output = PROJECT_ROOT / "ide" / "codex" / "auth.json"
    if codex_auth_template.exists():
        mcp.invoke_generate_step(flat_config, codex_auth_template, codex_auth_output)

    codex_config_template = PROJECT_ROOT / "ide" / "codex" / "config.template.toml"
    codex_config_output = PROJECT_ROOT / "ide" / "codex" / "config.toml"
    if codex_config_template.exists():
        mcp.invoke_generate_step(flat_config, codex_config_template, codex_config_output)

    # 4. 生成 claude settings.json（从模板）
    claude_template = PROJECT_ROOT / "ide" / "claude" / "settings.template.json"
    claude_output = PROJECT_ROOT / "ide" / "claude" / "settings.json"
    if claude_template.exists():
        mcp.invoke_generate_step(flat_config, claude_template, claude_output)

    # 5. 生成 proxy config.yaml（从模板，不剪枝）
    proxy_template = PROJECT_ROOT / "proxy" / "config.template.yaml"
    proxy_output = PROJECT_ROOT / "proxy" / "config.yaml"
    if proxy_template.exists():
        mcp.invoke_generate_step(flat_config, proxy_template, proxy_output, prune=False)

    print(f"{COLOR_CYAN}========================================{COLOR_RESET}")
    print(f"{COLOR_CYAN}  Generate Done.{COLOR_RESET}")
    print(f"{COLOR_CYAN}========================================{COLOR_RESET}")


def cmd_sync(args):
    """同步 rules/mcp/skills 到各 IDE。"""
    # 解析 scope
    scope = set(s.strip() for s in args.scope.split(",") if s.strip())
    # 解析 skills 白名单
    include = None
    if args.skills and args.skills.strip():
        include = set(s.strip() for s in args.skills.split(",") if s.strip())
        hint(f"Skills filter: {len(include)} skill(s) selected")

    ide_name = args.ide
    targets = get_ide(ide_name, project_root=PROJECT_ROOT, force=args.force,
                      include_skills=include, scope=scope)

    source_rules = PROJECT_ROOT / "agents" / "rules"
    source_mcp = PROJECT_ROOT / "agents" / "mcp" / "mcp.json"
    source_skills = PROJECT_ROOT / "agents" / "skills"
    source_agents_md = PROJECT_ROOT / "AGENTS.md"

    for t in targets:
        t.run(source_rules, source_mcp, source_skills, source_agents_md)

    print(f"\n{COLOR_GREEN}[DONE] Synced to {len(targets)} IDE(s){COLOR_RESET}")


def cmd_env(args):
    """设置环境变量（process/user 作用域）。"""
    env_config = llm.load_split_env_config(PROJECT_ROOT)
    active_provider = llm.get_active_provider(env_config)
    active_protocols = llm.get_active_protocols(env_config)
    flat_config = llm.flatten_env_config(env_config, active_provider, active_protocols)
    llm.invoke_env_step(flat_config, args.scope, args.force)


def cmd_shell(args):
    """导出 shell 环境变量语句。"""
    env_config = llm.load_split_env_config(PROJECT_ROOT, silent=True)
    active_provider = llm.get_active_provider(env_config)
    active_protocols = llm.get_active_protocols(env_config)
    flat_config = llm.flatten_env_config(env_config, active_provider, active_protocols)
    llm.invoke_export_shell(flat_config)


def cmd_provider(args):
    """切换活跃 LLM provider/protocol。"""
    env_config = llm.load_split_env_config(PROJECT_ROOT)
    providers = llm.list_providers(env_config)

    if not args.name and not args.protocol:
        # 无参数：显示当前状态
        active = llm.get_active_provider(env_config)
        active_protocols = llm.get_active_protocols(env_config)
        print(f"{COLOR_CYAN}Current: {active}/{'|'.join(active_protocols)}{COLOR_RESET}")
        print(f"{COLOR_CYAN}Available providers: {', '.join(providers)}{COLOR_RESET}")
        for p in providers:
            protos = llm.list_protocols(env_config, p)
            print(f"  - {p}: {', '.join(protos)}")
        return

    if args.name:
        env_config = llm.switch_provider(
            env_config, args.name, args.protocol,
            PROJECT_ROOT / "llm.yaml"
        )
    elif args.protocol:
        active = llm.get_active_provider(env_config)
        available = llm.list_protocols(env_config, active)
        current = llm.get_active_protocols(env_config)
        new_protocols = list(set(current + [args.protocol]))
        new_protocols = [p for p in new_protocols if p in available]
        if not new_protocols:
            new_protocols = [args.protocol] if args.protocol in available else available
        env_config["llm"]["_active_protocol"] = "|".join(new_protocols)
        llm.save_split_env_config(PROJECT_ROOT, env_config)
        print(f"{COLOR_GREEN}[OK] Protocol updated: {active}/{'|'.join(new_protocols)}{COLOR_RESET}")


def cmd_plugin_install(args):
    """安装插件。"""
    plugin_path = Path(args.plugin_file).resolve()
    env_path = PROJECT_ROOT / args.env_file
    plugins.install_plugin(
        plugin_path, env_path, PROJECT_ROOT,
        dry_run=args.dry_run, use_symlink=args.symlink
    )


def cmd_plugin_list(args):
    """列出可用插件。"""
    plugins_dir = PROJECT_ROOT / args.plugins_dir
    plugins.list_plugins(plugins_dir)


def cmd_skill_list(args):
    """从 skills-index.csv 列出所有技能。"""
    csv_path = PROJECT_ROOT / args.csv
    plugins.list_skills_from_csv(csv_path)


def cmd_skill_gen_plugin(args):
    """根据 skills-index.csv 生成插件配置。"""
    csv_path = PROJECT_ROOT / args.csv
    output_path = PROJECT_ROOT / args.output
    plugins.generate_plugin_from_csv(
        csv_path, output_path, args.name, args.description,
        category_filter=args.category
    )


def cmd_setup(args):
    """一键全流程：plugin install all → generate → sync。

    顺序说明（对应 plugin 工作流程）：
      1. plugin install all
         - 执行各插件的 install 脚本
         - 下载 skill 到 agents/skills/
         - 合并 envVars 到 llm.yaml
         （plugin.yaml 的 mcpServers 不在此阶段合并，保持 mcp.yaml 纯净）
      2. generate
         - 同时读取 mcp.yaml + agents/plugins/*.plugin.yaml 的 mcpServers，合并生成 mcp.json
         - 生成各 IDE 模板配置（opencode/codex/claude）
      3. sync All
         - 同步 mcp.json 到各 IDE（mcp 同步）
         - 同步 skills 到各 IDE（skill 同步）
    """
    header("Setup: Full Pipeline")

    # Step 1: 安装所有插件（执行 install 脚本 → 下载 skill → 合并 envVars）
    print(f"\n{COLOR_CYAN}==> Step 1/3: Install all plugins{COLOR_RESET}")
    plugins_dir = PROJECT_ROOT / "agents" / "plugins"
    if plugins_dir.exists():
        for p in sorted(plugins_dir.glob("*.plugin.yaml")):
            print(f"\n{COLOR_CYAN}--- Installing: {p.name} ---{COLOR_RESET}")
            plugins.install_plugin(
                p, PROJECT_ROOT / "llm.yaml", PROJECT_ROOT,
                dry_run=False, use_symlink=False
            )
    else:
        warn(f"Plugins dir not found: {plugins_dir}")

    # Step 2: 生成运行态配置（基于合并后的 llm.yaml + mcp.yaml）
    print(f"\n{COLOR_CYAN}==> Step 2/3: Generate runtime configs{COLOR_RESET}")
    ns_gen = argparse.Namespace(provider=None, protocol=None)
    cmd_generate(ns_gen)

    # Step 3: 同步到所有 IDE（mcp 同步 + skill 同步）
    print(f"\n{COLOR_CYAN}==> Step 3/3: Sync to all IDEs{COLOR_RESET}")
    ns_sync = argparse.Namespace(
        ide="All", force=True, scope="llm,mcp,skill,plugin,rules", skills=""
    )
    cmd_sync(ns_sync)

    print(f"\n{COLOR_GREEN}========================================{COLOR_RESET}")
    print(f"{COLOR_GREEN}  Setup Complete!{COLOR_RESET}")
    print(f"{COLOR_GREEN}========================================{COLOR_RESET}")


# ============================================================
# argparse 主入口
# ============================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentctl",
        description="AI 智能体配置统一 CLI（合并 init-env + init-ide + plugin-manager）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # generate
    p_gen = sub.add_parser("generate", help="生成运行态配置（mcp.json + IDE 模板）")
    p_gen.add_argument("--provider", default=None,
                       help="切换 LLM provider（如 openai/anthropic/deepseek）")
    p_gen.add_argument("--protocol", default=None, choices=["openai", "anthropic"],
                       help="切换 LLM 协议")
    p_gen.set_defaults(func=cmd_generate)

    # sync
    p_sync = sub.add_parser("sync", help="同步 rules/mcp/skills 到 IDE")
    p_sync.add_argument("--ide", "-i", default="All",
                        help=f"目标 IDE（默认 All；可选: {', '.join(IDE_REGISTRY.keys())}）")
    p_sync.add_argument("--force", "-f", action="store_true",
                        help="强制覆盖已存在文件")
    p_sync.add_argument("--scope", default="llm,mcp,skill,rules",
                        help="同步范围，逗号分隔（默认 llm,mcp,skill,rules）")
    p_sync.add_argument("--skills", default="",
                        help="技能白名单，逗号分隔（仅同步这些技能）")
    p_sync.set_defaults(func=cmd_sync)

    # env
    p_env = sub.add_parser("env", help="设置环境变量")
    p_env.add_argument("--scope", choices=["process", "user"], default="process",
                       help="作用域：process（当前会话）或 user（持久）")
    p_env.add_argument("--force", action="store_true", help="跳过确认")
    p_env.set_defaults(func=cmd_env)

    # shell
    p_shell = sub.add_parser("shell", help="导出 shell 环境变量语句")
    p_shell.set_defaults(func=cmd_shell)

    # provider
    p_prov = sub.add_parser("provider", help="切换/查看活跃 LLM provider")
    p_prov.add_argument("name", nargs="?", default=None,
                        help="provider 名称（省略则查看当前状态）")
    p_prov.add_argument("--protocol", default=None, choices=["openai", "anthropic"],
                        help="同时切换协议")
    p_prov.set_defaults(func=cmd_provider)

    # plugin
    p_plugin = sub.add_parser("plugin", help="插件管理")
    p_plugin_sub = p_plugin.add_subparsers(dest="sub", required=True)

    p_ins = p_plugin_sub.add_parser("install", help="安装插件")
    p_ins.add_argument("plugin_file", help="插件 .plugin.yaml 文件路径")
    p_ins.add_argument("--env-file", default="llm.yaml", help="环境变量文件（默认 llm.yaml）")
    p_ins.add_argument("--dry-run", action="store_true", help="模拟运行")
    p_ins.add_argument("--symlink", action="store_true",
                       help="使用 symlink 安装 skill（默认 --copy）")
    p_ins.set_defaults(func=cmd_plugin_install)

    p_lst = p_plugin_sub.add_parser("list", help="列出可用插件")
    p_lst.add_argument("--plugins-dir", default="agents/plugins",
                       help="插件目录（默认 agents/plugins）")
    p_lst.set_defaults(func=cmd_plugin_list)

    # skill
    p_skill = sub.add_parser("skill", help="技能管理（基于 skills-index.csv）")
    p_skill_sub = p_skill.add_subparsers(dest="sub", required=True)

    p_sl = p_skill_sub.add_parser("list", help="列出 CSV 中所有技能")
    p_sl.add_argument("--csv", default="agents/skills/skills-index.csv",
                      help="技能映射文件（默认 agents/skills/skills-index.csv）")
    p_sl.set_defaults(func=cmd_skill_list)

    p_sg = p_skill_sub.add_parser("gen-plugin", help="根据 CSV 生成插件配置")
    p_sg.add_argument("--csv", default="agents/skills/skills-index.csv",
                      help="技能映射文件（默认 agents/skills/skills-index.csv）")
    p_sg.add_argument("--output", default="agents/plugins/generated.plugin.yaml",
                      help="输出文件路径")
    p_sg.add_argument("--name", default="generated", help="插件名称")
    p_sg.add_argument("--description", default="", help="插件描述")
    p_sg.add_argument("--category", default=None, help="按分类过滤")
    p_sg.set_defaults(func=cmd_skill_gen_plugin)

    # setup
    p_setup = sub.add_parser("setup", help="一键全流程：generate + plugin install all + sync")
    p_setup.set_defaults(func=cmd_setup)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
