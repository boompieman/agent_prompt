#!/bin/sh
# 挑一個能用的 Python。Windows 上 python3 常是 Microsoft Store 空殼，要用 py -3。
if command -v python3 >/dev/null 2>&1 && python3 -c '' >/dev/null 2>&1; then
  exec python3 "$@"
fi
exec py -3 "$@"
