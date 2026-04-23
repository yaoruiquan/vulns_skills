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

### 2. 必填配置

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `VULN_DATA_DIR` | 漏洞数据根目录，包含 DAS-T* 文件夹 | `/path/to/your/vulnerability/data` |
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

### 3. 浏览器配置

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

### 4. MCP 配置

如果从本 skill 目录启动 Claude Code，`.mcp.json` 会作为项目配置使用，server 名为 `cnvd-chrome`。

如果从其他项目目录启动 Claude Code，在那个项目目录注册本 skill 的 wrapper：

```bash
claude mcp add cnvd-chrome -- /Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

本 skill 的端口/profile/MCP server 名都独立于其他浏览器型 skill；不要把它注册成通用的 `chrome-devtools`，否则会覆盖或误连到其他 wrapper。

### 5. 验证

```bash
curl -s http://127.0.0.1:9332/json/version
claude mcp get cnvd-chrome
```

---

## 工作流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 0 | 检查环境 | 确认 `.env`、Chrome 调试端口和 MCP 可用 |
| 1 | 准备数据 | 用 `prepare_form_context.py` 生成 `CNVD-xxx/form_context.json` |
| 2 | 导航表单 | 打开 CNVD、登录、进入漏洞上报表单 |
| 3 | 填写表单 | 浏览器阶段只读取 `form_context.json`，填写厂商、产品、版本和漏洞详情 |
| 4 | 上传附件 | 上传 `form_context.json` 中 `attachment_zip_path` 指向的 CNVD 原始整包 zip |
| 5 | 验证提交 | OCR 识别验证码，提交后提取并记录 `CNVD-xxxx` 编号 |
| 6 | 钉钉通知 | 已配置 `DINGTALK_WEBHOOK` 时上传单漏洞 CNVD zip，并推送漏洞名称、`DAS-ID`、`CNVD 编号` 和下载链接 |

详细步骤见 `references/workflow.md`。

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/setup.sh` | 初始化 `.env`、`.mcp.json` 和脚本权限 |
| `scripts/start-chrome-debug.sh` | 启动本 skill 专用 Chrome |
| `scripts/chrome-devtools-mcp-wrapper.sh` | MCP wrapper，连接到 `CHROME_DEBUG_PORT` |
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
- `publish_submission_zip.py` 只上传单个漏洞的 CNVD 原始整包 zip，不上传整个批次目录，也不重新压缩。
- 优先使用 `seed-default` 复用登录态；`live-default` 只在必要时使用。
- 浏览器阶段只能读取 `CNVD-xxx/form_context.json`；不要在第二阶段重新运行提取脚本、重新压缩目录或重新判断标题。
- `prepare_form_context.py` 会固化 `title_input` 和 `title_final_expected`；页面填 `title_input`，提交后用 `title_final_expected` 校验最终标题。
- `prepare_form_context.py` 会检查 `attachment_zip_path`；CNVD 上报必须上传该原始整包 zip，不要重新压缩 docx 目录。
- 基本信息“是否公开”必须选择“否”；漏洞描述不要带 `经恒脑AI代码审计智能体分析：` 前缀。
- 不要把其他 skill 的端口表放进本文件；跨 skill 并发说明放在 README 高级章节。
