# phase2-cnnvd-report-cdp

通过 Chrome DevTools MCP 控制真实浏览器完成 CNNVD 漏洞上报。

这个 README 面向第一次使用或接手维护这个 skill 的用户，包含：

- 这个 skill 的职责边界。
- 本地依赖和脚本入口。
- 浏览器调试端口、profile、MCP 的隔离方式。

## 这个 skill 做什么

`phase2-cnnvd-report-cdp` 用于将已经整理好的漏洞材料提交到 CNNVD 平台。常见操作包括：

- 从本地 `docx` 材料中提取字段。
- 打开 CNNVD 页面并导航到报送入口。
- 填写漏洞基本信息、漏洞详情和验证过程。
- 上传验证录像和其他附件。
- 提交成功后记录 CNNVD 编号。
- 在需要时更新本地汇总表。

## 与 CNVD skill 的区别

虽然 `phase2-cnvd-report-cdp` 和这个 skill 都使用 Chrome DevTools MCP，但流程并不相同：

- CNVD 的入口和表单结构不同。
- CNNVD 需要验证录像，且通常有更多人工确认点。
- CNNVD 的提交者单位和联系电话存在固定规则。
- CNNVD 还包含汇总表更新脚本 `update_summary.py`。

## 新用户上手

### 1. 安装依赖

```bash
npm install -g chrome-devtools-mcp@latest
pip install websocket-client python-docx openpyxl ddddocr
```

### 2. 确认项目级 MCP 配置

当前目录已经包含：

- `./.mcp.json`
- `./.claude/settings.json`

两者都应该指向本地 wrapper：

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

推荐做法和 CNVD 一样：在本 skill 目录里启动 Claude Code，不改全局 `~/.mcp.json`。

### 3. 启动当前 skill 专用浏览器

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh
```

如果后续遇到站点保护页、登录态异常，或者你需要复用真实 Chrome 足迹，优先改用：

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

可选启动模式：

- `isolated`：纯隔离 profile，默认值。
- `seed-default`：先把你日常 Chrome 的 `Default` profile 快照复制到 skill profile，再打开调试端口。
- `live-default`：直接挂到你日常 Chrome 的用户数据目录。只有在 `seed-default` 仍不够时再用，并且先关闭普通 Chrome。

### 4. 检查调试端口

```bash
curl -s http://127.0.0.1:9333/json/version
```

能返回 JSON 说明当前 skill 的浏览器实例已启动。

### 5. 检查 MCP 工具

在 Claude 会话中验证：

- `list_pages`
- `navigate_page`
- `take_snapshot`

如果这些工具可以正常执行，说明 Claude 已经连接到 `9333` 对应的 CNNVD 浏览器实例。

## 浏览器与端口隔离

这个 skill 固定使用独立浏览器实例，不复用你的日常 Chrome。

固定配置：

- 调试端口：`9333`
- 独立 profile：`~/.claude/chrome-profiles/cnnvd-report`
- MCP wrapper：`scripts/chrome-devtools-mcp-wrapper.sh`
- 浏览器启动脚本：`scripts/start-chrome-debug.sh`

这样设计是为了保证：

- CNNVD 登录态只保存在专用 profile 中。
- 不和 CNVD 或漏洞预警 skill 共用同一个调试端口。
- 日常浏览器查资料时不被自动化接管。

### 为什么现在只会看到一个 Chrome 实例

现在的架构是“一个真实 Chrome + 一个 MCP 进程 attach 到它”，不是“两套可见 Chrome”。

- `scripts/start-chrome-debug.sh` 只负责启动一个带 `9333` 端口的真实 Chrome。
- `scripts/chrome-devtools-mcp-wrapper.sh` 只负责把 `chrome-devtools-mcp` 连接到 `http://127.0.0.1:9333`。
- `chrome-devtools-mcp` 通过 `--browserUrl` attach 到现有浏览器，不会再额外拉起第二个可见窗口。

如果你以前见过两个实例，通常是因为手工启动了一个调试 Chrome，同时 MCP 又按默认行为自己启动了一套 automation Chrome。现在这个 skill 已经把浏览器生命周期收敛到 skill 脚本里，MCP 只接管，不再负责启动第二套浏览器。

### 与日常 Chrome 如何共存

- 日常 Chrome：正常启动，不带调试端口。
- CNNVD 自动化 Chrome：只通过 `start-chrome-debug.sh` 启动，固定监听 `9333`。
- 如果要用 `live-default`，先彻底退出普通 Chrome，再启动 skill 浏览器，避免同一个用户数据目录被两个实例同时占用。

如果你的日常浏览器也开启了 `9222`、`9223` 一类端口，Claude 可能误连到主浏览器。新的使用者应避免这种配置。

## 目录结构

```text
phase2-cnnvd-report-cdp/
├── SKILL.md
├── README.md
├── .mcp.json
├── .claude/settings.json
├── scripts/
│   ├── chrome-devtools-mcp-wrapper.sh
│   ├── start-chrome-debug.sh
│   ├── extract_vuln_data.py
│   ├── compress_zip.py
│   ├── captcha_ocr.py
│   └── update_summary.py
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
python3 /Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/extract_vuln_data.py DAS-T105966 --platform CNNVD --data-dir "/path/to/data"
```

### 压缩附件目录

```bash
python3 /Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/compress_zip.py "/path/to/CNNVD-folder"
```

### OCR 识别验证码

```bash
python3 /Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/captcha_ocr.py /tmp/captcha.png
```

### 更新本地汇总表

```bash
python3 /Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/update_summary.py \
  --title "漏洞标题" \
  --vendor "影响厂商" \
  --das-id "DAS-T105966" \
  --submitter "提交人员" \
  --cnvd-id "CNVD-2026-XXXX" \
  --cnnvd-id "CNNVD-202604-XXXX" \
  --date "2026-04-14"
```

## 推荐工作流

1. 在本目录启动 Claude Code。
2. 启动 skill 专用浏览器。
3. 用 `curl localhost:9333/json/version` 确认端口在线。
4. 用 `extract_vuln_data.py` 提取 docx 数据。
5. 用 `compress_zip.py` 准备上传包。
6. 让 Claude 使用 `chrome-devtools` 进入 CNNVD 页面。
7. 登录、进入报送入口、填写表单、上传验证录像和其他附件。
8. 提交成功后记录 CNNVD 编号。
9. 需要归档时，用 `update_summary.py` 更新汇总表。

## 数据与表单的关系

`extract_vuln_data.py` 提取出的常见字段包括：

- `title`
- `description`
- `vuln_type`
- `url`
- `affected_product`
- `contact`
- `verification`
- `folder_path`
- `docx_path`

这些数据会用于驱动浏览器填表。

## 执行流程概览

1. 准备数据
2. 打开 CNNVD 首页
3. 登录并处理验证码
4. 进入通用型漏洞报送入口
5. 填写漏洞基本信息
6. 填写漏洞详情和受影响实体描述
7. 填写验证过程
8. 上传验证录像和其他附件
9. 提交并记录 CNNVD 编号
10. 更新本地汇总表

## 常见问题

### `9333` 端口没有响应

重新执行：

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh
```

如果你需要复用日常 profile，也可以明确指定模式：

```bash
/Users/yao/.claude/skills/phase2-cnnvd-report-cdp/scripts/start-chrome-debug.sh seed-default
```

### Claude 没有接管到正确浏览器

优先检查：

- 当前会话是否从本 skill 目录启动。
- `.mcp.json` 是否仍指向本地 wrapper。
- 你的日常 Chrome 是否也开启了调试端口。

### 为什么现在不再出现两个可见 Chrome

因为这个 skill 现在固定走“先启动 skill Chrome，再由 MCP attach”的路径。只要你使用本目录的 `.mcp.json` 和 `scripts/start-chrome-debug.sh`，就只会有一个被接管的可见实例。

### 为什么 CNNVD 不能直接复用 CNVD 的浏览器

技术上可以同时存在多个调试实例，但这个 skill 故意不用共用浏览器。原因是：

- 两个平台登录态和流程差异大。
- 共用 profile 会让页面状态互相污染。
- 独立端口更容易排错。

## 与其他技能的关系

典型链路：

```text
phase1-test / 材料整理
  -> 生成 docx 和附件
phase2-cnvd-report-cdp
  -> 完成 CNVD 上报
phase2-cnnvd-report-cdp
  -> 完成 CNNVD 上报
```

## 参考文档

- [SKILL.md](./SKILL.md)
- [captcha-ocr.md](./references/captcha-ocr.md)
- [mcp-connection.md](./references/mcp-connection.md)
- [mcp-tools.md](./references/mcp-tools.md)
- [selectors.md](./references/selectors.md)
- [error-handling.md](./references/error-handling.md)
