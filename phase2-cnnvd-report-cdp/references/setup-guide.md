# CNNVD 上报环境配置

## 一、安装依赖

### 1.1 安装 chrome-devtools-mcp

```bash
npm install -g chrome-devtools-mcp@latest
```

### 1.2 安装 OCR 依赖

```bash
pip install ddddocr
```

### 1.3 安装其他 Python 依赖

```bash
pip install websocket-client python-docx openpyxl
```

## 二、配置 MCP

在当前 skill 目录的 `./.mcp.json` 或 `./.claude/settings.json` 中配置：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

## 三、启动 Chrome（调试端口）

### 3.1 默认启动（隔离 profile）

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh
```

该 skill 的固定隔离配置：

- 调试端口：`9333`
- 独立 profile：`~/.claude/chrome-profiles/cnnvd-report`
- 与日常 Chrome 默认 profile 隔离

### 3.2 复用日常 Chrome 足迹

如果站点保护页、登录态或浏览器足迹有问题，优先改用：

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

### 3.3 启动模式说明

| 模式 | 说明 |
|-----|------|
| `isolated` | 纯隔离 profile，默认值 |
| `seed-default` | 先复制日常 Chrome 的 `Default` profile 到 skill profile，再用 9333 启动 |
| `live-default` | 直接使用日常 Chrome 的用户数据目录。只有 seed-default 仍不够时再用，并先关闭普通 Chrome |

## 四、检查环境状态

### 4.1 检查 Chrome 调试端口

```bash
curl -s http://localhost:9333/json/version
```

**预期输出**：
```json
{
  "Browser": "Chrome/xxx.x.xxxx.xx",
  "Protocol-Version": "1.3",
  "webSocketDebuggerUrl": "ws://localhost:9333/devtools/browser/xxx"
}
```

### 4.2 检查 MCP 连接状态

```
MCP: list_pages
```

**预期输出**：返回当前浏览器打开的页面列表。

### 4.3 环境检查清单

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|----------|
| Chrome 调试端口 | `curl localhost:9333/json/version` | 返回 JSON |
| MCP 连接 | `list_pages` | 返回页面列表 |
| 登录状态 | 打开 CNNVD 首页检查 | 已登录/未登录 |

**只有当以上检查全部通过后，才继续执行后续步骤。**