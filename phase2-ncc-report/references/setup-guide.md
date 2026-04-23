# 前提条件与配置

## 1. 安装 chrome-devtools-mcp

```bash
npm install -g chrome-devtools-mcp@latest
```

Python 依赖：

```bash
pip3 install websocket-client python-docx openpyxl ddddocr
```

## 2. 初始化 skill

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/setup.sh
```

初始化脚本会生成当前 skill 路径的 `./.mcp.json`：

```json
{
  "mcpServers": {
    "ncc-chrome": {
      "command": "/Users/yao/.claude/skills/phase2-ncc-report/scripts/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

## 3. 启动 Chrome 调试端口

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/start-chrome-debug.sh
```

该 skill 的固定隔离配置：

- 调试端口：`9334`
- 独立 profile：`~/.claude/chrome-profiles/ncc-report`
- 与日常 Chrome 默认 profile 隔离

## 4. 启动模式说明

| 模式 | 命令 | 说明 |
|------|------|------|
| `isolated` | `./scripts/start-chrome-debug.sh` | 纯隔离 profile |
| `seed-default` | `./scripts/start-chrome-debug.sh seed-default` | 复制日常 Chrome Default profile 到 skill profile |
| `live-default` | `./scripts/start-chrome-debug.sh live-default` | 直接使用日常 Chrome 用户数据目录 |

首次登录 NCC 平台或需要复用登录态时，优先使用 `seed-default`。

## 5. 环境检查

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|----------|
| Chrome 调试端口 | `curl localhost:9334/json/version` | 返回 JSON |
| MCP 连接 | `list_pages` | 返回页面列表 |
| 登录状态 | 打开 `NCC_PLATFORM_URL` 检查 | 已登录/未登录 |

只有当以上检查全部通过后，才继续执行后续步骤。

MCP 连接原理和常见错误处理详见 [mcp-connection.md](mcp-connection.md)。
