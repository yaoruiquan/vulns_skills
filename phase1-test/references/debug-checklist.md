# 阶段1 调试检查清单

## 解压步骤调试

| 问题 | 检查项 | 解决方案 |
|------|--------|---------|
| zip 文件找不到 | 检查文件夹命名是否以 DAS-T 开头 | 手动检查目录结构 |
| 解压失败 | 检查 zip 是否损坏 | 用系统 unzip 命令测试 |
| 目录已存在 | 检查是否有同名文件夹 | 删除旧文件夹或跳过 |
| docx 未找到 | 检查解压后目录内容 | 手动打开文件夹查看 |

## docx 修改步骤调试

| 问题 | 检查项 | 解决方案 |
|------|--------|---------|
| 找不到漏洞文件夹 | 检查 das_id 是否正确 | 列出所有漏洞 `list_vulns()` |
| Excel 文件找不到 | 检查数据目录是否有 Excel | 手动检查目录 |
| 提交人员获取失败 | 检查 Excel 列名 | 用 openpyxl 读取 Excel |
| docx 字段找不到 | 检查模板段落名称 | 用 python-docx 读取段落 |
| 前缀未添加 | 检查段落是否为空 | 调试 material_service.py |

## 验证步骤调试

| 问题 | 检查项 | 解决方案 |
|------|--------|---------|
| 前缀位置不对 | 打开 docx 查看段落 | 检查修改规则 |
| 提交人员为空 | 检查 Excel/参数 | 重新传入 submitter |
| 文件损坏 | 检查 docx 是否可打开 | 用 Word 打开测试 |

## 日志位置

- 解压日志：终端输出
- 修改日志：MaterialService 返回的 result dict
- 错误信息：Python 异常 traceback

## 手动测试命令

### 检查目录结构
```bash
find /Users/yao/LLM/vulns/date -name "*.zip" | head -10
find /Users/yao/LLM/vulns/date -name "*.docx" | head -10
```

### 检查 Excel 内容
```python
from openpyxl import load_workbook
wb = load_workbook("path/to/Excel.xlsx")
ws = wb.active
for row in ws.iter_rows(max_row=10, values_only=True):
    print(row)
```

### 检查 docx 内容
```python
from docx import Document
doc = Document("path/to/docx.docx")
for para in doc.paragraphs:
    print(para.text[:50] if para.text else "[空]")
```