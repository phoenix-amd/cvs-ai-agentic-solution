#!/usr/bin/env bash
# ============================================================================
# cvs-ai — CVS AI Agentic Solution Launcher
# ============================================================================
# Two execution modes for cluster validation:
#
#   Interactive  (default)  — human-in-the-loop, permission prompts active
#   Autonomous              — agent-driven, safety via CLAUDE.md + deny hooks
#
# Usage:
#   cvs-ai                           # interactive mode
#   cvs-ai --auto                    # autonomous mode
#   cvs-ai --headless "prompt"       # CI/CD pipe mode (zero UI)
#   cvs-ai --mode interactive        # explicit mode selection
#   cvs-ai --mode autonomous         # explicit mode selection
#   cvs-ai --help                    # show this help
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

usage() {
    cat <<'EOF'
CVS AI Agentic Solution — Cluster Validation Agent

USAGE:
    cvs-ai [OPTIONS] [PROMPT...]

MODES:
    (default)               Interactive — human approves each cluster operation
    --auto                  Autonomous  — agent-driven, no permission prompts
    --headless "prompt"     CI/CD       — pipe mode, zero UI, stdout only
    --mode <interactive|autonomous>     Explicit mode selection

OPTIONS:
    -h, --help              Show this help
    -v, --version           Show version

EXAMPLES:
    cvs-ai                                          # start interactive session
    cvs-ai --auto                                   # start autonomous session
    cvs-ai --headless "Run preflight on 10.0.0.5"   # one-shot, no UI
    echo "Check GPU health" | cvs-ai --headless      # pipe from stdin

SAFETY ARCHITECTURE:
    Interactive:  Permission prompts + CLAUDE.md rules + deny hooks
    Autonomous:   CLAUDE.md rules + deny hooks (no prompts)
    Both modes:   Destructive commands (rm -rf, reboot, force push) are
                  ALWAYS blocked by the PreToolUse safety-guard hook.
EOF
}

show_version() {
    if [[ -f "$PROJECT_DIR/version.txt" ]]; then
        cat "$PROJECT_DIR/version.txt"
    else
        echo "unknown"
    fi
}

# Banner shown at session start
show_banner() {
    local mode="$1"
    echo -e ""
    echo -e "${BOLD}${CYAN}  CVS AI Agentic Solution${RESET}"
    echo -e "${CYAN}  ========================${RESET}"
    if [[ "$mode" == "autonomous" ]]; then
        echo -e "  Mode: ${BOLD}${GREEN}Autonomous${RESET} (agent-driven, deny hooks active)"
    else
        echo -e "  Mode: ${BOLD}${YELLOW}Interactive${RESET} (human-in-the-loop)"
    fi
    echo -e "  Safety: deny hooks + CLAUDE.md behavioral rules"
    echo -e ""
}

# Parse arguments
MODE="interactive"
HEADLESS=false
PROMPT_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto|--autonomous)
            MODE="autonomous"
            shift
            ;;
        --headless)
            MODE="autonomous"
            HEADLESS=true
            shift
            # Remaining args are the prompt
            PROMPT_ARGS=("$@")
            break
            ;;
        --mode)
            shift
            case "${1:-}" in
                interactive) MODE="interactive" ;;
                autonomous|auto) MODE="autonomous" ;;
                *)
                    echo -e "${RED}Error: Unknown mode '$1'. Use 'interactive' or 'autonomous'.${RESET}" >&2
                    exit 2
                    ;;
            esac
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -v|--version)
            show_version
            exit 0
            ;;
        *)
            PROMPT_ARGS+=("$1")
            shift
            ;;
    esac
done

# Build claude command
CLAUDE_CMD=(claude)
CLAUDE_ARGS=()

if [[ "$MODE" == "autonomous" ]]; then
    CLAUDE_ARGS+=(--dangerously-skip-permissions)
fi

# Headless mode: pipe prompt, capture output
if [[ "$HEADLESS" == true ]]; then
    PROMPT="${PROMPT_ARGS[*]:-}"
    if [[ -z "$PROMPT" ]]; then
        # Read from stdin if no prompt given
        PROMPT="$(cat)"
    fi
    if [[ -z "$PROMPT" ]]; then
        echo -e "${RED}Error: --headless requires a prompt (argument or stdin).${RESET}" >&2
        exit 2
    fi
    cd "$PROJECT_DIR"
    echo "$PROMPT" | "${CLAUDE_CMD[@]}" "${CLAUDE_ARGS[@]}" --print
    exit $?
fi

# Interactive / Autonomous: show banner, launch claude
show_banner "$MODE"
cd "$PROJECT_DIR"

if [[ ${#PROMPT_ARGS[@]} -gt 0 ]]; then
    # If user passed a prompt on the command line, send it as initial message
    "${CLAUDE_CMD[@]}" "${CLAUDE_ARGS[@]}" --prompt "${PROMPT_ARGS[*]}"
else
    "${CLAUDE_CMD[@]}" "${CLAUDE_ARGS[@]}"
fi
