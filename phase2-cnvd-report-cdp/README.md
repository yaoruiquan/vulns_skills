# phase2-cnvd-report-cdp

通过 Chrome DevTools MCP 控制真实浏览器完成 CNVD 漏洞上报。

这个 README 面向第一次接手这个 skill 的用户，重点说明三件事：

- 这个 skill 负责什么。
- 需要哪些本地依赖和数据。
- 浏览器如何隔离，避免和你的日常 Chrome 冲突。

## 这个 skill 做什么

`phase2-cnvd-report-cdp` 负责把已经整理好的漏洞材料提交到 CNVD 平台。典型流程包括：

- 从本地 `docx` 材料提取字段。
- 准备待上传的附件压缩包。
- 通过 Chrome DevTools MCP 打开 CNVD 页面并填写表单。
- 处理验证码、上传附件、提交并记录上报结果。

## 新用户上手

### 1. 安装依赖

```bash
npm install -g chrome-devtools-mcp@latest
pip install websocket-client python-docx openpyxl ddddocr
```

### 2. 确认项目级 MCP 配置

当前目录自带：

- `./.mcp.json`
- `./.claude/settings.json`

两者都应该指向当前 skill 的本地 wrapper：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/chrome-devtools-mcp-wrapper.sh",
      "args": []
    }
  }
}
```

推荐做法：

- 在本 skill 目录里启动 Claude Code。
- 让当前目录的 `.mcp.json` 生效。
- 不改全局 `~/.mcp.json`。

### 3. 启动当前 skill 专用浏览器

```bash
/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/start-chrome-debug.sh
```

如果 CNVD 打开后直接落到 Cloudflare 521，优先改用：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

可选启动模式：

- `isolated`：纯隔离 profile，默认值。
- `seed-default`：先把你日常 Chrome 的 `Default` profile 快照复制到 skill profile，再打开调试端口。CNVD 场景优先推荐这个。
- `live-default`：直接挂到你日常 Chrome 的用户数据目录。只有在 `seed-default` 仍被 Cloudflare 拦截时再用，并且先关闭普通 Chrome。

### 4. 检查浏览器调试端口

```bash
curl -s http://127.0.0.1:9332/json/version
```

能返回 JSON，说明 skill 专用 Chrome 已启动。

### 5. 检查 MCP 工具

在 Claude 会话里测试：

- `list_pages`
- `navigate_page`
- `take_snapshot`

如果这些工具能正常工作，说明 `chrome-devtools` 已经接管到正确的浏览器实例。

## 浏览器与端口隔离

这个 skill 默认使用独立的浏览器实例，而不是你的日常 Chrome。

固定配置：

- 调试端口：`9332`
- 独立 profile：`~/.claude/chrome-profiles/cnvd-report`
- MCP wrapper：`scripts/chrome-devtools-mcp-wrapper.sh`
- 浏览器启动脚本：`scripts/start-chrome-debug.sh`

这样做的原因：

- CNVD 上报流程会登录真实账号，不应该混入你的日常浏览器 profile。
- 这个 skill 需要稳定的调试端口，不能和别的 skill 抢占同一个端口。
- 即使浏览器卡住，也只影响这个 skill，不影响日常办公。

### 为什么现在只会看到一个 Chrome 实例

现在的架构是“一个真实 Chrome + 一个 MCP 进程 attach 到它”，不是“两套可见 Chrome”。

- `scripts/start-chrome-debug.sh` 只负责启动一个带 `9332` 端口的真实 Chrome。
- `scripts/chrome-devtools-mcp-wrapper.sh` 只负责把 `chrome-devtools-mcp` 连接到 `http://127.0.0.1:9332`。
- `chrome-devtools-mcp` 通过 `--browserUrl` attach 到现有浏览器，不会再额外拉起第二个可见窗口。

如果你以前见过两个实例，通常是因为手工启动了一个调试 Chrome，同时 MCP 又按默认行为自己启动了一套 automation Chrome。现在这个 skill 已经把浏览器生命周期收敛到 skill 脚本里，MCP 只接管，不再负责启动第二套浏览器。

但 CNVD 前面挂了 Cloudflare 时，完全干净的隔离 profile 可能反而更像机器人。这个 skill 现在支持在保留调试端口隔离的前提下，复用你真实 Chrome 的指纹和 cookies。

### 与日常 Chrome 如何共存

- 日常 Chrome：正常启动，不带 `--remote-debugging-port`。
- 本 skill Chrome：只通过 `start-chrome-debug.sh` 启动，固定监听 `9332`。
- 如果要用 `live-default`，先彻底退出普通 Chrome，再启动 skill 浏览器，避免同一个用户数据目录被两个实例同时占用。

只要保持这条边界，CNVD 自动化和你的主浏览器就能同时存在。

## 目录结构

```text
phase2-cnvd-report-cdp/
├── SKILL.md
├── README.md
├── .mcp.json
├── .claude/settings.json
├── scripts/
│   ├── chrome-devtools-mcp-wrapper.sh
│   ├── start-chrome-debug.sh
│   ├── extract_vuln_data.py
│   ├── compress_zip.py
│   └── captcha_ocr.py
└── references/
    ├── captcha-ocr.md
    ├── error-handling.md
    ├── mcp-connection.md
    ├── mcp-tools.md
    └── selectors.md
```

## 常用命令

### 提取漏洞数据

```bash
python3 /Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/extract_vuln_data.py DAS-T105966 --platform CNVD --data-dir "/path/to/data"
```

### 压缩附件目录

```bash
python3 /Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/compress_zip.py "/path/to/CNVD-folder"
```

### OCR 识别验证码

```bash
python3 /Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/captcha_ocr.py /tmp/captcha.png
```

## 推荐工作流

1. 在本目录启动 Claude Code。
2. 启动 skill 专用浏览器。
3. 用 `curl localhost:9332/json/version` 确认端口在线。
4. 运行 `extract_vuln_data.py` 提取 docx 数据。
5. 运行 `compress_zip.py` 准备上传附件。
6. 让 Claude 使用 `chrome-devtools` 工具进入 CNVD 页面。
7. 登录、切换到通用型漏洞、填写表单、上传附件、提交。

## 数据与表单的关系

`extract_vuln_data.py` 会从本地材料中提取出 CNVD 提交所需的关键字段，例如：

- `title`
- `description`
- `vuln_type`
- `unit_name`
- `affected_product`
- `version`
- `folder_path`
- `docx_path`

这些字段随后会被 Claude 填入浏览器表单。

## 执行流程概览

1. 准备数据
2. 打开 CNVD 首页
3. 登录并处理验证码
4. 导航到漏洞上报页
5. 切换到正确的表单类型
6. 填写基本信息和漏洞详情
7. 上传 zip 附件
8. 识别提交验证码并提交
9. 记录返回的 CNVD 编号

## 常见问题

### `9332` 端口打不开

重新执行：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/start-chrome-debug.sh
```

如果你要复用日常 profile，也可以明确指定模式：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

### Claude 连到了错误的浏览器

通常是因为：

- 你不是在本目录启动 Claude Code。
- 会话读取了别的 `.mcp.json`。
- 你的日常 Chrome 也暴露了调试端口。

优先修正目录和 MCP 配置，不要在同一个 skill 里混用全局浏览器配置。

### 为什么现在不再出现两个可见 Chrome

因为这个 skill 现在固定走“先启动 skill Chrome，再由 MCP attach”的路径。只要你使用本目录的 `.mcp.json` 和 `scripts/start-chrome-debug.sh`，就只会有一个被接管的可见实例。

### CNVD 打开后是验证码保护页

这是站点自身行为，不是 skill 或 MCP 配置错误。浏览器和端口正常时，页面可达但可能要求额外验证码验证。

### CNVD 打开后是 Cloudflare 521

这通常不是 CNVD 源站真的宕机，而是 Cloudflare 把当前浏览器实例判成了可疑流量。优先按下面顺序处理：

1. 用真实 Chrome 足迹启动：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

2. 如果还不行，彻底退出普通 Chrome 后再试：

```bash
/Users/yao/.claude/skills/phase2-cnvd-report-cdp/scripts/start-chrome-debug.sh live-default
```

3. 如果你本机默认不是 `Default` profile，可以先设置：

```bash
export CLAUDE_CHROME_PROFILE_DIRECTORY="Profile 1"
```

然后再启动上面的命令。

## 与其他技能的关系

典型链路：

```text
phase1-material-processor / 材料整理
  -> 生成 docx 和附件
phase2-cnvd-report-cdp
  -> 完成 CNVD 上报
phase2-cnnvd-report-cdp
  -> 可继续做 CNNVD 上报
```

## 参考文档

- [SKILL.md](./SKILL.md)
- [captcha-ocr.md](./references/captcha-ocr.md)
- [mcp-connection.md](./references/mcp-connection.md)
- [mcp-tools.md](./references/mcp-tools.md)
- [selectors.md](./references/selectors.md)
- [error-handling.md](./references/error-handling.md)
