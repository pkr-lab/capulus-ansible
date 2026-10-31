#!/bin/sh
case "$1" in
  post)
    mkdir -p /run/ollama-idle-suspend
    date +%s > /run/ollama-idle-suspend/last_busy
    systemctl --no-block restart nvidia-power-limit.service
    systemctl --no-block restart ollama.service
    ;;
esac
