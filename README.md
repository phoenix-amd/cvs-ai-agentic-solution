# CVS AI Agentic Solution

> AI-powered autonomous operator for AMD's [Cluster Validation Suite (CVS)](https://github.com/ROCm/cvs).
> Tell Claude what you want in plain English — it handles the rest.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blue.svg)](https://claude.ai/claude-code)
[![AMD ROCm](https://img.shields.io/badge/AMD-ROCm_CVS-red.svg)](https://github.com/ROCm/cvs)

---

## The Problem

Running CVS manually requires memorizing 34 test suites, configuring JSON files, chaining pytest commands, and interpreting raw logs. This is slow and error-prone, especially across large clusters.

## The Solution

A Claude Code skill that wraps CVS with natural language understanding. You describe what you want; the agent figures out the commands, configs, and sequence.

```
You:    "Run RCCL all_reduce on nodes 10.0.0.1 through 10.0.0.4"

Agent:  1. Generates cluster.json with those 4 IPs
        2. Copies RCCL config template
        3. Runs preflight checks (all pass)
        4. Runs rccl_perf with -k "all_reduce"
        5. Reports: "All nodes passed. Avg bus bandwidth: 348 GB/s (target: 330)"
```

## Quick Start

### Prerequisites

- [Claude Code](https://claude.ai/claude-code) installed
- Python 3.9+ with pip
- SSH access to your GPU cluster (passwordless key-based)
- AMD Instinct GPUs (MI300X, MI325X, MI350, MI355X)

### Install

```bash
# 1. Clone this skill
git clone https://github.com/phoenix-amd/cvs-ai-agentic-solution.git
cd cvs-ai-agentic-solution

# 2. Clone and install upstream CVS
git clone https://github.com/ROCm/cvs.git
cd cvs
python3 -m venv .cvs_venv && source .cvs_venv/bin/activate
pip3 install -r requirements.txt
cd ..

# 3. Verify
cvs --version && cvs list
```

### Use

Open Claude Code in the project directory:

```bash
cd cvs-ai-agentic-solution
claude
```

Then just talk:

| What you say | What happens |
|-------------|-------------|
| "Check if nodes 10.0.0.1-4 are healthy" | Preflight + platform checks on all 4 nodes |
| "Run RCCL all_reduce on the cluster" | Config generation → preflight → rccl_perf -k all_reduce |
| "Full cluster qualification" | Preflight → platform → AGFHC → RCCL (sequential pipeline) |
| "GPU burn-in on node 10.0.0.5" | AGFHC stress test (HBM, DMA, GFX, PCIe, XGMI) |
| "Test inference readiness with vLLM" | Preflight → platform → vLLM smoke test |
| "Is the cluster ready for distributed training?" | Preflight → platform → RCCL → single-node training canary |
| "Run memory bandwidth test" | TransferBench (all-to-all, P2P, healthcheck) |
| "Check RDMA connectivity across all nodes" | Preflight with full_mesh mode |

## Architecture

```
┌─────────────────────────────────────────────────┐
│  User: "run GPU health check on 10.0.0.1"      │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  CLAUDE.md (root instructions)                   │
│  ├── What CVS is, supported hardware             │
│  ├── 34 test suites with descriptions            │
│  ├── Natural language → action mapping           │
│  └── Safety rules & exit codes                   │
├──────────────────────────────────────────────────┤
│  .claude/skills/cvs-operate/SKILL.md             │
│  ├── First-contact guided flow (6 steps)         │
│  ├── Suite selection guide with paths            │
│  ├── Config parameters & performance targets     │
│  ├── Auto-heal playbook                          │
│  ├── Pre-built workflows                         │
│  └── Safety: SSH access, prompt-injection defense│
├──────────────────────────────────────────────────┤
│  .claude/settings.json                           │
│  ├── allow: read-only CVS commands               │
│  ├── ask: test execution, SSH, docker            │
│  └── deny: rm -rf, reboot, mkfs, force push     │
├──────────────────────────────────────────────────┤
│  .claude/hooks/                                  │
│  ├── post-edit.sh: auto-lint, auto-test          │
│  └── safety-guard.sh: block dangerous commands   │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────┐
│  Upstream CVS (unmodified)                       │
│  pip install / git clone ROCm/cvs                │
│  pytest + parallel-SSH → GPU cluster             │
└──────────────────────────────────────────────────┘
```

## Test Coverage (34 Suites)

| Category | Suites | What It Validates |
|----------|--------|-------------------|
| **Platform** | 1 | OS, kernel, BIOS, ROCm, PCIe, NUMA, firmware versions |
| **Preflight** | 1 | SSH connectivity, RDMA, GID consistency, NIC health |
| **Health** | 4 | GPU stress (AGFHC), memory bandwidth (TransferBench), GPU validation (RVS) |
| **RCCL** | 2 | Multi-node GPU communication: 9 collectives across message sizes |
| **IB Perf** | 1 | InfiniBand bandwidth and latency benchmarks |
| **Training** | 8 | JAX (Llama 70B/405B), Megatron (Llama 8B/70B), Aorta benchmark |
| **Inference** | 9 | vLLM, SGLang, InferenceMAX, xDiT (text/image/video) |
| **MORI** | 1 | RDMA benchmarks for AMD Pensando AINIC |

## Key Features

### Pure Agent Layer (No Fork)
Works with upstream CVS as-is. When CVS releases a new version, just
`pip install --upgrade cvs` — no fork to rebase, no merge conflicts.

### First-Run Onboarding
On first use, the agent collects SSH credentials, head/worker node IPs,
and Jira project keys from the user — then stores them in a local profile
(`~/.cvs_agent/`). No credentials are ever committed to git. Supports
multiple cluster profiles for teams managing several clusters.

### Auto-Heal Playbook
When tests fail, the agent doesn't just report — it attempts safe fixes:
- **Auto-fix**: NUMA balancing, docker pull, SSH key permissions
- **Suggest**: Firewall rules, environment variables, GRUB config
- **Escalate**: Reboots, driver installs, hardware issues

### Overnight Autonomous Mode
Start a full cluster qualification before leaving for the night. The agent:
1. Wraps all tests in **tmux** on the head node (survives disconnects)
2. Runs suites sequentially with auto-heal on failures
3. Re-runs failed tests after auto-heal succeeds
4. Collects diagnostics and creates Jira tickets for hardware issues
5. Writes a consolidated summary — results ready in the morning

```
You:    "Run full cluster qualification overnight"
Agent:  Launches watchdog in tmux → you disconnect → reconnect in the morning
        → summary report with pass/fail per suite is waiting for you
```

### Connection Resilience
Long-running tests (AGFHC, training, full RCCL sweeps) are wrapped in
**tmux sessions** on the head node. If your laptop disconnects, VPN drops,
or SSH times out — the test keeps running. Reconnect anytime to check
progress or collect results.

### Jira Escalation for Hardware Failures
When the agent detects a **real hardware issue** (GPU not detected, HBM
errors, PCIe link degraded, IB port down, RAS errors), it automatically:
1. Collects diagnostics (`rocm-smi`, `dmesg`, `ibstat`, `lspci`)
2. Creates a Jira ticket with failure summary
3. Attaches all diagnostic logs to the ticket
4. Tags the correct component from the cluster profile

Config/software issues are fixed in place — only hardware issues get escalated.

### Pre-Built Workflows
One command triggers multi-suite pipelines with conditional logic:
- Full Cluster Qualification (preflight → platform → health → RCCL)
- Network Validation (preflight → IB perf → RCCL)
- Pre-Training Readiness (preflight → platform → RCCL → training canary)
- GPU Burn-In (preflight → RVS → AGFHC → TransferBench)

### Canary-First Pattern
For multi-node clusters, tests run on ONE node first. If the canary passes,
the full fleet runs. This catches config errors before wasting cluster time.

### RCCL Pre-Run Validation
Automatically discovers network interfaces, validates env scripts against
actual NIC hardware (Mellanox/Broadcom/AINIC), and fixes common config
pitfalls (`mpi_dir`, `mpi_oob_port`, `NCCL_SOCKET_IFNAME`) before running.

### Smart Single-Node Handling
Correctly interprets single-node RCCL results — reports AlgBW instead of
BusBW, avoids false-negative failures from multi-node baseline comparisons.

### Diagnostic Collection
On any failure, the agent auto-collects from affected nodes:
`rocm-smi`, `ibstat`, `dmesg`, `ethtool`, `rdma link` — bundled into
a diagnostic summary.

### HTTP Report Delivery
After every test, serves HTML reports via local HTTP server with a
browser-ready link. Works from WSL, remote terminals, and headless
environments where `xdg-open` is not available.

### Prompt-Injection Defense
Cluster output is treated as DATA, never instructions. If remote node output
contains text that looks like commands or prompt fragments, it's ignored and
flagged.

> **Detailed documentation**: See [FEATURES.md](FEATURES.md) for in-depth
> explanation of each feature — why it exists, the value it provides, and
> how the mechanisms work under the hood (includes flow diagrams).

## Safety Model

| Tier | Commands | Behavior |
|------|----------|----------|
| **Allow** | `cvs list`, `cvs --version`, `cvs copy-config`, `cvs generate`, `pip list` | Auto-approved |
| **Ask** | `cvs run`, `cvs exec`, `pytest`, `ssh`, `docker`, `sudo` | Requires human approval |
| **Deny** | `rm -rf /`, `mkfs`, `reboot`, `shutdown`, `git push --force` | Blocked entirely |

## Project Structure

```
.
├── CLAUDE.md                              # Root agent instructions
├── README.md                              # This file
├── FEATURES.md                            # Detailed feature docs with mechanisms
├── CHANGELOG.md                           # Version history, fixes, features
├── ONENOTE_EXPORT.md                      # Formatted export for documentation
├── .gitignore
└── .claude/
    ├── NOTES.md                           # Working notes & TODOs
    ├── settings.json                      # Permission rules + hooks
    ├── hooks/
    │   ├── post-edit.sh                   # Auto-lint + auto-test
    │   └── safety-guard.sh                # Dangerous command blocker
    └── skills/
        ├── cvs-operate/
        │   ├── SKILL.md                   # Main operator playbook
        │   ├── AUTO_HEAL.md               # Auto-remediation decision tree
        │   └── WORKFLOWS.md               # Pre-built validation sequences
        └── cvs-dev/
            └── SKILL.md                   # Developer workflow guide
```

## Why Use This

| Problem | Without This Tool | With This Tool |
|---------|------------------|----------------|
| Running overnight tests | You babysit SSH or risk losing results | Agent wraps in tmux, auto-heals, results ready at 8 AM |
| Hardware failure at 2 AM | Nobody notices until morning standup | Agent creates Jira ticket with full diagnostics at 2:01 AM |
| Wrong RCCL config | 3 failed attempts figuring out `mpi_dir`, `eth0`, env scripts | Agent auto-discovers interfaces, validates env scripts, runs first time |
| New team member onboarding | Read 50 pages of CVS docs, memorize 34 suites | Say "check if the cluster is healthy" — agent does the rest |
| Cluster qualification | 4+ hours of manual pytest commands, config editing, log parsing | "Full cluster qualification" — one command, consolidated report |
| Single-node RCCL confusion | CVS says FAILED (false negative), you panic | Agent explains bus_bw=0 is expected, reports AlgBW correctly |
| VPN drops mid-test | Test killed, start over | tmux keeps it running, reconnect anytime |

## Comparison with Alternatives

| Feature | Raw CVS CLI | Fork-based Agent | **This Project** |
|---------|------------|-----------------|------------------|
| Natural language | No | Limited | Full mapping |
| Version updates | Manual | Rebase required | `pip upgrade` — done |
| Auto-heal | No | No | Safe fixes + escalation |
| Overnight autonomous | No | No | tmux + watchdog + Jira |
| Jira escalation | Manual | No | Auto-create with diagnostics |
| Connection resilience | No | No | tmux wrapping |
| RCCL auto-config | Manual | Partial | Full auto-discovery |
| Pre-built workflows | No | No | 6 pipelines |
| Canary-first | Manual | No | Built-in |
| Diagnostics on failure | Manual | No | Auto-collected |
| Team onboarding | Read docs | Read docs | First-run wizard |
| Prompt-injection defense | N/A | No | Built-in |
| Maintenance | N/A | Ongoing fork sync | Near-zero |

## Supported Hardware

| Component | Models |
|-----------|--------|
| **GPUs** | AMD Instinct MI300X, MI325X, MI350, MI355X |
| **OS** | Ubuntu 24.04 (kernel 6.8/6.14), Ubuntu 22.04 (kernel 5.15/6.8) |
| **ROCm** | 7.0.2+ |
| **Network** | InfiniBand, RoCE, AMD Pensando AINIC |

## License

MIT

## Credits

- [AMD ROCm CVS](https://github.com/ROCm/cvs) — upstream cluster validation framework
- [Claude Code](https://claude.ai/claude-code) — AI agent runtime
- [AMD ROCm Documentation](https://rocm.docs.amd.com/projects/cvs/en/latest/)
