#!/bin/bash
# chrome-devtools-mcp wrapper script
# 用于 Claude Code MCP 集成
# 连接到用户启动的调试端口 9223

exec /opt/homebrew/bin/chrome-devtools-mcp --browserUrl http://127.0.0.1:9223 "$@"