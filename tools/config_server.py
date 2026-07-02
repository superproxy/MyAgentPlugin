#!/usr/bin/env python3
"""
MyAgentPlugin 配置工具 Web UI 后端

启动: python tools/config_server.py
访问: http://127.0.0.1:5000
依赖: flask, pyyaml, requests
"""

import argparse
import csv
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any, Dict, List, Optional

def _resolve_project_root() -> Path:
    """Frozen-aware 项目根定位。
    - dev: 仓库根（tools/config_server.py 的上两级）
    - frozen (PyInstaller onedir): exe 所在目录（_MEIPASS == exe dir，可写）
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


PROJECT_ROOT = _resolve_project_root()
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _script_run_cmd(script_name: str, args: list) -> list:
    """构建运行 scripts/ 下脚本的命令列表（frozen-aware）。
    - dev: [python, scripts/<name>.py, *args]
    - frozen: [exe, --run, <name>, *args]（由 app.py 的 --run 派发器执行）
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, "--run", script_name, *args]
    return [sys.executable, str(SCRIPTS_DIR / f"{script_name}.py"), *args]


def _script_run_shell_cmd(script_name: str, args: list) -> str:
    """构建 shell 字符串形式的脚本运行命令（frozen-aware），用于 _stream_process。"""
    parts = _script_run_cmd(script_name, args)
    # 给含空格/特殊字符的路径加引号
    return " ".join(f'"{p}"' if (" " in p or '"' in p) else p for p in parts)

try:
    from flask import Flask, Response, jsonify, request, send_file, stream_with_context
except ImportError:
    print("[ERROR] Flask 未安装。请执行: pip install flask")
    sys.exit(1)

try:
    import yaml
except ImportError:
    print("[ERROR] PyYAML 未安装。请执行: pip install pyyaml")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("[ERROR] requests 未安装。请执行: pip install requests")
    sys.exit(1)


def _load_script_module(module_name: str, file_path: Path):
    """加载 scripts/ 目录下含连字符的脚本作为模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载模块: {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# 从 lib/ 公共库导入（替代旧脚本的 importlib 加载）
sys.path.insert(0, str(SCRIPTS_DIR))
from lib.config_io import load_env_config_file, save_env_config_file
from lib.skills import build_install_command, parse_shorthand
from lib.plugins import install_plugin, update_env_file

app = Flask(__name__, static_folder=None)

# ============================================================
# 路径常量
# ============================================================
ENV_EXAMPLE = PROJECT_ROOT / "env.example.yaml"
ENV_FILE = PROJECT_ROOT / "env.yaml"
# 新拆分：env.yaml → llm.yaml + mcp.yaml
LLM_FILE = PROJECT_ROOT / "llm.yaml"
MCP_CONFIG_FILE = PROJECT_ROOT / "mcp.yaml"
# 拆分后的示例模板（可安全提交）
LLM_EXAMPLE = PROJECT_ROOT / "llm-env-example.yaml"
MCP_CONFIG_EXAMPLE = PROJECT_ROOT / "mcp-env-example.yaml"
MCP_TEMPLATE = PROJECT_ROOT / "agents" / "mcp" / "mcp.template.json"
PLUGINS_DIR = PROJECT_ROOT / "agents" / "plugins"
SKILLS_CSV = PROJECT_ROOT / "agents" / "skills" / "skills-index.csv"
AGENTS_SKILLS_CACHE = PROJECT_ROOT / "agents" / "skills"
DOT_AGENTS_SKILLS = PROJECT_ROOT / ".agents" / "skills"

# env.yaml 中属于 llm.yaml 的顶层键（其余归 mcp.yaml 的只有 mcp）
LLM_TOP_KEYS = ["llm", "embedding", "tts", "asr", "vision", "misc"]

# 外部市场端点
MODELSCOPE_SKILLS_API = "https://www.modelscope.cn/openapi/v1/skills"
MODELSCOPE_MCP_LIST_API = "https://www.modelscope.cn/openapi/v1/mcp/servers"
MODELSCOPE_MCP_DETAIL_API = "https://www.modelscope.cn/openapi/v1/mcp/servers/{owner}/{name}"
SKILLS_SH_API = "https://skills.sh/api/search"

HTTP_TIMEOUT = 15  # 外部 API 超时秒数


# ============================================================
# 通用工具
# ============================================================
def _ensure_llm_file() -> Path:
    """确保 llm.yaml 存在。
    优先级：
      1. llm.yaml 已存在 → 直接返回
      2. llm-env-example.yaml 存在 → 直接复制（推荐方式）
      3. env.yaml / env.example.yaml 存在 → 从中拆出 llm/embedding/tts/asr/vision/misc 部分（向后兼容）
      4. 创建空模板
    """
    if LLM_FILE.exists():
        return LLM_FILE
    # 优先使用拆分后的示例文件
    if LLM_EXAMPLE.exists():
        try:
            data = load_env_config_file(LLM_EXAMPLE)
            save_env_config_file(LLM_FILE, data)
            return LLM_FILE
        except Exception:
            pass
    # 向后兼容：从 env.yaml / env.example.yaml 拆分
    src = ENV_FILE if ENV_FILE.exists() else (ENV_EXAMPLE if ENV_EXAMPLE.exists() else None)
    if src and src.exists():
        try:
            data = load_env_config_file(src)
            llm_data = {k: v for k, v in (data or {}).items() if k in LLM_TOP_KEYS}
            save_env_config_file(LLM_FILE, llm_data)
            return LLM_FILE
        except Exception:
            pass
    save_env_config_file(LLM_FILE, {"llm": {"_active_provider": "", "_active_protocol": "openai|anthropic"}})
    return LLM_FILE


def _ensure_mcp_config_file() -> Path:
    """确保 mcp.yaml 存在（统一存放 mcpServers 服务定义 + mcp 密钥）。
    优先级：
      1. mcp.yaml 已存在 → 直接返回
      2. mcp-env-example.yaml 存在 → 直接复制（推荐方式）
      3. env.yaml / env.example.yaml 存在 → 从中拆出 mcp 部分（向后兼容）
      4. 创建空模板
    """
    if MCP_CONFIG_FILE.exists():
        return MCP_CONFIG_FILE
    # 优先使用拆分后的示例文件
    if MCP_CONFIG_EXAMPLE.exists():
        try:
            data = load_env_config_file(MCP_CONFIG_EXAMPLE)
            save_env_config_file(MCP_CONFIG_FILE, data)
            return MCP_CONFIG_FILE
        except Exception:
            pass
    # 向后兼容：从 env.yaml / env.example.yaml 拆分
    src = ENV_FILE if ENV_FILE.exists() else (ENV_EXAMPLE if ENV_EXAMPLE.exists() else None)
    if src and src.exists():
        try:
            data = load_env_config_file(src)
            mcp_data = {"mcp": (data or {}).get("mcp", {})}
            save_env_config_file(MCP_CONFIG_FILE, mcp_data)
            return MCP_CONFIG_FILE
        except Exception:
            pass
    save_env_config_file(MCP_CONFIG_FILE, {"mcp": {}})
    return MCP_CONFIG_FILE


def _load_mcp_yaml_full() -> dict:
    """加载 mcp.yaml 全量数据（含 mcpServers + mcp），并从 mcp.template.json 迁移。"""
    path = _ensure_mcp_config_file()
    try:
        data = load_env_config_file(path)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    # 迁移：若 mcp.yaml 没有 mcpServers，但 mcp.template.json 存在，则合并进来
    if "mcpServers" not in data and MCP_TEMPLATE.exists():
        try:
            tpl = _read_json(MCP_TEMPLATE)
            if isinstance(tpl.get("mcpServers"), dict):
                data["mcpServers"] = tpl["mcpServers"]
                save_env_config_file(path, data)
        except Exception:
            pass
    if "mcpServers" not in data:
        data["mcpServers"] = {}
    if "mcp" not in data or not isinstance(data.get("mcp"), dict):
        data["mcp"] = {}
    return data


def _save_mcp_yaml_full(data: dict) -> None:
    """保存 mcp.yaml 全量数据。"""
    path = _ensure_mcp_config_file()
    save_env_config_file(path, data)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _stream_process(cmd: str, cwd: Optional[Path] = None):
    """运行子进程并以生成器形式逐行产出日志（SSE 格式）"""
    yield f"data: [CMD] {cmd}\n\n"
    try:
        proc = subprocess.Popen(
            cmd,
            shell=True,
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="ignore",
            bufsize=1,
        )
        try:
            for line in iter(proc.stdout.readline, ""):
                if line:
                    # SSE 每行一条
                    yield f"data: {line.rstrip()}\n\n"
            proc.wait(timeout=300)
            yield f"data: [EXIT] returncode={proc.returncode}\n\n"
        except subprocess.TimeoutExpired:
            proc.kill()
            yield "data: [TIMEOUT] 进程超时被终止（>300s）\n\n"
    except Exception as e:
        yield f"data: [ERROR] {e}\n\n"
    yield "data: [DONE]\n\n"


# ============================================================
# 首页
# ============================================================
@app.route("/")
def index():
    return send_file(PROJECT_ROOT / "tools" / "config_ui.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    """提供本地静态资源（Vue / Tailwind JIT 等），避免依赖外部 CDN。"""
    from flask import send_from_directory
    return send_from_directory(PROJECT_ROOT / "tools" / "static", filename)


# ============================================================
# Env 配置 API（向后兼容：从 llm.yaml + mcp.yaml 合并读写）
# ============================================================
@app.route("/api/env", methods=["GET"])
def get_env():
    """返回合并后的配置（llm.yaml + mcp.yaml）。"""
    try:
        llm_data = load_env_config_file(_ensure_llm_file())
        mcp_data = load_env_config_file(_ensure_mcp_config_file())
        merged = {}
        for k in LLM_TOP_KEYS:
            if k in llm_data:
                merged[k] = llm_data[k]
        merged["mcp"] = (mcp_data or {}).get("mcp", {})
        if isinstance(llm_data, dict) and "_description" in llm_data:
            merged["_description"] = llm_data["_description"]
        return jsonify({"ok": True, "data": merged, "path": "llm.yaml + mcp.yaml"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/env", methods=["POST"])
def save_env():
    """向后兼容：将合并配置拆分保存到 llm.yaml + mcp.yaml。"""
    body = request.get_json(force=True)
    data = body.get("data")
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "data 必须是对象"}), 400
    try:
        llm_data = {k: v for k, v in data.items() if k in LLM_TOP_KEYS}
        if "_description" in data:
            llm_data["_description"] = data["_description"]
        mcp_data = {"mcp": data.get("mcp", {})}
        save_env_config_file(_ensure_llm_file(), llm_data)
        save_env_config_file(_ensure_mcp_config_file(), mcp_data)
        return jsonify({"ok": True, "path": "llm.yaml + mcp.yaml"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# LLM Provider 配置 API (llm.yaml)
# ============================================================
@app.route("/api/llm", methods=["GET"])
def get_llm():
    path = _ensure_llm_file()
    try:
        data = load_env_config_file(path)
        return jsonify({
            "ok": True,
            "data": data,
            "path": str(path.relative_to(PROJECT_ROOT)),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/llm", methods=["POST"])
def save_llm():
    body = request.get_json(force=True)
    data = body.get("data")
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "data 必须是对象"}), 400
    try:
        path = _ensure_llm_file()
        save_env_config_file(path, data)
        return jsonify({"ok": True, "path": str(path.relative_to(PROJECT_ROOT))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# MCP 配置 API (mcp.yaml - 密钥层)
# ============================================================
@app.route("/api/mcp-config", methods=["GET"])
def get_mcp_config():
    path = _ensure_mcp_config_file()
    try:
        full = _load_mcp_yaml_full()
        return jsonify({
            "ok": True,
            "data": {"mcp": full.get("mcp", {})},
            "path": str(path.relative_to(PROJECT_ROOT)),
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mcp-config", methods=["POST"])
def save_mcp_config():
    body = request.get_json(force=True)
    data = body.get("data")
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "data 必须是对象"}), 400
    try:
        full = _load_mcp_yaml_full()
        full["mcp"] = data.get("mcp", {})
        _save_mcp_yaml_full(full)
        return jsonify({"ok": True, "path": str(MCP_CONFIG_FILE.relative_to(PROJECT_ROOT))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mcp-config/key", methods=["POST"])
def add_mcp_config_key():
    """添加单个 MCP 密钥条目。Body: {key, value=''}"""
    body = request.get_json(force=True)
    key = (body.get("key") or "").strip()
    if not key:
        return jsonify({"ok": False, "error": "key 必填"}), 400
    try:
        full = _load_mcp_yaml_full()
        if not isinstance(full.get("mcp"), dict):
            full["mcp"] = {}
        full["mcp"][key] = body.get("value", "")
        _save_mcp_yaml_full(full)
        return jsonify({"ok": True, "key": key})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mcp-config/key/<key>", methods=["DELETE"])
def delete_mcp_config_key(key):
    try:
        full = _load_mcp_yaml_full()
        if isinstance(full.get("mcp"), dict) and key in full["mcp"]:
            del full["mcp"][key]
            _save_mcp_yaml_full(full)
            return jsonify({"ok": True})
        return jsonify({"ok": False, "error": f"未找到 key: {key}"}), 404
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# Skills API
# ============================================================
@app.route("/api/skills/local", methods=["GET"])
def list_local_skills():
    if not SKILLS_CSV.exists():
        return jsonify({"ok": True, "data": []})
    rows = []
    with open(SKILLS_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return jsonify({"ok": True, "data": rows})


@app.route("/api/skills/installed", methods=["GET"])
def list_installed_skills():
    installed = []
    if DOT_AGENTS_SKILLS.exists():
        for d in DOT_AGENTS_SKILLS.iterdir():
            if d.is_dir() and (d / "SKILL.md").exists():
                installed.append({
                    "name": d.name,
                    "path": str(d.relative_to(PROJECT_ROOT)),
                    "skill_md_exists": True,
                })
    return jsonify({"ok": True, "data": installed})


@app.route("/api/skills/search", methods=["GET"])
def search_skills():
    """聚合搜索: source=modelscope|skillssh|all"""
    q = request.args.get("q", "").strip()
    source = request.args.get("source", "all")
    if not q:
        return jsonify({"ok": False, "error": "缺少 q 参数"}), 400

    results = []
    errors = []

    if source in ("modelscope", "all"):
        try:
            resp = requests.get(
                MODELSCOPE_SKILLS_API,
                params={"page_number": 1, "page_size": 30, "search": q},
                timeout=HTTP_TIMEOUT,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data") or payload
            items = data.get("skills") or data.get("list") or []
            for it in items:
                results.append({
                    "source": "modelscope",
                    "name": it.get("name") or it.get("skill_name") or "",
                    "description": it.get("description") or it.get("chinese_description") or "",
                    "install_command": it.get("install_command") or "",
                    "install_count": it.get("install_count") or it.get("download_count") or 0,
                    "author": it.get("owner") or it.get("author") or "",
                    "license": it.get("license") or "",
                    "raw": it,
                })
        except Exception as e:
            errors.append(f"ModelScope: {e}")

    if source in ("skillssh", "all"):
        try:
            resp = requests.get(
                SKILLS_SH_API,
                params={"q": q},
                timeout=HTTP_TIMEOUT,
            )
            resp.raise_for_status()
            payload = resp.json()
            items = payload.get("skills") or payload.get("data") or []
            if isinstance(items, dict):
                items = list(items.values())
            for it in items:
                if not isinstance(it, dict):
                    continue
                results.append({
                    "source": "skillssh",
                    "name": it.get("name") or it.get("title") or "",
                    "description": it.get("description") or "",
                    "install_command": f"npx skills add {it.get('source', '')}".strip(),
                    "install_count": it.get("install_count") or 0,
                    "author": it.get("owner") or "",
                    "license": "",
                    "raw": it,
                })
        except Exception as e:
            errors.append(f"skills.sh: {e}")

    return jsonify({"ok": True, "data": results, "errors": errors})


@app.route("/api/skills/install", methods=["GET"])
def install_skill_sse():
    """SSE: 流式安装 skill。
    Query: source=owner/repo[&skill=name] 或 command=完整 npx 命令
    """
    source = request.args.get("source", "").strip()
    skill = request.args.get("skill", "").strip()
    command = request.args.get("command", "").strip()

    if command:
        cmd = command
        skill_name = skill or "custom"
    else:
        if not source:
            return Response("data: [ERROR] 缺少 source 或 command\n\n", mimetype="text/event-stream")
        # 构造 npx skills add 命令（强制 --copy）
        parsed_source, parsed_skill = parse_shorthand(source)
        effective_source = parsed_source or source
        effective_skill = skill or parsed_skill
        if effective_skill:
            cmd = f"npx skills add {effective_source} --skill {effective_skill} --copy -y"
        else:
            cmd = f"npx skills add {effective_source} --copy -y"
        skill_name = effective_skill or effective_source

    return Response(
        stream_with_context(_stream_process(cmd, cwd=PROJECT_ROOT)),
        mimetype="text/event-stream",
    )


@app.route("/api/skills/<name>", methods=["DELETE"])
def uninstall_skill(name):
    target = DOT_AGENTS_SKILLS / name
    if not target.exists() or not target.is_dir():
        return jsonify({"ok": False, "error": f"未找到技能: {name}"}), 404
    # 防路径穿越
    try:
        target.resolve().relative_to(DOT_AGENTS_SKILLS.resolve())
    except ValueError:
        return jsonify({"ok": False, "error": "非法路径"}), 400
    try:
        shutil.rmtree(target)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/skills/<name>/skillmd", methods=["GET"])
def get_skill_md(name):
    target = DOT_AGENTS_SKILLS / name / "SKILL.md"
    if not target.exists():
        return jsonify({"ok": False, "error": "SKILL.md 不存在"}), 404
    try:
        content = target.read_text(encoding="utf-8")
        return jsonify({"ok": True, "content": content})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# MCP API
# ============================================================
@app.route("/api/mcp/list", methods=["GET"])
def mcp_list():
    full = _load_mcp_yaml_full()
    data = {"mcpServers": full.get("mcpServers", {})}
    return jsonify({"ok": True, "data": data, "path": str(MCP_CONFIG_FILE.relative_to(PROJECT_ROOT))})


@app.route("/api/mcp/save", methods=["POST"])
def mcp_save():
    body = request.get_json(force=True)
    data = body.get("data")
    if not isinstance(data, dict):
        return jsonify({"ok": False, "error": "data 必须是对象"}), 400
    try:
        full = _load_mcp_yaml_full()
        full["mcpServers"] = data.get("mcpServers", data)
        _save_mcp_yaml_full(full)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mcp/search", methods=["GET"])
def mcp_search():
    q = request.args.get("q", "").strip()
    page = int(request.args.get("page", 1))
    if not q:
        return jsonify({"ok": False, "error": "缺少 q 参数"}), 400
    try:
        # ModelScope 列表用 PUT
        resp = requests.put(
            MODELSCOPE_MCP_LIST_API,
            json={"page_number": page, "page_size": 20, "search": q},
            headers={"Content-Type": "application/json"},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") or payload
        servers = data.get("servers") or data.get("list") or []
        results = []
        for s in servers:
            sid = s.get("id") or s.get("mcp_server_id") or ""
            # id 格式 @owner/name
            owner = ""
            name = s.get("name") or s.get("en_name") or ""
            if sid.startswith("@") and "/" in sid:
                owner = sid[1:].split("/")[0]
            results.append({
                "id": sid,
                "name": name,
                "owner": owner,
                "description": s.get("description") or s.get("chinese_description") or "",
                "author": s.get("author") or owner,
                "categories": s.get("categories") or [],
                "is_hosted": s.get("is_hosted", False),
                "raw": s,
            })
        return jsonify({"ok": True, "data": results, "total": data.get("total_count", 0)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/mcp/detail", methods=["GET"])
def mcp_detail():
    owner = request.args.get("owner", "").strip()
    name = request.args.get("name", "").strip()
    if not owner or not name:
        return jsonify({"ok": False, "error": "缺少 owner/name"}), 400
    try:
        url = MODELSCOPE_MCP_DETAIL_API.format(owner=owner, name=name)
        resp = requests.get(
            url,
            params={"get_operational_url": "true"},
            headers={"Content-Type": "application/json"},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload.get("data") or payload
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ============================================================
# Plugin API
# ============================================================
@app.route("/api/plugins", methods=["GET"])
def list_plugins():
    plugins = []
    if PLUGINS_DIR.exists():
        # 支持 .plugin.yaml / .plugin.yml / .plugin.json
        files = []
        for pat in ("*.plugin.yaml", "*.plugin.yml", "*.plugin.json"):
            files.extend(PLUGINS_DIR.glob(pat))
        for f in sorted(files):
            try:
                cfg = load_env_config_file(f)
                if isinstance(cfg, dict) and "name" in cfg:
                    plugins.append({
                        "file": f.name,
                        "name": cfg.get("name"),
                        "version": cfg.get("version", ""),
                        "description": cfg.get("description", ""),
                        "skills_count": len(cfg.get("skills", [])),
                        "mcp_count": len(cfg.get("mcpServers", {})),
                    })
            except Exception:
                continue
    return jsonify({"ok": True, "data": plugins})


@app.route("/api/plugin/save", methods=["POST"])
def save_plugin():
    body = request.get_json(force=True)
    name = body.get("name", "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name 必填"}), 400
    config = {
        "name": name,
        "version": body.get("version", "1.0.0").strip() or "1.0.0",
        "description": body.get("description", "").strip(),
        "author": body.get("author", "MyAgentPlugin").strip() or "MyAgentPlugin",
        "mcpServers": body.get("mcpServers", {}),
        "skills": body.get("skills", []),
    }
    # 安全文件名
    safe_name = "".join(c for c in name if c.isalnum() or c in ("-", "_"))
    out_path = PLUGINS_DIR / f"{safe_name}.plugin.yaml"
    try:
        save_env_config_file(out_path, config)
        return jsonify({"ok": True, "path": str(out_path.relative_to(PROJECT_ROOT))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/plugin/load", methods=["GET"])
def load_plugin():
    """加载完整 plugin 配置。Query: file=xxx.plugin.yaml"""
    fname = request.args.get("file", "").strip()
    if not fname:
        return jsonify({"ok": False, "error": "缺少 file 参数"}), 400
    path = (PLUGINS_DIR / fname).resolve()
    try:
        path.relative_to(PLUGINS_DIR.resolve())
    except ValueError:
        return jsonify({"ok": False, "error": "非法路径"}), 400
    if not path.exists():
        return jsonify({"ok": False, "error": "文件不存在"}), 404
    try:
        data = load_env_config_file(path)
        return jsonify({"ok": True, "data": data, "path": str(path.relative_to(PROJECT_ROOT))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/plugin/delete", methods=["POST"])
def delete_plugin():
    """删除 plugin 配置。Body: {file: xxx.plugin.yaml}"""
    body = request.get_json(force=True)
    fname = (body.get("file") or "").strip()
    if not fname:
        return jsonify({"ok": False, "error": "缺少 file 参数"}), 400
    path = (PLUGINS_DIR / fname).resolve()
    try:
        path.relative_to(PLUGINS_DIR.resolve())
    except ValueError:
        return jsonify({"ok": False, "error": "非法路径"}), 400
    if not path.exists():
        return jsonify({"ok": False, "error": "文件不存在"}), 404
    try:
        path.unlink()
        return jsonify({"ok": True, "path": str(path.relative_to(PROJECT_ROOT))})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/plugin/install", methods=["GET"])
def install_plugin_sse():
    """SSE: 流式安装插件。Query: file=xxx.plugin.yaml"""
    fname = request.args.get("file", "").strip()
    if not fname:
        return Response("data: [ERROR] 缺少 file 参数\n\n", mimetype="text/event-stream")
    plugin_path = (PLUGINS_DIR / fname).resolve()
    try:
        plugin_path.relative_to(PLUGINS_DIR.resolve())
    except ValueError:
        return Response("data: [ERROR] 非法路径\n\n", mimetype="text/event-stream")
    if not plugin_path.exists():
        return Response(f"data: [ERROR] 文件不存在: {fname}\n\n", mimetype="text/event-stream")

    def gen():
        yield f"data: [PLUGIN] {fname}\n\n"
        yield f"data: [STEP] 加载插件配置\n\n"
        try:
            cfg = load_env_config_file(plugin_path)
            yield f"data:   名称: {cfg.get('name')}\n\n"
            yield f"data:   版本: {cfg.get('version')}\n\n"
            yield f"data:   技能数: {len(cfg.get('skills', []))}\n\n"
        except Exception as e:
            yield f"data: [ERROR] 加载失败: {e}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 复用 install_plugin 的底层步骤（capture 部分输出无法流式，这里直接调用）
        # 注意：plugin.yaml 的 mcpServers 不在此阶段合并，由 agentctl generate
        # 阶段同时读取 mcp.yaml + plugins/*.plugin.yaml 合并生成 mcp.json
        yield f"data: [STEP] 更新 llm.yaml\n\n"
        try:
            env_path = _ensure_llm_file()
            # 重定向 stdout 到管道（update_env_file 内部有 print）
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                update_env_file(env_path, cfg)
            for line in buf.getvalue().splitlines():
                if line.strip():
                    yield f"data: {line}\n\n"
        except Exception as e:
            yield f"data: [ERROR] llm 更新失败: {e}\n\n"

        yield f"data: [STEP] 安装技能\n\n"
        try:
            skills = cfg.get("skills", [])
            for i, sk in enumerate(skills):
                skill_name, cmd = build_install_command(sk, use_symlink=False)
                yield f"data: [{i+1}/{len(skills)}] {skill_name}\n\n"
                yield from _stream_process(cmd, cwd=PROJECT_ROOT)
        except Exception as e:
            yield f"data: [ERROR] 技能安装失败: {e}\n\n"

        yield "data: [DONE] 插件安装完成\n\n"

    return Response(stream_with_context(gen()), mimetype="text/event-stream")


# ============================================================
# init-env / init-ide 触发
# ============================================================
@app.route("/api/init-env", methods=["POST"])
def trigger_init_env():
    """触发 agentctl generate（原 init-env.py -a Generate）"""
    try:
        result = subprocess.run(
            _script_run_cmd("agentctl", ["generate"]),
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=60,
        )
        return jsonify({
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        })
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/init-ide", methods=["GET"])
def trigger_init_ide_sse():
    """SSE: 触发 agentctl sync --ide <ide> --force --scope <scope>"""
    ide = request.args.get("ide", "All")
    scope = request.args.get("scope", "llm,mcp,skill,plugin").strip()
    # 白名单校验，防止注入
    allowed = {"llm", "mcp", "skill", "plugin", "rules"}
    scopes = [s.strip().lower() for s in scope.split(",") if s.strip().lower() in allowed]
    if not scopes:
        scopes = ["llm", "mcp", "skill", "plugin"]
    scope_arg = ",".join(scopes)
    cmd_args = ["sync", "--ide", ide, "--force", "--scope", scope_arg]
    # 可选：仅同步勾选的技能（逗号分隔的技能名）
    skills = request.args.get("skills", "").strip()
    if skills:
        # 仅保留安全字符（字母、数字、-、_、逗号、空格），防止注入
        safe_skills = ",".join(s.strip() for s in skills.split(",") if s.strip() and all(c.isalnum() or c in "-_ " for c in s.strip()))
        if safe_skills:
            cmd_args += ["--skills", safe_skills]
    cmd = _script_run_shell_cmd("agentctl", cmd_args)
    return Response(
        stream_with_context(_stream_process(cmd, cwd=PROJECT_ROOT)),
        mimetype="text/event-stream",
    )


@app.route("/api/proxy/start", methods=["GET"])
def start_proxy_sse():
    """SSE: 启动 LLM 代理服务（litellm）。
    Query: cmd=启动命令（默认 litellm --config proxy/config.yaml --port 4000）
    """
    cmd = request.args.get("cmd", "").strip()
    if not cmd:
        cmd = "litellm --config proxy/config.yaml --port 4000"
    # 代理服务是长期运行进程，直接流式输出直到用户中断或进程退出
    return Response(
        stream_with_context(_stream_process(cmd, cwd=PROJECT_ROOT)),
        mimetype="text/event-stream",
    )


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="MyAgentPlugin 配置工具 Web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    _ensure_llm_file()
    _ensure_mcp_config_file()

    url = f"http://{args.host}:{args.port}"
    print(f"[Config UI] 服务启动中: {url}")
    print(f"[Config UI] 项目根: {PROJECT_ROOT}")
    print(f"[Config UI] Ctrl+C 退出")

    if not args.no_open:
        try:
            webbrowser.open(url)
        except Exception:
            pass

    app.run(host=args.host, port=args.port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
