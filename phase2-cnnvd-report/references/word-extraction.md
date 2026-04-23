# Word 验证过程处理

## 一、使用边界

本文件只用于数据准备阶段理解 Word 中的验证过程来源。

第三页“漏洞验证”阶段禁止重新运行 `extract_vuln_data.py` 或任何 Word 提取脚本；只能使用数据准备阶段已经整理好的 `FormContext.verification`。

## 二、处理规则

Word 中的验证过程由 `extract_vuln_data.py` 在 Step 1 提取为 `verification_source`，它只是总结输入，不直接填表。整理规则：

- Word 文档内容在表格中，不在普通段落里；脚本会遍历所有表格查找字段。
- 去掉开头标记：`此分析报告由VF自动生成，并经过人工核验。`
- 去掉开头标记：`此分析报告由恒脑AI代码审计智能体自动生成，并经过人工核验。`
- 去掉结尾标记：`（更多成果请查看VF官网：https://v.das-ai.com/）`
- 去掉结尾标记：`（查看恒脑AI代码审计智能体官网: https://www.dbappsecurity.com.cn/）`
- 数据准备阶段再把 `verification_source` 总结压缩成一段 `verification`。
- 不提取、不插入 Word 中的图片。
- 验证过程内容在 Word 表格的"漏洞验证过程"单元格中。

## 三、提取命令

```bash
python3 scripts/extract_vuln_data.py <DAS-ID> --platform CNNVD --data-dir "<数据目录>"
```

该命令只在 Step 1 数据准备阶段运行一次。进入第 2 页或第 3 页后不要再次运行。

## 四、富文本编辑器填写

验证过程字段如果是富文本编辑器（iframe），通过 JavaScript 填写已经整理好的 `FormContext.verification`：

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
        const content = `<FormContext.verification>`;
        iframe.contentDocument.body.innerHTML = `<p>${content}</p>`;
        return '验证过程已填写';
      }
      return '未找到iframe';
    }
```
