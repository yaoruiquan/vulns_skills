# phase2-cnnvd-report

通过 Chrome DevTools MCP 控制真实浏览器完成 CNNVD 漏洞上报，并在需要时更新本地漏洞汇总表。

## 这个 skill 做什么

- 从本地 CNNVD `docx` 材料提取上报字段。
- 打开 CNNVD 页面并进入通用型漏洞报送流程。
- 填写漏洞基本信息、漏洞详情和漏洞验证过程。
- 上传验证录像、PoC 或其他附件。
- 提交成功后记录 CNNVD 编号，并按需更新本地汇总表。

## 新用户上手

### 1. 安装依赖

```bash
npm install -g chrome-devtools-mcp@latest
pip3 install websocket-client python-docx openpyxl ddddocr
```

### 2. 初始化配置

```bash
cd /Users/yao/.claude/skills/phase2-cnnvd-report
./scripts/setup.sh
```

初始化脚本会：

- 从 `.env.example` 创建 `.env`，已有 `.env` 不覆盖。
- 生成指向当前目录 wrapper 的 `.mcp.json`。
- 设置脚本可执行权限。

`.env.template` 会保留为历史兼容模板，新用户优先使用 `.env.example`。

### 3. 编辑 `.env`

新用户只需要修改路径、账号、密码，以及必要时修改端口/profile。

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `CNNVD_USERNAME` | CNNVD 登录用户名 | `user@example.com` |
| `CNNVD_PASSWORD` | CNNVD 登录密码 | `your_password` |
| `VULNS_DATA_DIR` | 漏洞数据根目录，包含 DAS-ID 文件夹 | `/path/to/vulns/date` |
| `SUMMARY_TABLE_PATH` | 漏洞汇总表 xlsx 路径 | `/path/to/漏洞汇总表.xlsx` |
| `COMPANY_NAME` | 技术支持单位名称 | `杭州安恒信息技术股份有限公司` |
| `DEFAULT_CONTACT_PHONE` | 默认联系电话 | `15700082275` |
| `CHROME_DEBUG_PORT` | Chrome 调试端口 | `9333` |
| `CHROME_PROFILE_NAME` | Chrome profile 名称 | `cnnvd-report` |

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
curl -s http://127.0.0.1:9333/json/version
claude mcp get chrome-devtools
```

如果 Claude Code 不是从本 skill 目录启动，在实际项目目录注册：

```bash
claude mcp add chrome-devtools -- /Users/yao/.claude/skills/phase2-cnnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

## 浏览器与 MCP

本 skill 默认：

- 调试端口：`9333`
- Chrome profile：`cnnvd-report`
- MCP wrapper：`scripts/chrome-devtools-mcp-wrapper.sh`
- MCP server 名：`chrome-devtools`

`scripts/start-chrome-debug.sh` 负责启动真实 Chrome，`scripts/chrome-devtools-mcp-wrapper.sh` 只负责让 MCP attach 到 `http://127.0.0.1:9333`。

## 常用命令

```bash
cd /Users/yao/.claude/skills/phase2-cnnvd-report
./scripts/setup.sh
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9333/json/version
python3 scripts/extract_vuln_data.py DAS-T105966 --platform CNNVD
python3 scripts/compress_zip.py "/path/to/CNNVD-folder"
python3 scripts/captcha_ocr.py /tmp/captcha.png
```

更新本地汇总表：

```bash
python3 scripts/update_summary.py \
  --title "漏洞标题" \
  --vendor "影响厂商" \
  --das-id "DAS-T105966" \
  --submitter "提交人员" \
  --cnvd-id "CNVD-2026-XXXX" \
  --cnnvd-id "CNNVD-202604-XXXX" \
  --date "2026-04-14"
```

## 工作流程

1. 准备本地漏洞材料、验证视频和附件。
2. 运行 `extract_vuln_data.py` 提取字段。
3. 必要时运行 `compress_zip.py` 压缩附件目录。
4. 启动 skill 专用浏览器并确认 MCP 可用。
5. 打开 CNNVD、登录并进入通用型漏洞报送。
6. 填写基本信息、漏洞详情和验证过程。
7. 上传验证视频和 PoC 附件。
8. 提交后获取 CNNVD-ID，并按需运行 `update_summary.py`。

## 目录结构

```text
phase2-cnnvd-report/
├── SKILL.md
├── README.md
├── .env.example
├── .env.template
├── .mcp.json
├── scripts/
│   ├── setup.sh
│   ├── config.py
│   ├── chrome-devtools-mcp-wrapper.sh
│   ├── start-chrome-debug.sh
│   ├── extract_vuln_data.py
│   ├── compress_zip.py
│   ├── captcha_ocr.py
│   └── update_summary.py
└── references/
    ├── setup-guide.md
    ├── data-fields.md
    ├── vuln-type-mapping.md
    ├── captcha-ocr.md
    ├── word-extraction.md
    ├── video-compression.md
    ├── summary-table.md
    ├── mcp-tools.md
    ├── mcp-connection.md
    ├── original-SKILL.md
    └── original-README.md
```

## 排错

### 端口打不开

```bash
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9333/json/version
```

### Claude 连到了错误的浏览器

- 确认当前 Claude Code 启动目录。
- 确认 `claude mcp get chrome-devtools` 的 wrapper 路径。
- 确认 `.mcp.json` 指向当前 skill 的 `scripts/chrome-devtools-mcp-wrapper.sh`。

### 找不到漏洞材料

- 检查 `.env` 中的 `VULNS_DATA_DIR`。
- 确认目录下存在以 DAS-ID 开头的漏洞文件夹。
- 确认平台子目录以 `CNNVD-` 开头，且其中存在非隐藏 `.docx` 文件。

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
claude mcp add cnnvd-chrome -- /Users/yao/.claude/skills/phase2-cnnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

这个是高级用法，不是单个 skill 的默认使用方式。单独使用本 skill 时，保持 `chrome-devtools` 这个默认名称即可。

## 参考文档

- [setup-guide.md](references/setup-guide.md)
- [data-fields.md](references/data-fields.md)
- [vuln-type-mapping.md](references/vuln-type-mapping.md)
- [captcha-ocr.md](references/captcha-ocr.md)
- [word-extraction.md](references/word-extraction.md)
- [video-compression.md](references/video-compression.md)
- [summary-table.md](references/summary-table.md)
- [mcp-tools.md](references/mcp-tools.md)
- [mcp-connection.md](references/mcp-connection.md)
- [original-SKILL.md](references/original-SKILL.md)
- [original-README.md](references/original-README.md)
