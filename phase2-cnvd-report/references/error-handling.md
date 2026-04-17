# 错误处理指南

## 常见错误

### 1. Chrome 连接失败

**错误信息**: `❌ Chrome 未运行或调试端口未开启`

**解决方案**:
```bash
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh
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
lsof -i :9332

# 重启 skill 专用 Chrome
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh
```

### 2.0 只想看到一个被 MCP 接管的 Chrome

**现象**: 之前像是有两个 Chrome，一个自己开的，一个写着 MCP 正在控制

**原因**:
- 手工启动了一个调试 Chrome
- `chrome-devtools-mcp` 又按默认行为自行拉起了一套 automation Chrome

**解决方案**:
```bash
# 只使用 skill 自带启动脚本启动浏览器
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh

# 只使用本 skill 的 wrapper 连接 MCP
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/chrome-devtools-mcp-wrapper.sh
```

现在这套 skill 里，浏览器由 `start-chrome-debug.sh` 启动，MCP 只通过 `--browserUrl` attach 到 `9332` 端口，不会再额外拉起第二个可见实例。

### 2.1 CNVD 返回 Cloudflare 521

**错误信息**: `HTTP 521` 或页面提示 `Web server is down`

**可能原因**:
- 隔离的 Chrome profile 过于干净，缺少正常浏览器足迹
- 缺少 Cloudflare 认可的 cookies，例如 `cf_clearance`
- Cloudflare 将当前 skill 浏览器识别为异常自动化流量

**解决方案**:
```bash
# 优先：从日常 Chrome 的 Default profile 复制一份快照到 skill profile
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh seed-default

# 如果你平时不是 Default profile，先指定真实 profile 名称
export CLAUDE_CHROME_PROFILE_DIRECTORY="Profile 1"

# 仍然不行，再关闭普通 Chrome 后直接挂到真实 profile
/Users/yao/.claude/skills/phase2-cnvd-report/scripts/start-chrome-debug.sh live-default
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
