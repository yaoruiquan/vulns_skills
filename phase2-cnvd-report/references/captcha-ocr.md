# 验证码 OCR 自动识别

## 概述

使用 ddddocr 库自动识别 CNVD 验证码，实现全自动化流程。默认不启动后台 OCR 进程，避免端口占用和旧进程代码不一致。

## 验证码类型

| 场景 | 验证码类型 | 示例 | OCR 识别率 |
|------|----------|------|-----------|
| 登录验证码 | 中文词语 | "读书"、"学习" | ~80% |
| 提交验证码 | 字母数字组合 | "db3D"、"ws7k" | ~50-70% |

## OCR 脚本

### 脚本位置

```
scripts/captcha_recognize.py  # 推荐：带人工回退
scripts/captcha_ocr.py         # 纯 OCR，无回退
```

### 使用方法

**必须使用带人工回退的 captcha_recognize.py**：

```bash
# 登录验证码
python3 scripts/captcha_recognize.py /tmp/captcha.png \
  --context login \
  --max-ocr-attempts 2 \
  --state-file /tmp/captcha_state_login.json

# 提交验证码
python3 scripts/captcha_recognize.py /tmp/captcha.png \
  --context submit \
  --max-ocr-attempts 2 \
  --state-file /tmp/captcha_state_submit.json

# 完整流程（必须按此顺序）
python3 scripts/browser_snippets.py captcha-tab
python3 scripts/captcha_recognize.py /tmp/captcha.png \
  --context login \
  --state-file /tmp/captcha_state_login.json
```

**禁止使用 captcha_ocr.py**（无人工回退，识别率低时会无限循环）

参数说明：

| 参数 | 必填 | 作用 |
|------|------|------|
| `--context login/submit` | 是 | 验证码上下文，用于区分登录和提交验证码 |
| `--state-file <path>` | 是 | 状态文件路径，用于跨调用计数失败次数 |
| `--max-ocr-attempts 2` | 否 | OCR 最大尝试次数，默认 2，超过后切换到人工识别 |
| `--preprocess cnvd` | 否 | OCR 预处理模式，默认已启用 |

## 当前识别逻辑

### OCR + 人工回退（推荐）

使用 `captcha_recognize.py`：

1. **前 N 次**：使用 `ddddocr` 自动识别
2. **第 N+1 次**：OCR 失败次数达到阈值，自动切换到人工识别
3. **状态持久化**：通过 `--state-file` 跨调用计数失败次数
4. **成功后重置**：登录成功后删除状态文件，重置计数

### 纯 OCR（不推荐）

使用 `captcha_ocr.py`：

- 每次执行都会启动 Python 进程并加载一次 `ddddocr` 模型
- 不含失败计数和人工回退机制
- 适合测试或确定 OCR 识别率高的场景

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
│  3. 执行带人工回退的识别脚本                                  │
│     python3 scripts/captcha_recognize.py /tmp/captcha.png \  │
│       --context login \                                      │
│       --state-file /tmp/captcha_state_login.json             │
│         ↓                                                    │
│  4. OCR 识别（前 2 次）                                       │
│     ├── 成功 → 返回识别结果                                   │
│     └── 失败 → 计数 +1，刷新验证码重试                        │
│         ↓                                                    │
│  5. 失败 2 次后自动切换人工识别                               │
│     脚本输出 "MANUAL_INPUT_REQUIRED"                          │
│     等待前端用户输入验证码                                    │
│         ↓                                                    │
│  6. 填入验证码并提交                                          │
│     同一次 evaluate_script 完成                               │
│         ↓                                                    │
│  7. 检查结果                                                 │
│     ├── 成功 → 删除状态文件，重置计数                         │
│     └── 失败 → 保持计数，继续人工识别                         │
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
   - 如果返回 `code=CNVD_CAPTCHA_IMAGE_BROKEN`，说明提交验证码图片没有成功加载，通常是该图片请求被 CNVD 防火墙验证码拦截。此时不要 OCR 当前页面的“看不清/点击更换”占位文字，必须保存防火墙截图并等待前端人工输入。
2. **只截图片元素**：新标签页只截验证码 `<img>` 元素本体到 `/tmp/captcha.png`，不要截整个视口。
3. **禁止整页截图**：验证码原图通常只有约 `80x35` 像素，整页截图会把图片缩在大画布里，ddddocr 容易返回空字符串。
4. **单次脚本识别**：默认执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd`，不启动或复用后台 OCR 进程。
5. **填入+提交合并**：识别结果返回后，使用一次 `evaluate_script` 设置验证码输入框并点击提交按钮，减少 MCP 往返
6. **地址校验**：`captcha-tab` 会校验验证码 URL 的 path 必须是 `/common/myCodeNew`，避免误打开页面上的其他图片
7. **失败重试**：如果页面提示验证码错误，重新执行 `captcha-tab` 打开新的验证码图片标签页并识别，不复用旧标签页和旧结果
8. **错误 OCR 防护**：如果 OCR 结果包含“看不清”“点击更换”“存在”“二进制”“验证码”等页面文字，说明截图范围或图片加载状态错误，禁止提交。
## 最快稳定路径

最快路径不是反复截图页面或刷新验证码，而是固定为：

1. 原表单页执行 `captcha-tab`，读取当前 `#codeSpan1 img.src` 并新开验证码图片标签页。
   - 返回 `CNVD_CAPTCHA_IMAGE_BROKEN` 时，切换到 CNVD 防火墙人工验证码流程。
2. MCP 只截验证码图片元素到 `/tmp/captcha.png`，不要截整个视口。
3. OCR 使用单次脚本识别，不依赖端口和后台进程。
4. 识别完成立即用一次 `submit-captcha` 脚本完成填入和提交。
