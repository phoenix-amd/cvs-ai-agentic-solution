#!/bin/bash
# Pre-execution safety guard
# Claude Code passes tool input as JSON on stdin:
# {"tool_name":"Bash","tool_input":{"command":"..."}, ...}

COMMAND=$(python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

BLOCKED_PATTERNS=(
    "rm -rf /"
    "rm -rf /*"
    "mkfs"
    "fdisk"
    "dd if="
    "reboot"
    "shutdown"
    "poweroff"
    "halt"
    "init 0"
    "init 6"
    "chmod -R 777 /"
    "chown -R .* /"
    "git push --force"
    "git push -f"
)

for pattern in "${BLOCKED_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        echo "BLOCKED: $pattern"
        exit 1
    fi
done

exit 0
