# Word 文档验证过程提取

## 一、提取规则

验证过程内容需要去掉开头和结尾标记：

- **去掉开头**：`此分析报告由VF自动生成，并经过人工核验。`
- **去掉结尾**：`（更多成果请查看VF官网：https://v.das-ai.com/）`
- 验证过程内容在 Word 表格的"漏洞验证过程"单元格中

## 二、提取脚本

```bash
python3 -c "
from docx import Document

doc = Document('<docx路径>')

# 获取表格中验证过程的内容
table = doc.tables[0]
for row in table.rows:
    cells = row.cells
    if len(cells) >= 2 and cells[0].text.strip() == '漏洞验证过程':
        content = cells[1].text.strip()
        # 去掉开头和结尾标记
        if content.startswith('此分析报告由VF自动生成，并经过人工核验。'):
            content = content[len('此分析报告由VF自动生成，并经过人工核验。'):].strip()
        if '（更多成果请查看VF官网：https://v.das-ai.com/）' in content:
            content = content.replace('（更多成果请查看VF官网：https://v.das-ai.com/）', '').strip()
        print(content)
        break
"
```

## 三、富文本编辑器填写

验证过程字段为富文本编辑器（iframe），通过 JavaScript 填写：

```
# 点击编辑区域
MCP: click
  uid: "<编辑区的 uid>"

# 执行 JavaScript 填写内容
MCP: evaluate_script
  function: |
    () => {
      const iframe = document.querySelector('iframe[title="Rich Text Area"]');
      if (iframe && iframe.contentDocument) {
        const content = `<验证过程内容>`;
        // 将文本转换为段落
        const paragraphs = content.split('\n\n').map(p => `<p>${p.replace(/\n/g, '<br>')}</p>`).join('');
        iframe.contentDocument.body.innerHTML = paragraphs;
        return '验证过程已填写';
      }
      return '未找到iframe';
    }
```