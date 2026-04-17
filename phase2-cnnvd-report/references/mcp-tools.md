# chrome-devtools-mcp 工具详细参考

## 输入自动化工具

### click - 点击元素

```json
{
  "tool": "click",
  "params": {
    "uid": "element-uid-from-snapshot",
    "dblClick": false,
    "includeSnapshot": false
  }
}
```

**用途**: 点击页面元素（按钮、链接等）

---

### fill - 填写单个表单字段

```json
{
  "tool": "fill",
  "params": {
    "uid": "input-element-uid",
    "value": "要填写的值",
    "includeSnapshot": false
  }
}
```

**用途**: 在输入框中填写文本，或选择下拉框选项

---

### fill_form - 批量填写表单

```json
{
  "tool": "fill_form",
  "params": {
    "elements": [
      {"uid": "uid1", "value": "value1"},
      {"uid": "uid2", "value": "value2"},
      {"uid": "uid3", "value": "value3"}
    ],
    "includeSnapshot": false
  }
}
```

**用途**: 一次性填写多个表单字段，提高效率

---

### upload_file - 上传文件

```json
{
  "tool": "upload_file",
  "params": {
    "uid": "file-input-uid",
    "filePath": "/absolute/path/to/file.zip",
    "includeSnapshot": false
  }
}
```

**用途**: 上传文件到文件输入框

---

### type_text - 键盘输入

```json
{
  "tool": "type_text",
  "params": {
    "text": "输入的文本",
    "submitKey": "Enter"
  }
}
```

**用途**: 使用键盘输入文本（适用于特殊场景）

---

### press_key - 按键

```json
{
  "tool": "press_key",
  "params": {
    "key": "Control+A"
  }
}
```

**用途**: 发送按键或组合键（如 Ctrl+A, Enter, Tab）

---

## 导航工具

### list_pages - 列出所有页面

```json
{
  "tool": "list_pages"
}
```

**返回**: 所有打开的标签页列表

---

### navigate_page - 导航

```json
// 导航到 URL
{
  "tool": "navigate_page",
  "params": {
    "type": "url",
    "url": "https://www.cnvd.org.cn/"
  }
}

// 后退
{
  "tool": "navigate_page",
  "params": {"type": "back"}
}

// 前进
{
  "tool": "navigate_page",
  "params": {"type": "forward"}
}

// 刷新
{
  "tool": "navigate_page",
  "params": {"type": "reload"}
}
```

---

### new_page - 打开新标签页

```json
{
  "tool": "new_page",
  "params": {
    "url": "https://www.cnvd.org.cn/",
    "background": false
  }
}
```

---

### select_page - 选择标签页

```json
{
  "tool": "select_page",
  "params": {
    "pageId": 1
  }
}
```

---

### wait_for - 等待

```json
{
  "tool": "wait_for",
  "params": {
    "time": 2
  }
}
```

**用途**: 等待指定秒数

---

## 调试工具

### take_snapshot - 获取页面快照

```json
{
  "tool": "take_snapshot"
}
```

**返回**: 页面的可访问性树快照，包含所有可交互元素的 uid

**示例输出**:
```
[1] link "用户中心"
[2] link "漏洞报送"
[3] textbox "漏洞名称"
[4] button "提交"
```

---

### take_screenshot - 截图

```json
{
  "tool": "take_screenshot"
}
```

**用途**: 截取当前页面的截图

---

### evaluate_script - 执行 JavaScript

```json
{
  "tool": "evaluate_script",
  "params": {
    "script": "(function() { return document.title; })()"
  }
}
```

**用途**: 在页面中执行 JavaScript 并获取返回值

---

## 完整流程示例

```
1. list_pages → 查看当前页面
2. navigate_page(url) → 打开 CNVD 首页
3. take_snapshot → 获取快照
4. click(uid: "用户中心") → 点击用户中心
5. take_snapshot → 获取新快照
6. click(uid: "漏洞报送") → 点击漏洞报送
7. take_snapshot → 获取新快照
8. click(uid: "立即漏洞上报") → 进入表单
9. evaluate_script → 切换表单类型
10. take_snapshot → 获取表单快照
11. fill_form([...]) → 填写所有字段
12. upload_file → 上传附件
13. take_screenshot → 截图验证码
14. (用户输入验证码)
15. click(uid: "提交") → 提交
16. evaluate_script → 提取 CNVD-ID
```