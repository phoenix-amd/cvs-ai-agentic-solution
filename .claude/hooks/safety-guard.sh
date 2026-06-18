#!/bin/bash
# Pre-execution safety guard
# Blocks dangerous commands before they run

COMMAND="$1"

if [[ -z "$COMMAND" ]]; then
    exit 0
fi

# Block destructive system commands
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
        echo "BLOCKED: Command matches dangerous pattern: $pattern"
        echo "This command has been denied by the safety guard."
        exit 1
    fi
done

# Warn on CVS run/exec commands (require human confirmation)
if echo "$COMMAND" | grep -qE "^cvs (run|exec)"; then
    echo "[safety-guard] NOTE: CVS test execution detected. Ensure user has approved this command."
fi

exit 0
