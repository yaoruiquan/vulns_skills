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
```

4. 将识别结果填入验证码输入框。

## 注意事项

- 识别失败时重新刷新验证码并截图。
- 验证码字段和图片位置需要登录后用 MCP `take_snapshot` 确认，并记录到 `selectors.md`。
- 不要在文档中保存真实验证码图片。
