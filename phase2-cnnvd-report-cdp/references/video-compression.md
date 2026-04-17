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

如果视频超过 50MB，使用 ffmpeg 压缩：

```bash
ffmpeg -i "<原视频路径>" -vcodec libx264 -crf 28 -preset fast -acodec aac -b:a 128k /tmp/cnnvd_video_compressed.mp4 -y
```

### 2.3 验证压缩结果

```bash
ls -lh /tmp/cnnvd_video_compressed.mp4
```

## 三、压缩参数说明

| 参数 | 说明 |
|-----|------|
| `-crf 28` | 压缩质量（数值越大压缩率越高，28 为较高压缩） |
| `-preset fast` | 编码速度（可选：ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow） |
| `-b:a 128k` | 音频比特率 |

## 四、上传压缩后的文件

```
MCP: upload_file
  uid: "<点击上传按钮的 uid>"
  filePath: "/tmp/cnnvd_video_compressed.mp4"
```