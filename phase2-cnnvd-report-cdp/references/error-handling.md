# 错误处理指南

## 常见错误

### 1. Chrome 连接失败

**错误信息**: `❌ Chrome 未运行或调试端口未开启`

**解决方案**:
```bash
# 启动 Chrome 调试模式
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-profile
```

### 2. WebSocket 连接超时

**错误信息**: `WebSocket connection timeout`

**可能原因**:
- Chrome 已关闭
- 端口被占用
- 防火墙阻止

**解决方案**:
```bash
# 检查端口
lsof -i :9222

# 清理进程
pkill -f "chrome-debug-profile"

# 重启 Chrome
```

### 3. 元素未找到

**错误信息**: `not_found: #xxx`

**可能原因**:
- 页面未加载完成
- 表单类型未切换
- 选择器错误

**解决方案**:
```python
# 等待元素
browser.wait_for_selector('#title1', timeout=10)

# 切换表单类型
browser.select('#isEvent1', '0')
browser.wait(1)
```

### 4. 表单类型错误

**症状**: 填写的值不显示在页面上

**原因**: CNVD 有两种表单模式：
- 事件型漏洞: 元素 ID 无后缀 (`title`, `description`)
- 通用型漏洞: 元素 ID 有 `1` 后缀 (`title1`, `description1`)

**解决方案**:
```python
# 必须触发 change 事件
browser.eval_js("""
    const isEvent = document.getElementById('isEvent1');
    isEvent.value = '0';
    isEvent.dispatchEvent(new Event('change', {bubbles: true}));
""")
```

### 5. 文件上传失败

**症状**: CDP 无法上传文件

**原因**: 浏览器安全限制，CDP 无法直接操作文件输入框

**解决方案**:
- 方案1: 手动上传（推荐）
- 方案2: 使用 Playwright CDP 连接
- 方案3: 使用 `Input.setFileInputFiles` (需要 DOM 域权限)

### 6. 验证码识别失败

**症状**: 自动识别验证码错误

**解决方案**:
- 手动输入验证码（最可靠）
- 使用 OCR 服务（如 ddddocr）

## 调试技巧

### 1. 截图调试
```python
browser.screenshot("debug_step")
```

### 2. 打印页面内容
```python
text = browser.get_text()
print(text[:500])
```

### 3. 验证选择器
```python
result = browser.eval_js("""
    () => {
        const el = document.querySelector('#title1');
        return el ? {id: el.id, value: el.value} : null;
    }
""")
print(result)
```

### 4. 查看当前 URL
```python
url = browser.eval_js("() => window.location.href")
print(url)
```

## 重试机制

```python
def retry_operation(func, max_retries=3, delay=2):
    for i in range(max_retries):
        try:
            return func()
        except Exception as e:
            print(f"尝试 {i+1}/{max_retries} 失败: {e}")
            if i < max_retries - 1:
                time.sleep(delay)
    return None
```