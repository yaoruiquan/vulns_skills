# NCC 平台表单选择器记录

平台入口：

```text
https://www.nccsec.cn/company-center/manage-center
```

## 使用原则

- 第一次操作或平台页面变化后，先用 MCP `take_snapshot` 获取可访问元素。
- 优先使用 MCP 返回的 `uid` 操作，不要直接依赖 CSS 选择器。
- 如果必须使用 `evaluate_script` 或 CSS 选择器，先记录在本文件。
- 不要把未验证的选择器写成确定规则。

## 当前页面观察结果

已根据 `assets/1进入页面.png` 到 `assets/8提交成功后.png` 确认以下页面逻辑：

- 平台入口是企业中心：`https://www.nccsec.cn/company-center/manage-center`
- 未登录时会进入登录页，且登录方式是“企业”页签
- 登录页有账号输入框、密码输入框、协议勾选框、蓝色“登录”按钮
- 登录成功后，在管理中心右上角通过“提交漏洞”下拉菜单进入填表页
- 企业登录后可能出现阿里云滑块验证；表单底部点击“提交”后也可能出现拖拽拼图验证
- 验证通过并提交成功后，会进入“我的漏洞”列表页，可读到 `NCC-xxxx` 编号

## 登录与导航

| 页面/动作 | MCP uid 或选择器 | 状态 | 备注 |
|-----------|------------------|------|------|
| 管理中心入口 | `NCC_PLATFORM_URL` | ✅ 已确认 | `.env` 中配置 |
| 登录页 URL | `https://www.nccsec.cn/login` | ✅ 已确认 | 未登录时自动跳转 |
| 登录页”企业”页签 | 点击 StaticText “企业” | ✅ 已确认 | 默认显示”个人”登录 |
| 登录账号输入框 | textbox “请输入邮箱号” | ✅ 已确认 | 企业登录模式 |
| 登录密码输入框 | textbox “请输入密码” | ✅ 已确认 | 企业登录模式 |
| 协议勾选框 | checkbox “我已阅读并同意” | ✅ 已确认 | 点击关联 StaticText 即可勾选 |
| 登录按钮 | button “登录” | ✅ 已确认 | 表单底部蓝色按钮 |
| 管理中心页 | `https://www.nccsec.cn/company-center/manage-center` | ✅ 已确认 | 登录成功后进入 |
| 右上角”提交漏洞”按钮 | button “提交漏洞” expandable | ✅ 已确认 | uid 需运行时获取 |
| 下拉菜单”提交漏洞”项 | menuitem “提交漏洞” | ✅ 已确认 | 点击后进入 `/vulnerabilities/create` |

## 漏洞表单字段 (2026-04-22 实测)

页面 URL: `https://www.nccsec.cn/vulnerabilities/create`

| 字段 | MCP uid 模式 | 类型 | 说明 |
|------|--------------|------|------|
| 漏洞业务类型 | 第 1 个 radio group | radio | 事件型/通用型，固定选择 `通用型漏洞` |
| 是否0Day漏洞 | 第 2 个 radio group | radio | 使用 `is_0day`，值为“是/否” |
| 是否为原创漏洞 | 第 3 个 radio group | radio | 使用 `is_original`，值为“是/否”；强制按 group index 2 点击，不走 label 匹配 |
| 发现日期 | combobox “* 发现日期：” value=”YYYY-MM-DD HH:MM:SS” | datetime | 页面自动填充当前时间，可修改 |
| 漏洞类型/漏洞详细分类 | combobox/select | select | 对应 `detail_category`，不要误操作第 1 个业务类型 radio group |
| 影响对象 | combobox “* 影响对象：” | select | 需点击选择，对应 `target_type` |
| 厂商所属国家/地区 | combobox，label 可能为“产品厂商归属国家及地区”“产品厂商归属国家/地区”“厂商所属国家及地区”“所属国家/地区”“国家/地区” | select | 对应 `vendor_country`，不要用单独“产品厂商”宽泛匹配；无法判断时默认“中国大陆” |
| 漏洞厂商 | textbox “* 漏洞厂商：” | input | 对应 `unit_name` |
| 影响组件 | textbox “* 影响组件：” | input | 对应 `affected_product` |
| 影响版本 | textbox “* 影响版本：” | input | 对应 `version` |
| 漏洞名称 | textbox “* 漏洞名称：” | input | 对应 `title` |
| 漏洞详细分类 | combobox “* 漏洞详细分类：” | select | 平台默认可能是”SQL注入”；取值必须在 `field-mapping.md` 的允许选项中 |
| 版本号 | textbox | 动态 input | 选择“二进制”后出现，填 `version` |
| 触发位置 | textbox multiline | 动态 textarea | 选择“二进制”后出现，填 `trigger_location` |
| PoC | textbox multiline | 动态 textarea | 选择“二进制”后出现，填 `poc_text` |
| SQL注入 POC 方法 | radio “get” / “post” | radio | 仅 SQL 注入类型显示 |
| 目录导航/POC详情 | textbox multiline | textarea | 漏洞利用过程描述 |
| 漏洞 URL | textbox “* 漏洞URL：” multiline | textarea | 对应 `url` |
| 漏洞描述 | textbox “* 漏洞描述：” multiline | textarea | 对应 `description` |
| 漏洞危害 | textbox “* 漏洞危害：” multiline | textarea | 优先来自 `impact` |
| 修复方案 | radio “临时方案” / “正式解决方案，有官方补丁” | radio | 默认”临时方案” |
| 修复方案说明 | textbox “* 修复方案说明：” multiline | textarea | 对应解决方案文本 |
| 漏洞附件 | button “选择文件” | upload | 格式限制: doc/docx/zip/py，≤50M |
| 提交按钮 | button “提交” | button | 表单底部 |

### 注意事项

1. **uid 动态变化**: 每次页面加载 uid 会变化，需用 `combobox/textbox` 的 label 文本匹配
2. **下拉选项**: 点击 combobox 后弹出 listbox，选项需运行时获取
3. **SQL注入专属字段**: 当漏洞详细分类为”SQL注入”时，显示 get/post radio 和目录导航输入
4. **Element UI 选项池共享**: 影响对象、国家、分类等下拉选项会混在同一个 DOM 池，关闭后的历史 `.el-select-dropdown__item` 仍留在 DOM 中。主下拉按固定 `.el-select-dropdown` 索引取值：`[0]=影响对象`、`[1]=厂商国家/地区`、`[2]=漏洞详细分类`；动态下拉才定位当前 `.el-form-item` 触发器并回读当前控件值，未写回当前控件就返回失败
5. **textarea 顺序不稳定**: 不要按页面 textarea 索引填 PoC/触发位置/URL/描述，必须按 `.el-form-item__label` 定位后填写
6. **短 label 精确匹配**: 动态字段如“类型”“中间件/框架”必须按完整 label 精确匹配当前表单项，不得用 `label.includes('类型')`，否则会误命中“漏洞类型/漏洞详细分类”
7. **附件格式限制**: 仅支持 doc/docx/zip/py，当前默认只上传 `upload_zip_path`；多次上传可能导致前一个文件被替换

## 验证与提交结果

| 结果项 | 获取方式 | 状态 | 备注 |
|--------|----------|------|------|
| 拖拽拼图验证 | 人工处理 | 已观察 | 点击提交后出现，第一版允许人工接管 |
| 平台返回编号 | 列表页文本 | 已观察 | 提交成功页可读到 `NCC-xxxx` |
| 成功提示 | 待补充 | 待确认 | 首次实际提交后记录具体文本 |
| 我的漏洞列表页 | `https://www.nccsec.cn/vulnerabilities` | ✅ 已确认 | 提交成功后可查看编号 |
