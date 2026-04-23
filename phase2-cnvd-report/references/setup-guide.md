# 前提条件与配置

## 1. 安装 chrome-devtools-mcp

```bash
npm install -g chrome-devtools-mcp@latest
```

## 2. 配置 MCP

首次使用先在 skill 目录运行初始化脚本：

```bash
cd /Users/yao/.claude/skills/phase2-cnvd-report
./scripts/setup.sh
```

初始化脚本会生成当前 skill 路径的 `./.mcp.json`：

```json
{
  "mcpServers": {
    "cnvd-chrome": {
      "command": "/Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

## 3. 启动 Chrome（调试端口）

```bash
cd /Users/yao/.claude/skills/phase2-cnvd-report
./scripts/start-chrome-debug.sh
```

该 skill 的固定隔离配置：

- 调试端口：`9332`
- 独立 profile：`~/.claude/chrome-profiles/cnvd-report`
- 与日常 Chrome 默认 profile 隔离

### 启动模式说明

| 模式 | 命令 | 说明 |
|------|------|------|
| `isolated` | 默认 | 纯隔离 profile |
| `seed-default` | `./scripts/start-chrome-debug.sh seed-default` | 复制日常 Chrome Default profile 到 skill profile |
| `live-default` | `./scripts/start-chrome-debug.sh live-default` | 直接使用日常 Chrome 用户数据目录 |

**如果 CNVD 返回 Cloudflare 521**，优先改用 `seed-default` 模式。

## 4. 环境检查

| 检查项 | 命令/操作 | 预期结果 |
|--------|----------|----------|
| Chrome 调试端口 | `curl localhost:9332/json/version` | 返回 JSON |
| MCP 连接 | `list_pages` | 返回页面列表 |
| 登录状态 | 打开 CNVD 首页检查 | 已登录/未登录 |

**只有当以上检查全部通过后，才继续执行后续步骤。**

---

> MCP 连接原理和常见错误处理详见 [mcp-connection.md](mcp-connection.md)。
