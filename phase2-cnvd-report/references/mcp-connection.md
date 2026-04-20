# chrome-devtools MCP 连接原理与经验

## 技术架构详解

```
┌─────────────────┐     MCP Protocol      ┌─────────────────┐
│  Claude Code    │ ◄──────────────────► │ chrome-devtools │
│  Agent          │    (JSON-RPC/stdio)   │ -mcp (Node.js)  │
└─────────────────┘                        └────────┬────────┘
                                                    │
                                           CDP (WebSocket)
                                                    │
                                           ┌────────▼────────┐
                                           │  Chrome Browser │
                                           │  (调试端口 9332) │
                                           └─────────────────┘
```

## 协议层级

| 层级 | 协议 | 说明 |
|------|------|------|
| **L1: MCP** | JSON-RPC over stdio | Claude Code 与 MCP 服务器通信 |
| **L2: CDP** | WebSocket | MCP 服务器与 Chrome 通信 |
| **L3: Browser** | HTTP/HTML | Chrome 与网站通信 |

## 为什么能绑过防火墙？

**关键点：控制的是真实用户浏览器**

| 方案 | 浏览器类型 | 防火墙检测 |
|------|-----------|-----------|
| Playwright/Selenium | 无头浏览器 | ✓ 易被检测 |
| **chrome-devtools MCP** | **真实 Chrome** | ✗ 无法区分 |

```
Playwright 无头浏览器：
  特征：navigator.webdriver = true
  特征：缺少真实浏览器指纹
  → 防火墙识别 → 拦截

chrome-devtools MCP：
  连接：用户已打开的真实 Chrome
  特征：与正常用户完全相同
  → 防火墙无法区分 → 正常访问
```

**访问 CNVD：可以 ✓**

原因：
1. Chrome 是**你手动启动**的真实浏览器
2. 你已经**手动登录**了 CNVD（有 cookies/session）
3. MCP 只是发送命令控制浏览器，**不是自动化浏览器**
4. CNVD 防火墙看到的是**正常用户行为**

**补充：Cloudflare 521 的根因通常不是 MCP，而是浏览器 profile 太“干净”**

如果你给 skill 启动了一个全新的隔离 profile，Cloudflare 可能会把它判成异常浏览器。CNVD 场景优先建议：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh seed-default
```

这样会保留调试端口隔离，同时把你真实 Chrome 的 cookies、历史和本地状态快照到 skill profile 里。

**补充：现在的 skill 默认只会有一个可见 Chrome 实例**

当前实现里，浏览器和 MCP 的职责已经拆开：

- `scripts/start-chrome-debug.sh` 只负责启动 skill 专用 Chrome
- `scripts/chrome-devtools-mcp-wrapper.sh` 只负责让 `chrome-devtools-mcp` 连接到 `http://127.0.0.1:9332`
- `chrome-devtools-mcp` 通过 `--browserUrl` attach 到现有浏览器，不再自己拉起第二个可见 Chrome

如果你以前见过两个实例，通常是因为“手工开的调试浏览器”和“MCP 默认拉起的 automation 浏览器”同时存在。现在 skill 本地 wrapper 已经把这个问题收敛掉了。

## 连接失败问题与解决方案

### 问题：MCP 工具未加载

**原因**：chrome-devtools-mcp 启动时输出警告到 stderr，干扰 MCP 协议握手：

```
(node:74926) Warning: `--localstorage-file` was provided without a valid path
chrome-devtools-mcp exposes content of the browser instance to the MCP clients...
Google collects usage statistics...
```

### 解决方案：使用 skill 本地 wrapper 脚本

**Step 1: 创建 wrapper 脚本**

```bash
#!/bin/bash
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

```bash
chmod +x /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

**Step 2: 配置 `.mcp.json`**

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "/Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

**关键点**：
- wrapper 通过 `--browserUrl` 连接到本 skill 专用 Chrome
- 由 `CHROME_DEBUG_PORT` 决定连接端口，默认 `9332`
- 不要用 `grep -v` 过滤 MCP 输出，会破坏协议管道

## 完整配置步骤

**Step 1: 全局安装 chrome-devtools-mcp**

```bash
npm install -g chrome-devtools-mcp@latest
```

**Step 2: 启动 skill 专用 Chrome**

```bash
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh
```

如果站点前面有 Cloudflare，改用：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh seed-default
```

**Step 3: 确认 wrapper 脚本路径**

```bash
ls -l /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

**Step 4: 确认项目级 `.mcp.json`**

文件路径：`/Users/yao/.claude/skills/phase2-cnvd-report/.mcp.json`

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "/Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

**Step 5: 重新加载 MCP**

```
/mcp
```

**Step 6: 验证连接**

```
MCP: list_pages
```

预期输出：
```
Pages:
  1: https://www.baidu.com/ [selected]
  2: https://www.cnvd.org.cn/...
```

## 与其他方案对比

| 方案 | 连接方式 | 防火墙 | 登录态 | 配置复杂度 |
|------|----------|--------|--------|-----------|
| Playwright 无头 | 自动启动无头浏览器 | ✗ 被拦截 | 需重新登录 | 低 |
| Playwright 有头 | 自动启动有头浏览器 | △ 可能被检测 | 需重新登录 | 低 |
| 旧式 MCP 直启 | 手工浏览器 + MCP 自启浏览器 | △ 易混淆 | 易串环境 | 中 |
| **当前 skill 方案** | **一个真实 Chrome + MCP attach** | ✓ 正常访问 | **保留登录态** | 中 |

## 测试验证

```bash
# 测试 1: 列出页面
MCP: list_pages

# 测试 2: 截图
MCP: take_screenshot

# 测试 3: 填写表单
MCP: fill
  uid: "1_20"
  value: "测试内容"

# 测试 4: 点击按钮
MCP: click
  uid: "1_21"
```

## 常见问题

**Q: MCP 工具列表中没有 chrome-devtools？**

A: 检查以下几点：
1. wrapper 脚本是否有执行权限 (`chmod +x`)
2. Chrome 是否已通过 `scripts/start-chrome-debug.sh` 启动，并监听 `9332`
3. 运行 `/mcp` 重新加载 MCP 连接
4. 检查 `.mcp.json` 或 `claude mcp get chrome-devtools` 的 wrapper 路径是否正确

**Q: 连接成功但无法操作页面？**

A: 确保：
1. Chrome 使用 `--remote-allow-origins=*` 参数启动（可选）
2. 目标页面已完全加载
3. 使用正确的 uid（从 `take_snapshot` 获取）

**Q: 调试端口正常，但打开 CNVD 是 Cloudflare 521？**

A: 这通常是 Cloudflare 拒绝了“全新 profile”的浏览器指纹。按顺序尝试：
1. `scripts/start-chrome-debug.sh seed-default`
2. 如果默认不是 `Default` profile，先设置 `CLAUDE_CHROME_PROFILE_DIRECTORY`
3. 仍不行再关闭日常 Chrome，使用 `scripts/start-chrome-debug.sh live-default`

**Q: 配置了 .mcp.json 但不生效？**

A: 确认 Claude Code 是从本 skill 目录启动的；如果不是，请在实际项目目录运行 `claude mcp add chrome-devtools -- /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh`。

**Q: 为什么现在没有第二个写着“被 MCP 控制”的 Chrome？**

A: 因为 wrapper 现在显式使用了 `--browserUrl`，MCP 只 attach 到 `9332` 端口对应的已有 Chrome，不再自行 launch 第二个可见浏览器。
