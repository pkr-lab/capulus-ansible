#!/bin/sh
set -u

state_dir="${STATE_DIR:-/run/ollama-idle-suspend}"
state_file="${state_dir}/last_busy"
idle_minutes="${IDLE_MINUTES:-15}"
max_load="${MAX_LOAD:-1.0}"
ollama_port="${OLLAMA_PORT:-11434}"
suspend_command="${SUSPEND_COMMAND:-systemctl suspend}"

now="$(date +%s)"
mkdir -p "$state_dir"
[ -f "$state_file" ] || echo "$now" > "$state_file"

busy_reason() {
  if curl -fsS --max-time 3 "http://127.0.0.1:${ollama_port}/api/ps" 2>/dev/null | grep -q '"name"'; then
    echo "ollama-modell geladen"
    return 0
  fi
  for session in $(loginctl list-sessions --no-legend 2>/dev/null | awk '{print $1}'); do
    if [ "$(loginctl show-session "$session" -p IdleHint --value 2>/dev/null)" = "no" ]; then
      echo "sitzung $session aktiv"
      return 0
    fi
  done
  if systemd-inhibit --list --no-legend 2>/dev/null | grep -qE '(sleep|idle).*block[[:space:]]*$'; then
    echo "sperre gegen schlafen aktiv"
    return 0
  fi
  if awk -v max="$max_load" '{ exit !($2 >= max) }' /proc/loadavg; then
    echo "last ueber ${max_load}"
    return 0
  fi
  return 1
}

if reason="$(busy_reason)"; then
  echo "$now" > "$state_file"
  exit 0
fi

last="$(cat "$state_file")"
idle_seconds=$((now - last))
if [ "$idle_seconds" -ge $((idle_minutes * 60)) ]; then
  echo "$now" > "$state_file"
  logger -t ollama-idle-suspend "seit $((idle_seconds / 60)) min ohne aktivitaet, suspend"
  $suspend_command
fi
