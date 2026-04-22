# phase2-ncc-report

通过 Chrome DevTools MCP 控制真实浏览器完成 NCC 平台漏洞上报。平台入口：`https://www.nccsec.cn/company-center/manage-center`。

## 这个 skill 做什么

- 从本地漏洞 `docx` 材料提取上报字段。
- 自动识别同目录下的 `zip / 截图 / 视频` 附件。
- 打开 NCC 平台企业中心，完成登录、表单填写、验证码识别和提交。
- 上传平台要求的附件材料。
- 提交成功后记录平台返回的 `NCC-xxxx` 编号。
- 可选推送钉钉机器人通知。

## 新用户上手

### 1. 安装依赖

```bash
npm install -g chrome-devtools-mcp@latest
pip3 install websocket-client python-docx openpyxl ddddocr
```

### 2. 初始化配置

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/setup.sh
```

初始化脚本会：

- 从 `.env.example` 创建 `.env`，已有 `.env` 不覆盖。
- 生成指向当前目录 wrapper 的 `.mcp.json`。
- 设置脚本可执行权限。

### 3. 编辑 `.env`

新用户只需要修改父目录、账号、密码，以及必要时修改端口/profile。具体某一次要处理的 `DAS` 目录或 `docx` 路径，不放进 `.env`，而是在运行命令时传入。

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `NCC_PLATFORM_URL` | NCC 平台管理中心地址 | `https://www.nccsec.cn/company-center/manage-center` |
| `VULN_DATA_DIR` | 漏洞数据根目录，包含 DAS-T* 文件夹 | `/path/to/your/vulnerability/data` |
| `PYTHON_PROJECT_PATH` | Python 项目路径，可选 | `/path/to/your/python/project` |
| `NCC_USERNAME` | NCC 平台登录账号，可选 | 空 |
| `NCC_PASSWORD` | NCC 平台登录密码，可选 | 空 |
| `CHROME_DEBUG_PORT` | Chrome 调试端口 | `9334` |
| `CHROME_PROFILE_NAME` | Chrome profile 名称 | `ncc-report` |
| `DINGTALK_WEBHOOK` | 钉钉机器人 webhook，可选 | 空 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥，可选 | 空 |
| `DINGTALK_KEYWORD` | 钉钉机器人关键词，可选 | 空 |
| `DINGTALK_ENABLED` | 是否启用钉钉通知 | `true` |

`CLAUDE_CHROME_MCP_PORT` 和 `CLAUDE_CHROME_PROFILE_NAME` 仍兼容旧配置，但新用户应使用 `CHROME_DEBUG_PORT` 和 `CHROME_PROFILE_NAME`。

### 4. 启动专用浏览器

```bash
./scripts/start-chrome-debug.sh
```

可选模式：

- `isolated`：独立空 profile，默认模式。
- `seed-default`：复制日常 Chrome profile 快照，适合复用登录态。
- `live-default`：直接使用日常 Chrome 用户数据目录，使用前先关闭普通 Chrome。

### 5. 验证

```bash
curl -s http://127.0.0.1:9334/json/version
claude mcp get chrome-devtools
```

如果 Claude Code 不是从本 skill 目录启动，在实际项目目录注册：

```bash
claude mcp add chrome-devtools -- /Users/yao/.claude/skills/phase2-ncc-report/scripts/chrome-devtools-mcp-wrapper.sh
```

## 浏览器与 MCP

本 skill 默认：

- 调试端口：`9334`
- Chrome profile：`ncc-report`
- MCP wrapper：`scripts/chrome-devtools-mcp-wrapper.sh`
- MCP server 名：`chrome-devtools`

`scripts/start-chrome-debug.sh` 负责启动真实 Chrome，`scripts/chrome-devtools-mcp-wrapper.sh` 只负责让 MCP attach 到 `http://127.0.0.1:9334`。

## 常用命令

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/setup.sh
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9334/json/version
python3 scripts/extract_vuln_data.py --input-path "/path/to/DAS-T106003-漏洞目录"
python3 scripts/extract_vuln_data.py --docx-path "/path/to/report.docx"
python3 scripts/captcha_ocr.py /tmp/captcha.png
python3 scripts/dingtalk_notify.py --title "NCC 平台上报完成" --status success --text "DAS-ID：DAS-T106003\nNCC编号：NCC-2026-04947"
```

提取脚本会优先选择 `CNVD-` 材料目录，并自动返回：

- `docx_path`
- `upload_zip_path`
- `screenshot_paths`
- `video_paths`

## 钉钉机器人通知

在 `.env` 中填写 `DINGTALK_WEBHOOK` 后，可手动推送上报结果：

```bash
python3 scripts/dingtalk_notify.py \
  --title "NCC 平台上报完成" \
  --status success \
  --text "DAS-ID：DAS-T106003\nNCC编号：NCC-2026-04947" \
  --output "/path/to/data/DAS-T106003"
```

`--text` 支持命令行字面量 `\n`，脚本会转换为真实换行；`--link` 支持 `名称=URL` 格式；如果机器人启用了关键词，可在 `.env` 中配置 `DINGTALK_KEYWORD`。真实 webhook 只放在 `.env`，不要写入 README 或提交到 Git。

## 工作流程

1. 准备本地漏洞材料；`.env` 只维护父目录。
2. 运行 `extract_vuln_data.py`，把具体 `DAS` 目录或 `docx` 路径传进去。
3. 启动 skill 专用浏览器并确认 MCP 可用。
4. 打开 `NCC_PLATFORM_URL`，如果未登录则走“企业”登录页。
5. 登录成功后，在右上角“提交漏洞”下拉菜单进入填表页。
6. 用 MCP 快照确认字段 `uid` 和下拉值。
7. 填写漏洞信息，第一版优先上传 `upload_zip_path`。
8. 点击提交后，人工完成拖拽拼图验证。
9. 成功页记录 `NCC-xxxx`。
10. 如已配置 `DINGTALK_WEBHOOK`，可推送钉钉通知。

详细流程见 `references/workflow.md`。

## 目录结构

```text
phase2-ncc-report/
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
    └── workflow.md
```

## 排错

### 端口打不开

```bash
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9334/json/version
```

### Claude 连到了错误的浏览器

- 确认当前 Claude Code 启动目录。
- 确认 `claude mcp get chrome-devtools` 的 wrapper 路径。
- 确认 `.mcp.json` 指向当前 skill 的 `scripts/chrome-devtools-mcp-wrapper.sh`。

### 平台登录态或验证码问题

优先使用：

```bash
./scripts/start-chrome-debug.sh seed-default
```

如仍不行，先彻底退出普通 Chrome，再尝试：

```bash
./scripts/start-chrome-debug.sh live-default
```

当前已知情况：

- 登录页没有普通验证码。
- 点击提交后会出现拖拽拼图验证。
- 第一版把这一步留给人工处理，不强行脚本化。

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
claude mcp add ncc-chrome -- /Users/yao/.claude/skills/phase2-ncc-report/scripts/chrome-devtools-mcp-wrapper.sh
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
