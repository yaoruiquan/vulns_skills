# CNNVD 运行强约束

本文件承接 `SKILL.md` 中不适合长期放在入口的执行规则。执行时优先级：

```text
脚本输出 / form_context.json > 本文件 > data-preparation.md > data-fields.md > README
```

## 数据源

- 浏览器阶段只能读取 `form_context.json`。
- 不要在浏览器阶段重新读取 Word、重新运行 `extract_vuln_data.py`、重新总结验证过程或重新压缩目录。
- `prepare_form_context.py` 已固化 `dropdown_plan`、`page_payloads`、`ocr`、附件路径和钉钉收尾信息。
- `ready` 必须为 `true` 才能进入浏览器阶段；如为 `false`，先修复 `checks` 中失败项。

## 页面操作

- CNNVD 表单只填写带 danger/红色必填标记的字段。
- 第 1 页只操作三个必填下拉框：漏洞类型、漏洞自评级、受影响实体分类。
- 漏洞类型级联必须点击最终叶子选项前面的圆圈/单选按钮完成选择，不要只点击文字，也不要按 Escape 关闭。
- 每页优先按 `page_payloads` 一次性填写，不要因为单个字段反复 `take_snapshot`。
- 第 2 页只填 `page_payloads.page2_text.description`、`technical_support`、`contact`。
- `漏洞描述或简介` 最多 255 字，只填 `description`，不要改用 `description_full`。
- 第 3 页只填 `page_payloads.page3_text.verification`，不要直接粘贴 `verification_source` 或 Word 原文。
- 第 3 页必须上传 `verification_video_path` 和 `poc_file_path`；路径为空或不存在时先回到数据准备阶段修复。

## 验证过程

- 验证过程必须是一段压缩总结后的文字，包含入口点、触发条件、关键利用步骤和验证结果。
- 不插入图片，不粘贴大段 HTTP 报文、Cookie、代码或 Word 图片占位。
- 如果 `verification` 为空，必须先补齐 `form_context.json`，不要在页面里临时编写。

## 验证码

- CNNVD OCR 默认端口 `18766`；CNVD 默认 `18765`。
- 提交验证码必须是提交前最后一步。
- 如遇验证码，优先使用 `form_context.json.ocr.start_command` 启动常驻服务。
- 识别后立即填入并提交，不要再执行 `take_snapshot`、字段复核或长时间等待。
- 验证码失败时重新截图当前验证码并重试，不复用旧识别结果。

## 批量上报

- 批量状态只由 `scripts/batch_report.py` 管理。
- 第一条完成环境检查后执行 `mark-env`。
- 每条提交成功后立刻执行 `record` 记录 `CNNVD-ID`。
- `record` 输出 `next_command` 后直接进入下一条；第二条及之后跳过环境检查。
- 批量模式禁止单条执行 `publish_submission_zip.py --notify`。
- 全部完成后只执行一次 `batch_report.py notify <state_path>`，统一上传附件并推送一条钉钉消息。

## 通知与汇总表

- 监管上报类技能统一使用同一个钉钉机器人，关键词为 `监管上报`。
- `publish_submission_zip.py` 只上传单个漏洞的 CNNVD 原始整包 zip，不上传整个批次目录。
- 钉钉 webhook 和密钥只能来自 `.env`，不要写进文档或提交到 Git。
- 用户要求更新汇总表时使用 `scripts/update_summary.py`，并先读取 `references/summary-table.md`。
