# 产品安全研究部 AI-Skills

> 赋能安全研究，探索AI驱动的下一代安全能力

## 🧠 关于本仓库

本仓库由 **产品安全研究部** 维护，聚焦于 **人工智能与安全研究深度融合** 的实践沉淀。我们致力于探索利用大语言模型（LLM）、机器学习（ML）等 AI 技术，提升安全检测、漏洞分析、威胁情报、自动化攻防等方向的研究效率与创新边界。

无论你是安全研究员、开发工程师，还是对 AI + Security 交叉领域感兴趣的探索者，这里都将为你提供可落地的代码、实验案例、研究思路和最佳实践。

## 🎯 主要方向

- **智能漏洞挖掘**：基于 LLM 的代码审计、Fuzzing 用例生成、污点分析辅助
- **自动化逆向分析**：二进制理解、反编译代码注释、控制流/数据流智能分析
- **威胁情报与态势感知**：非结构化情报信息抽取、IOC 自动化提炼、攻击链推理
- **AI 安全评估**：模型鲁棒性测试、对抗样本生成、提示词注入检测
- **安全运营自动化**：告警降噪、事件自动分类、响应剧本生成

# phase2-cnnvd-report

通过 Chrome DevTools MCP 控制真实浏览器完成 CNNVD 漏洞上报，并在需要时更新本地漏洞汇总表。

## 这个 skill 做什么

- 从本地 CNNVD `docx` 材料提取上报字段。
- 打开 CNNVD 页面并进入通用型漏洞报送流程。
- 按 CNNVD 页面 danger/红色必填项填写，减少下拉框重复交互。
- 上传 `exp验证视频` 或 `poc验证视频` 中的验证录像，以及 `exp` 或 `poc` 目录中的 PoC 文件。
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

所有 Python 脚本一律使用 `python3` 执行，不要使用 `python`。

`.env.template` 会保留为历史兼容模板，新用户优先使用 `.env.example`。

### 3. 编辑 `.env`

新用户只需要修改路径、账号、密码，以及必要时修改端口/profile。

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `CNNVD_USERNAME` | CNNVD 登录用户名 | `user@example.com` |
| `CNNVD_PASSWORD` | CNNVD 登录密码 | `your_password` |
| `VULNS_DATA_DIR` | 漏洞数据根目录，包含 DAS-ID 文件夹 | `/path/to/vulns/date` |
| `FORM_CONTEXT_DIR` | 运行时 `form_context.json` 暂存目录 | `/tmp/vulns-skills/phase2-cnnvd-report/form-contexts` |
| `SUMMARY_TABLE_PATH` | 漏洞汇总表 xlsx 路径 | `/path/to/漏洞汇总表.xlsx` |
| `COMPANY_NAME` | 技术支持单位名称 | `杭州安恒信息技术股份有限公司` |
| `DEFAULT_CONTACT_PHONE` | 默认联系电话 | `15700082275` |
| `CHROME_DEBUG_PORT` | Chrome 调试端口 | `9333` |
| `CHROME_PROFILE_NAME` | Chrome profile 名称 | `cnnvd-report` |
| `DINGTALK_WEBHOOK` | 钉钉机器人 webhook，可选 | 空 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥，可选 | 空 |
| `DINGTALK_ENABLED` | 是否启用钉钉通知 | `true` |
| `REPORT_UPLOAD_REMOTE_DIR` | CNNVD zip 远端存放目录 | `/root/msrc-report-downloads/cnnvd-submissions` |
| `REPORT_DOWNLOAD_BASE_URL` | CNNVD zip 下载 URL 根路径 | `http://10.50.10.29:8080/download/msrc/cnnvd-submissions` |

### 4. 推荐启动方式

如果一次只跑一个浏览器型 skill，推荐每个 Claude session 都先进入对应 skill 目录再启动 Claude Code：

```bash
cd /Users/yao/.claude/skills/phase2-cnnvd-report
claude
```

这样 Claude 会自动读取本目录的 `.mcp.json`，使用 `cnnvd-chrome` 连接本 skill 的 `9333` 端口和 `cnnvd-report` Chrome profile。多个并发 session 分别 `cd` 到各自 skill 目录启动即可。

### 5. 启动专用浏览器

```bash
./scripts/start-chrome-debug.sh
```

可选模式：

- `isolated`：独立空 profile，默认模式。
- `seed-default`：复制日常 Chrome profile 快照，适合复用登录态。
- `live-default`：直接使用日常 Chrome 用户数据目录，使用前先关闭普通 Chrome。

### 6. 验证

```bash
curl -s http://127.0.0.1:9333/json/version
claude mcp get cnnvd-chrome
```

如果 Claude Code 不是从本 skill 目录启动，在实际项目目录注册：

```bash
claude mcp add cnnvd-chrome -- /Users/yao/.claude/skills/phase2-cnnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

## 浏览器与 MCP

本 skill 默认：

- 调试端口：`9333`
- Chrome profile：`cnnvd-report`
- MCP wrapper：`scripts/chrome-devtools-mcp-wrapper.sh`
- MCP server 名：`cnnvd-chrome`

`scripts/start-chrome-debug.sh` 负责启动真实 Chrome，`scripts/chrome-devtools-mcp-wrapper.sh` 只负责让 MCP attach 到 `http://127.0.0.1:9333`。

## 常用命令

```bash
cd /Users/yao/.claude/skills/phase2-cnnvd-report
./scripts/setup.sh
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9333/json/version
python3 scripts/prepare_form_context.py "/path/to/DAS-T105966-xxx" --entity-description "产品简介..." --verification "验证过程摘要..."
python3 scripts/captcha_ocr.py /tmp/captcha.png
python3 scripts/captcha_ocr.py --serve --port 18765
python3 scripts/captcha_ocr.py /tmp/captcha.png --server-url http://127.0.0.1:18765
python3 scripts/dingtalk_notify.py --title "监管上报 CNNVD 上报完成" --status success --text "编号：CNNVD-202604-XXXX\n材料已提交"
python3 scripts/publish_submission_zip.py "/tmp/vulns-skills/phase2-cnnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json" --platform-id "CNNVD-202604-XXXX" --notify
```

`extract_vuln_data.py` 只作为 `prepare_form_context.py` 的底层提取工具；浏览器填表前必须以 `/tmp/vulns-skills/phase2-cnnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json` 为准。该 JSON 会提前固化 `dropdown_plan`、分页 `page_payloads`、`ocr` 和附件状态。运行时 JSON 不写入 CNNVD 提交材料目录。

验证码刷新较快时，先启动 `captcha_ocr.py --serve` 常驻 OCR 服务，优先使用 `form_context.json.ocr.preferred_server_url` / `ocr.recognize_command`；提交前最后一步截图验证码并走 `--server-url` 识别；识别后不要再 `take_snapshot`，直接填入并提交。

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

推送钉钉通知（监管上报类技能统一使用同一个机器人，关键词为 `监管上报`）：

```bash
python3 scripts/dingtalk_notify.py \
  --title "监管上报 CNNVD 上报完成" \
  --status success \
  --text "DAS-ID：DAS-T105966\nCNNVD 编号：CNNVD-202604-XXXX" \
  --output "/path/to/CNNVD-folder"
```

`--text` 支持命令行字面量 `\n`，脚本会转换为真实换行。真实 webhook 只放在 `.env`，不要写入 README 或提交到 Git。

`--title` 有默认值，但提交成功或失败通知建议显式传入，避免群消息标题不清楚。

提交成功后推荐使用 `publish_submission_zip.py` 作为收尾动作，它只上传单个漏洞的 CNNVD 原始整包 zip，并在钉钉 Markdown 中附带漏洞名称、`DAS-ID`、`CNNVD 编号`、附件名、大小和下载链接。若材料目录里还没有 `CNNVD-*.zip`，`prepare_form_context.py` 和 `publish_submission_zip.py` 会自动按单漏洞目录补建，不需要再手工 `zip -r`。默认远端目录为：

```text
/root/msrc-report-downloads/cnnvd-submissions/YYYY-MM/DAS-ID/
```

默认下载链接复用现有 MSRC 下载服务前缀：

```text
http://10.50.10.29:8080/download/msrc/cnnvd-submissions/YYYY-MM/DAS-ID/CNNVD-xxx.zip
```

## 工作流程

1. 准备本地漏洞材料、验证视频和附件。
2. 数据准备阶段运行 `prepare_form_context.py` 生成 `/tmp/vulns-skills/phase2-cnnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json`；websearch 补齐受影响实体描述，并把 Word 中的详细验证过程总结压缩为一段文字。
3. 启动 skill 专用浏览器并确认 MCP 可用。
4. 打开 CNNVD、登录并进入通用型漏洞报送。
5. 第 1 页只处理必填项；优先按 `dropdown_plan` 和 `page_payloads.page1_dropdowns` 选择漏洞类型、漏洞自评级、受影响实体分类，再按 `page_payloads.page1_text` 一次性填写文本字段。
6. 第 2 页只填写漏洞描述或简介、技术支持、技术支持联系电话。
7. 第 3 页填写单段验证过程，并上传 `verification_video_path` 和 `poc_file_path`。
8. 提交后获取 CNNVD-ID，并按需运行 `update_summary.py`。
9. 如已配置 `DINGTALK_WEBHOOK`，运行 `publish_submission_zip.py <form_context.json> --platform-id <CNNVD-ID> --notify`，上传单漏洞 CNNVD zip 并推送包含漏洞名称、`DAS-ID`、`CNNVD 编号` 和下载链接的钉钉通知。

进入浏览器阶段后，只读取 `/tmp` 下的 `form_context.json`。第 1/2/3 页都直接读取 `page_payloads`，每页尽量一次性填写，不要为单个字段反复 `take_snapshot`。第 2 页和第 3 页不要重新运行提取脚本；第 2 页“漏洞描述或简介”只填 255 字以内的 `description`，不要改用 `description_full`。第 3 页漏洞验证阶段也不要再跑 Word 提取脚本或重新总结，只填已有的 `FormContext.verification`。

遇到下拉框判断不确定时，先查 `references/dropdown-options.md`，不要在页面里反复展开后再临时判断。级联下拉要点击最终叶子选项前面的圆圈/单选按钮完成选择，不要只点击文字，也不要按 Escape 关闭。

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
│   ├── prepare_form_context.py
│   ├── publish_submission_zip.py
│   ├── compress_zip.py
│   ├── captcha_ocr.py
│   ├── update_summary.py
│   └── dingtalk_notify.py
└── references/
    ├── data-preparation.md
    ├── data-fields.md
    ├── dropdown-options.md
    ├── vuln-type-mapping.md
    ├── captcha-ocr.md
    ├── word-extraction.md
    ├── video-compression.md
    └── summary-table.md
```

## 排错

### 端口打不开

```bash
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9333/json/version
```

### Claude 连到了错误的浏览器

- 确认当前 Claude Code 启动目录。
- 确认 `claude mcp get cnnvd-chrome` 的 wrapper 路径。
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

## 多浏览器 MCP 并发

各 skill 的端口/profile/MCP server 名必须独立运行。后续新增浏览器型 skill 时，也必须分配唯一端口、唯一 Chrome profile、唯一 MCP server 名。本 skill 默认使用唯一名称：

```bash
claude mcp add cnnvd-chrome -- /Users/yao/.claude/skills/phase2-cnnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

不要把本 skill 注册成通用的 `chrome-devtools`，否则同一 Claude 项目里加载 CNVD、CNNVD、NCC 或预警 skill 时会互相覆盖。

## 参考文档

- [data-preparation.md](references/data-preparation.md)
- [data-fields.md](references/data-fields.md)
- [dropdown-options.md](references/dropdown-options.md)
- [vuln-type-mapping.md](references/vuln-type-mapping.md)
- [captcha-ocr.md](references/captcha-ocr.md)
- [word-extraction.md](references/word-extraction.md)
- [video-compression.md](references/video-compression.md)
- [summary-table.md](references/summary-table.md)
