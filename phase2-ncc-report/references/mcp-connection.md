# MCP 连接说明

## 结构

```text
Claude Code
  -> .mcp.json
  -> scripts/chrome-devtools-mcp-wrapper.sh
  -> chrome-devtools-mcp
  -> http://127.0.0.1:9334
  -> 专用 Chrome profile: ncc-report
```

## 启动顺序

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/setup.sh
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9334/json/version
```

如果 Claude Code 不是从本 skill 目录启动，在实际项目目录注册：

```bash
claude mcp add ncc-chrome -- /Users/yao/.claude/skills/phase2-ncc-report/scripts/chrome-devtools-mcp-wrapper.sh
```

同一项目同时加载多个浏览器 MCP 时，不要改回通用的 `chrome-devtools` 名称。

## 常见问题

### 端口不可用

```bash
curl -s http://127.0.0.1:9334/json/version
```

无返回时，重新运行：

```bash
./scripts/start-chrome-debug.sh
```

### 登录态不可用

优先尝试复制日常 Chrome profile：

```bash
./scripts/start-chrome-debug.sh seed-default
```

仍不行时，关闭普通 Chrome 后尝试：

```bash
./scripts/start-chrome-debug.sh live-default
```

### Claude 连错浏览器

- 确认 `.mcp.json` 的 wrapper 路径指向 `phase2-ncc-report`。
- 确认 wrapper 使用 `CHROME_DEBUG_PORT=9334`。
- 同项目多 MCP 时，确认 server 名没有冲突。
