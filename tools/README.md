# 配置工具 Web UI

本地 Web 配置工具，通过浏览器管理 `llm.yaml` / `mcp.yaml`、插件、MCP、Skill。

## 启动

```bash
# 安装依赖（一次性）
pip install flask pyyaml requests

# 启动
python tools/config_server.py

# 自定义端口/不自动开浏览器
python tools/config_server.py --port 8080 --no-open
```

启动后自动打开 `http://127.0.0.1:5000`。

## 功能页签

| 页签 | 功能 |
|---|---|
| **LLM 配置** | 可视化编辑 `llm.yaml`（LLM providers / proxy / embedding / tts / asr / vision / misc） |
| **MCP** | 单页三区：市场搜索 / 已配置（含手动添加） / 密钥配置（`mcp.yaml`） |
| **Skills 配置** | ModelScope 市场 + skills.sh + 本地预置 + 手动 `owner/repo`，一键 `npx skills add` |
| **插件组装** | 预定义插件卡片 + 从技能目录/MCP 目录勾选组装 `plugin.yaml` 并安装 |
| **IDE 同步** | 触发 `init-ide.py` 同步配置到各 IDE |

## 设计要点

- **复用现有脚本**：后端直接 `import scripts/plugin_manager.py` 和 `scripts/init-env.py` 的函数，不重写逻辑
- **流式安装日志**：所有 `npx` / `subprocess` 调用通过 SSE 推送实时日志，避免界面卡死
- **强制 `--copy`**：复用 `plugin-manager.py` 的策略，避免 Trae 沙箱下 symlink 失败
- **外部 API 代理**：ModelScope / skills.sh 由后端代理调用，前端不跨域

## 外部市场源

- MCP：`https://www.modelscope.cn/openapi/v1/mcp/servers`（列表 + 详情，返回 `server_config`）
- Skill：`https://www.modelscope.cn/openapi/v1/skills`（搜索 + `install_command`）
- Skill 备源：`https://skills.sh/api/search`

## 文件清单

```
tools/
  ├── config_server.py    # Flask 后端
  ├── config_ui.html      # 单页前端
  └── README.md           # 本文件
```

## 依赖

- Python 3.8+
- flask, pyyaml, requests
- Node.js（`npx skills add` 需要）
