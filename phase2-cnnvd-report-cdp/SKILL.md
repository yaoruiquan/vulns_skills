# phase2-cnnvd-report-cdp

通过 chrome-devtools MCP 控制浏览器完成 CNNVD 漏洞上报。

> 环境配置参见 [references/setup-guide.md](references/setup-guide.md)

---

## 一、流程概览

```
Step 0: 检查环境 → Step 1: 准备数据 → Step 2: 导航登录 → Step 3: 基本信息 → Step 4: 漏洞详情 → Step 5: 漏洞验证 → 提交
```

**表单分为3步**：
1. 漏洞基本信息
2. 漏洞详情
3. 漏洞验证

---

## 二、详细步骤

### Step 0: 检查环境状态

**第一步必须先检查调试端口和 MCP 连接状态。**

> 详细检查步骤参见 [references/setup-guide.md](references/setup-guide.md#四检查环境状态)

### Step 1: 准备数据

#### 1.1 提取漏洞数据

```bash
python3 ~/.claude/skills/phase2-cnnvd-report-cdp/scripts/extract_vuln_data.py <DAS-ID> --platform CNNVD
```

> 数据字段映射参见 [references/data-fields.md](references/data-fields.md)

#### 1.2 压缩附件

```bash
cd "<CNNVD文件夹路径>" && zip -r /tmp/<DAS-ID>-CNNVD.zip .
```

---

### Step 2: 导航到表单页面

#### 2.1 打开 CNNVD 首页

```
MCP: navigate_page
  type: "url"
  url: "https://www.cnnvd.org.cn/home/childHome"
```

#### 2.2 登录流程（自动 OCR 识别）

> 验证码 OCR 详细说明参见 [references/captcha-ocr.md](references/captcha-ocr.md)

**验证码识别流程**：
```
# 1. 点击刷新验证码
MCP: click
  uid: "<验证码图片的 uid>"

# 2. 截图验证码
MCP: take_screenshot
  uid: "<验证码图片的 uid>"
  filePath: "/tmp/cnnvd_captcha.png"

# 3. OCR 识别
python3 ~/.claude/skills/phase2-cnnvd-report-cdp/scripts/captcha_ocr.py /tmp/cnnvd_captcha.png

# 4. 填入验证码
MCP: type_text
  text: "<OCR识别结果>"
```

#### 2.3 导航到漏洞上报表单

登录成功后，导航到"漏洞管理" → "通用型漏洞报送"。

---

### Step 3: 填写表单（第1步：漏洞基本信息）

#### 3.1 填写漏洞名称

```
MCP: fill
  uid: "<漏洞名称输入框的 uid>"
  value: "<title>"
```

#### 3.2 选择漏洞类型（级联下拉框）

> 级联路径参见 [references/vuln-type-mapping.md](references/vuln-type-mapping.md#三级联选择操作)

**操作示例**：
```
MCP: click
  uid: "<漏洞类型下拉框的 uid>"

MCP: take_snapshot
# 逐级展开选择
```

#### 3.3 填写受影响实体信息

```
MCP: fill_form
  elements:
    - uid: "<受影响实体厂商名称的 uid>"
      value: "<unit_name>"
    - uid: "<受影响实体名称的 uid>"
      value: "<affected_product>"
    - uid: "<受影响实体版本的 uid>"
      value: "<version>"
```

#### 3.4 填写受影响实体描述

**注意**：需联网搜索产品描述，约 50-200 字。

#### 3.5 点击"下一步"

```
MCP: click
  uid: "<下一步按钮的 uid>"
```

---

### Step 4: 漏洞详情

#### 4.1 填写漏洞描述

```
MCP: fill
  uid: "<漏洞描述或简介文本框的 uid>"
  value: "<description>"
```

#### 4.2 填写提交者信息

**规则**：
- 技术支持：固定填写【杭州安恒信息技术股份有限公司】
- 技术支持联系电话：优先按 word 文档填写，无则填写 15700082275

#### 4.3 点击"下一步"

---

### Step 5: 漏洞验证

#### 5.1 填写验证过程

> Word 提取规则参见 [references/word-extraction.md](references/word-extraction.md)

#### 5.2 上传验证录像

**重要**：如果有验证视频，必须上传。

> 压缩指南参见 [references/video-compression.md](references/video-compression.md)

```
MCP: take_snapshot
MCP: click
  uid: "<有 radio 按钮的 uid>"

MCP: upload_file
  uid: "<点击上传按钮的 uid>"
  filePath: "<视频路径>"
```

#### 5.3 上传 PoC 附件

```
MCP: click
  uid: "<其他/脚本文件/二进制文件 radio 的 uid>"

MCP: upload_file
  uid: "<点击上传按钮的 uid>"
  filePath: "<PoC路径>"
```

#### 5.4 提交表单

**重要**：根据实际测试，最终提交**不需要验证码**。

```
MCP: click
  uid: "<提交按钮的 uid>"
```

#### 5.5 获取 CNNVD-ID

提交成功后，页面跳转到"我的漏洞"页面，在页面中查找 `CNNVD-\d{8}-\d+` 格式的编号。

#### 5.6 更新漏洞汇总表

> 汇编表说明参见 [references/summary-table.md](references/summary-table.md)

---

## 三、人工介入点

| 步骤 | 操作 | 说明 |
|------|------|------|
| Step 2.2 | 登录验证码 | **已自动化**：ddddocr OCR 识别 |
| Step 3.4 | 受影响实体描述 | 需联网搜索产品描述 |
| Step 5.1 | 验证过程内容 | 从 Word 提取，去掉开头结尾标记 |

---

## 四、文件结构

```
phase2-cnnvd-report-cdp/
├── SKILL.md                  # 本文件
├── README.md                 # 详细说明
├── scripts/
│   ├── extract_vuln_data.py  # 提取漏洞数据
│   ├── compress_zip.py       # 压缩附件
│   ├── captcha_ocr.py        # 验证码 OCR 识别
│   ├── update_summary.py     # 更新漏洞汇总表
│   ├── start-chrome-debug.sh # 启动调试浏览器
│   └── chrome-devtools-mcp-wrapper.sh # MCP wrapper
└── references/
    ├── setup-guide.md        # 环境配置
    ├── data-fields.md        # 数据字段映射
    ├── vuln-type-mapping.md  # 漏洞类型映射
    ├── captcha-ocr.md        # 验证码 OCR 说明
    ├── word-extraction.md    # Word 提取规则
    ├── video-compression.md  # 视频压缩指南
    ├── summary-table.md      # 汇编表说明
    └── mcp-tools.md          # MCP 工具参考
```

---

## 五、参考文档

- [环境配置](references/setup-guide.md)
- [数据字段映射](references/data-fields.md)
- [漏洞类型映射](references/vuln-type-mapping.md)
- [验证码 OCR](references/captcha-ocr.md)
- [Word 提取规则](references/word-extraction.md)
- [视频压缩](references/video-compression.md)
- [汇编表](references/summary-table.md)
- [MCP 工具参考](references/mcp-tools.md)

---

## 六、相关链接

- [chrome-devtools-mcp](https://github.com/ChromeDevTools/chrome-devtools-mcp)
- [CNNVD 官网](https://www.cnnvd.org.cn/)