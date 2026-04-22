# NCC 平台漏洞上报流程

## 流程概览

```text
Step 0: 检查环境 -> Step 1: 准备数据 -> Step 2: 登录并进入填表页 -> Step 3: 确认表单 -> Step 4: 填表上传 -> Step 5: 提交与人工滑块验证 -> Step 6: 记录 NCC 编号 -> Step 7: 钉钉通知
```

## Step 0: 检查环境

```bash
cd /Users/yao/.claude/skills/phase2-ncc-report
./scripts/start-chrome-debug.sh
curl -s http://127.0.0.1:9334/json/version
```

确认 MCP 可用：

```text
MCP: list_pages
```

## Step 1: 准备数据

### 1.1 提取漏洞数据

```bash
python3 scripts/extract_vuln_data.py --docx-path "<具体 docx 路径>"
# 或
python3 scripts/extract_vuln_data.py --input-path "<具体 DAS 目录>"
# 或兼容旧用法
python3 scripts/extract_vuln_data.py <DAS-ID> --data-dir "<数据根目录>"
```

输出示例：

```json
{
  "platform": "NCC",
  "das_id": "DAS-T106003",
  "material_dir": "/path/to/CNVD-材料目录",
  "material_source": "CNVD",
  "title": "7z系统WIM格式解析器模块存在内存缓冲区操作限制不当漏洞",
  "description": "经恒脑AI代码审计智能体分析：7z WIM格式解析器递归调用无深度限制导致栈溢出",
  "vuln_type": "二进制",
  "target_type": "应用程序",
  "unit_name": "其他",
  "affected_product": "7z<=26.00",
  "version": "7z<=26.00",
  "url": "http://none",
  "docx_path": "/path/to/report.docx",
  "upload_zip_path": "/path/to/poc/example.zip",
  "screenshot_paths": [
    "/path/to/poc验证图片/example.png"
  ],
  "video_paths": [
    "/path/to/poc验证视频/example.mp4"
  ]
}
```

### 1.2 准备附件

第一版按当前约定这样用：

- 以 `docx` 作为信息提取输入
- 以 `CNVD` 材料目录下的 `poc/*.zip` 作为优先上传附件
- 页面若支持多文件，再补充 `docx / 截图 / 视频`

## Step 2: 登录并进入填表页

```text
MCP: navigate_page
  type: "url"
  url: "<NCC_PLATFORM_URL>"
```

默认地址：

```text
https://www.nccsec.cn/company-center/manage-center
```

如果未登录，按截图确认的顺序操作：

1. 切到“企业”页签。
2. 填写 `.env` 中的 `NCC_USERNAME`、`NCC_PASSWORD`。
3. 勾选协议复选框。
4. 点击蓝色“登录”按钮。
5. 登录成功后，在管理中心右上角点击“提交漏洞”下拉按钮。
6. 点击下拉菜单里的“提交漏洞”项，进入填表页。

## Step 3: 确认上报入口和表单

首次开发或页面变化时必须执行：

```text
MCP: take_snapshot
```

根据快照确认：

- 登录页 tab、账号框、密码框、协议勾选框、登录按钮
- 管理中心“提交漏洞”按钮和菜单项
- 表单字段名称
- 各下拉框真实选项值
- 附件上传控件
- 提交按钮
- 提交成功后 `NCC-xxxx` 所在位置

将确认结果补充到 [selectors.md](selectors.md)。

## Step 4: 填写表单

按 [field-mapping.md](field-mapping.md) 使用提取数据填表。原则：

- `是否为原创漏洞` 固定选“是”。
- `发现日期` 不直接拿 `提交日期` 硬填。
- `漏洞类型`、`漏洞详细分类` 以页面实际下拉值为准。
- `影响对象` 优先根据 `target_type` 选择。
- `漏洞厂商 / 影响组件 / 影响版本 / 漏洞名称 / 漏洞 URL / 漏洞描述` 直接使用提取值。
- `漏洞危害` 优先使用 `impact`；如果材料没有单独危害字段，人工提炼关键危害结论。
- `修复方案` 先选页面单选项，再把解决方案文本写入说明框。
- 平台必填但材料缺失时暂停，不要凭空编写。

示例操作：

```text
MCP: fill_form
  elements:
    - uid: "<漏洞名称 uid>"
      value: "<title>"
    - uid: "<漏洞描述 uid>"
      value: "<description>"
    - uid: "<影响组件 uid>"
      value: "<affected_product>"
    - uid: "<影响版本 uid>"
      value: "<version>"
```

## Step 5: 上传附件

```text
MCP: upload_file
  uid: "<文件上传输入框 uid>"
  filePath: "<upload_zip_path>"
```

第一版默认先传 `upload_zip_path`。如果页面支持多文件，再补充：

- `docx_path`
- `screenshot_paths`
- `video_paths`

## Step 6: 提交与人工滑块验证

提交前必须复核：

| 字段 | 要求 |
|------|------|
| 是否为原创漏洞 | 已选择 |
| 漏洞类型 | 已选择 |
| 影响对象 | 已选择 |
| 漏洞厂商 | 已填写 |
| 影响组件 | 已填写 |
| 影响版本 | 已填写 |
| 漏洞名称 | 已填写 |
| 漏洞描述 | 已填写 |
| 漏洞危害 | 已填写 |
| 修复方案 | 已填写 |
| 附件 | 已上传 |
| 提交按钮 | 已确认 |

点击“提交”后，会出现拖拽拼图验证。第一版按以下策略执行：

1. 自动化流程在点击提交前完成全部填表和上传。
2. 出现拖拽验证后，切换人工处理。
3. 人工完成拖拽后，自动化继续读取结果页。

## Step 7: 记录 NCC 编号

提交后使用快照或页面文本记录结果：

```text
MCP: take_snapshot
MCP: evaluate_script
  function: |
    () => document.body.innerText
```

记录：

- `NCC-xxxx` 编号
- 成功提示
- 提交时间
- 对应 `DAS-ID`

## Step 8: 钉钉通知

```bash
python3 scripts/dingtalk_notify.py \
  --title "NCC 平台上报完成" \
  --status success \
  --text "DAS-ID：<DAS-ID>\nNCC编号：<NCC-xxxx>" \
  --output "<材料目录>"
```
