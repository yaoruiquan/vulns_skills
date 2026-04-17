# 漏洞汇总表

## 一、汇总表路径

`/Users/yao/Documents/网安- AI应用开发/监管上报/汇总表/漏洞汇总表.xlsx`

## 二、字段说明

| 字段 | 说明 | 示例 |
|------|------|------|
| 漏洞标题 | 漏洞完整名称 | Linux内核系统-rxrpc模块存在二进制-内存缓冲区操作限制不当漏洞 |
| 影响厂商 | 受影响厂商名称 | Linux |
| 漏洞编号 | DAS-ID | DAS-T105980 |
| 提交人员 | 分析人员姓名 | 从 Word 文档提取 |
| 上报CNVD编号 | CNVD 编号（如有） | CNVD-2026-xxxxx |
| 上报CNNVD编号 | CNNVD 编号 | CNNVD-2026-99372920 |
| 上报日期 | 提交日期 | 2026-04-09 |

## 三、更新脚本

```bash
python3 ~/.claude/skills/phase2-cnnvd-report-cdp/scripts/update_summary.py \
  --title "<漏洞标题>" \
  --vendor "<影响厂商>" \
  --das-id "<DAS-ID>" \
  --submitter "<提交人员>" \
  --cnvd-id "<CNVD编号>" \
  --cnnvd-id "<CNNVD编号>" \
  --date "<上报日期>"
```

## 四、脚本特性

- 如果汇总表文件不存在，脚本会自动创建
- 如果漏洞已存在（根据 DAS-ID 判断），则更新对应行
- CNVD 编号可为空，CNNVD 编号必填