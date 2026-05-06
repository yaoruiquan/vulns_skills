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
scripts/captcha_ocr.py
```

### 使用方法

```bash
# 基本用法
python3 scripts/captcha_ocr.py <图片路径>

# 示例
python3 scripts/captcha_ocr.py /tmp/captcha.png
# 输出：读书

# 默认流程：打开验证码图片新标签页，只截验证码图片本体，再由脚本单次识别
python3 scripts/browser_snippets.py captcha-tab
python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd
```

参数说明：

| 参数 | 作用 |
|------|------|
| `--preprocess cnvd` | 做对比度增强并至少放大 3 倍；直接验证码图通常不需要裁剪，但保留该参数更稳 |
| `--crop-box x1,y1,x2,y2` | 旧截图排障参数；正常 CNVD 提交流程不要使用裁剪分支 |
| `--scale 3` | OCR 前放大图片，适合验证码原图过小的情况 |

## 当前识别逻辑

当前脚本使用 `ddddocr`：

- 默认模式：每次执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd` 都会启动 Python 进程并加载一次 `ddddocr` 模型。
验证码有效期较短时，优先减少浏览器切换和截图范围，不启动后台 OCR 进程。

## 自动化流程

```
┌─────────────────────────────────────────────────────────────┐
│                      验证码自动识别流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  提交前最后一步打开验证码图片新标签页                           │
│         ↓                                                    │
│  python3 scripts/browser_snippets.py captcha-tab              │
│         ↓                                                    │
│  MCP: 只截验证码 img 元素，不截整页/视口                       │
│         ↓                                                    │
│  python3 scripts/captcha_ocr.py /tmp/captcha.png              │
│    --preprocess cnvd                                          │
│         ↓                                                    │
│  识别结果: "读书"                                             │
│         ↓                                                    │
│  同一次 evaluate_script 内完成填入验证码并点击提交              │
│         ↓                                                    │
│  检查结果 → 成功/失败                                         │
│         ├── 成功 → 继续                                       │
│         └── 失败 → 重新 captcha-tab 打开新图再识别              │
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
2. **只截图片元素**：新标签页只截验证码 `<img>` 元素本体到 `/tmp/captcha.png`，不要截整个视口。
3. **禁止整页截图**：验证码原图通常只有约 `80x35` 像素，整页截图会把图片缩在大画布里，ddddocr 容易返回空字符串。
4. **单次脚本识别**：默认执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png --preprocess cnvd`，不启动或复用后台 OCR 进程。
5. **填入+提交合并**：识别结果返回后，使用一次 `evaluate_script` 设置验证码输入框并点击提交按钮，减少 MCP 往返
6. **地址校验**：`captcha-tab` 会校验验证码 URL 的 path 必须是 `/common/myCodeNew`，避免误打开页面上的其他图片
7. **失败重试**：如果页面提示验证码错误，重新执行 `captcha-tab` 打开新的验证码图片标签页并识别，不复用旧标签页和旧结果
## 最快稳定路径

最快路径不是反复截图页面或刷新验证码，而是固定为：

1. 原表单页执行 `captcha-tab`，读取当前 `#codeSpan1 img.src` 并新开验证码图片标签页。
2. MCP 只截验证码图片元素到 `/tmp/captcha.png`，不要截整个视口。
3. OCR 使用单次脚本识别，不依赖端口和后台进程。
4. 识别完成立即用一次 `submit-captcha` 脚本完成填入和提交。
