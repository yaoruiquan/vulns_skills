# 验证码 OCR

NCC 平台如出现图片验证码，可使用 `scripts/captcha_ocr.py` 识别。

## 依赖

```bash
pip3 install ddddocr
```

## 使用方式

1. 通过 MCP 截取验证码图片。
2. 保存到本地临时文件，例如 `/tmp/ncc-captcha.png`。
3. 运行 OCR：

```bash
python3 scripts/captcha_ocr.py /tmp/ncc-captcha.png

# 加速模式：先启动常驻 OCR 服务，模型只加载一次
python3 scripts/captcha_ocr.py --serve --port 18765

# 之后每次识别走本地服务，避免重复加载 ddddocr
python3 scripts/captcha_ocr.py /tmp/ncc-captcha.png --server-url http://127.0.0.1:18765
```

4. 将识别结果填入验证码输入框。

## 注意事项

- 识别失败时重新刷新验证码并截图。
- 验证码刷新较快时，优先使用 `--serve` 常驻 OCR 服务；识别结果返回后不要再 `take_snapshot`，直接填入并提交。
- 验证码字段和图片位置需要登录后用 MCP `take_snapshot` 确认，并记录到 `selectors.md`。
- 不要在文档中保存真实验证码图片。
