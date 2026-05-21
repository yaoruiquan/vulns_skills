# 验证码 OCR 自动识别

## 概述

使用 ddddocr 库自动识别 CNVD 验证码，实现全自动化流程。默认不启动后台 OCR 进程，避免端口占用和旧进程代码不一致。

## 验证码类型

| 场景 | 验证码类型 | 示例 | OCR 识别率 |
|------|----------|------|-----------|
| 登录验证码 | 中文词语 | "读书"、"学习" | ~80% |
| 提交验证码 | 字母数字组合 | "db3D"、"ws7k" | ~50-70% |
| 防火墙/WAF 验证码 | 中文词语或短文本 | "地球"、"学习" | 先 OCR 3 次，失败后人工 |

## OCR 脚本

### 脚本位置

```
scripts/captcha_ocr.py         # 当前主流程：单次本地 OCR
scripts/captcha_recognize.py   # 保留脚本：不作为当前主流程默认命令
```

### 使用方法

当前真实运行路径以 `form_context.json.ocr.recognize_command` 为准：

```bash
# 登录验证码
python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd

# 提交验证码
python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd

# 防火墙验证码：先 OCR 3 次，仍失败再人工
python3 scripts/captcha_ocr.py /tmp/cnvd-waf-captcha-1.png --preprocess cnvd

# 完整流程（必须按此顺序）
python3 scripts/browser_snippets.py captcha-tab
python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd
```

普通登录验证码和提交验证码不走人工；识别失败时重新打开当前验证码图片、重新截图、重新 OCR，不复用旧标签页和旧识别结果。只有 CNVD 防火墙/WAF 访问验证码在连续 3 次 OCR 失败后才等待人工输入。

参数说明：

| 参数 | 必填 | 作用 |
|------|------|------|
| `/tmp/captcha.png` | 是 | MCP 截取的验证码图片元素本体 |
| `--preprocess cnvd` | 是 | CNVD 验证码预处理模式：自动对比度、放大，并兼容旧截图裁剪 |
| `--crop-box` | 否 | 仅用于旧截图排障；主流程不依赖 |
| `--scale` | 否 | 识别前放大倍数；`--preprocess cnvd` 会至少放大 3 倍 |

## 当前识别逻辑

### 普通验证码：captcha_ocr.py 单次识别

使用 `captcha_ocr.py`：

1. MCP 只截验证码图片元素本体到 `/tmp/captcha.png`。
2. 执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd`。
3. OCR 返回后立即用 `browser_helpers.submit_captcha_command_template` 或 `scripts/browser_snippets.py submit-captcha` 填入并提交。
4. 如果页面提示验证码错误，重新执行 `captcha-tab` 打开新验证码，重新截图和识别。
5. 如果 OCR 返回空、`ERROR` 或页面提示文字，禁止提交该值。

普通验证码的硬性边界：

- `captcha-tab` 返回 `ok=true` 后，下一步只能切到验证码图片新标签页，并截图图片元素本体；禁止调用不带 `uid` 的整页/视口截图。
- 如果因为没有图片元素而只能截整页，说明当前不是普通验证码图片页，必须回到原表单页重新执行 `captcha-tab` 或切换到防火墙验证码流程。
- 禁止从整页截图、表单页占位文字或“看不清/点击更换”等提示文字中提取 OCR。

### CNVD 防火墙/WAF：3 次 OCR 后人工

防火墙/WAF 访问验证码的识别特征包括页面标题或正文出现“本站开启了验证码保护”“请输入验证码，以继续访问”“防火墙”“WAF”等。

1. 保存当前防火墙页截图到 `logs/human-cnvd-firewall.png` 或 `logs/human-cnvd-firewall-<attempt>.png`。
2. 截取真实验证码 img 元素到 `/tmp/cnvd-waf-captcha-<attempt>.png`。
3. 执行 `python3 scripts/captcha_ocr.py /tmp/cnvd-waf-captcha-<attempt>.png --preprocess cnvd`。
4. 最多尝试 3 次，每次失败后必须刷新或换新图，不复用旧验证码和旧结果。
5. 连续 3 次仍未通过、无法取得真实验证码 img、验证码图片加载失败，或页面只剩占位文字时，等待人工输入防火墙验证码。
6. 如果 OCR 来源是真实防火墙验证码 `img` 元素本体，识别出中文词语或短文本时必须先提交，不要因为结果包含“存在”“验证码”等中文词就当作页面文字丢弃；只有 OCR 为空、以 `ERROR` 开头、确认截图不是验证码元素，或提交后仍在验证码保护页，才算本次失败。

### captcha_recognize.py 状态

`scripts/captcha_recognize.py` 保留在仓库中，作为历史包装脚本和排障备用脚本；当前 `prepare_form_context.py` 生成的主流程命令不是它。不要把普通登录验证码或提交验证码切换到 `captcha_recognize.py` 的人工回退路径。

## 自动化流程

```
┌─────────────────────────────────────────────────────────────┐
│                  验证码识别流程（必须遵守）                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 打开验证码图片新标签页                                    │
│     python3 scripts/browser_snippets.py captcha-tab          │
│         ↓                                                    │
│  2. MCP 只截验证码 img 元素到 /tmp/captcha.png                │
│     （禁止截整页/视口）                                       │
│         ↓                                                    │
│  3. 执行当前主流程 OCR 命令                                   │
│     python3 scripts/captcha_ocr.py /tmp/captcha.png \        │
│       --preprocess cnvd                                      │
│         ↓                                                    │
│  4. OCR 返回识别结果                                          │
│     ├── 成功 → 立即填入并提交                                 │
│     └── 失败 → 刷新/换图后重新截图识别                        │
│         ↓                                                    │
│  5. 仅防火墙/WAF 验证码连续 3 次 OCR 失败后等待人工输入       │
│         ↓                                                    │
│  6. 填入验证码并提交                                          │
│     同一次 evaluate_script 完成                               │
│         ↓                                                    │
│  7. 检查结果                                                 │
│     ├── 成功 → 提取 CNVD 编号                                 │
│     └── 失败 → 记录 summary 并说明失败点                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 测试验证

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 登录验证码识别 | ✓ 通过 | 中文词语"读书"正确识别 |
| 提交验证码识别 | ✓ 通过 | 字母数字"db3D"正确识别 |
| 全流程自动化 | ✓ 通过 | 新标签页登录 → 填表 → 提交 |

## 注意事项

1. **直接开图识别**：提交前不要点击刷新；执行 `python3 scripts/browser_snippets.py captcha-tab`，把当前 `#codeSpan1 img.src` 指向的 `/common/myCodeNew?t=...` 打开到新标签页。
   - 如果返回 `code=CNVD_CAPTCHA_IMAGE_BROKEN`，说明提交验证码图片没有成功加载，通常是该图片请求被 CNVD 防火墙验证码拦截。此时不要 OCR 当前页面的“看不清/点击更换”占位文字，必须保存防火墙截图，改为截取防火墙页真实验证码 img 元素，OCR 最多尝试 3 次，仍未通过再等待人工输入。
2. **只截图片元素**：新标签页只截验证码 `<img>` 元素本体到 `/tmp/captcha.png`，不要截整个视口。
3. **禁止整页截图**：验证码原图通常只有约 `80x35` 像素，整页截图会把图片缩在大画布里，ddddocr 容易返回空字符串。MCP `take_screenshot` 必须带验证码图片元素 `uid`；不带 `uid` 的截图视为流程错误。
4. **单次脚本识别**：默认执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd`，不启动或复用后台 OCR 进程。
5. **填入+提交合并**：识别结果返回后，使用一次 `evaluate_script` 设置验证码输入框并点击提交按钮，减少 MCP 往返
6. **地址校验**：`captcha-tab` 会校验验证码 URL 的 path 必须是 `/common/myCodeNew`，避免误打开页面上的其他图片
7. **失败重试**：如果页面提示验证码错误，重新执行 `captcha-tab` 打开新的验证码图片标签页并识别，不复用旧标签页和旧结果
8. **错误 OCR 防护**：只有 OCR 为空、以 `ERROR` 开头、或确认截图来自整页/占位文字而不是真实验证码图片元素时，才禁止提交；真实验证码 `img` 元素 OCR 出来的中文词语必须先提交验证。
9. **防火墙回退阈值**：防火墙验证码每次失败后必须换新图并重新截图；连续 3 次 OCR 为空、报错、无法取得真实验证码元素、提交后仍在验证码保护页或提示过期，才切换到人工输入。
## 最快稳定路径

最快路径不是反复截图页面或刷新验证码，而是固定为：

1. 原表单页执行 `captcha-tab`，读取当前 `#codeSpan1 img.src` 并新开验证码图片标签页。
   - 返回 `CNVD_CAPTCHA_IMAGE_BROKEN` 时，切换到 CNVD 防火墙验证码流程：先 OCR 3 次，仍未通过再人工。
2. MCP 只截验证码图片元素到 `/tmp/captcha.png`，不要截整个视口。
3. OCR 使用单次脚本识别，不依赖端口和后台进程。
4. 识别完成立即用一次 `submit-captcha` 脚本完成填入和提交。
