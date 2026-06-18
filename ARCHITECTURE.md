# CVS AI Agentic Solution — Skill Guide & Comparison

---

## How to Create Any Claude Code Skill — Step by Step

### What is a Claude Code Skill?

A skill is a set of markdown files that teach Claude how to do a specific job. When you type `/skill-name` in Claude Code, it loads the skill's instructions and Claude follows them like a playbook. No Python code required — just `.md` files.

### Minimum Files Needed

| File | Required? | Purpose |
|------|-----------|---------|
| `CLAUDE.md` (project root) | Yes | Master instructions: what the tool is, how it works, safety rules. Loaded every conversation. |
| `.claude/skills/<name>/SKILL.md` | Yes | The detailed playbook for the skill. Contains frontmatter (name, description, user_invocable) + step-by-step instructions. |
| `.claude/settings.json` | Recommended | Permission rules: which commands are auto-allowed, which need human approval, which are blocked. |
| `.claude/hooks/*.sh` | Optional | Shell scripts that run automatically before/after tool use (e.g., auto-lint, auto-test, safety guards). |
| `README.md` | Optional | Documentation for humans browsing the repo. |

### Step-by-Step: Creating a Skill (Using CVS as Example)

#### Step 1: Create Project Folder
```
mkdir "CVS AI Agentic Solution"
cd "CVS AI Agentic Solution"
mkdir -p .claude/skills/cvs-operate .claude/skills/cvs-dev .claude/hooks
```

#### Step 2: Write CLAUDE.md (Root Instructions)
This is the brain. Include:
- **What the tool is**: "CVS is AMD's cluster validation framework for GPU clusters"
- **How to use it**: The 5-step validation loop (setup → discover → validate → run → analyze)
- **Available commands**: All 34 test suites with descriptions
- **Natural language mapping**: "When user says X, do Y"
- **Safety rules**: What's allowed, what needs approval, what's blocked
- **Configuration templates**: cluster.json examples

#### Step 3: Write SKILL.md (The Playbook)
File: `.claude/skills/cvs-operate/SKILL.md`

Frontmatter:
```yaml
---
name: cvs-operate
description: Autonomously operate AMD CVS to validate GPU clusters
user_invocable: true    # Makes it available as /cvs-operate
---
```

Body includes:
- How to parse user requests (extract IPs, test type, mode)
- How to generate cluster.json from user-provided IPs
- Which config file to use for each test suite
- How to run preflight → tests → analysis in sequence
- Error handling and diagnostics
- Auto-heal playbook (fix what's safe, escalate the rest)

#### Step 4: Write settings.json (Permissions)
File: `.claude/settings.json`
```json
{
  "permissions": {
    "allow": ["cvs list", "cvs --version", "cvs copy-config*"],
    "ask":   ["cvs run *", "cvs exec *", "ssh *"],
    "deny":  ["rm -rf /", "reboot", "mkfs*", "git push --force*"]
  }
}
```

#### Step 5: Write Hooks (Quality Gates)
- `post-edit.sh`: Auto-runs linter + matching unit tests after file edits
- `safety-guard.sh`: Blocks dangerous commands before execution

#### Step 6: Write README.md
Explain what the project does, how to install, how to use.

#### Step 7: Publish to GitHub
```bash
git init && git add -A && git commit -m "Initial commit"
gh repo create username/repo-name --public --source . --push
```

---

## How Version Updates Actually Work

**Important clarification**: Updates are NOT automatic. Here's the real flow:

| Question | Answer |
|----------|--------|
| Does CVS auto-update? | **No.** You must run `pip install --upgrade cvs` yourself. |
| Does the agent detect new versions? | **Yes.** On first use each session, the agent checks your installed version and tells you if a newer one is available. |
| Does the agent auto-upgrade? | **No.** It asks you first: "CVS v1.3.0 is available, want me to upgrade?" |
| What happens after you upgrade? | **Our agent**: keeps working immediately, no changes needed. **Fork (fork architecture)**: custom plugins may break, requires code fixes. |

**The advantage is not auto-updating — it's that when you DO update, nothing breaks on our side.** fork architecture must rebase his fork, fix merge conflicts, and update custom plugins every time upstream CVS changes.

### Visual: What Happens When CVS Releases a New Version

```
CVS v1.2 → CVS v1.3 released

Our approach:
  pip install --upgrade cvs → Done. Agent works immediately.

Fork approach (fork architecture):
  git fetch upstream
  git rebase upstream/main   → Merge conflicts in custom plugins?
  Fix conflicts               → Test everything again
  Update custom JSON plugins  → May need new code
  Finally ready               → Hours/days of work
```

---

## Architecture: Pure Agent Layer vs Fork

| Aspect | Fork Approach (fork architecture) | Pure Agent Layer (Ours) |
|--------|---------------------------|------------------------|
| **How it works** | Forks upstream CVS repo, adds custom Python plugins and modified source code | Installs upstream CVS as-is, adds `.claude/` config files on top |
| **When CVS updates** | Must rebase/merge upstream changes; custom plugins may conflict | Just `pip install --upgrade cvs` — agent config unchanged |
| **New test suites** | Must update custom JSON plugins to expose new suites | Agent runs `cvs list` dynamically — new suites appear automatically |
| **CLI flag changes** | Custom plugins (`run-json`, `list-json`) may break | Uses upstream CLI directly — `cvs --help` tells Claude new syntax |
| **Maintenance burden** | Ongoing: rebase, fix conflicts, update forked code | Near-zero: only update SKILL.md if workflows change |
| **Code to maintain** | ~625 files (full CVS fork + custom plugins) | ~11 files (all markdown/JSON/shell) |
| **Analogy** | Built a custom engine inside the car | Built a smart driver that can drive any car |

---

## Feature Comparison: Ours vs fork architecture

| Feature | JSON-enhanced CVS fork | CVS AI Agentic Solution (Ours) | Why It Matters |
|---------|---------------|----------------------------------|----------------|
| **Approach** | Fork of upstream CVS — modifies source code | Pure agent layer — works with unmodified upstream CVS | No fork maintenance, no merge conflicts, always compatible with latest CVS |
| **Auto-Heal** | Not present | Automatic remediation for safe fixes (NUMA balancing, docker pull, SSH key permissions) | Reduces manual debugging — agent fixes what it can, escalates the rest |
| **Pre-Built Workflows** | Not present | 6 workflow sequences: full qualification, network validation, pre-training readiness, GPU burn-in, quick health check, inference readiness | One command runs a full multi-suite validation pipeline with conditional logic |
| **Diagnostic Collection** | Not present | Auto-collects rocm-smi, ibstat, dmesg from failed nodes | Failures come with actionable diagnostic data, not just "test failed" |
| **Natural Language Mapping** | Limited — requires knowing CVS CLI commands | Rich mapping: "check if my cluster is ready for training" just works | Accessible to non-CLI-experts; faster for everyone |
| **JSON CLI Plugins** | Custom `describe`, `list-json`, `run-json`, `compare`, `baseline`, `validate`, `preflight` commands | Uses upstream CVS commands as-is | No custom code to maintain; works with any CVS version |
| **Fork Sync Needed?** | Yes — requires periodic rebase against upstream | No — upstream is a pip dependency, not a fork | Zero maintenance burden |
| **Install Complexity** | Clone fork, install fork's custom code | `pip install cvs` + drop in .claude/ config | Simpler, cleaner setup |
| **Skills** | 2 (operate + dev) | 2 skills + auto-heal playbook + pre-built workflows library | More operational depth |
| **Hooks** | `upstream-guard.sh` + `post-edit.sh` | `safety-guard.sh` + `post-edit.sh` | Both have quality gates; ours focuses on operational safety |

---

## CVS-Specific Unique Features (Ours)

| Feature | What It Does | Why It's Useful |
|---------|-------------|----------------|
| **All 34 suites mapped with config paths** | Agent knows exactly which config file goes with each test suite | No guessing, no wrong configs |
| **Suite selection guide** | Translates user intent → correct suite name | "Run GPU health check" → `agfhc_cvs` automatically |
| **RCCL collective filtering** | "Run all_reduce" → `-k "all_reduce"` flag | Test specific collectives without knowing pytest syntax |
| **Container vs baremetal auto-detection** | Generates the right cluster.json format based on context | No manual template switching |
| **Scalability awareness** | Knows shard tuning for 1000+ node clusters (`CVS_HOSTS_PER_SHARD`, `CVS_WORKERS_PER_CPU`) | Proper large-cluster configuration out of the box |
| **Multi-step conditional workflows** | If preflight fails → auto-heal → retry → escalate if still failing | Intelligent pipeline, not dumb sequential execution |

---

## What Each File Does (CVS Example)

| File | Lines | Purpose |
|------|-------|---------|
| `CLAUDE.md` | 195 | Root instructions: what CVS is, 5-step validation loop, 34 test suites, safety rules, config templates |
| `.claude/skills/cvs-operate/SKILL.md` | 195 | Operator playbook: parse requests, generate configs, run tests, analyze results, error handling |
| `.claude/skills/cvs-operate/AUTO_HEAL.md` | 85 | Auto-remediation: decision tree for common failures, safe vs moderate vs critical fix classification |
| `.claude/skills/cvs-operate/WORKFLOWS.md` | 95 | 6 pre-built validation sequences with conditional logic |
| `.claude/skills/cvs-dev/SKILL.md` | 85 | Developer guide: repo layout, TDD workflow, lint/test commands, plugin creation template |
| `.claude/settings.json` | 55 | Permissions: allow (read-only), ask (test execution), deny (destructive commands) |
| `.claude/hooks/post-edit.sh` | 40 | Auto-format with ruff + run matching unit tests + warn if file > 500 lines |
| `.claude/hooks/safety-guard.sh` | 35 | Block dangerous commands (rm -rf, reboot, force push) |
| `.claude/NOTES.md` | 20 | Working notes + TODO list for future features |
| `README.md` | 130 | Project documentation: what, why, install, usage, feature comparison |
| `.gitignore` | 20 | Ignore logs, results, credentials, IDE files |
