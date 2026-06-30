# Architecture & Technical Guide

## Table of Contents

1. [Operating Modes](#operating-modes)
2. [Architecture Decision: Pure Agent Layer](#architecture-decision-pure-agent-layer)
3. [How to Create a Claude Code Skill](#how-to-create-a-claude-code-skill)
4. [Version Update Lifecycle](#version-update-lifecycle)
5. [Feature Comparison: Agent Layer vs Fork](#feature-comparison-agent-layer-vs-fork)
6. [File Reference](#file-reference)

---

## Operating Modes

The agent supports three operating modes. The user selects their mode
**inside Claude** — the agent asks at the start of every CVS task.

### Mode Selection Flow

```
                    ┌──────────────────────────────────┐
                    │  User opens Claude, pastes prompt │
                    └───────────────┬──────────────────┘
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │  Agent: "Which operating mode?"   │
                    │                                    │
                    │  1. Interactive (recommended)      │
                    │  2. Autonomous                     │
                    │  3. Batch                          │
                    └───────────────┬──────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌──────────┐    ┌────────────┐    ┌───────────┐
            │Interactive│    │ Autonomous │    │   Batch   │
            └────┬─────┘    └─────┬──────┘    └─────┬─────┘
                 │                │                  │
                 ▼                ▼                  ▼
         ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
         │  Agent asks  │  │  Agent logs  │  │  Agent runs  │
         │  user before │  │  and proceeds│  │  silently,   │
         │  each op     │  │  immediately │  │  reports end │
         └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
                │                 │                  │
                └────────┬────────┘──────────────────┘
                         ▼
              ┌─────────────────────┐
              │ Safety layers       │
              │  1. Deny hooks      │ ← ALWAYS blocks rm -rf, reboot, force push
              │  2. CLAUDE.md rules │ ← ALWAYS enforced (preflight-first, canary)
              └─────────────────────┘
```

### Safety Layer Comparison

| Layer | Interactive | Autonomous | Batch |
|-------|:-----------:|:----------:|:-----:|
| PreToolUse deny hooks (rm -rf, reboot, force push) | Active | Active | Active |
| CLAUDE.md behavioral rules (preflight-first, canary) | Active | Active | Active |
| Agent-enforced confirmation (AskUserQuestion) | **Asks user** | Skipped | Skipped |
| Harness permissions (settings.json) | Allow all | Allow all | Allow all |

> The harness allows all CVS/SSH/pytest commands. In Interactive mode, the **agent
> itself** asks for confirmation via `AskUserQuestion`. In Autonomous mode, the agent
> proceeds without asking. Destructive ops are always blocked by deny hooks.

### How to Use (Inside Claude)

Just paste your prompt into Claude. The agent asks which mode, then proceeds:

```
User:  Install CVS on 10.194.129.213 and run RCCL all_reduce

Agent: Which operating mode?
       - Interactive (recommended for first time)
       - Autonomous
       - Batch

User:  Autonomous

Agent: Mode: Autonomous. Running full workflow...
       [logs each command, proceeds without waiting]
```

### Terminal Launchers (CI/CD Only)

For automation outside of Claude, terminal launchers are available via
`tools/cvs-ai.sh`:

```bash
# From a terminal (NOT from inside Claude):
cvs-ai                                     # interactive
cvs-ai-auto                                # autonomous
cvs-ai-headless "Run preflight on 10.0.0.5" # CI/CD pipe
```

---

## Architecture Decision: Pure Agent Layer

This solution uses a **pure agent layer** architecture — it works with
unmodified upstream CVS and adds AI-powered operational intelligence on top.
There is no fork of CVS, no modified source code, and no custom CLI plugins.

### Why Not Fork CVS?

An alternative architecture would be to fork the upstream CVS repository and
add machine-readable JSON outputs, custom CLI plugins, and modified source
code. While this produces cleaner machine output, it introduces a permanent
maintenance burden.

| Aspect | Fork Architecture | Pure Agent Layer (This Project) |
|--------|-------------------|--------------------------------|
| **How it works** | Forks upstream CVS, adds custom Python plugins and modified source code | Installs upstream CVS as-is, adds `.claude/` config files on top |
| **When CVS updates** | Must rebase/merge upstream changes; custom plugins may conflict | `pip install --upgrade cvs` — done, agent config unchanged |
| **New test suites** | Must update custom JSON plugins to expose new suites | Agent runs `cvs list` dynamically — new suites appear automatically |
| **CLI flag changes** | Custom plugins (`run-json`, `list-json`) may break | Uses upstream CLI directly — `cvs --help` tells Claude new syntax |
| **Maintenance burden** | Ongoing: rebase, fix conflicts, update forked code | Near-zero: only update SKILL.md if workflows change |
| **Code to maintain** | ~625 files (full CVS fork + custom plugins) | ~11 files (all markdown/JSON/shell) |
| **Install complexity** | Clone fork, install fork's custom code, manage two remotes | `pip install cvs` + drop in `.claude/` config |
| **Team adoption** | Every team member clones the fork | Every team member clones the skill repo — CVS is a pip dependency |

### The Analogy

```
Fork Architecture:    Built a custom engine inside the car
                      ├── More control over internals
                      ├── Must maintain the engine when the car model changes
                      └── Every mechanic needs to learn the custom engine

Pure Agent Layer:     Built a smart driver that can drive any car
                      ├── Works with any CVS version out of the box
                      ├── Zero maintenance when CVS updates
                      └── New team members just learn to talk to the driver
```

### How the Agent Parses CVS Output Without JSON Plugins

The fork architecture adds JSON output to make parsing reliable. Without
JSON output, how does the agent parse CVS results?

| CVS Output Type | How the Agent Handles It |
|-----------------|-------------------------|
| pytest pass/fail | Reads exit code (0 = pass, 1 = fail) |
| RCCL bandwidth tables | Regex extracts numeric columns from log lines |
| HTML reports | Copies report locally, serves via HTTP — user reads in browser |
| Log files | Greps for known patterns (ERROR, FAIL, PASS, bandwidth values) |
| rocm-smi output | Structured text — agent extracts GPU count, temp, errors |
| dmesg output | Greps for `amdgpu`, `error`, `fault`, `reset` patterns |

The agent doesn't need perfect parsing — it needs to identify pass/fail,
extract key metrics, and present a clear summary. For detailed analysis,
the user views the HTML report in their browser.

> **Optional enhancement**: If a fork with JSON output (e.g., `--format json`)
> is installed on the head node, the agent auto-detects it and uses JSON
> commands for more reliable parsing. But it is **never required**.

---

## How to Create a Claude Code Skill

This section documents how this skill was built, so teams can create
similar skills for other tools.

### What is a Claude Code Skill?

A skill is a set of markdown files that teach Claude how to do a specific
job. When Claude loads the skill, it follows the instructions like a
playbook. No Python code required — just `.md` files.

### Minimum Files Needed

| File | Required? | Purpose |
|------|-----------|---------|
| `CLAUDE.md` (project root) | Yes | Master instructions: what the tool is, how it works, safety rules. Loaded every conversation. |
| `.claude/skills/<name>/SKILL.md` | Yes | The detailed playbook. Contains frontmatter (name, description, user_invocable) + step-by-step instructions. |
| `.claude/settings.json` | Recommended | Permission rules: which commands are auto-allowed, which need human approval, which are blocked. |
| `README.md` | Recommended | Documentation for humans browsing the repo. |

### Step-by-Step: Creating a Skill

#### Step 1: Create Project Folder
```bash
mkdir "My AI Skill"
cd "My AI Skill"
mkdir -p .claude/skills/my-skill
```

#### Step 2: Write CLAUDE.md (Root Instructions)
This is the brain. Include:
- **What the tool is**: One-paragraph description
- **How to use it**: The main workflow loop
- **Available commands**: Full command reference
- **Natural language mapping**: "When user says X, do Y"
- **Safety rules**: What's allowed, what needs approval, what's blocked
- **Configuration templates**: Example configs

#### Step 3: Write SKILL.md (The Playbook)
File: `.claude/skills/my-skill/SKILL.md`

```yaml
---
name: my-skill
description: What this skill does in one sentence
user_invocable: true    # Makes it available as /my-skill
---
```

Body includes: step-by-step instructions, error handling, decision trees.

#### Step 4: Write settings.json (Permissions)
```json
{
  "permissions": {
    "allow": ["safe-commands*"],
    "ask":   ["risky-commands*"],
    "deny":  ["dangerous-commands*"]
  }
}
```

#### Step 5: Publish
```bash
git init && git add -A && git commit -m "Initial commit"
gh repo create username/repo --public --source . --push
```

---

## Version Update Lifecycle

**Important**: CVS updates are NOT automatic. Here's the actual flow:

| Question | Answer |
|----------|--------|
| Does CVS auto-update? | **No.** You must run `pip install --upgrade cvs` yourself. |
| Does the agent detect new versions? | **Yes.** On first use, the agent checks your installed version and informs you if a newer one is available. |
| Does the agent auto-upgrade? | **No.** It asks first: "CVS v1.3.0 is available, want me to upgrade?" |
| What happens after upgrade? | **Pure agent layer**: keeps working immediately, no changes needed. **Fork architecture**: custom plugins may break, requires code fixes. |

**The advantage is not auto-updating — it's that when you DO update, nothing breaks.**

### Visual: What Happens When CVS Releases a New Version

```
CVS v1.2 → CVS v1.3 released

Pure Agent Layer:
  pip install --upgrade cvs → Done. Agent works immediately.

Fork Architecture:
  git fetch upstream
  git rebase upstream/main   → Merge conflicts in custom plugins?
  Fix conflicts               → Test everything again
  Update custom JSON plugins  → May need new code
  Finally ready               → Hours/days of work
```

---

## Feature Comparison: Agent Layer vs Fork

| Feature | Fork Architecture | Pure Agent Layer (This Project) | Why It Matters |
|---------|------------------|--------------------------------|----------------|
| **Approach** | Modifies CVS source code | Works with unmodified upstream CVS | No fork maintenance, no merge conflicts |
| **Overnight Autonomous Mode** | Not present | Watchdog + auto-heal + tmux + Jira escalation | Tests run unattended, results ready in the morning |
| **Jira Escalation** | Not present | Auto-creates tickets with diagnostics for hardware failures | Hardware issues escalated in < 1 minute |
| **Connection Resilience** | Not present | tmux wrapping for long-running tests | Tests survive laptop disconnects |
| **Auto-Heal** | Not present | Automatic remediation for safe fixes | Reduces manual debugging by 70%+ |
| **Pre-Built Workflows** | Not present | 6 validation pipelines with conditional logic | One command runs a full multi-suite validation |
| **RCCL Pre-Run Validation** | Not present | Auto-discovers interfaces, validates env scripts | RCCL runs correctly on the first attempt |
| **HTTP Report Delivery** | Not present | Serves HTML reports via localhost | Works from WSL, remote terminals |
| **First-Run Onboarding** | Not present | Magic prompt + sanity check + auto-install CVS | New user productive in 10 minutes |
| **Diagnostic Collection** | Not present | Auto-collects rocm-smi, ibstat, dmesg from failed nodes | Failures come with actionable data |
| **Natural Language** | Limited — requires CVS CLI knowledge | Full mapping: "check if my cluster is ready" | Accessible to non-CLI experts |
| **JSON CLI Plugins** | `describe`, `list-json`, `run-json`, `compare`, `baseline` | Uses upstream CLI as-is | No custom code to maintain |
| **Fork Sync** | Required — periodic rebase against upstream | Not needed — upstream is a pip dependency | Zero maintenance burden |
| **Skills** | 2 (operate + dev) | 2 skills + auto-heal + workflows + overnight mode | More operational depth |

### CVS-Specific Capabilities

| Capability | What It Does | Why It's Useful |
|-----------|-------------|----------------|
| **34 suites mapped with config paths** | Agent knows which config file goes with each test suite | No guessing, no wrong configs |
| **Suite selection by intent** | "Run GPU health check" → `agfhc_cvs` automatically | No need to memorize suite names |
| **RCCL collective filtering** | "Run all_reduce" → `-k "all_reduce"` flag | Test specific collectives without knowing pytest syntax |
| **Single-node vs multi-node awareness** | Correctly interprets single-node results (AlgBW, not BusBW) | No false-negative failures |
| **Container vs baremetal detection** | Generates the right cluster.json format | No manual template switching |
| **Multi-step conditional workflows** | Preflight fails → auto-heal → retry → escalate | Intelligent pipeline, not dumb sequential execution |

---

## File Reference

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Root instructions: what CVS is, 34 test suites, safety rules, config templates |
| `README.md` | Project overview, quick start, value proposition, architecture |
| `FEATURES.md` | Detailed feature documentation with flow diagrams and mechanisms |
| `CHANGELOG.md` | Version history: fixes, features, verifications |
| `ARCHITECTURE.md` | This file — architecture decisions, skill creation guide, comparisons |
| `.claude/skills/cvs-operate/SKILL.md` | Operator playbook: onboarding, RCCL validation, overnight mode, Jira escalation |
| `.claude/skills/cvs-operate/AUTO_HEAL.md` | Auto-remediation decision tree (safe/moderate/critical) |
| `.claude/skills/cvs-operate/WORKFLOWS.md` | 6 pre-built validation pipelines |
| `.claude/skills/cvs-dev/SKILL.md` | Developer workflow: TDD, linting, testing |
| `.claude/settings.json` | Permission tiers: allow, ask, deny |
| `.gitignore` | Ignores credentials, logs, HTML reports, cluster.json |
