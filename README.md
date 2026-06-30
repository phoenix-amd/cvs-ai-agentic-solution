# CVS AI Agentic Solution

> **Autonomous AI-powered GPU cluster validation** — validates AMD Instinct clusters
> end-to-end using natural language, runs overnight unattended, auto-heals failures,
> and escalates hardware issues to Jira with full diagnostics.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-Skill-blue.svg)](https://claude.ai/claude-code)
[![AMD ROCm](https://img.shields.io/badge/AMD-ROCm_CVS-red.svg)](https://github.com/ROCm/cvs)
[![Field Tested](https://img.shields.io/badge/Field_Tested-MI300X_Cluster-green.svg)](#)

---

## Executive Summary

| Metric | Impact |
|--------|--------|
| **Overnight utilization** | Tests run unattended with auto-heal — zero wasted overnight hours |
| **Time to first result** | Minutes instead of hours — no manual config, auto-discovers hardware |
| **Escalation speed** | Hardware failures create Jira tickets in < 1 minute with full diagnostics |
| **Team onboarding** | New engineers productive in 10 minutes — no CVS expertise needed |
| **Test coverage** | 34 test suites across platform, health, RCCL, training, and inference |
| **Connection resilience** | Tests survive laptop disconnects — tmux wrapping on head node |

## The Problem

Validating AMD GPU clusters with CVS today requires:
- **Memorizing 34 test suites** and their config file locations
- **Manually editing JSON configs** with cluster-specific IPs, interfaces, and paths
- **Chaining pytest commands** in the right sequence (preflight before RCCL before training)
- **Babysitting overnight runs** — if a fixable issue occurs at 2 AM, nobody is there to fix it
- **Manually collecting diagnostics** (rocm-smi, dmesg, ibstat) and creating Jira tickets
- **Interpreting raw logs** — knowing that single-node bus_bw=0 is expected, not a failure

This is slow, error-prone, and wastes engineering hours — especially across large clusters
and during overnight qualification runs.

## The Solution

An AI agent built on [Claude Code](https://claude.ai/claude-code) that wraps AMD's
[Cluster Validation Suite (CVS)](https://github.com/ROCm/cvs) with autonomous
operation capabilities. You describe what you want in plain English; the agent
handles configuration, execution, analysis, remediation, and escalation.

```
You:    "Run RCCL all_reduce on nodes 10.0.0.1 through 10.0.0.4"

Agent:  1. Generates cluster.json with those 4 IPs
        2. Copies RCCL config template
        3. Runs preflight checks (all pass)
        4. Runs rccl_perf with -k "all_reduce"
        5. Reports: "All nodes passed. Avg bus bandwidth: 348 GB/s (target: 330)"
```

## Quick Start — 3 Steps, 10 Minutes

**You do NOT need to install CVS, edit configs, or set up anything manually.**
Clone, launch Claude, paste one prompt — the agent does the rest.

### Prerequisites

| Requirement | How to Check | Install Guide |
|-------------|-------------|---------------|
| **Claude Code** | `claude --version` | [claude.ai/claude-code](https://claude.ai/claude-code) |
| **SSH key access** to your GPU cluster | `ssh <headnode> hostname` | Your cluster admin |
| **Python 3.9+** on the head node | `ssh <headnode> 'python3 --version'` | Pre-installed on most clusters |
| **(Optional) Atlassian MCP** for Jira | Already configured if you use Jira with Claude | [setup guide](https://github.com/sooperset/mcp-atlassian) |

> You do NOT need to install CVS on the head node yourself — the agent does it automatically.

---

### Step 1: Clone

```bash
git clone https://github.com/phoenix-amd/cvs-ai-agentic-solution.git
cd cvs-ai-agentic-solution
```

### Step 2: Launch Claude Code

```bash
claude
```

Claude Code automatically loads the CVS skills. You'll see the Claude prompt.

> **Alternative for CI/CD**: Terminal launchers are also available —
> see [Terminal Launchers](#alternative-terminal-launchers-for-cicd) below.

### Step 3: Paste the Magic Prompt

Copy this template, fill in your cluster details, and paste it into Claude:

```
Set up CVS on head node <HEAD_IP> with worker nodes <WORKER_IP1,WORKER_IP2>.
SSH user is <YOUR_USERNAME>, key is ~/.ssh/id_ed25519.
Jira project is <JIRA_PROJECT_KEY>.
Check everything is installed and ready, then run a quick health check.
```

**Real example:**
```
Set up CVS on head node 10.194.129.213 with worker node 10.194.129.211.
SSH user is rghaffar, key is ~/.ssh/id_ed25519.
Jira project is DCCS.
Check everything is installed and ready, then run a quick health check.
```

### Step 4: Pick Your Mode (Agent Asks Automatically)

After you paste the prompt, the agent asks you to pick an operating mode:

```
Agent: "Which operating mode would you like for this task?"

  1. Interactive (recommended for first time)
     → I'll confirm before each cluster operation

  2. Autonomous
     → I'll run the full workflow end-to-end, logging each step

  3. Batch
     → I'll execute everything with minimal output
```

| Mode | Best For | What Happens |
|------|----------|-------------|
| **Interactive** | First-time use, debugging, demos | Agent asks "proceed?" before each SSH, CVS, and pytest command |
| **Autonomous** | Routine validation, overnight runs | Agent logs each command and proceeds without waiting |
| **Batch** | Repeat runs, quick checks | Agent runs silently, reports results at the end |

> **All modes run inside Claude.** No terminal commands, no mode switching,
> no separate launchers. Just type your prompt and pick a mode.

### What Happens Next (All Automatic)

After you paste the magic prompt, the agent runs through this checklist
automatically — you just watch:

```
 #   What the Agent Does                                You Do
 ──   ─────────────────────────────────────────────      ──────────
  1   Saves your cluster profile locally                 Nothing
  2   SSHes to head node, checks if CVS is installed     Nothing
  3   CVS missing? Installs it (pip install cvs)         Nothing
  4   Sets up SSH keys (head→self, head→workers)         Nothing
  5   Discovers network interfaces (eno8303, etc.)       Nothing
  6   Discovers RDMA hardware (mlx5, bnxt_re, etc.)      Nothing
  7   Checks Jira MCP connection                         Nothing*
  8   Runs 9-point sanity check                          Nothing
  9   Runs preflight + platform health check             Nothing
 10   Serves HTML report at http://localhost:7788         Open browser

 * If Jira MCP is not configured, the agent tells you how to set it up.
   All CVS tests still work — only Jira escalation is skipped.
```

### After Setup: Just Talk

Once setup is complete, you never need the magic prompt again.
Just describe what you want in plain English:

| What You Say | What the Agent Does |
|-------------|---------------------|
| "Check if the cluster is healthy" | Preflight + platform checks, per-node pass/fail report |
| "Run RCCL all_reduce on all nodes" | Auto-config → preflight → rccl_perf, bandwidth table |
| "Run full cluster qualification overnight" | Wraps in tmux → runs all suites → auto-heals → Jira for HW issues → results in the morning |
| "GPU burn-in on node 10.0.0.5" | AGFHC stress test (HBM, DMA, GFX, PCIe, XGMI) |
| "Is the cluster ready for training?" | Preflight → platform → RCCL → training canary |
| "Run memory bandwidth test" | TransferBench (all-to-all, P2P, healthcheck) |
| "Test inference readiness with vLLM" | Preflight → platform → vLLM smoke test |
| "Check RDMA connectivity across all nodes" | Preflight with full_mesh mode |

### Sample Prompts (Paste Any of These Into Claude)

| Task | What to Type |
|------|-------------|
| Quick health check | `Quick health check on 10.194.129.213 and 10.194.129.211. SSH user root, key ~/.ssh/id_rsa.` |
| Install + RCCL test | `Install CVS on head node 10.194.129.213 with worker 10.194.129.211. SSH user root, key ~/.ssh/id_rsa. Run health check and rccl all_reduce afterward.` |
| RCCL performance | `Run RCCL all_reduce and all_gather on 10.194.129.213 and 10.194.129.211. SSH user root, key ~/.ssh/id_rsa.` |
| GPU burn-in | `Run GPU burn-in on 10.194.129.213. SSH user root, key ~/.ssh/id_rsa.` |
| Network validation | `Check RDMA connectivity and IB bandwidth on 10.194.129.213 and 10.194.129.211. SSH user root, key ~/.ssh/id_rsa.` |
| Pre-training readiness | `Is cluster 10.194.129.213 with worker 10.194.129.211 ready for distributed training? SSH user root, key ~/.ssh/id_rsa.` |
| Overnight qualification | `Run full cluster qualification overnight on 10.194.129.213 with worker 10.194.129.211. SSH user root, key ~/.ssh/id_rsa. Auto-heal what you can, escalate hardware failures to Jira DCCS.` |

> After pasting any prompt, the agent asks which mode (Interactive / Autonomous / Batch).
> Pick one and the agent adjusts its behavior for the rest of the session.

## Architecture: Pure Agent Layer (No Fork)

This solution is a **pure agent layer**. It uses **unmodified upstream CVS**
(`pip install cvs`) and adds AI-powered operational intelligence on top.
No fork, no source code changes, no merge conflicts — ever.

### Why Pure Agent Layer, Not a Fork?

| Aspect | Fork Approach | Pure Agent Layer (This Project) |
|--------|--------------|--------------------------------|
| **How it works** | Forks CVS repo, modifies source code, adds custom plugins | Installs CVS as-is, adds `.claude/` config files on top |
| **When CVS updates** | Must rebase/merge; custom plugins may conflict | `pip install --upgrade cvs` — done |
| **New test suites** | Must update custom plugins to expose them | Agent runs `cvs list` — new suites appear automatically |
| **CLI flag changes** | Custom plugins may break | Uses upstream CLI directly |
| **Maintenance burden** | Ongoing: rebase, fix conflicts, update forked code | Near-zero: only update SKILL.md if workflows change |
| **Code to maintain** | ~625 files (full CVS fork + plugins) | ~11 files (all markdown/JSON/shell) |
| **Analogy** | Built a custom engine inside the car | Built a smart driver that can drive any car |

### How It Works

```
┌───────────────────────────────────────────────────────────────────┐
│  User: "run full cluster qualification overnight"                 │
└──────────────────────────────┬────────────────────────────────────┘
                               │
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                    CVS AI AGENTIC SOLUTION                         │
│                                                                    │
│  CLAUDE.md ──────────────────── Root instructions                  │
│  ├── 34 test suites, natural language mapping, safety rules        │
│                                                                    │
│  .claude/skills/cvs-operate/ ── Operator playbook                  │
│  ├── SKILL.md ─── Guided flow, RCCL validation, Jira escalation    │
│  ├── AUTO_HEAL.md ─── Fix-it-or-escalate decision tree             │
│  └── WORKFLOWS.md ─── 6 pre-built validation pipelines             │
│                                                                    │
│  Key Capabilities:                                                 │
│  ├── First-run onboarding ─── Collects creds, runs sanity check    │
│  ├── Auto-discovery ───────── Interfaces, NIC type, MPI paths      │
│  ├── Connection resilience ── tmux wrapping for long tests         │
│  ├── Overnight autonomous ── Watchdog + auto-heal + re-run         │
│  ├── Jira escalation ─────── Hardware failures → ticket + logs     │
│  ├── HTTP report serving ─── Browser-ready localhost links         │
│  └── Prompt-injection defense  Cluster output = data, never code   │
│                                                                    │
│  Safety tiers: Allow (read-only) | Ask (test exec) | Deny (rm -rf) │
└──────────────────────────────┬─────────────────────────────────────┘
                               │
            ┌──────────────────┼─────────────────┐
            ▼                  ▼                 ▼
  ┌──────────────────┐ ┌──────────────┐ ┌─────────────────┐
  │  Upstream CVS    │ │  Jira (MCP)  │ │  Confluence     │
  │  (unmodified)    │ │  Escalation  │ │  Documentation  │
  │  pytest + pSSH   │ │  tickets     │ │  pages          │
  │  → GPU cluster   │ │  + logs      │ │                 │
  └──────────────────┘ └──────────────┘ └─────────────────┘
```

## Test Coverage (34 Suites)

### Summary by Category

| Category | Suites | What You Learn |
|----------|--------|----------------|
| **Platform** | 1 | Is the OS, BIOS, kernel, ROCm, firmware correct and consistent? |
| **Preflight** | 1 | Can all nodes talk to each other (SSH + RDMA)? |
| **Health** | 4 (+5 install) | Are the GPUs physically healthy (memory, compute, PCIe, XGMI)? |
| **RCCL** | 2 | How fast can GPUs communicate across nodes? |
| **IB Perf** | 1 (+1 install) | How fast is the network fabric? |
| **Training** | 8 | Can the cluster actually train LLMs at expected throughput? |
| **Inference** | 9 | Can the cluster serve inference at expected throughput? |
| **MORI** | 1 | Is the Pensando AINIC performing correctly? |

### Detailed Suite Reference

#### Platform & Preflight

| Suite | What It Collects | Key Commands on Nodes | Key Metrics |
|-------|-----------------|----------------------|-------------|
| **`host_configs_cvs`** | OS version, kernel, BIOS, ROCm version, GPU firmware (CP_MEC, RLC, SDMA, VCN, PSP, TA_RAS, TA_XGMI, PM per GPU), PCI realloc, IOMMU PT, NUMA balancing, total memory, GPU count, PCIe speed/width per GPU, PCIe ACS, dmesg errors | `cat /etc/os-release`, `uname -a`, `dmidecode`, `amd-smi`, `lspci`, `sysctl`, `dmesg` | Per-node pass/fail for 13 system checks |
| **`preflight_checks`** | SSH reachability, RDMA interface presence/state, GID index consistency, ROCm version consistency, inter-node RDMA connectivity (basic or full-mesh) | `rdma link`, `ibv_rc_pingpong`, `amd-smi version` | Node reachability matrix, RDMA pair connectivity |

#### GPU Health

| Suite | What It Validates | Key Metrics |
|-------|------------------|-------------|
| **`agfhc_cvs`** | GPU burn-in: HBM memory stress, DMA engine, GFX compute, PCIe bandwidth, XGMI link stress | Per-GPU pass/fail, error counts, temperature under stress |
| **`csp_qual_agfhc`** | CSP qualification variant — same tests, cloud provider thresholds | Per-GPU pass/fail with CSP criteria |
| **`transferbench_cvs`** | GPU memory bandwidth: all-to-all, peer-to-peer, healthcheck | GB/s per GPU pair, P2P bandwidth matrix |
| **`rvs_cvs`** | ROCm Validation Suite: memory test, compute stress, PCIe bandwidth | Memory errors, compute correctness, PCIe GB/s |

#### RCCL (Multi-GPU Communication)

| Suite | What It Validates | Key Metrics |
|-------|------------------|-------------|
| **`rccl_perf`** | Multi-node collective performance: all_reduce, all_gather, reduce_scatter, broadcast, alltoall, alltoallv, scatter, gather, sendrecv (message sizes 1KB–16GB) | AlgBW (GB/s), BusBW (GB/s), latency (us), #Wrong errors |
| **`rccl_regression`** | Same collectives sweeping algorithm (Ring/Tree), protocol (Simple), QPS, PXN, channel combinations | Per-algorithm/protocol bandwidth comparison |

#### IB / Network Performance

| Suite | What It Validates | Key Metrics |
|-------|------------------|-------------|
| **`ib_perf_bw_test`** | InfiniBand bandwidth and latency between node pairs | Bandwidth (GB/s), latency (us) per IB port pair |

#### Training Benchmarks

| Suite | Model | Scope | Key Metrics |
|-------|-------|-------|-------------|
| **`jax_llama3_1_70b_single`** | Llama 3.1 70B | Single-node JAX | TFLOPS/GPU, tokens/sec/GPU |
| **`jax_llama3_1_70b_distributed`** | Llama 3.1 70B | Multi-node JAX | TFLOPS/GPU, scaling efficiency |
| **`jax_llama3_1_405b_distributed`** | Llama 3.1 405B | Multi-node JAX | TFLOPS/GPU, scaling efficiency |
| **`megatron_llama3_1_8b_single`** | Llama 3.1 8B | Single-node Megatron | TFLOPS/GPU, tokens/sec/GPU |
| **`megatron_llama3_1_8b_distributed`** | Llama 3.1 8B | Multi-node Megatron | TFLOPS/GPU, scaling efficiency |
| **`megatron_llama3_1_70b_single`** | Llama 3.1 70B | Single-node Megatron | TFLOPS/GPU, tokens/sec/GPU |
| **`megatron_llama3_1_70b_distributed`** | Llama 3.1 70B | Multi-node Megatron | TFLOPS/GPU, scaling efficiency |
| **`test_aorta`** | Aorta benchmark | Distributed | Training throughput, convergence |

#### Inference Benchmarks

| Suite | Model | Key Metrics |
|-------|-------|-------------|
| **`vllm_gpt_oss_120b_single`** | GPT-OSS 120B | Tokens/sec, latency (ms) |
| **`vllm_qwen3_235b_single`** | Qwen3 235B | Tokens/sec, latency (ms) |
| **`vllm_qwen3_80b_single`** | Qwen3 80B | Tokens/sec, latency (ms) |
| **`vllm_deepseek31_685b_single`** | DeepSeek V3.1 685B | Tokens/sec, latency (ms) |
| **`inferencemax_gpt_oss_120b_single`** | GPT-OSS 120B | Tokens/sec, latency (ms) |
| **`sglang_deepseek_r1_671b_distributed`** | DeepSeek R1 671B | Tokens/sec, latency (ms) |
| **`sglang_llama_70b_distributed`** | Llama 70B | Tokens/sec, latency (ms) |
| **`pytorch_xdit_flux1_dev_single`** | Flux.1 text-to-image | Images/sec, latency per image |
| **`pytorch_xdit_wan22_14b_single`** | WAN 2.2 14B video | Frames/sec, latency per frame |

#### MORI (AMD Pensando AINIC)

| Suite | What It Validates | Key Metrics |
|-------|------------------|-------------|
| **`mori_benchmark_test`** | RDMA benchmarks for Pensando AINIC | Bandwidth (GB/s), latency (us) |

## Key Features

### Pure Agent Layer (No Fork Required)
Works with **upstream unmodified CVS** (`pip install cvs`). The agent
installs CVS on the head node automatically — you never touch CVS directly.
When AMD releases a new CVS version, just `pip install --upgrade cvs` — no
fork to rebase, no merge conflicts, always compatible.

> **Note**: If a JSON-enhanced CVS fork (with `--format json` support) is
> installed, the skill auto-detects it and uses JSON commands for more reliable
> parsing. But it is **not required** — upstream CVS works perfectly.

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

### Persistent Result Storage
Every test result is saved to a **timestamped folder** on your local drive
— never lost on reboot. Auto-detects your OS:

| Platform | Save Location |
|----------|-------------|
| **WSL** | `C:\Users\<you>\Downloads\cvs_results\` (Windows Explorer) |
| **Linux** | `~/Downloads/cvs_results/` |
| **Custom** | Set `CVS_RESULTS_DIR` env var |

```
Downloads/cvs_results/
├── 2026-06-18_173025_preflight_checks/
├── 2026-06-18_180730_rccl_perf_all_reduce/
└── 2026-06-19_091500_host_configs_cvs/
```

Multiple runs per day each get their own folder — nothing is overwritten.

### HTTP Report Delivery
After every test, serves HTML reports via local HTTP server with a
browser-ready link. Works from WSL, remote terminals, and headless
environments where `xdg-open` is not available.

### Interactive Dashboard
Say "show me a dashboard" and the agent generates a Grafana-inspired
interactive HTML dashboard with gauge meters, bandwidth charts, per-node
comparison tables, and pass/fail status cards. 4 tabs: Overview, Nodes,
Tests, RCCL Performance. Served locally via `http://localhost:7788/`.

> **Static Sample**: [View Sample Dashboard](https://phoenix-amd.github.io/cvs-ai-agentic-solution/sample_dashboard.html)
> | [View Feature Guide](https://phoenix-amd.github.io/cvs-ai-agentic-solution/features.html)
>
> The sample is a static example for reference only. **Live dashboards are
> always generated fresh** from real test data and served locally — the agent
> prints a clickable `http://localhost:7788/` link in the conversation.

### Self-Update Version Check
On every session start, the agent checks GitHub for newer versions. If an
update is available, it informs you and offers to update with one command.
Never auto-updates without asking.

### Prompt-Injection Defense
Cluster output is treated as DATA, never instructions. If remote node output
contains text that looks like commands or prompt fragments, it's ignored and
flagged.

> **Detailed documentation**: See [FEATURES.md](FEATURES.md) for in-depth
> explanation of each feature — why it exists, the value it provides, and
> how the mechanisms work under the hood (includes flow diagrams).

## Safety Model

| Tier | Commands | Interactive | Autonomous | Batch |
|------|----------|:-----------:|:----------:|:-----:|
| **Allow** | `cvs list`, `cvs --version`, `pip list` | Auto | Auto | Auto |
| **Cluster ops** | `ssh`, `cvs run`, `cvs exec`, `pytest`, `scp` | **Agent asks you** | Auto (zero prompts) | Auto (silent) |
| **Deny** | `rm -rf /`, `mkfs`, `reboot`, `force push` | **Blocked** | **Blocked** | **Blocked** |

> **How it works**: The harness allows all commands at the settings level. In
> **Interactive mode**, the agent itself enforces confirmation using `AskUserQuestion`
> before each cluster operation. In **Autonomous mode**, the agent skips confirmation
> and proceeds immediately. **Deny hooks** block destructive operations regardless of mode.

### Alternative: Terminal Launchers (for CI/CD)

For automation outside of Claude (cron jobs, CI pipelines), terminal launchers
are available:

```bash
# From a terminal (NOT from inside Claude):
cvs-ai                              # launches Claude in interactive mode
cvs-ai-auto                         # launches Claude in autonomous mode
cvs-ai-headless "your prompt here"  # one-shot pipe mode, no UI
```

> These are shell aliases in `~/.bashrc`. They launch new Claude sessions.
> For normal use, just open Claude and type your prompt — the agent handles mode selection.

## Project Structure

```
.
├── CLAUDE.md                              # Root agent instructions (34 suites, safety rules)
├── README.md                              # This file — overview, quick start, value prop
├── FEATURES.md                            # Detailed feature docs with flow diagrams
├── CHANGELOG.md                           # Version history: fixes, features, verifications
├── ARCHITECTURE.md                        # Architecture decisions, pure agent vs fork, skill guide
├── version.txt                            # Current version (used by self-update checker)
├── .gitignore                             # Ignores .cvs_agent/, *.html, cluster.json
├── tools/
│   ├── cvs-ai.sh                          # Two-mode launcher (interactive/autonomous/headless)
│   ├── cssh.sh                            # Clean SSH wrapper (strips Conductor banner noise)
│   ├── dashboard.py                       # Interactive HTML dashboard generator
│   └── version_check.py                   # Self-update version checker
└── .claude/
    ├── NOTES.md                           # Working notes & TODOs
    ├── settings.json                      # Permission rules (allow/deny + agent-enforced confirmation)
    └── skills/
        ├── cvs-operate/                   # THE MAIN SKILL — cluster validation operator
        │   ├── SKILL.md                   # Guided flow, RCCL validation, overnight mode,
        │   │                              #   Jira escalation, sanity check, 15 don'ts
        │   ├── AUTO_HEAL.md               # Fix-it-or-escalate decision tree
        │   └── WORKFLOWS.md               # 6 pre-built validation pipelines
        └── cvs-dev/
            └── SKILL.md                   # Developer workflow (TDD, linting, testing)
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
| Persistent results | No | No | Timestamped folders, OS-aware |
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
