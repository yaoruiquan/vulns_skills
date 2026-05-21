# CNVD 运行强约束

本文件承接 `SKILL.md` 中不适合长期放在入口的执行规则。执行时优先级：

```text
脚本输出 / form_context.json > 本文件 > workflow.md > README
```

## 数据源

- 浏览器阶段只能读取 `form_context.json`。
- 不要在浏览器阶段重新读取 Word、重新运行字段提取、重新压缩目录或重新判断标题。
- `prepare_form_context.py` 已固化 `title_input`、`title_final_expected`、`dropdown_phase`、`page_payloads`、`browser_helpers`、`ocr` 和附件路径。
- 页面填 `title_input`，提交后用 `title_final_expected` 校验最终标题。

## 页面操作

- 登录成功或进入 `/user/reportManage` 后，必须实际导航到 `/flaw/create` 或点击“立即上报漏洞”；如果当前仍在 reportManage 列表页，禁止只 `take_snapshot` 后结束。
- 进入 `/flaw/create` 后先执行 `browser_helpers.login_guard_command`。
- 如果返回 Cloudflare 或登录页，先恢复会话，不要继续填表。
- 登录验证码失败后页面可能清空密码框；每次重试前确认账号、密码、验证码都已重新填写。
- CNVD 下拉框是 Select2 组件，必须用 `browser_helpers.select2_command` 或 `scripts/browser_snippets.py select2`。
- `scripts/browser_snippets.py` 输出的是可直接传给 `Runtime.evaluate` / MCP `evaluate_script` 的 IIFE 表达式；必须原样执行。禁止把脚本改回 `() => {...}` 或 `async () => {...}` 函数定义，否则 CDP 只会返回函数对象 `{}`，页面逻辑不会真正执行。
- 不要依赖 a11y 树点击 Select2 选项，也不要只改 `<select>.value`。
- Select2 返回 `ok=false` 时先看 `results[].options`，修正字段后再继续。
- 除导航、下拉联动确认和提交结果确认外，不要为单个字段反复 `take_snapshot`。

## 字段规则

- 基本信息”是否公开”必须使用 `browser_helpers.is_open_command` 生成的脚本设置”否”（CNVD 页面有两组 radio，必须全部处理）。
- 漏洞描述不要带 `经恒脑AI代码审计智能体分析：` 前缀。
- 选择完“漏洞类型”后，只继续填写 `description`。
- `漏洞URL` 固定为 `http://test.com`。
- 其余缺失必填项统一使用 `无` 或 `见附件`，不要再回 Word 补字段。
- 附件原始来源必须是 `attachment_zip_path` 指向的 CNVD 原始整包 zip；浏览器上传时优先使用 `browser_upload_path` 指向的 ASCII 路径副本，避免 Chrome/CDP 中文路径上传失败。

## 验证码

- CNVD 验证码默认不启动后台 OCR 进程，避免端口占用和旧进程代码不一致。
- 提交验证码必须是提交前最后一步。
- 提交前不要点击刷新验证码。
- 默认执行 `browser_helpers.open_captcha_tab_command`，把当前 `/common/myCodeNew?t=...` 打开到新标签页；不要覆盖原表单页。
- 如果 `open_captcha_tab_command` 返回 `code=CNVD_CAPTCHA_IMAGE_BROKEN`，说明提交验证码图片没有加载成功，通常是 `/common/myCodeNew` 被 CNVD 防火墙验证码拦截。此时禁止 OCR 页面占位文字，必须切到防火墙验证码处理：保存防火墙截图到 `logs/human-cnvd-firewall.png`，截取真实验证码 img 元素到 `/tmp/cnvd-waf-captcha-<attempt>.png`，用 `captcha_ocr.py --preprocess cnvd` 最多尝试 3 次。
- CNVD 防火墙/WAF 访问验证码（页面出现“本站开启了验证码保护”“请输入验证码，以继续访问”）先 OCR 自动识别，最多 3 次。
- 防火墙验证码 OCR 结果为空、以 `ERROR` 开头，或提交后仍停留在验证码保护页/提示验证码过期，都算本次未通过；必须刷新/换一张后重试，不复用旧验证码和旧结果。
- 只要 OCR 来源确认是真实防火墙验证码 `img` 元素本体，就不要因为识别结果包含中文、`存在`、`验证码` 等词而判定“不是验证码”；CNVD 防火墙验证码可能就是中文词语或短文本，应先提交，再依据页面响应判断成功或重试。
- 只有 3 次 OCR 仍未通过、无法取得真实验证码 img、或页面只剩占位文字时，才等待人工输入防火墙验证码。
- 识别命令默认加 `--preprocess cnvd`。
- 切到验证码图片标签页后，只截验证码图片元素本体到 `/tmp/captcha.png`，再通过 `ocr.recognize_command` 单次本地识别。
- 禁止截整个视口或整页；CNVD 验证码原图很小，整页截图会导致 ddddocr 识别为空。
- OCR 结果返回后，用 `browser_helpers.submit_captcha_command_template` 生成脚本，立即填入并提交。
- 如果提交脚本返回 `INVALID_OCR_TEXT`，只代表 OCR 结果为空、错误输出或明显来自非验证码截图；不要提交，重新获取真实验证码图片。防火墙验证码累计 3 次仍失败后再进入人工处理。
- 验证码失败时重新执行 `captcha-tab` 打开新图，不复用旧标签页和旧结果。

## 批量上报

- 批量状态只由 `scripts/batch_report.py` 管理。
- 第一条完成环境检查后执行 `mark-env`。
- 每条提交成功后立刻执行 `record` 记录 `CNVD-ID`。
- `record` 输出 `next_command` 后直接进入下一条；第二条及之后跳过环境检查。
- 批量模式禁止单条执行 `publish_submission_zip.py --notify`。
- 全部完成后只执行一次 `batch_report.py notify <state_path>`，统一上传附件并推送一条钉钉消息。

## 通知与上传

- 监管上报类技能统一使用同一个钉钉机器人，关键词为 `监管上报`。
- `publish_submission_zip.py` 只上传单个漏洞的 CNVD 原始整包 zip，不上传整个批次目录。
- 钉钉 webhook 和密钥只能来自 `.env`，不要写进文档或提交到 Git。
