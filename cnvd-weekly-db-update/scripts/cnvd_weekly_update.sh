#!/bin/bash
# CNVD 每周数据库更新脚本
# 用法: ./cnvd_weekly_update.sh [xml文件目录] [文件名1 文件名2 ...]
#   默认使用当前 job 的 input/xml
#   不指定文件名则处理该目录下所有 .xml 文件

set -e

# 路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(dirname "$SCRIPT_DIR")"
NOTIFY_SCRIPT="${SCRIPT_DIR}/dingtalk_notify.py"
JOB_ROOT="${JOB_ROOT:-$(pwd)}"
OUTPUT_DIR="${OUTPUT_DIR:-$JOB_ROOT/output}"
SUMMARY_FILE="$OUTPUT_DIR/summary.txt"
RESULT_FILE="$OUTPUT_DIR/update-result.json"

# 配置
SERVER="10.50.10.8"
SERVER_USER="root"
CONTAINER="crawlab"
REMOTE_TMP="/tmp"
CONTAINER_NEW="/opt/cnvd/new"
CONTAINER_CNVD="/opt/cnvd/cnvd"
SERVICE_CONFIG="${SERVICE_CONFIG:-$JOB_ROOT/input/service-config.json}"
MODE="${CNVD_WEEKLY_MODE:-update}"
DRY_RUN="${CNVD_WEEKLY_DRY_RUN:-false}"
DINGTALK_NOTIFY="${CNVD_WEEKLY_DINGTALK_NOTIFY:-false}"

read_service_config() {
    local field="$1"
    python3 - "$SERVICE_CONFIG" "$field" <<'PY' 2>/dev/null || true
import json
import sys

path, field = sys.argv[1], sys.argv[2]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

value = data
for part in field.split("."):
    if not isinstance(value, dict):
        value = None
        break
    value = value.get(part)

if isinstance(value, bool):
    print("true" if value else "false")
elif value is not None:
    print(value)
PY
}

if [ -f "$SERVICE_CONFIG" ]; then
    CONFIG_MODE="$(read_service_config mode)"
    CONFIG_REMOTE_HOST="$(read_service_config serviceConfig.remote_host)"
    CONFIG_REMOTE_USER="$(read_service_config serviceConfig.remote_user)"
    CONFIG_CONTAINER="$(read_service_config serviceConfig.docker_container)"
    CONFIG_DRY_RUN="$(read_service_config serviceConfig.dry_run)"
    CONFIG_DINGTALK_NOTIFY="$(read_service_config serviceConfig.dingtalk_notify)"

    [ -n "$CONFIG_MODE" ] && MODE="$CONFIG_MODE"
    [ -n "$CONFIG_REMOTE_HOST" ] && SERVER="$CONFIG_REMOTE_HOST"
    [ -n "$CONFIG_REMOTE_USER" ] && SERVER_USER="$CONFIG_REMOTE_USER"
    [ -n "$CONFIG_CONTAINER" ] && CONTAINER="$CONFIG_CONTAINER"
    [ -n "$CONFIG_DRY_RUN" ] && DRY_RUN="$CONFIG_DRY_RUN"
    [ -n "$CONFIG_DINGTALK_NOTIFY" ] && DINGTALK_NOTIFY="$CONFIG_DINGTALK_NOTIFY"
fi

# 参数
XML_DIR="${1:-$JOB_ROOT/input/xml}"
if [ "$#" -gt 0 ]; then
    shift
fi
FILE_NAMES=("$@")
PROCESSED_FILES=""
RESULT_WRITTEN="false"

mkdir -p "$OUTPUT_DIR"

json_escape() {
    python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'
}

write_result() {
    local status="$1"
    local message="$2"
    local escaped_xml_dir
    local escaped_message
    local escaped_files

    escaped_xml_dir="$(printf '%s' "$XML_DIR" | json_escape)"
    escaped_message="$(printf '%s' "$message" | json_escape)"
    escaped_files="$(printf '%s' "$PROCESSED_FILES" | json_escape)"

    cat > "$RESULT_FILE" <<RESULT_JSON
{
  "status": "$status",
  "message": $escaped_message,
  "xmlDir": $escaped_xml_dir,
  "processedFiles": $escaped_files
}
RESULT_JSON

    {
        echo "CNVD 周库更新: $status"
        echo ""
        echo "XML 目录: $XML_DIR"
        echo "结果: $message"
        if [ -n "$PROCESSED_FILES" ]; then
            echo ""
            echo "处理文件:"
            printf '%s\n' "$PROCESSED_FILES"
        fi
    } > "$SUMMARY_FILE"
    RESULT_WRITTEN="true"
}

notify_dingtalk() {
    local status="$1"
    local title="$2"
    local text="$3"

    if [ "$DINGTALK_NOTIFY" != "true" ]; then
        return 0
    fi

    if [ -f "$NOTIFY_SCRIPT" ]; then
        python3 "$NOTIFY_SCRIPT" \
            --title "$title" \
            --skill "cnvd-weekly-db-update" \
            --status "$status" \
            --text "$text" \
            --output "$XML_DIR" || true
    fi
}

notify_on_exit() {
    local exit_code="$?"
    if [ "$exit_code" -ne 0 ]; then
        if [ "$RESULT_WRITTEN" != "true" ]; then
            write_result "failed" "脚本异常退出，退出码：$exit_code"
        fi
        notify_dingtalk "failed" "CNVD每周数据库更新失败" "$(printf 'XML目录：%s\n退出码：%s' "$XML_DIR" "$exit_code")"
    fi
}

trap notify_on_exit EXIT

echo "=== CNVD 每周数据库更新 ==="
echo "XML 目录: $XML_DIR"
echo "执行模式: $MODE"
echo "dry_run: $DRY_RUN"
echo "dingtalk_notify: $DINGTALK_NOTIFY"
echo ""

# Step 1: 检查 XML 文件
echo "[Step 1] 检查 XML 文件..."
if [ ${#FILE_NAMES[@]} -gt 0 ]; then
    # 只处理指定的文件
    XML_FILES=""
    for fname in "${FILE_NAMES[@]}"; do
        fpath="$XML_DIR/$fname"
        if [ -f "$fpath" ]; then
            XML_FILES="$XML_FILES $fpath"
        else
            echo "警告: 文件不存在，跳过: $fname"
        fi
    done
    XML_FILES=$(echo "$XML_FILES" | xargs)  # trim
else
    # 默认处理所有 XML 文件
    XML_FILES=$(ls "$XML_DIR"/*.xml 2>/dev/null || true)
fi

if [ -z "$XML_FILES" ]; then
    echo "错误: 未找到 XML 文件"
    echo "请先通过前端或 API 上传 CNVD 周库 XML 到 input/xml/"
    write_result "failed" "未找到 XML 文件，请上传到 input/xml/"
    exit 1
fi
echo "找到文件:"
for f in $XML_FILES; do
    echo "  - $(basename "$f")"
done
echo ""

if [ "$MODE" = "check" ] || [ "$DRY_RUN" = "true" ]; then
    echo "[Check] 校验远端 SSH 和 Docker 容器，不执行写入更新..."
    ssh "$SERVER_USER@$SERVER" "docker ps --format '{{.Names}}' | grep -qx '$CONTAINER'"
    write_result "success" "检查完成：XML 文件存在，远端 SSH 和 Docker 容器可用；未执行写入更新。"
    echo "检查完成，未执行写入更新"
    exit 0
fi

if [ "$MODE" != "update" ]; then
    write_result "failed" "不支持的执行模式：$MODE"
    echo "错误: 不支持的执行模式: $MODE"
    exit 1
fi

# Step 2: 上传到服务器
echo "[Step 2] 上传文件到服务器 $SERVER..."
REMOTE_BASENAMES=""
for f in $XML_FILES; do
    scp -C "$f" "$SERVER_USER@$SERVER:$REMOTE_TMP/"
    REMOTE_BASENAMES="$REMOTE_BASENAMES $(basename "$f")"
done
echo "上传完成"
echo ""

# Step 3: 拷贝到 Docker 容器 + 执行解析
echo "[Step 3] 在服务器上执行操作..."
ssh "$SERVER_USER@$SERVER" bash -s -- "$CONTAINER" $REMOTE_BASENAMES << 'REMOTE_SCRIPT'
set -e
CONTAINER="$1"
shift

echo "进入 /tmp 目录..."
cd /tmp

# 列出 XML 文件
echo "待处理文件: $*"
if [ "$#" -eq 0 ]; then
    echo "错误: 未收到本次上传的 XML 文件名"
    exit 1
fi

# 逐个拷贝到容器
echo "拷贝文件到 Docker 容器..."
for f in "$@"; do
    echo "  docker cp $f $CONTAINER:/opt/cnvd/new/"
    docker cp "$f" "$CONTAINER:/opt/cnvd/new/"
done

# 进入容器执行解析
echo "进入容器执行解析脚本..."
docker exec "$CONTAINER" python3 /opt/cnvd/parse.py

# 归档文件
echo "归档处理完成的文件..."
docker exec "$CONTAINER" bash -c "cd /opt/cnvd/new && mv * ../cnvd/ 2>/dev/null || true"

echo "服务器端操作完成"
REMOTE_SCRIPT

echo ""
echo "=== 更新完成 ==="
echo "所有 XML 文件已解析入库并归档"

PROCESSED_FILES=""
for f in $XML_FILES; do
    PROCESSED_FILES="${PROCESSED_FILES}- $(basename "$f")
"
done
write_result "success" "所有 XML 文件已解析入库并归档"
notify_dingtalk "success" "CNVD每周数据库更新完成" "$(printf 'XML目录：%s\n处理文件：\n%s' "$XML_DIR" "$PROCESSED_FILES")"
