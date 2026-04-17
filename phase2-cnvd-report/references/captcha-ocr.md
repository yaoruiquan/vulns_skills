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

# 静默模式（只输出结果）
python3 scripts/captcha_ocr.py /tmp/captcha.png 2>/dev/null | tail -1
```

### 脚本实现

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import ddddocr

def recognize_captcha(image_path: str) -> str:
    """识别验证码图片"""
    ocr = ddddocr.DdddOcr()
    with open(image_path, 'rb') as f:
        image_data = f.read()
    result = ocr.classification(image_data)
    return result.strip()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python captcha_ocr.py <图片路径>")
        sys.exit(1)
    result = recognize_captcha(sys.argv[1])
    print(result)
```

## 自动化流程

```
┌─────────────────────────────────────────────────────────────┐
│                      验证码自动识别流程                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  MCP: take_screenshot                                        │
│    filePath: "/tmp/captcha.png"                              │
│    uid: "<验证码图片的 uid>"                                  │
│         ↓                                                    │
│  python3 scripts/captcha_ocr.py /tmp/captcha.png             │
│         ↓                                                    │
│  识别结果: "读书"                                             │
│         ↓                                                    │
│  MCP: fill                                                   │
│    uid: "<验证码输入框的 uid>"                                │
│    value: "读书"                                             │
│         ↓                                                    │
│  MCP: click                                                  │
│    uid: "<提交按钮的 uid>"                                    │
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
2. **验证码刷新**：点击"换一张"可以刷新验证码
3. **静默模式**：使用 `2>/dev/null | tail -1` 只获取识别结果，过滤欢迎信息