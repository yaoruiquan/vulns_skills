# MCP 工具使用参考

## 基本顺序

1. `list_pages`：确认 MCP 连接到了专用 Chrome。
2. `navigate_page`：打开 `NCC_PLATFORM_URL`。
3. `take_snapshot`：读取页面可访问元素和 uid。
4. `click`：点击登录、菜单、按钮。
5. `fill` / `fill_form`：填写表单。
6. `upload_file`：上传附件。
7. `evaluate_script`：必要时读取页面文本或提取返回编号。

## 打开平台

```text
MCP: navigate_page
  type: "url"
  url: "https://www.nccsec.cn/company-center/manage-center"
```

## 获取表单结构

```text
MCP: take_snapshot
```

将关键 uid 记录到 `selectors.md`。

## 填写表单

```text
MCP: fill_form
  elements:
    - uid: "<字段 uid>"
      value: "<字段值>"
```

## 上传附件

```text
MCP: upload_file
  uid: "<文件上传 input uid>"
  filePath: "/path/to/file.zip"
```

## 读取提交结果

```text
MCP: evaluate_script
  function: |
    () => document.body.innerText
```

从页面文本中提取平台返回编号或成功提示。
