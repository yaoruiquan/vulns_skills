# phase2-cnvd-report

通过 Chrome DevTools MCP 控制真实浏览器完成 CNVD 漏洞上报。

## 这个 skill 做什么

- 从本地 CNVD `docx` 材料提取上报字段。
- 打开 CNVD 页面，完成登录、表单填写、验证码识别和提交。
- 上传按 CNVD 要求准备的附件压缩包。
- 提交成功后记录 CNVD 编号或页面返回结果。

## 新用户上手

### 1. 安装依赖

```bash
npm install -g chrome-devtools-mcp@latest
pip3 install websocket-client python-docx openpyxl ddddocr
```

### 2. 初始化配置

```bash
cd /Users/yao/.claude/skills/phase2-cnvd-report
./scripts/setup.sh
```

初始化脚本会：

- 从 `.env.example` 创建 `.env`，已有 `.env` 不覆盖。
- 生成指向当前目录 wrapper 的 `.mcp.json`。
- 设置脚本可执行权限。

### 3. 编辑 `.env`

新用户只需要修改路径、账号、密码，以及必要时修改端口/profile。

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `VULN_DATA_DIR` | 漏洞数据根目录，包含 DAS-T* 文件夹 | `/path/to/your/vulnerability/data` |
| `PYTHON_PROJECT_PATH` | Python 项目路径，可选 | `/path/to/your/python/project` |
| `CNVD_EMAIL` | CNVD 登录邮箱，可选 | 空 |
| `CNVD_PASSWORD` | CNVD 登录密码，可选 | 空 |
| `CHROME_DEBUG_PORT` | Chrome 调试端口 | `9332` |
| `CHROME_PROFILE_NAME` | Chrome profile 名称 | `cnvd-report` |
| `DINGTALK_WEBHOOK` | 钉钉机器人 webhook，可选 | 空 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥，可选 | 空 |
| `DINGTALK_ENABLED` | 是否启用钉钉通知 | `true` |

`CLAUDE_CHROME_MCP_PORT` 和 `CLAUDE_CHROME_PROFILE_NAME` 仍兼容旧配置，但新用户应使用 `CHROME_DEBUG_PORT` 和 `CHROME_PROFILE_NAME`。

### 4. 启动专用浏览器

```bash
./scripts/start-chrome-debug.sh
```

可选模式：

- `isolated`：独立空 profile，默认模式。
- `seed-default`：复制日常 Chrome profile 快照，CNVD 场景常用。
- `live-default`：直接使用日常 Chrome 用户数据目录，使用前先关闭普通 Chrome。

如果 CNVD 打开后出现 Cloudflare 521 或登录态问题，优先改用：

```bash
./scripts/start-chrome-debug.sh seed-default
```

### 5. 验证

```bash
curl -s http://127.0.0.1:9332/json/version
claude mcp get chrome-devtools
```

如果 Claude Code 不是从本 skill 目录启动，在实际项目目录注册：

```bash
claude mcp add chrome-devtools -- /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

## 浏览器与 MCP

本 skill 默认：

- 调试端口：`9332`
- Chrome profile：`cnvd-report`
- MCP wrapper：`scripts/chrome-devtools-mcp-wrapper.sh`
- MCP server 名：`chrome-devtools`

`scripts/start-chrome-debug.sh` 负责启动真实 Chrome，`scripts/chrome-devtools-mcp-wrapper.sh` 只负责让 MCP attach 到 `http://127.0.0.1:9332`。

## 常用命令

```bash
cd /Users/yao/.claude/skills/phase2-cnvd-report
./scripts/setup.sh
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9332/json/version
python3 scripts/extract_vuln_data.py DAS-T105966 --platform CNVD --data-dir "/path/to/data"
python3 scripts/captcha_ocr.py /tmp/captcha.png
python3 scripts/dingtalk_notify.py --title "CNVD 上报完成" --status success --text "编号：CNVD-2026-XXXX\n材料已提交"
```

附件压缩包按 CNVD 页面上传要求准备；当前 skill 不包含独立的 `compress_zip.py`。

## 钉钉机器人通知

在 `.env` 中填写 `DINGTALK_WEBHOOK` 后，可手动推送上报结果：

```bash
python3 scripts/dingtalk_notify.py \
  --title "CNVD 上报完成" \
  --status success \
  --text "DAS-ID：DAS-T105966\nCNVD 编号：CNVD-2026-XXXX" \
  --output "/path/to/data/DAS-T105966"
```

`--text` 支持命令行字面量 `\n`，脚本会转换为真实换行。真实 webhook 只放在 `.env`，不要写入 README 或提交到 Git。

## 工作流程

1. 准备本地漏洞材料和附件目录。
2. 运行 `extract_vuln_data.py` 提取字段。
3. 启动 skill 专用浏览器并确认 MCP 可用。
4. 打开 CNVD、登录并进入漏洞上报页。
5. 填写通用型漏洞表单并上传附件。
6. 识别验证码、提交并记录结果。
7. 如已配置 `DINGTALK_WEBHOOK`，可推送钉钉通知。

详细流程见 `references/workflow.md`。

## 目录结构

```text
phase2-cnvd-report/
├── SKILL.md
├── README.md
├── .env.example
├── .mcp.json
├── scripts/
│   ├── setup.sh
│   ├── chrome-devtools-mcp-wrapper.sh
│   ├── start-chrome-debug.sh
│   ├── extract_vuln_data.py
│   ├── captcha_ocr.py
│   └── dingtalk_notify.py
└── references/
    ├── captcha-ocr.md
    ├── field-mapping.md
    ├── mcp-connection.md
    ├── mcp-tools.md
    ├── selectors.md
    ├── setup-guide.md
    ├── workflow.md
    ├── original-SKILL.md
    └── original-README.md
```

## 排错

### 端口打不开

```bash
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9332/json/version
```

### Claude 连到了错误的浏览器

- 确认当前 Claude Code 启动目录。
- 确认 `claude mcp get chrome-devtools` 的 wrapper 路径。
- 确认 `.mcp.json` 指向当前 skill 的 `scripts/chrome-devtools-mcp-wrapper.sh`。

### CNVD 打开后是 Cloudflare 521

这通常是浏览器指纹或登录态问题，不是 MCP 路径错误。优先使用：

```bash
./scripts/start-chrome-debug.sh seed-default
```

如仍不行，先彻底退出普通 Chrome，再尝试：

```bash
./scripts/start-chrome-debug.sh live-default
```

## 复用/迁移

复制 skill 给其他用户时：

1. 复制整个目录。
2. 运行 `./scripts/setup.sh`。
3. 只修改 `.env` 中的路径、账号、密码、端口/profile。
4. 如需从其他项目目录使用，运行 `claude mcp add ...`。

不要手工改 wrapper 脚本；路径变化由 `setup.sh` 重新生成 `.mcp.json`。

## 高级：同项目加载多个浏览器 MCP

各 skill 的端口/profile 可以独立运行。同一个 Claude 项目里同时注册多个 MCP server 时，server 名必须唯一：

```bash
claude mcp add cnvd-chrome -- /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

这个是高级用法，不是单个 skill 的默认使用方式。单独使用本 skill 时，保持 `chrome-devtools` 这个默认名称即可。

## 参考文档

- [setup-guide.md](references/setup-guide.md)
- [workflow.md](references/workflow.md)
- [field-mapping.md](references/field-mapping.md)
- [selectors.md](references/selectors.md)
- [captcha-ocr.md](references/captcha-ocr.md)
- [mcp-connection.md](references/mcp-connection.md)
- [mcp-tools.md](references/mcp-tools.md)
- [original-SKILL.md](references/original-SKILL.md)
- [original-README.md](references/original-README.md)
