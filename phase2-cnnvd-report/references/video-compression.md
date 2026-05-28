# 视频压缩指南

## 一、文件上传限制

| 类型 | 限制 |
|-----|------|
| 验证录像 | ≤50MB |
| PoC附件 | ≤50MB |

### 支持的视频格式

avi, wmv, mpeg, mp4, m4v, mov, asf, flv, f4v, rmvb, rm, 3gp, vob

### 支持的 PoC 格式

zip, rar

## 二、视频压缩流程

### 2.1 检查视频大小

```bash
ls -lh "<视频路径>"
```

### 2.2 压缩命令

如果视频超过 50MB，优先使用脚本压缩。脚本会用 `ffprobe` 获取视频时长，按 48MB 目标计算码率，并最多重试 3 次降低码率：

```bash
python3 scripts/compress_cnnvd_video.py "<原视频路径>" --json
```

默认输出到原视频目录下的 `cnnvd-compressed/<原名>-cnnvd-compressed.mp4`。

如果只想查看将执行的 ffmpeg 命令：

```bash
python3 scripts/compress_cnnvd_video.py "<原视频路径>" --dry-run --json
```

脚本内部使用的 ffmpeg 形式：

```bash
ffmpeg -y -hide_banner -i "<原视频路径>" -vf "scale=trunc(min(1280\\,iw)/2)*2:-2" -c:v libx264 -preset fast -b:v "<按时长计算>k" -maxrate "<按时长计算>k" -bufsize "<2倍码率>k" -c:a aac -b:a 96k -movflags +faststart "<输出路径>"
```

### 2.3 验证压缩结果

```bash
python3 scripts/compress_cnnvd_video.py "<原视频路径>" --json
```

## 三、压缩参数说明

| 参数 | 说明 |
|-----|------|
| `--target-mb 48` | 目标大小，默认留 2MB 余量，避免刚好卡 50MB |
| `-preset fast` | 编码速度（可选：ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow） |
| `-b:a 96k` | 音频比特率 |
| `--max-width 1280` | 默认最大宽度，避免无意义上传超大分辨率 |

## 四、上传压缩后的文件

`upload_cnnvd_attachments.py` 默认会自动检查和压缩视频，然后上传压缩后的文件：

```bash
python3 scripts/upload_cnnvd_attachments.py \
  --form-context "<form_context.json>" \
  --token-stdin \
  --output "<logs_dir>/cnnvd-uploaded-attachments.json" \
  --apply-js "<logs_dir>/cnnvd-apply-upload-state.js"
```

如果需要手动指定压缩输出目录：

```bash
python3 scripts/upload_cnnvd_attachments.py \
  --form-context "<form_context.json>" \
  --token-stdin \
  --compressed-video-dir "<logs_dir>/compressed-video" \
  --output "<logs_dir>/cnnvd-uploaded-attachments.json" \
  --apply-js "<logs_dir>/cnnvd-apply-upload-state.js"
```

禁止上传超过 50MB 的原始视频继续尝试；先压缩，再上传。
