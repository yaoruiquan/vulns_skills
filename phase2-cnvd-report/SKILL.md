---
name: phase2-cnvd-report
description: 使用 Chrome DevTools MCP 完成 CNVD 单个或批量漏洞上报；从 CNVD 材料目录生成 form_context.json，按脚本输出填写 CNVD 表单、上传原始 zip、提交验证码、记录 CNVD 编号，并在批量完成后统一推送钉钉。
---

# phase2-cnvd-report

CNVD 上报 skill。执行时以脚本输出和 `form_context.json` 为准，不靠临场记忆规则。

## 入口判断

- 单个上报：用户给出 `DAS-*` 目录、`CNVD-*` 目录、CNVD docx 或 DAS-ID。
- 批量上报：用户给出批次根目录，内部包含多个 `DAS-*` 目录。
- 环境初始化：用户要求安装、初始化、检查环境。

## 必读引用

- 单个上报细节：`references/workflow.md`
- 批量上报细节：`references/batch-report.md`
- 运行强约束：`references/runtime-rules.md`
- 验证码问题：`references/captcha-ocr.md`

## 执行前加载规则

开始执行本 skill 时，不要只读本文件后直接操作浏览器，必须按场景加载引用文件：

1. 所有上报任务先读 `references/runtime-rules.md`。
2. 单个上报再读 `references/workflow.md`。
3. 批量上报再读 `references/batch-report.md`，每条漏洞进入浏览器前按单个上报骨架执行。
4. 进入验证码步骤前读 `references/captcha-ocr.md`，并以 `form_context.json.ocr` 和 `browser_helpers` 为准。

## 固定命令

所有 Python 命令使用 `python3`。

环境初始化：

```bash
./scripts/setup.sh
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9332/json/version
```

单个上报先生成上下文：

```bash
python3 scripts/prepare_form_context.py "<DAS-ID或DAS目录或CNVD目录或docx路径>"
```

批量上报先创建状态：

```bash
python3 scripts/batch_report.py init "<批次目录>"
python3 scripts/batch_report.py start-next "<state_path>"
```

## 最短执行骨架

单个上报必须按以下顺序执行；详细字段和选择器以 `references/workflow.md`、脚本输出和 `form_context.json` 为准：

1. 检查 `.env`、Chrome 调试端口和 MCP 连接。
2. 执行 `prepare_form_context.py` 生成 `form_context.json`，确认 `ready=true`。
3. 先打开 `https://www.cnvd.org.cn/` 通过门户验证码，登录后再导航到 `/flaw/create`，最后执行 `browser_helpers.login_guard_command`。
4. 执行 `browser_helpers.select2_command`，等待 Select2 联动完成。
5. 只读取 `form_context.json.page_payloads` 填写文本字段，并用 `browser_helpers.is_open_command` 设置“是否公开”为“否”。
6. 上传 `attachment_zip_path` 指向的 CNVD 原始 zip。
7. 提交前执行字段完整性校验。
8. 最后处理验证码：先执行 `open_captcha_tab_command`。返回 `ok=true` 才新标签页开图并 OCR；若返回 `CNVD_CAPTCHA_IMAGE_BROKEN`，说明提交验证码图片被 CNVD 防火墙拦截，必须走前端人工防火墙验证码，不要 OCR 页面占位文字。
9. 提交成功后提取 `CNVD-ID`，再执行通知或批量记录。

批量上报必须按以下顺序执行：

1. `batch_report.py init` 创建状态文件。
2. `batch_report.py start-next` 获取第一条任务。
3. 第一条执行环境检查，成功后 `mark-env`。
4. 每条按单个上报骨架完成提交。
5. 每条成功或失败后立即 `batch_report.py record`。
6. 直接执行 `record` 输出的 `next_command` 进入下一条，第二条开始跳过环境检查。
7. 全部完成后只执行一次 `batch_report.py notify`，不要单条通知。

## 执行原则

1. 浏览器阶段只读取 `form_context.json`，不要重新读取 Word、重新压缩、重新判断标题。
2. 表单里的登录态检查、Select2 下拉框、验证码新标签页开图和验证码提交，必须使用 `form_context.json.browser_helpers` 或 `scripts/browser_snippets.py` 输出的脚本。
3. 验证码只走 MCP 截图图片元素到 `/tmp/captcha.png` 后单次脚本识别，不启动后台 OCR 进程；如果图片元素 `naturalWidth=0` 或脚本返回 `CNVD_CAPTCHA_IMAGE_BROKEN`，禁止继续 OCR，按 CNVD 防火墙验证码转前端人工处理。
4. 单个上报成功后记录 `CNVD-ID`；批量模式每条只 `record`，全部完成后只执行一次 `batch_report.py notify`。
5. 如果脚本输出、`form_context.json` 和 Markdown 文档冲突，以脚本输出和 `form_context.json` 为准。

## 关键脚本

- `scripts/prepare_form_context.py`：生成浏览器阶段唯一数据源。
- `scripts/browser_snippets.py`：生成页面内 `evaluate_script`，处理 Select2、登录态、验证码开图和提交。
- `scripts/batch_report.py`：批量状态推进、记录编号、最终统一通知。
- `scripts/publish_submission_zip.py`：上传单个 CNVD 原始 zip。
- `scripts/captcha_ocr.py`：验证码 OCR，读取截图文件并单次识别。
