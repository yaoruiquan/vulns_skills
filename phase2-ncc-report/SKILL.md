---
name: phase2-ncc-report
description: 通过 Chrome DevTools MCP 控制真实浏览器完成 NCC 平台漏洞上报。适用于 https://www.nccsec.cn/company-center/manage-center 的企业中心漏洞材料提交、表单填写、附件上传、验证码/OCR 处理和提交结果记录。
---

# phase2-ncc-report

通过 Chrome DevTools MCP 控制真实浏览器完成 NCC 平台漏洞上报。

---

## 环境配置

### 1. 初始化

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/setup.sh
vim .env
```

`setup.sh` 会创建 `.env`、生成当前路径的 `.mcp.json`，并设置脚本可执行权限。已有 `.env` 不会被覆盖。

### 2. 必填配置

| 环境变量 | 说明 | 默认/示例 |
|----------|------|-----------|
| `NCC_PLATFORM_URL` | NCC 平台管理中心地址 | `https://www.nccsec.cn/company-center/manage-center` |
| `VULN_DATA_DIR` | 漏洞数据父目录，包含 DAS-T* 文件夹 | `/path/to/your/vulnerability/data` |
| `FORM_CONTEXT_DIR` | 运行时 `form_context.json` 暂存目录 | `/tmp/vulns-skills/phase2-ncc-report/form-contexts` |
| `PYTHON_PROJECT_PATH` | Python 项目路径，可选，用于导入共享模块 | `/path/to/your/python/project` |
| `NCC_REPORT_TEMPLATE_PATH` | NCC 通用型漏洞报告 Word 模板 | `/Users/yao/Documents/网安- AI应用开发/监管上报/NCC通用型漏洞报告模板.docx` |
| `REGULATORY_SUMMARY_DIR` | 监管上报汇总表目录 | `/Users/yao/Documents/网安- AI应用开发/监管上报/汇总表` |
| `NCC_USERNAME` | NCC 平台登录账号，可选 | 空 |
| `NCC_PASSWORD` | NCC 平台登录密码，可选 | 空 |
| `CHROME_DEBUG_PORT` | 本 skill 专用 Chrome 调试端口 | `9334` |
| `CHROME_PROFILE_NAME` | 本 skill 专用 Chrome profile | `ncc-report` |
| `DINGTALK_WEBHOOK` | 钉钉机器人 webhook，可选 | 空 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥，可选 | 空 |
| `DINGTALK_KEYWORD` | 钉钉机器人关键词，可选 | 空 |
| `DINGTALK_ENABLED` | 是否启用钉钉通知 | `true` |
| `NCC_UPLOAD_WORK_DIR` | NCC 上传 zip 运行时副本父目录；不写回源材料目录 | `/tmp` |
| `NCC_UPLOAD_MAX_MB` | NCC 附件大小限制，单位 MiB | `50` |
| `NCC_VIDEO_COMPRESS_ENABLED` | 上传 zip 超限时是否用 ffmpeg 压缩包内视频 | `true` |
| `NCC_FFMPEG_BIN` | ffmpeg 可执行文件路径或命令名 | `ffmpeg` |

兼容旧变量 `CLAUDE_CHROME_MCP_PORT` 和 `CLAUDE_CHROME_PROFILE_NAME`，但新配置优先使用 `CHROME_DEBUG_PORT` 和 `CHROME_PROFILE_NAME`。

### 3. 推荐启动方式

如果一次只跑一个浏览器型 skill，推荐每个 Claude session 都先进入对应 skill 目录再启动 Claude Code：

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
claude
```

这样 Claude 会自动读取本目录的 `.mcp.json`，使用 `ncc-chrome` 连接本 skill 的 `9334` 端口和 `ncc-report` Chrome profile。多个并发 session 分别 `cd` 到各自 skill 目录启动即可。

### 4. 浏览器配置

本 skill 默认使用：

- 调试端口：`9334`
- Chrome profile：`ncc-report`
- 启动脚本：`scripts/start-chrome-debug.sh`

```bash
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9334/json/version
```

可选模式：

- `isolated`：独立空 profile，默认模式。
- `seed-default`：复制日常 Chrome profile 快照，适合复用登录态。
- `live-default`：直接使用日常 Chrome 用户数据目录，使用前先关闭普通 Chrome。

### 5. MCP 配置

如果从本 skill 目录启动 Claude Code，`.mcp.json` 会作为项目配置使用，server 名为 `ncc-chrome`。

如果从其他项目目录启动 Claude Code，在那个项目目录注册本 skill 的 wrapper：

```bash
claude mcp add ncc-chrome -- /Users/yao/.claude/skills/phase2-ncc-report/scripts/chrome-devtools-mcp-wrapper.sh
```

本 skill 的端口/profile/MCP server 名都独立于其他浏览器型 skill；不要把它注册成通用的 `chrome-devtools`，否则会覆盖或误连到其他 wrapper。

### 6. 验证

```bash
curl -s http://127.0.0.1:9334/json/version
claude mcp get ncc-chrome
```

---

## 工作流程

| 步骤 | 操作 | 说明 |
|------|------|------|
| 0 | 检查环境 | 确认 `.env`、Chrome 调试端口和 MCP 可用 |
| 1 | 准备数据 | 先生成/复用同级 `NCC-<漏洞名>` 材料目录，再用 `prepare_form_context.py` 生成 `/tmp/vulns-skills/phase2-ncc-report/form-contexts/YYYY-MM/DAS-ID/form_context.json` |
| 2 | 登录并进入填表页 | 打开 `NCC_PLATFORM_URL`，必要时完成企业登录，再从右上角“提交漏洞”进入表单 |
| 3 | 确认表单 | 用 MCP 快照确认表单字段、下拉值和上传控件 |
| 4 | 填写表单 | 浏览器阶段只读取 `form_context.json`，按 `references/field-mapping.md` 填写漏洞信息 |
| 5 | 上传附件 | 默认只上传 `form_context.json` 中的 `upload_zip_path`；该文件是从 CNVD 材料 zip 复制/改名，或在没有现成 zip 时由 CNVD 材料目录自动打包出的 `NCC-*.zip` 运行时副本；超过 `NCC_UPLOAD_MAX_MB` 时会先用 ffmpeg 压缩包内视频并改用 `NCC-*-compressed.zip` |
| 6 | 提交前表单检查 | 上传附件后必须运行 `browser_snippets.py post-upload-audit`，确认 `ok=true`、无漏填、附件已上传后才能提交 |
| 7 | 提交验证 | 点击提交后，人工完成拖拽拼图验证 |
| 8 | 记录结果 | 读取成功页中的 `NCC-xxxx` 编号 |
| 9 | 可选通知 | 已配置 `DINGTALK_WEBHOOK` 时推送钉钉通知 |

详细步骤见 `references/workflow.md`。

---

## 脚本说明

| 脚本 | 用途 |
|------|------|
| `scripts/setup.sh` | 初始化 `.env`、`.mcp.json` 和脚本权限 |
| `scripts/start-chrome-debug.sh` | 启动本 skill 专用 Chrome |
| `scripts/chrome-devtools-mcp-wrapper.sh` | MCP wrapper，连接到 `CHROME_DEBUG_PORT` |
| `scripts/extract_vuln_data.py` | 从 `DAS` 目录或 `docx` 提取 NCC 上报字段，并识别 zip/截图/视频附件 |
| `scripts/compress_upload_zip.py` | 当上传 zip 超过限制时解包、压缩视频并重新打包 |
| `scripts/prepare_ncc_material.py` | 上报前根据 CNVD/CNNVD Word 生成 `NCC-<漏洞名>` 材料目录和 NCC 通用型漏洞报告 Word |
| `scripts/prepare_form_context.py` | 生成浏览器填表阶段唯一读取的 NCC `form_context.json` |
| `scripts/web_enrichment.py` | 信息收集阶段补全 `漏洞危害` 和 `修复方案`：Word 缺失时先 websearch，再按漏洞类型策略兜底 |
| `scripts/resolve_upload_path.py` | 上传前从 `form_context.json` 校验并输出真实 `upload_zip_path`，诊断手敲文件名错误 |
| `scripts/browser_snippets.py` | 根据 `form_context.json` 输出 NCC 页面可执行的填表、上传后漏填检查 `evaluate_script` 片段 |
| `scripts/captcha_ocr.py` | 验证码 OCR |
| `scripts/dingtalk_notify.py` | 将上报结果推送到钉钉机器人，支持关键词和链接 |

---

## 参考资料

- `references/setup-guide.md`：环境与依赖说明
- `references/workflow.md`：NCC 平台上报步骤
- `references/field-mapping.md`：字段映射
- `references/selectors.md`：平台表单选择器记录
- `references/captcha-ocr.md`：验证码 OCR
- `references/mcp-connection.md`：MCP 连接经验
- `references/mcp-tools.md`：MCP 工具参考

---

## 注意事项

- NCC 平台账号密码明文存储有风险，不要复制或分享 `.env`。
- 钉钉 webhook 属于敏感配置，只能放在 `.env`，不要写进文档或提交到 Git。
- `.env` 里只保存父目录，不保存具体某一次的 `docx` 路径；实际运行时通过 `--input-path` 或 `--docx-path` 传入。
- Step 1 默认会先生成/复用 `NCC-<漏洞名>` 材料目录；已有 NCC 目录一般不覆盖，但如果既有 Word 缺少“漏洞危害/修复方案”，准备阶段会补齐这两个审核必填字段；全量重建需显式使用 `--force-ncc-material`。
- Step 1 必须先生成 `/tmp/vulns-skills/phase2-ncc-report/form-contexts/.../form_context.json`；浏览器阶段只读这个文件，不再运行 Word 提取或 NCC 材料生成脚本。
- Step 1 生成任何材料或 JSON 前，必须先向用户确认一次“是否0Day漏洞/是否原创漏洞”的绑定值。二者绑定：是都为是，否都为否。`prepare_form_context.py` 和单独运行的 `prepare_ncc_material.py` 都优先使用 `--is-0day-original 是/否`；兼容旧参数 `--is-0day`、`--is-original`，但旧参数必须一致；不得从 Word 字段或 `.env` 兜底猜测。
- Step 1 信息收集阶段必须补齐 `impact` 和 `temporary_solution/formal_solution`。Word 没有有效“漏洞危害/修复方案”时，`web_enrichment.py` 会按标题、产品、厂商和漏洞详细分类执行 websearch，并把查询词、结果、来源写入 `security_guidance`；检索失败时按漏洞类型策略生成保守文本。浏览器阶段禁止把这两个字段填成“见附件”。
- Step 6 是硬性提交 gate：附件上传后必须执行 `post-upload-audit`，返回 `ok=true`、`missingRequired=[]`、`skippedProtected=[]`、`attachmentUploaded=true`、`exactAttachmentMatch=true`、`uploadErrors=[]` 才能点击提交。
- 钉钉通知是可选收尾动作；`--text` 中的字面量 `\n` 会被脚本转换为真实换行。
- 上传附件前必须用 `resolve_upload_path.py --context <form_context.json>` 读取真实 `filePath`；批量处理前必须用 `resolve_upload_path.py --batch-root <form_context父目录>` 扫描整批；不要手动把漏洞名里的空格改成短横线或重新拼 zip 文件名。
- 第一次开发或平台页面变化时，必须先用 MCP `take_snapshot` 更新 `references/selectors.md`，再执行填表。
- 当前已知登录页没有普通验证码；点击提交后会出现拖拽拼图验证，第一版由人工接管。
- 企业登录后如出现阿里云滑块验证，必须人工完成后再继续自动化。
- NCC 页面附件控件可能只保留最后一次上传文件；默认只上传 `upload_zip_path`，不要再补传 docx/截图/视频导致 zip 被替换。
- MP4 通常已经压缩过，zip 本身降幅有限；附件超 50MB 时必须靠 `ffmpeg` 降低视频码率/分辨率，脚本只处理运行时 zip 副本，不改源材料。
- 不要把其他 skill 的端口表放进本文件；跨 skill 并发说明放在 README 高级章节。
