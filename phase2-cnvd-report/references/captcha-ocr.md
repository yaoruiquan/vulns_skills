# 验证码 OCR 自动识别

## 概述

使用 ddddocr 库自动识别 CNVD 验证码，实现全自动化流程。优先启动常驻服务，只在本地保持一份模型实例，避免每次提交时重复加载。

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

# 加速模式：先启动常驻 OCR 服务，模型只加载一次
python3 scripts/captcha_ocr.py --serve --port 18765

# 之后每次识别走本地服务，避免重复加载 ddddocr
python3 scripts/captcha_ocr.py /tmp/captcha.png --server-url http://127.0.0.1:18765

# 固定流程：先用 captcha-tab 打开验证码图片新标签页，再截图识别
python3 scripts/browser_snippets.py captcha-tab
python3 scripts/captcha_ocr.py /tmp/captcha.png --server-url http://127.0.0.1:18765 --preprocess cnvd

# 也可以通过环境变量配置
export CAPTCHA_OCR_SERVER_URL=http://127.0.0.1:18765
python3 scripts/captcha_ocr.py /tmp/captcha.png
```

参数说明：

| 参数 | 作用 |
|------|------|
| `--preprocess cnvd` | 做对比度增强并至少放大 3 倍；直接验证码图通常不需要裁剪，但保留该参数更稳 |
| `--crop-box x1,y1,x2,y2` | 旧截图排障参数；正常 CNVD 提交流程不要使用裁剪分支 |
| `--scale 3` | OCR 前放大图片，适合验证码原图过小的情况 |

## 当前识别逻辑

当前脚本使用 `ddddocr`：

- 普通模式：每次执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png` 都会启动 Python 进程并加载一次 `ddddocr` 模型。
- 加速模式：执行 `python3 scripts/captcha_ocr.py --serve --port 18765` 后，OCR 模型常驻内存；后续识别只把图片发给本地服务，速度明显更快。

验证码有效期较短时，优先使用加速模式。

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
│  MCP: 切到新标签页，只截验证码图片本体                          │
│    filePath: "/tmp/captcha.png"                              │
│         ↓                                                    │
│  python3 scripts/captcha_ocr.py /tmp/captcha.png              │
│    --server-url http://127.0.0.1:18765 --preprocess cnvd      │
│         ↓                                                    │
│  识别结果: "读书"                                             │
│         ↓                                                    │
│  同一次 evaluate_script 内完成填入验证码并点击提交              │
│         ↓                                                    │
│  检查结果 → 成功/失败                                         │
│         ├── 成功 → 继续                                       │
│         └── 失败 → 重新执行 captcha-tab 打开新图再识别          │
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

1. **直接开图识别**：提交前不要点击刷新；直接执行 `python3 scripts/browser_snippets.py captcha-tab`，把当前 `#codeSpan1 img.src` 指向的 `/common/myCodeNew?t=...` 打开到新标签页
2. **不覆盖表单页**：验证码图片必须用新标签页打开，原表单页保持不动；识别后回到原表单页提交
3. **加速优先**：验证码刷新太快时，先启动 `python3 scripts/captcha_ocr.py --serve --port 18765`，后续识别统一走 `--server-url`
4. **填入+提交合并**：识别结果返回后，使用一次 `evaluate_script` 设置验证码输入框并点击提交按钮，减少 MCP 往返
5. **地址校验**：`captcha-tab` 会校验验证码 URL 的 path 必须是 `/common/myCodeNew`，避免误打开页面上的其他图片
6. **失败重试**：如果页面提示验证码错误，重新执行 captcha-tab 打开新的验证码图片标签页并识别，不复用旧标签页和旧结果

## 最快稳定路径

最快路径不是反复截图页面或刷新验证码，而是固定为：

1. 原表单页只执行一次 `captcha-tab`，读取当前 `#codeSpan1 img.src` 并新开标签页。
2. 新标签页只截验证码图片本体，避免识别到“看不清？点击更换”等干扰文字。
3. OCR 常驻服务提前启动，识别命令走 `--server-url`，避免每次加载模型。
4. 识别完成立即回原表单页，用一次 `submit-captcha` 脚本完成填入和提交。
