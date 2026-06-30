# Testing Guide — How to Test Both Approaches

This guide shows how to test the CVS AI agent's two approaches
and what results to expect from each prompt.

---

## Two Approaches Available

| Approach | How It Works | Where Mode Is Selected |
|----------|-------------|----------------------|
| **In-Session** (primary) | Open `claude`, paste prompt, agent asks which mode | Inside Claude |
| **Terminal Launcher** (CI/CD) | Run `cvs-ai` / `cvs-ai-auto` / `cvs-ai-headless` from terminal | Before opening Claude |

---

## Approach 1: In-Session Mode (Test This First)

### How to Test

```bash
# Step 1: Open a terminal and launch Claude normally
cd ~/cvs-ai-agentic-solution-dell2N
claude

# Step 2: Paste any prompt from the table below

# Step 3: Agent asks "Which operating mode?"
#   → Pick Interactive, Autonomous, or Batch

# Step 4: Watch the agent adjust its behavior based on your choice
```

### Prompt-to-Result Table (In-Session)

| # | What You Paste Into Claude | Mode to Pick | What You Should See |
|---|---------------------------|:------------:|-------------------|
| 1 | `Set up CVS on head node 10.194.129.213 with worker 10.194.129.211. SSH user is root, key is ~/.ssh/id_rsa. Check everything is installed and ready.` | **Interactive** | Agent asks "proceed?" before SSH, before CVS install, before preflight. You approve each step. |
| 2 | `Set up CVS on head node 10.194.129.213 with worker 10.194.129.211. SSH user is root, key is ~/.ssh/id_rsa. Check everything is installed and ready.` | **Autonomous** | Agent SSHes, installs CVS, runs preflight — all without asking. Logs each command as it goes. |
| 3 | `Set up CVS on head node 10.194.129.213 with worker 10.194.129.211. SSH user is root, key is ~/.ssh/id_rsa. Check everything is installed and ready.` | **Batch** | Agent runs everything silently, gives you a summary at the end. |
| 4 | `Install CVS on head node 10.194.129.213 with worker 10.194.129.211. SSH user is root, key is ~/.ssh/id_rsa. Run health check and rccl all_reduce afterward.` | **Autonomous** | Full end-to-end: install → preflight → health check → RCCL. No permission prompts. |
| 5 | `Quick health check on 10.194.129.213. SSH user root, key ~/.ssh/id_rsa.` | **Batch** | Fast preflight + platform check. Minimal output. Pass/fail summary. |
| 6 | `Run RCCL all_reduce and all_gather on 10.194.129.213 and 10.194.129.211. SSH user root, key ~/.ssh/id_rsa.` | **Autonomous** | Preflight → RCCL test. Bandwidth table with GB/s per collective. |
| 7 | `Run GPU burn-in on 10.194.129.213. SSH user root, key ~/.ssh/id_rsa.` | **Interactive** | Agent asks before running each stress test (RVS, AGFHC, TransferBench). |
| 8 | `Is cluster 10.194.129.213 with worker 10.194.129.211 ready for distributed training? SSH user root, key ~/.ssh/id_rsa.` | **Autonomous** | Preflight → platform → RCCL → training canary. "Ready / Not ready" verdict. |
| 9 | `Run full cluster qualification overnight on 10.194.129.213 with worker 10.194.129.211. SSH user root, key ~/.ssh/id_rsa. Escalate hardware failures to Jira DCCS.` | **Autonomous** | tmux wrap → all suites → auto-heal → Jira tickets for HW issues. |

### What to Verify

| Check | Expected |
|-------|----------|
| Agent asks "Which mode?" | Yes — every time you start a new CVS task |
| Interactive mode: agent confirms before SSH | Yes — agent uses `AskUserQuestion` ("Proceed?") |
| Interactive mode: harness prompts appear | **No** — harness allows all, agent enforces confirmation |
| Autonomous mode: agent proceeds without asking | Yes — logs command, runs it, zero prompts |
| Autonomous mode: harness prompts appear | **No** — harness allows all |
| Batch mode: minimal output | Yes — summary at the end only |
| Deny hook blocks `rm -rf` | Yes — all modes, always |

### How Confirmation Works (Important)

```
                    settings.json
                    ┌──────────────────┐
                    │ allow: ssh, cvs, │ ← harness never prompts
                    │   pytest, scp    │
                    │ deny: rm -rf,    │ ← harness always blocks
                    │   reboot         │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        Interactive     Autonomous       Batch
              │              │              │
         Agent asks     Agent logs     Agent runs
         user first     and proceeds   silently
```

No harness popups in any mode. Interactive confirmation is done by the agent.

---

## Approach 2: Terminal Launcher (Test From Terminal)

### Prerequisites

```bash
# Make sure aliases are loaded
source ~/.bashrc

# Verify aliases exist
type cvs-ai cvs-ai-auto cvs-ai-headless
```

### Prompt-to-Result Table (Terminal)

| # | Terminal Command | What You Should See |
|---|-----------------|-------------------|
| 1 | `cvs-ai` | Banner says "Mode: Interactive". Claude opens. Paste your prompt inside. Agent asks permission before each cluster op. |
| 2 | `cvs-ai-auto` | Banner says "Mode: Autonomous". Claude opens. Paste your prompt inside. Agent runs without asking. |
| 3 | `cvs-ai-headless "Run preflight on 10.194.129.213. SSH user root, key ~/.ssh/id_rsa."` | No UI. Output prints to stdout. Claude exits when done. |
| 4 | `echo "Quick health check on 10.194.129.213. SSH user root, key ~/.ssh/id_rsa." \| cvs-ai-headless` | Same as #3 but prompt comes from stdin pipe. |
| 5 | `cvs-ai --help` | Shows usage, modes, examples, safety architecture. |
| 6 | `cvs-ai --version` | Shows current version (1.4.0). |
| 7 | `cvs-ai-auto` then paste: `Install CVS on 10.194.129.213 with worker 10.194.129.211. SSH user root, key ~/.ssh/id_rsa. Run rccl all_reduce.` | Full autonomous run: install → preflight → RCCL. No prompts. |

### What to Verify

| Check | Expected |
|-------|----------|
| `cvs-ai` shows Interactive banner | Yes |
| `cvs-ai-auto` shows Autonomous banner | Yes |
| `cvs-ai-headless` exits after completion | Yes |
| `cvs-ai-headless` with no prompt shows error | Yes — "Error: --headless requires a prompt" |
| `cvs-ai --help` shows all modes | Yes |

---

## Quick Validation Checklist

Run these commands in order to verify everything works:

```bash
# 1. Check aliases are loaded
source ~/.bashrc
type cvs-ai          # should show: cvs-ai is aliased to...

# 2. Test help
cvs-ai --help        # should show usage guide

# 3. Test version
cvs-ai --version     # should show 1.4.0

# 4. Test headless error handling
cvs-ai-headless      # should show error: requires a prompt

# 5. Test in-session mode (open Claude, paste a prompt)
claude
# paste: Quick health check on 10.194.129.213. SSH user root, key ~/.ssh/id_rsa.
# agent should ask "Which operating mode?"
# pick Interactive → agent confirms before SSH
# OR pick Autonomous → agent proceeds without asking
```

---

## Comparison: Which Approach to Use When

| Scenario | Use This | Why |
|----------|----------|-----|
| Normal daily use | **In-Session** (`claude` + paste prompt) | Most natural, mode selection inside Claude |
| Want to test mode behavior | **In-Session** | Can switch modes per-task without restarting |
| CI/CD pipeline | **Terminal** (`cvs-ai-headless`) | No interactive session needed |
| Cron job | **Terminal** (`cvs-ai-headless`) | Runs unattended |
| Demo to a customer | **In-Session** (pick Interactive) | Shows the human-in-the-loop safety |
| Overnight autonomous | **In-Session** (pick Autonomous) | Agent wraps in tmux, you disconnect |
| Scripted batch of clusters | **Terminal** (loop `cvs-ai-headless`) | One-shot per cluster |

---

## Troubleshooting

| Problem | Solution |
|---------|---------|
| `cvs-ai: command not found` | Run `source ~/.bashrc` or open a new terminal |
| `cvs-ai-headless` hangs | Check if Claude Code is installed: `claude --version` |
| Agent doesn't ask "which mode?" | Make sure you're in the `cvs-ai-agentic-solution-dell2N` directory |
| Terminal launcher spawns inside Claude | You ran it inside Claude. Exit Claude first, then run from terminal. |
| Prompt is missing SSH credentials | Always include: `SSH user is <user>, key is <path>` |

---

## File Locations

| File | Purpose |
|------|---------|
| `tools/cvs-ai.sh` | Terminal launcher script (all 3 modes) |
| `~/.bashrc` | Shell aliases (`cvs-ai`, `cvs-ai-auto`, `cvs-ai-headless`) |
| `CLAUDE.md` | In-session mode selection instructions (agent reads this) |
| `.claude/skills/cvs-operate/SKILL.md` | Magic prompt and sample prompts |
| `.claude/skills/cvs-operate/WORKFLOWS.md` | 7 pre-built workflows |
| `docs/terminal-mode/` | Backup of terminal-launcher approach docs |
| `docs/TESTING-GUIDE.md` | This file |
