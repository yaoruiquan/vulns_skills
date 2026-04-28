# CNVD 表单 CSS 选择器参考

## 基本信息

| 字段 | 选择器 | 类型 | 说明 |
|------|--------|------|------|
| 发现者 | `#discovererName1` | input | 文本输入 |
| 发现日期 | `#foundTime1` | input | 日期选择 |
| 漏洞类型 | `#isEvent1` | select | 事件型(1)/通用型(0) |
| 是否公开 | `input[name="isOpen"]` | radio | 是(1)/否(0) |

## 厂商信息

| 字段 | 选择器 | 类型 | 说明 |
|------|--------|------|------|
| 漏洞厂商 | `#manuName` | input | 文本输入 |
| 厂商官网 | `#changshang1` | input | URL |
| 影响对象类型 | `#softStyleId1` | select | 下拉选择 |
| 影响产品 | `#productCategoryName` | input | 文本输入 |
| 影响版本 | `#edition` | input | 文本输入 |

## 漏洞详情

| 字段 | 选择器 | 类型 | 说明 |
|------|--------|------|------|
| 漏洞名称 | `#title1` | input | 文本输入 |
| 漏洞类型 | `#titlel1` | select | 下拉选择 |
| 漏洞描述 | `#description1` | textarea | 多行文本 |
| 漏洞URL | `#url1` | input | URL |
| 临时方案 | `#tempWay1` | textarea | 多行文本 |
| 正式方案 | `#formalWay11` | textarea | 多行文本 |

## 二进制漏洞特有字段

| 字段 | 选择器 | 类型 | 说明 |
|------|--------|------|------|
| 版本 | `#binaryVulnerabilityVersion1` | input | 文本输入 |
| 触发位置 | `#binaryVulnerabilityTriggerPosition1` | textarea | 多行文本 |
| POC | `#binaryVulnerabilityPoc1` | textarea | 多行文本 |

## 附件与提交

| 字段 | 选择器 | 类型 | 说明 |
|------|--------|------|------|
| 附件上传 | `#flawAttFile` | input[file] | 文件上传 |
| 验证码 | `#myCode1` | input | 文本输入 |
| 验证码图片 | `#codeSpan1 img` | img | 截图识别 |
| 提交按钮 | `#subForm` | button | 点击提交 |

## 注意事项

1. **表单类型切换**：必须先触发 `#isEvent1` 的 `change` 事件，否则表单字段不会更新
2. **元素 ID 后缀**：通用型漏洞字段有 `1` 后缀（如 `title1`），事件型无后缀
3. **隐藏字段**：某些字段可能在表单类型切换前不可见
4. **Select2 组件**：`#isEvent1` / `#titlel1` / `#softStyleId1` 这些选择器指向底层 `<select>`，页面实际显示的是 Select2 组件；a11y 树里的选项可能不可点击
5. **下拉框设值**：优先运行 `python3 scripts/browser_snippets.py select2 ...` 生成的 `evaluate_script`，它会同步原生 select、`change` 事件和 jQuery Select2 UI
