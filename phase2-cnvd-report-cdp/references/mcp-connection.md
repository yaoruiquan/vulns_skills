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
                                           │  (调试端口 9223) │
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

## 连接失败问题与解决方案

### 问题：MCP 工具未加载

**原因**：chrome-devtools-mcp 启动时输出警告到 stderr，干扰 MCP 协议握手：

```
(node:74926) Warning: `--localstorage-file` was provided without a valid path
chrome-devtools-mcp exposes content of the browser instance to the MCP clients...
Google collects usage statistics...
```

### 解决方案：使用 wrapper 脚本

**Step 1: 创建 wrapper 脚本**

```bash
#!/bin/bash
# /tmp/chrome-devtools-mcp-wrapper.sh
exec node /opt/homebrew/lib/node_modules/chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js \
  --browserUrl http://127.0.0.1:9223 \
  --no-usage-statistics \
  --no-performance-crux \
  2>/dev/null
```

```bash
chmod +x /tmp/chrome-devtools-mcp-wrapper.sh
```

**Step 2: 配置 settings.json**

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "/tmp/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

**关键点**：
- `2>/dev/null` 将 stderr 警告重定向到空设备
- 只保留 stdout 用于 MCP 协议通信
- 不要用 `grep -v` 过滤，会破坏管道

## 完整配置步骤

**Step 1: 全局安装 chrome-devtools-mcp**

```bash
npm install -g chrome-devtools-mcp@latest
```

**Step 2: 启动 Chrome（调试端口）**

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9223 \
  --user-data-dir=/tmp/chrome-debug-cnvd
```

**Step 3: 创建 wrapper 脚本**

```bash
cat << 'EOF' > /tmp/chrome-devtools-mcp-wrapper.sh
#!/bin/bash
exec node /opt/homebrew/lib/node_modules/chrome-devtools-mcp/build/src/bin/chrome-devtools-mcp.js \
  --browserUrl http://127.0.0.1:9223 \
  --no-usage-statistics \
  --no-performance-crux \
  2>/dev/null
EOF

chmod +x /tmp/chrome-devtools-mcp-wrapper.sh
```

**Step 4: 配置项目级 settings.json**

文件路径：`/Users/yao/LLM/vulns/.claude/settings.json`

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "/tmp/chrome-devtools-mcp-wrapper.sh",
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
| **chrome-devtools MCP** | **连接现有浏览器** | ✓ 正常访问 | **保留登录态** | 中 |

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
2. Chrome 是否以调试端口启动 (`--remote-debugging-port=9223`)
3. 运行 `/mcp` 重新加载 MCP 连接
4. 检查 settings.json 配置是否正确

**Q: 连接成功但无法操作页面？**

A: 确保：
1. Chrome 使用 `--remote-allow-origins=*` 参数启动（可选）
2. 目标页面已完全加载
3. 使用正确的 uid（从 `take_snapshot` 获取）

**Q: 配置了 .mcp.json 但不生效？**

A: `.claude/settings.json` 的 `mcpServers` 会覆盖 `.mcp.json`，确保两个文件配置一致。