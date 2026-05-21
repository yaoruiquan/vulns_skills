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
- 第 3 页附件上传不要优先使用 MCP `upload_file`。CNNVD 页面是 Vue/Element UI 自定义上传组件，隐藏 input 可能出现“工具返回成功但组件 fileList 为空”。默认使用 `scripts/upload_cnnvd_attachments.py` 先调用 CNNVD 上传接口，再通过脚本生成的 `handleChange` 流程喂给 Vue 组件，触发组件内部上传和表单校验。

## 附件上传确定性流程

1. 在浏览器页通过 `chrome-devtools-cnnvd_evaluate_script` 读取登录 token，示例只返回 token 给当前执行上下文，不写入日志：

   ```javascript
   () => localStorage.getItem('token') || sessionStorage.getItem('token') || ''
   ```

2. 把 token 写入临时文件或通过 stdin 传给脚本，禁止把 token 写进 `output/`、`summary.txt`、Git 或最终回复。
3. 上传附件：

   ```bash
   python3 scripts/upload_cnnvd_attachments.py \
     --form-context "<form_context.json>" \
     --token-stdin \
     --output "<logs_dir>/cnnvd-uploaded-attachments.json" \
     --apply-js "<logs_dir>/cnnvd-apply-upload-state.js"
   ```

4. 用 `chrome-devtools-cnnvd_evaluate_script` 执行 `logs/cnnvd-apply-upload-state.js` 中的函数，确认返回 `success=true` 且 video、poc 两项均成功；每项成功模式必须是 `mode=handleChange`，不要接受 `direct-fileList`。
5. `apply-upload-state.js` 会从 CNNVD 返回的 server file URL 拉取文件 Blob，构造 `File`/`DataTransfer`，再调用组件 `handleChange`。这是 CNNVD Vue 组件校验需要的正式路径，不是本地文件绕路。
6. 大视频会在组件内重新上传，等待时间按文件大小放大，13MB 左右视频允许等待 3 分钟以上；不要因为 10 秒内 `fileList` 未 success 就判定失败。
7. 如果 `fetch` server file URL 失败、组件没有 `handleChange`/file input、或等待超时，必须判定附件上传失败并记录失败原因；禁止 fallback 为直接写 `comp.fileList` 后继续提交，因为表单校验不认可这个状态。
8. 只有在脚本上传接口失败时，才退回手工 DOM 调试；不要启动长期 HTTP server，也不要依赖临时本地地址给 CNNVD 页面 fetch 本地文件。

## 最终提交按钮无响应处理

- 第 3 页附件上传成功后，必须写入进度 `stage=submit,status=running,label=CNNVD 最终提交`，再处理验证码和提交。
- 最终提交按钮只按明确按钮文案定位：`提 交` 或 `提交`。不要用页面静态文字 `CNNVD` 作为等待、成功或失败判断条件。
- 点击前先检查按钮是否 disabled/loading，以及页面是否有明确校验错误（如 `请填写`、`不能为空`、`请选择`、`格式不正确`）。如有校验错误，记录失败原因后停止。
- 点击最终提交最多尝试 3 次。每次点击后等待 8-10 秒，只接受以下显式信号：
  - 验证码弹窗、验证码输入框或验证码图片出现；
  - `提交成功`、`报送成功`、`操作成功` 等平台成功提示；
  - 页面跳转到工作台、我的漏洞、漏洞列表等提交后页面；
  - 页面出现新的 `CNNVD-\d{4}-\d+` 编号；
  - 明确表单校验错误，例如 `请填写`、`不能为空`、`请选择`。
- 每次点击后必须确认页面、弹窗、网络请求或按钮状态至少一项发生变化；如果 3 次后仍无变化，判定为 CNNVD 前端提交未触发，而不是附件上传失败。
- 3 次点击均无响应时必须写入：
  - 记录“CNNVD 提交按钮无响应”；
  - 说明附件已上传成功，但最终提交没有触发平台响应；
  - 停止任务，不要继续反复截图或重复上传附件。

## 验证过程

- 验证过程必须是一段压缩总结后的文字，包含入口点、触发条件、关键利用步骤和验证结果。
- 不插入图片，不粘贴大段 HTTP 报文、Cookie、代码或 Word 图片占位。
- 如果 `verification` 为空，必须先补齐 `form_context.json`，不要在页面里临时编写。

## 验证码

- 登录页如果已经填写账号、密码或验证码，并保存了 `logs/login-page.png`，不能把任务停在 `stage=browser,status=running` 后静默退出。
- 登录验证码识别后必须立即点击 `登 录`，并等待明确结果：进入用户中心/上报页、出现登录错误提示、验证码错误提示或验证码刷新。
- 登录验证码不要用 `evaluate_script` 返回 `data:image/...;base64,...` 再保存；MCP 会截断长输出，导致图片损坏和 OCR `broken data stream`。
- 登录验证码固定流程：
  1. 用 `take_screenshot` 保存整页截图到 `logs/login-page.png`；
  2. 用 `evaluate_script` 只返回验证码输入框右侧最近图片的 `{x,y,width,height,viewportWidth,viewportHeight}` 坐标，不返回 `src` 或 base64；
  3. 执行 `python3 scripts/crop_captcha_from_screenshot.py --screenshot "<logs_dir>/login-page.png" --output /tmp/captcha.png --x <x> --y <y> --width <width> --height <height> --viewport-width <viewportWidth> --viewport-height <viewportHeight>`；
  4. 执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png`；
  5. 识别后立即填入验证码并点击 `登 录`。
- 验证码图片定位不要按“第几张图片”猜。必须以验证码输入框为锚点，选择同一水平区域、位于输入框右侧、尺寸大于 80x25 的最近 `img/canvas`。
- 如果裁剪结果小于 80x25，说明坐标缩放或元素定位错误，必须重新取 `window.innerWidth/innerHeight` 和元素 `getBoundingClientRect()`，不要继续 OCR。
- CNNVD 登录验证码按字母数字处理；不要因为 OCR 为空或短结果就假设它是中文词语验证码。是否中文只以实际裁剪图片可见内容为准。
- 登录最多尝试 3 次。每次失败都必须重新截取当前验证码，不复用旧识别结果。
- 3 次后仍未登录成功时必须记录“CNNVD 登录未完成”，说明停在登录页、是否已保存 `login-page.png`、验证码/OCR/平台提示的可见原因，然后停止任务，不要继续进入表单填写、附件上传或最终提交。
- CNNVD 验证码默认不启动后台 OCR 进程，避免端口占用和旧进程代码不一致。
- 提交验证码必须是提交前最后一步。
- 如遇验证码，只截验证码图片元素到 `/tmp/captcha.png`，再执行 `form_context.json.ocr.recognize_command` 单次本地识别。
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
