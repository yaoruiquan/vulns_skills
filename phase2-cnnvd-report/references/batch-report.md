# CNNVD 批量上报模式

## 适用输入

用户给出批次根目录，例如：

```bash
/Users/yao/Documents/网安- AI应用开发/监管上报/杭州安恒信息原创漏洞报送2个-2026-04-28-094514
```

目录结构要求：

```text
批次目录/
├── DAS-Txxxxx-漏洞A/
│   └── CNNVD-漏洞A/
└── DAS-Tyyyyy-漏洞B/
    └── CNNVD-漏洞B/
```

按 DAS 目录名称排序上报。只处理 `CNNVD-*` 子目录，忽略 `CNVD-*` 子目录。

## 固定流程

### 1. 初始化批次

```bash
python3 scripts/batch_report.py init "<批次目录>"
```

脚本会输出 `state_path`，默认位于：

```text
/tmp/vulns-skills/phase2-cnnvd-report/batches/<批次名>/batch_state.json
```

后续所有推进、记录、通知都只使用这个状态文件。

### 2. 第一条漏洞

第一条必须走完整单漏洞流程，包括环境检查：

```bash
python3 scripts/batch_report.py start-next "<state_path>"
```

按输出的 `prepare_context_command` 生成本条 `form_context.json`，然后执行单个 CNNVD 上报流程。环境检查完成后标记一次：

```bash
python3 scripts/batch_report.py mark-env "<state_path>"
```

### 3. 记录本条结果

提交成功拿到 CNNVD 编号后立刻记录：

```bash
python3 scripts/batch_report.py record "<state_path>" \
  --das-id "<DAS-ID>" \
  --platform-id "<CNNVD-ID>" \
  --context "<form_context.json>" \
  --status submitted
```

失败也要记录，便于批次状态完整：

```bash
python3 scripts/batch_report.py record "<state_path>" \
  --das-id "<DAS-ID>" \
  --status failed \
  --error "<失败原因>"
```

### 4. 连续推进下一条

每条记录完成后，直接执行 `record` 输出的 `next_command`：

```bash
python3 scripts/batch_report.py start-next "<state_path>" --skip-env-check
```

脚本会输出下一条的 `prepare_context_command` 和 `single_report_target`。第二条及之后不再检查环境，直接从信息提取和单漏洞上报流程开始。

整个批次连续推进；第二条开始不要重复环境检查。

### 5. 统一钉钉通知

全部漏洞记录为 `submitted` 后，只发送一条钉钉消息：

```bash
python3 scripts/batch_report.py notify "<state_path>"
```

注意：

- 批量模式禁止在单条上报后执行 `publish_submission_zip.py --notify`。
- `notify` 会逐条调用 `publish_submission_zip.py --json` 上传附件，但只调用一次 `dingtalk_notify.py`。
- 如需演练，不上传不发送：

```bash
python3 scripts/batch_report.py notify "<state_path>" --dry-run
```
