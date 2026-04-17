---
name: phase1-material-processor
description: 监管上报前材料整理功能（重命名文件夹 + 修改 docx 模板）。当用户说"材料整理"、"监管上报准备"、"处理 docx"、修改了 material_service.py 后验证功能时，必须使用此 skill。
---

# phase1-material-processor

监管上报前材料整理功能：
1. 重命名漏洞文件夹（统计漏洞数量）
2. 修改 docx 模板（添加恒脑AI前缀后缀、填写提交人员）

## 用法

```
/phase1-material-processor /path/to/漏洞批次文件夹
```

## 流程概览

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | 统计漏洞数量 | 计算文件夹内漏洞目录个数 |
| 2 | 重命名文件夹 | 改为"杭州安恒信息原创漏洞报送N个" |
| 3 | 修改 docx 模板 | 添加恒脑AI前缀后缀、填写提交人员 |
| 4 | 验证结果 | 检查 docx 内容 |

---

## 步骤 1: 统计漏洞数量

**输入文件夹**：通常是日期格式命名，如 `2026-04-13`

统计文件夹内以 `DAS-T` 开头的漏洞目录个数：

```bash
ls -d /path/to/日期文件夹/DAS-T* | wc -l
```

**示例结构**：
```
2026-04-13/                    ← 输入文件夹（日期命名）
├── DAS-T105981-xxx/           ← 漏洞目录
├── DAS-T105982-xxx/           ← 漏洞目录
├── DAS-T105983-xxx/           ← 漏洞目录
...                            ← N 个漏洞目录
```

---

## 步骤 2: 重命名文件夹

将文件夹名改为 `杭州安恒信息原创漏洞报送N个`：

```bash
mv "/path/to/原始文件夹名" "/path/to/杭州安恒信息原创漏洞报送N个"
```

示例：7个漏洞 → `杭州安恒信息原创漏洞报送7个`

---

## 步骤 3: 修改 docx 模板

### 单个漏洞处理

```bash
python /Users/yao/.claude/skills/phase1-material-processor/scripts/test_material.py \
  --dir /path/to/data DAS-T105916
```

### 批量处理

```bash
python /Users/yao/.claude/skills/phase1-material-processor/scripts/test_material.py \
  --dir /path/to/data batch
```

### 列出漏洞状态

```bash
python /Users/yao/.claude/skills/phase1-material-processor/scripts/test_material.py \
  --dir /path/to/data list
```

### 修改规则（references/modification-rules.md）

---

## 步骤 4: 验证结果

打开 docx 文件检查：

| 平台 | 检查项 |
|------|--------|
| CNVD | 漏洞描述前缀"经恒脑AI代码审计智能体分析：" |
| CNVD | 提交人员填写"恒脑AI代码审计智能体" |
| CNVD | 漏洞分析有开头段落和官网链接后缀 |
| CNVD | 漏洞验证过程已替换为标准语句 |
| CNNVD | 漏洞简介前缀"经恒脑AI代码审计智能体分析：" |
| CNNVD | 提交人员填写"恒脑AI代码审计智能体" |
| CNNVD | 漏洞验证过程有开头段落和官网链接后缀 |

---

## 调试参考

详见 `references/debug-checklist.md`