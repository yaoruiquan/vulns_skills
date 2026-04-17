# CNNVD 数据字段映射

## 一、表单字段与数据来源

| 表单字段 | 数据来源 | 字段名 | 备注 |
|---------|---------|-------|------|
| 漏洞名称 | extract_vuln_data | title | |
| CVE编号 | extract_vuln_data | cve_id | 可选 |
| 漏洞类型 | extract_vuln_data | vuln_type | 需映射到级联路径 |
| 漏洞自评级 | extract_vuln_data | risk_level | 超危/高危/中危/低危 |
| 公开情况 | 固定值 | 未公开 | 默认即可 |
| 受影响实体厂商名称 | extract_vuln_data | unit_name | |
| 受影响实体分类 | 根据产品判断 | - | 操作系统/Web应用/数据库等 |
| 受影响实体名称 | extract_vuln_data | affected_product | |
| 受影响实体版本 | extract_vuln_data | version | |
| 受影响实体原始下载链接 | extract_vuln_data | download_url | 可选 |
| 受影响实体描述 | 联网搜索 | - | 产品简介，50-200字 |
| 受影响网络资源数量 | 固定值 | 空 | 默认即可 |
| 漏洞描述或简介 | extract_vuln_data | description | |
| 技术支持 | 固定值 | 杭州安恒信息技术股份有限公司 | |
| 技术支持联系电话 | extract_vuln_data | contact | 或默认 15700082275 |
| 验证过程 | Word 文档表格 | verification | 去掉开头结尾标记 |

## 二、数据提取脚本输出示例

```json
{
  "das_id": "DAS-T105970",
  "title": "Claude Code系统getMcpHeadersFromHelper模块存在命令执行漏洞",
  "description": "漏洞描述内容...",
  "vuln_type": "命令执行",
  "affected_product": "Claude Code",
  "version": "2.1.89",
  "unit_name": "Anthropic",
  "verification": "详细验证过程...",
  "contact": "15700082275",
  "folder_path": "/Users/yao/LLM/vulns/date/DAS-T105970-xxx/CNNVD-xxx",
  "docx_path": "/Users/yao/LLM/vulns/date/DAS-T105970-xxx/CNNVD-xxx/xxx.docx"
}
```

## 三、受影响实体分类选项

- 应用软件
- 操作系统
- 网络设备
- 安全设备
- 智能家居设备
- 移动设备
- 数据库
- Web应用
- 其他

## 四、漏洞自评级选项

- 超危
- 高危
- 中危
- 低危