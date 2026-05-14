---
name: phase2-cnnvd-report
description: 使用 Chrome DevTools MCP 完成 CNNVD 单个或批量漏洞上报；从 CNNVD 材料目录生成 form_context.json，按准备阶段固化的 dropdown_plan 和 page_payloads 填写表单、上传验证材料、提交验证码、记录 CNNVD 编号，并在批量完成后统一推送钉钉。
---

# phase2-cnnvd-report

CNNVD 上报 skill。执行时以脚本输出和 `form_context.json` 为准，不靠临场记忆规则。

## 入口判断

- 单个上报：用户给出 `DAS-*` 目录、`CNNVD-*` 目录、CNNVD docx 或 DAS-ID。
- 批量上报：用户给出批次根目录，内部包含多个 `DAS-*` 目录。
- 环境初始化：用户要求安装、初始化、检查环境。
- 汇总表维护：用户要求补录或更新 CNNVD 汇总表。

## 必读引用

- 数据准备：`references/data-preparation.md`
- 字段填写：`references/data-fields.md`
- 下拉选项：`references/dropdown-options.md`
- 漏洞类型级联：`references/vuln-type-mapping.md`
- 批量上报：`references/batch-report.md`
- 运行强约束：`references/runtime-rules.md`
- 验证码问题：`references/captcha-ocr.md`
- 汇总表更新：`references/summary-table.md`

## 执行前加载规则

开始执行本 skill 时，不要只读本文件后直接操作浏览器，必须按场景加载引用文件：

1. 所有上报任务先读 `references/runtime-rules.md`。
2. 单个上报再读 `references/data-preparation.md`、`references/data-fields.md` 和 `references/dropdown-options.md`。
3. 选择漏洞类型级联时读 `references/vuln-type-mapping.md`。
4. 批量上报再读 `references/batch-report.md`，每条漏洞进入浏览器前按单个上报骨架执行。
5. 进入验证码步骤前读 `references/captcha-ocr.md`，并以 `form_context.json.ocr` 为准。
6. 用户要求更新汇总表时读 `references/summary-table.md`。

## 固定命令

所有 Python 命令使用 `python3`。

环境初始化：

```bash
./scripts/setup.sh
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9333/json/version
```

单个上报先生成上下文：

```bash
python3 scripts/prepare_form_context.py "<DAS-ID或DAS目录或CNNVD目录或docx路径>"
```

批量上报先创建状态：

```bash
python3 scripts/batch_report.py init "<批次目录>"
python3 scripts/batch_report.py start-next "<state_path>"
```

## 最短执行骨架

单个上报必须按以下顺序执行；详细字段和页面选择以引用文件、脚本输出和 `form_context.json` 为准：

1. 检查 `.env`、Chrome 调试端口和 MCP 连接。
2. 执行 `prepare_form_context.py` 生成 `form_context.json`，确认 `ready=true`。
3. 打开 CNNVD 通用型漏洞报送页面并恢复登录态。
4. 第 1 页只按 `dropdown_plan` / `page_payloads.page1_dropdowns` 处理漏洞类型、漏洞自评级、受影响实体分类三个必填下拉框。
5. 第 1 页文本字段、第 2 页漏洞详情、第 3 页验证信息都只读取 `page_payloads`，每页一次性填写。
6. 第 3 页上传 `verification_video_path` 和 `poc_file_path`，不要重新压缩或临时找文件。
7. 提交前检查必填下拉框、描述长度、验证过程、视频和 PoC 路径。
8. 如遇验证码，最后一步截图识别，OCR 后立即填入并提交。
9. 提交成功后提取 `CNNVD-ID`，再执行通知、批量记录或汇总表更新。

批量上报必须按以下顺序执行：

1. `batch_report.py init` 创建状态文件。
2. `batch_report.py start-next` 获取第一条任务。
3. 第一条执行环境检查，成功后 `mark-env`。
4. 每条按单个上报骨架完成提交。
5. 每条成功或失败后立即 `batch_report.py record`。
6. 直接执行 `record` 输出的 `next_command` 进入下一条，第二条开始跳过环境检查。
7. 全部完成后只执行一次 `batch_report.py notify`，不要单条通知。

## 执行原则

1. 浏览器阶段只读取 `form_context.json`，不要重新读取 Word、重新运行提取脚本、重新压缩、重新总结验证过程。
2. 页面填写优先使用 `dropdown_plan` 和 `page_payloads`，不要因为单个字段反复 `take_snapshot`。
3. 验证码只走 MCP 截图图片元素到 `/tmp/captcha.png` 后单次脚本识别，不启动后台 OCR 进程。
4. 批量模式每条只 `record`，全部完成后只执行一次 `batch_report.py notify`。
5. 如果脚本输出、`form_context.json` 和 Markdown 文档冲突，以脚本输出和 `form_context.json` 为准。

## 关键脚本

- `scripts/prepare_form_context.py`：生成浏览器阶段唯一数据源。
- `scripts/batch_report.py`：批量状态推进、记录编号、最终统一通知。
- `scripts/captcha_ocr.py`：验证码 OCR，读取截图文件并单次识别。
- `scripts/upload_cnnvd_attachments.py`：通过 CNNVD 上传接口上传第 3 页视频和 PoC，并生成回填 Vue 上传组件状态的浏览器脚本。
- `scripts/publish_submission_zip.py`：上传单个 CNNVD 原始 zip。
- `scripts/update_summary.py`：更新漏洞汇总表。
- `scripts/start-chrome-debug.sh`：启动本 skill 专用 Chrome。
- `scripts/chrome-devtools-mcp-wrapper.sh`：连接本 skill 的 Chrome 调试端口。
