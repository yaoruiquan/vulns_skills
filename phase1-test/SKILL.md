---
name: phase1-test
description: 测试阶段1材料整理功能（解压 zip + 修改 docx 模板）。当用户说"测试材料整理"、"测试阶段1"、"验证材料处理"、"解压漏洞文件"、"处理 docx"、修改了 material_service.py 后验证功能时，必须使用此 skill。
---

# phase1-test

测试阶段1材料整理功能，包含两个步骤：
1. **解压 zip 文件** - 解压 CNVD/CNNVD 压缩包
2. **修改 docx 模板** - 添加 VF 前缀后缀、填写提交人员

## 用法

```
/phase1-test --dir /path/to/data DAS-T105916
/phase1-test --dir /path/to/data batch
/phase1-test --dir /path/to/data list
```

## 流程概览

| 步骤 | 操作 | 工具 |
|------|------|------|
| 1 | 解压 zip 文件 | scripts/unzip_vuln.py |
| 2 | 修改 docx 模板 | scripts/test_material.py |
| 3 | 验证结果 | 检查 docx 内容 |

---

## 步骤 1: 解压 zip 文件

### 单个漏洞解压

```bash
python /Users/yao/.claude/skills/phase1-test/scripts/unzip_vuln.py \
  "/path/to/漏洞目录/DAS-T105917-xxx"
```

### 批量解压

```bash
python /Users/yao/.claude/skills/phase1-test/scripts/unzip_vuln.py \
  "/path/to/漏洞批次目录"
```

### 预期结果

```
DAS-T105917-xxx/
├── CNVD-xxx.zip           # 原始 zip
├── CNNVD-xxx.zip          # 原始 zip
├── CNVD-xxx/              # 解压后的目录
│   └── xxx.docx           # 待修改的 docx
└── CNNVD-xxx/             # 解压后的目录
│   └ xxx.docx             # 待修改的 docx
```

---

## 步骤 2: 修改 docx 模板

### 单个漏洞处理

```bash
python /Users/yao/.claude/skills/phase1-test/scripts/test_material.py \
  --dir /path/to/data DAS-T105916
```

### 批量处理

```bash
python /Users/yao/.claude/skills/phase1-test/scripts/test_material.py \
  --dir /path/to/data batch
```

### 列出漏洞状态

```bash
python /Users/yao/.claude/skills/phase1-test/scripts/test_material.py \
  --dir /path/to/data list
```

### 修改规则（references/modification-rules.md）

---

## 步骤 3: 验证结果

打开 docx 文件检查：

| 平台 | 检查项 |
|------|--------|
| CNVD | 漏洞描述前缀"经VF分析：" |
| CNVD | 提交人员已填写 |
| CNVD | 漏洞分析有 VF 前缀后缀 |
| CNNVD | 漏洞简介前缀"经VF分析：" |
| CNNVD | 提交人员已填写 |

---

## 调试参考

详见 `references/debug-checklist.md`