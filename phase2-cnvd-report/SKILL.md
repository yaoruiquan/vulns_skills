# phase2-cnvd-report

通过 Chrome DevTools MCP 控制真实浏览器完成 CNVD 漏洞上报。

---

## 环境配置

### 1. 初始化

```bash
cd /Users/yao/.claude/skills/phase2-cnvd-report
./scripts/setup.sh
vim .env
```

`setup.sh` 会创建 `.env`、生成当前路径的 `.mcp.json`，并设置脚本可执行权限。已有 `.env` 不会被覆盖。

所有 Python 脚本一律使用 `python3` 执行，不要使用 `python`。

### 2. 必填配置

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `VULN_DATA_DIR` | 漏洞数据根目录，包含 DAS-T* 文件夹 | `/path/to/your/vulnerability/data` |
| `FORM_CONTEXT_DIR` | 运行时 `form_context.json` 暂存目录 | `/tmp/vulns-skills/phase2-cnvd-report/form-contexts` |
| `PYTHON_PROJECT_PATH` | Python 项目路径，可选，用于导入共享模块 | `/path/to/your/python/project` |
| `CNVD_EMAIL` | CNVD 登录邮箱，可选 | 空 |
| `CNVD_PASSWORD` | CNVD 登录密码，可选 | 空 |
| `CHROME_DEBUG_PORT` | 本 skill 专用 Chrome 调试端口 | `9332` |
| `CHROME_PROFILE_NAME` | 本 skill 专用 Chrome profile | `cnvd-report` |
| `DINGTALK_WEBHOOK` | 钉钉机器人 webhook，可选 | 空 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥，可选 | 空 |
| `DINGTALK_ENABLED` | 是否启用钉钉通知 | `true` |
| `DINGTALK_KEYWORD` | 钉钉机器人关键词 | `监管上报` |
| `REPORT_UPLOAD_REMOTE_DIR` | CNVD zip 远端存放目录 | `/root/msrc-report-downloads/cnvd-submissions` |
| `REPORT_DOWNLOAD_BASE_URL` | CNVD zip 下载 URL 根路径 | `http://10.50.10.29:8080/download/msrc/cnvd-submissions` |

兼容旧变量 `CLAUDE_CHROME_MCP_PORT` 和 `CLAUDE_CHROME_PROFILE_NAME`，但新配置优先使用 `CHROME_DEBUG_PORT` 和 `CHROME_PROFILE_NAME`。

### 3. 推荐启动方式

如果一次只跑一个浏览器型 skill，推荐每个 Claude session 都先进入对应 skill 目录再启动 Claude Code：

```bash
cd /Users/yao/.claude/skills/phase2-cnvd-report
claude
```

这样 Claude 会自动读取本目录的 `.mcp.json`，使用 `cnvd-chrome` 连接本 skill 的 `9332` 端口和 `cnvd-report` Chrome profile。多个并发 session 分别 `cd` 到各自 skill 目录启动即可。

### 4. 浏览器配置

本 skill 默认使用：

- 调试端口：`9332`
- Chrome profile：`cnvd-report`
- 启动脚本：`scripts/start-chrome-debug.sh`

```bash
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9332/json/version
```

可选模式：

- `isolated`：独立空 profile，默认模式。
- `seed-default`：复制日常 Chrome profile 快照，适合绕过 CNVD 登录态或 Cloudflare 干扰。
- `live-default`：直接使用日常 Chrome 用户数据目录，使用前先关闭普通 Chrome。

### 5. MCP 配置

如果从本 skill 目录启动 Claude Code，`.mcp.json` 会作为项目配置使用，server 名为 `cnvd-chrome`。

如果从其他项目目录启动 Claude Code，在那个项目目录注册本 skill 的 wrapper：

```bash
claude mcp add cnvd-chrome -- /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

本 skill 的端口/profile/MCP server 名都独立于其他浏览器型 skill；不要把它注册成通用的 `chrome-devtools`，否则会覆盖或误连到其他 wrapper。

### 6. 验证

```bash
curl -s http://127.0.0.1:9332/json/version
claude mcp get cnvd-chrome
```

---

## 工作流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 0 | 检查环境 | 确认 `.env`、Chrome 调试端口和 MCP 可用 |
| 1 | 准备数据 | 用 `prepare_form_context.py` 生成 `/tmp/vulns-skills/phase2-cnvd-report/form-contexts/YYYY-MM/DAS-ID/form_context.json`，提前固化 `dropdown_phase`、`page_payloads` 和 `ocr` |
| 2 | 导航表单 | 打开 CNVD、登录、进入漏洞上报表单 |
| 3 | 填写表单 | 浏览器阶段只读取 `form_context.json`；先选 `form_type_label` 和 `vuln_type`，再填写其余字段 |
| 4 | 上传附件 | 上传 `form_context.json` 中 `attachment_zip_path` 指向的 CNVD 原始整包 zip |
| 5 | 验证提交 | 提交前最后一步 OCR 识别验证码；验证码刷新快时使用 `captcha_ocr.py --serve` 常驻服务加速，提交后提取并记录 `CNVD-xxxx` 编号 |
| 6 | 钉钉通知 | 已配置 `DINGTALK_WEBHOOK` 时上传单漏洞 CNVD zip，并推送漏洞名称、`DAS-ID`、`CNVD 编号` 和下载链接 |

详细步骤见 `references/workflow.md`。

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/setup.sh` | 初始化 `.env`、`.mcp.json` 和脚本权限 |
| `scripts/start-chrome-debug.sh` | 启动本 skill 专用 Chrome |
| `scripts/chrome-devtools-mcp-wrapper.sh` | MCP wrapper，连接到 `CHROME_DEBUG_PORT` |
| `scripts/compress_zip.py` | 按单漏洞目录生成 CNVD 原始整包 zip；通常由准备/上传脚本自动调用 |
| `scripts/extract_vuln_data.py` | 从 docx 提取 CNVD/CNNVD 上报字段 |
| `scripts/prepare_form_context.py` | 生成浏览器填表阶段唯一使用的 CNVD `form_context.json` |
| `scripts/publish_submission_zip.py` | 上传单个 CNVD 原始整包 zip，并推送钉钉下载链接 |
| `scripts/captcha_ocr.py` | 验证码 OCR |
| `scripts/dingtalk_notify.py` | 将上报结果推送到钉钉机器人 |

---

## 参考资料

- `references/workflow.md`：CNVD 上报步骤
- `references/field-mapping.md`：字段映射
- `references/selectors.md`：CNVD 表单选择器参考
- `references/captcha-ocr.md`：验证码 OCR

---

## 注意事项

- CNVD 密码明文存储有风险，不要复制或分享 `.env`。
- 钉钉 webhook 属于敏感配置，只能放在 `.env`，不要写进文档或提交到 Git。
- 监管上报类技能统一使用同一个机器人，关键词统一为 `监管上报`。
- 钉钉通知是收尾动作；提交成功后优先使用 `publish_submission_zip.py <form_context.json> --platform-id <CNVD-ID> --notify`，消息必须包含漏洞名称、`DAS-ID`、`CNVD 编号` 和附件下载链接。
- `publish_submission_zip.py` 只上传单个漏洞的 CNVD 原始整包 zip，不上传整个批次目录；若本地尚未生成 `CNVD-*.zip`，脚本会自动补建。
- 优先使用 `seed-default` 复用登录态；`live-default` 只在必要时使用。
- 浏览器阶段只能读取 `/tmp/vulns-skills/phase2-cnvd-report/form-contexts/.../form_context.json`；优先使用其中的 `dropdown_phase`、`page_payloads` 和 `ocr`，不要在第二阶段重新运行提取脚本、重新压缩目录或重新判断标题。
- CNVD 表单顺序固定：先只处理 `dropdown_phase` 中两个下拉框 `form_type_label`（漏洞所属类型）和 `vuln_type`（漏洞类型），等页面联动完成后，再按 `page_payloads.base_info`、`page_payloads.vendor_info`、`page_payloads.detail_info` 一次性填写其余字段。
- 除导航、下拉联动确认和提交结果确认外，不要因为单个字段反复 `take_snapshot`；页面联动完成后优先用一次 `fill_form` 写完整组字段。
- 执行任何 `.py` 脚本时都使用 `python3 scripts/...`，不要写成 `python scripts/...`。
- `prepare_form_context.py` 会固化 `title_input` 和 `title_final_expected`；页面填 `title_input`，提交后用 `title_final_expected` 校验最终标题。
- `prepare_form_context.py` 会同时固化漏洞详情页默认值；选择完“漏洞类型”后，只继续填写 `description`，`漏洞URL` 固定为 `http://test.com`，其余缺失必填项统一使用“无”或“见附件”，不要再次读取 Word。
- `prepare_form_context.py` 会检查 `attachment_zip_path`；CNVD 上报必须上传该原始整包 zip。若材料目录里还没有 `CNVD-*.zip`，准备阶段会自动补建，不需要手工压缩。
- 提交验证码时先点击验证码图片刷新，再截图识别；若识别失败，就把验证码图片在新标签页打开后再截图识别，然后立即回填并提交。
- 基本信息“是否公开”必须选择“否”；漏洞描述不要带 `经恒脑AI代码审计智能体分析：` 前缀。
- 不要把其他 skill 的端口表放进本文件；跨 skill 并发说明放在 README 高级章节。
