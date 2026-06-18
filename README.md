# CVS AI Agentic Solution

An AI-powered autonomous operator for AMD's [Cluster Validation Suite (CVS)](https://github.com/ROCm/cvs). Instead of memorizing CLI commands and manually checking results, just tell Claude what you want in plain English.

## What This Does

| Traditional CVS | With This Agent |
|----------------|-----------------|
| Write cluster.json manually | Say "use nodes 10.0.0.1 through 10.0.0.4" |
| Remember 34 suite names | Say "run GPU health check" |
| Copy and edit config files | Agent picks the right config automatically |
| Read raw pytest output | Agent summarizes pass/fail per node |
| Debug failures manually | Agent runs diagnostics and suggests fixes |
| Chain multiple tests manually | Say "full cluster qualification" and it runs the whole sequence |

## Quick Start

### Prerequisites
- [Claude Code](https://claude.ai/claude-code) installed
- Python 3.9+
- SSH access to your GPU cluster nodes

### Install

```bash
# 1. Clone this repo
git clone https://github.com/phoenix-amd/cvs-ai-agentic-solution.git
cd cvs-ai-agentic-solution

# 2. Install upstream CVS
git clone https://github.com/ROCm/cvs.git
cd cvs && pip install -e . && cd ..

# 3. Verify
cvs --version
cvs list
```

### Use

Open Claude Code in this directory and just talk:

```
> Check if nodes 10.0.0.1 and 10.0.0.2 are healthy

> Run RCCL all_reduce on the cluster

> Full cluster qualification on 10.0.0.1, 10.0.0.2, 10.0.0.3, 10.0.0.4

> Run GPU burn-in on node 10.0.0.5

> Test inference readiness with vLLM
```

The agent will:
1. Generate `cluster.json` from your IPs
2. Run preflight checks first (always)
3. Execute the right test suite with the right config
4. Summarize results clearly
5. If something fails — run diagnostics and suggest fixes

## Skills

| Skill | Invoked By | Purpose |
|-------|-----------|---------|
| `cvs-operate` | `/cvs-operate` | Full cluster validation operator — the main skill |
| `cvs-dev` | (auto-loaded) | Development workflow for CVS contributors |

## What Makes This Different

### vs. Raw CVS CLI
- No need to memorize commands, suite names, or config paths
- Automatic preflight before every test run
- Human-readable summaries instead of raw pytest output

### vs. JSON-enhanced CVS fork fork
- **Auto-healing**: Automatically attempts safe fixes (NUMA, docker pull, SSH perms) before escalating
- **Pre-built workflows**: Full qualification, network validation, pre-training readiness — one command
- **Diagnostic collection**: On failure, automatically gathers rocm-smi, ibstat, dmesg from failed nodes
- **No fork required**: Works with upstream ROCm/cvs as-is — pure agent layer, no code modifications
- **Natural language**: Richer command mapping — "check if my cluster is ready for training" just works

## Supported Hardware

- AMD Instinct MI300X
- AMD Instinct MI355X
- InfiniBand / RoCE networking
- AMD Pensando AINIC

## Project Structure

```
.claude/
  NOTES.md                          # Agent working notes
  settings.json                     # Permission rules (allow/ask/deny)
  hooks/
    post-edit.sh                    # Auto-lint + auto-test after edits
    safety-guard.sh                 # Block dangerous commands
  skills/
    cvs-operate/
      SKILL.md                      # Main operator skill definition
      AUTO_HEAL.md                  # Auto-remediation playbook
      WORKFLOWS.md                  # Pre-built validation sequences
    cvs-dev/
      SKILL.md                      # Developer workflow skill
CLAUDE.md                           # Root agent instructions
README.md                           # This file
```

## Safety

- **Read-only commands are auto-allowed**: `cvs list`, `cvs --version`, `cvs copy-config --list`
- **Test execution requires human approval**: `cvs run`, `cvs exec`, SSH commands
- **Dangerous commands are blocked**: `rm -rf /`, `reboot`, `mkfs`, force push
- Preflight is always run before heavy tests
- Agent shows the exact command before executing

## License

MIT

## Credits

- [AMD ROCm CVS](https://github.com/ROCm/cvs) — the upstream cluster validation framework
- [Claude Code](https://claude.ai/claude-code) — the AI agent runtime
- Inspired by [JSON-enhanced CVS fork](https://github.com/JSON-enhanced CVS fork/tree/feature/cluster-validation-engine)
