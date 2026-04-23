# 验证码 OCR 自动识别

## 概述

使用 ddddocr 库自动识别 CNVD 验证码，实现全自动化流程。

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

# 也可以通过环境变量配置
export CAPTCHA_OCR_SERVER_URL=http://127.0.0.1:18765
python3 scripts/captcha_ocr.py /tmp/captcha.png
```

## 当前识别逻辑

当前脚本使用 `ddddocr`：

- 普通模式：每次执行 `python3 scripts/captcha_ocr.py /tmp/captcha.png` 都会启动 Python 进程并加载一次 `ddddocr` 模型。
- 加速模式：执行 `python3 scripts/captcha_ocr.py --serve --port 18765` 后，OCR 模型常驻内存；后续识别只把图片发给本地服务，速度明显更快。

验证码刷新太快时，优先使用加速模式。

## 自动化流程

```
┌─────────────────────────────────────────────────────────────┐
│                      验证码自动识别流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  提交前最后一步刷新验证码                                      │
│         ↓                                                    │
│  MCP: take_screenshot，只截验证码图片区域                      │
│    filePath: "/tmp/captcha.png"                              │
│         ↓                                                    │
│  python3 scripts/captcha_ocr.py /tmp/captcha.png              │
│    --server-url http://127.0.0.1:18765                       │
│         ↓                                                    │
│  识别结果: "读书"                                             │
│         ↓                                                    │
│  同一次 evaluate_script 内完成填入验证码并点击提交              │
│         ↓                                                    │
│  检查结果 → 成功/失败                                         │
│         ├── 成功 → 继续                                       │
│         └── 失败 → 重新截图识别                               │
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

1. **识别失败处理**：OCR 识别率不是 100%，失败时重新截图并重试
2. **验证码刷新**：验证码必须放到提交前最后一步处理；不要在识别后再 `take_snapshot`、检查字段或等待人工判断，否则验证码可能刷新
3. **加速优先**：验证码刷新太快时，先启动 `python3 scripts/captcha_ocr.py --serve --port 18765`，后续识别统一走 `--server-url`
4. **填入+提交合并**：识别结果返回后，使用一次 `evaluate_script` 设置验证码输入框并点击提交按钮，减少 MCP 往返
5. **失败重试**：如果页面提示验证码错误，立即重新截图当前验证码并重试，不复用旧识别结果
