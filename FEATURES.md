# Feature Guide — CVS AI Agentic Solution

Comprehensive technical documentation of every capability in the CVS AI
Agentic Solution. Each feature is documented with a consistent structure:

- **Why This Exists** — the problem it solves
- **Value** — measurable impact on engineering time and reliability
- **Who Decides** — whether the agent acts autonomously or waits for user input
- **How It Works** — technical mechanism with flow diagrams
- **Scenario** — real-world example showing the feature in action

This document is designed for **technical presentations, architecture reviews,
and executive briefings**. Every feature has been field-tested on production
AMD Instinct MI300X GPU clusters.

**15 features | 34 test suites | Pure agent layer | Zero fork maintenance**

---

## Table of Contents

1. [Overnight Autonomous Mode](#1-overnight-autonomous-mode)
2. [Jira Escalation for Hardware Failures](#2-jira-escalation-for-hardware-failures)
3. [Connection Resilience (tmux)](#3-connection-resilience-tmux-wrapping)
4. [First-Run Onboarding](#4-first-run-onboarding)
5. [RCCL Pre-Run Validation](#5-rccl-pre-run-validation)
6. [Auto-Heal Playbook](#6-auto-heal-playbook)
7. [Smart Single-Node Handling](#7-smart-single-node-handling)
8. [HTTP Report Delivery & Persistent Storage](#8-http-report-delivery--persistent-result-storage)
9. [Pre-Built Workflows](#9-pre-built-workflows)
10. [Canary-First Pattern](#10-canary-first-pattern)
11. [Prompt-Injection Defense](#11-prompt-injection-defense)
12. [Persistent Result Storage (OS-Aware)](#12-persistent-result-storage-os-aware)
13. [Auto-Install CVS](#13-auto-install-cvs)
14. [Magic Prompt (Single Entry Point)](#14-magic-prompt-single-entry-point)
15. [9-Point Sanity Check](#15-9-point-sanity-check)

---

## 1. Overnight Autonomous Mode

### Why This Exists

GPU cluster validation tests can take **hours**. AGFHC level 3 stress tests
run 2-8 hours. Full cluster qualification across preflight, platform, health,
and RCCL can take 4+ hours. Teams typically start these tests in the evening
and check results in the morning.

**The problem**: If a test fails at 2 AM due to a fixable issue (wrong config,
NUMA balancing enabled, docker image not pulled), the entire overnight window
is wasted. Nobody is watching. The team arrives at 8 AM, sees the failure,
fixes the config, and has to wait another 4 hours.

### Value

- **Zero wasted overnight hours**: Agent auto-heals fixable issues and re-runs
- **Morning-ready results**: Team arrives to a consolidated pass/fail report
- **Hardware issues caught immediately**: Jira tickets created at 2:01 AM, not 10 AM
- **No babysitting required**: Launch and disconnect — results are waiting

### How It Works — Full Mechanism

```
                    USER SAYS: "Run full qualification overnight"
                                       |
                                       v
                    ┌──────────────────────────────────────┐
                    │  Agent generates watchdog script      │
                    │  customized for requested test suites │
                    └──────────────────┬───────────────────┘
                                       |
                                       v
                    ┌──────────────────────────────────────┐
                    │  Agent launches script in tmux        │
                    │  on the HEAD NODE (not laptop)        │
                    │  ssh head 'tmux new -d -s cvs_night   │
                    │    "bash ~/cvs_overnight.sh"'         │
                    └──────────────────┬───────────────────┘
                                       |
                     USER CAN DISCONNECT — TEST KEEPS RUNNING
                                       |
                                       v
              ┌─────────────────────────────────────────────────┐
              │            WATCHDOG LOOP (on head node)          │
              │                                                  │
              │  for each suite in [preflight, platform,         │
              │                     health, rccl, ...]:          │
              │                                                  │
              │    ┌─────────────┐                               │
              │    │  Run Suite   │                               │
              │    └──────┬──────┘                               │
              │           |                                      │
              │     ┌─────┴─────┐                                │
              │     │  PASSED?  │                                │
              │     └─────┬─────┘                                │
              │       YES │    NO                                │
              │           │     |                                │
              │           │     v                                │
              │           │  ┌──────────────────────┐            │
              │           │  │ Categorize Failure    │            │
              │           │  │ (config? software?    │            │
              │           │  │  hardware?)           │            │
              │           │  └──────────┬───────────┘            │
              │           │         ┌───┴───┐                    │
              │           │    CONFIG/SW    HARDWARE              │
              │           │         |           |                │
              │           │         v           v                │
              │           │  ┌────────────┐ ┌──────────────────┐ │
              │           │  │ Auto-Heal  │ │ Collect          │ │
              │           │  │ Attempt    │ │ Diagnostics      │ │
              │           │  └─────┬──────┘ │ (rocm-smi,       │ │
              │           │        |        │  dmesg, ibstat)   │ │
              │           │   ┌────┴────┐   └────────┬─────────┘ │
              │           │   │ FIXED?  │            |           │
              │           │   └────┬────┘            v           │
              │           │   YES  │  NO    ┌────────────────┐   │
              │           │        │   |    │ Create Jira    │   │
              │           │        v   |    │ Ticket +       │   │
              │           │  ┌────────┐|    │ Attach Logs    │   │
              │           │  │RE-RUN  │|    └────────────────┘   │
              │           │  │Suite   │|                         │
              │           │  └────────┘|                         │
              │           │        |   |                         │
              │           v        v   v                         │
              │    ┌──────────────────────────┐                  │
              │    │ Log result to summary.txt │                  │
              │    │ Continue to next suite     │                  │
              │    └───────────────────────────┘                  │
              └─────────────────────────────────────────────────┘
                                       |
                                       v
              ┌─────────────────────────────────────────────────┐
              │  ALL SUITES COMPLETE                             │
              │                                                  │
              │  summary.txt contains:                           │
              │  - Per-suite PASS/FAIL with timestamps           │
              │  - Auto-heal actions taken and results           │
              │  - Jira tickets created (if any)                 │
              │  - HTML reports for each suite                   │
              │  - Total runtime                                 │
              └─────────────────────────────────────────────────┘
                                       |
                        USER RECONNECTS IN THE MORNING
                                       |
                                       v
              ┌─────────────────────────────────────────────────┐
              │  Agent reads summary.txt                         │
              │  Serves all HTML reports via HTTP                │
              │  Presents consolidated report to user            │
              │  Lists any Jira tickets created                  │
              └─────────────────────────────────────────────────┘
```

### Failure Classification (How the Agent Decides)

The agent classifies each failure to decide whether to auto-heal or escalate:

| Signal in Logs | Classification | Action |
|---------------|---------------|--------|
| `<changeme>` in config | **Config issue** | Fix the config field, re-run |
| `Permission denied (publickey)` | **SSH issue** | Fix SSH keys, re-run |
| `No network interfaces for OOB` | **Config issue** | Discover correct interface, re-run |
| `NCCL failure: invalid usage` | **Software issue** | Fix env script, re-run |
| `numa_balancing = 1` | **Config issue** | Auto-fix: `echo 0 > /proc/sys/kernel/numa_balancing`, re-run |
| `Container not found` | **Software issue** | Auto-fix: `docker pull <image>`, re-run |
| `GPU not detected` / missing in `lspci` | **Hardware** | Collect diagnostics → Jira |
| `ECC error` / `page retirement` in dmesg | **Hardware** | Collect diagnostics → Jira |
| `PCIe width x8` (expected x16) | **Hardware** | Collect diagnostics → Jira |
| `XGMI link failure` | **Hardware** | Collect diagnostics → Jira |
| `ibstat: port DOWN` | **Hardware** | Collect diagnostics → Jira |
| `amdgpu: GPU reset` in dmesg | **Hardware** | Collect diagnostics → Jira |
| Repeated RCCL timeout after env fix | **Hardware** | Collect diagnostics → Jira |

### Auto-Heal Retry Rules

- **Maximum 1 auto-heal attempt per failure type** — no retry loops
- If auto-heal fixes the issue → re-run the suite **once**
- If the re-run passes → continue to next suite
- If the re-run fails again → classify as unresolvable, log it, continue
- **Never auto-heal hardware issues** — always escalate

---

## 2. Jira Escalation for Hardware Failures

### Why This Exists

When a GPU has a memory error at 3 AM, the current workflow is:
1. Nobody notices until morning
2. Engineer checks logs manually
3. Engineer copies error messages into a Jira ticket
4. Engineer runs `rocm-smi`, `dmesg`, `ibstat` to collect diagnostics
5. Engineer attaches files to the ticket
6. Hardware team gets the ticket at 11 AM

**9 hours wasted.** With automated escalation, the Jira ticket exists at 3:01 AM
with all diagnostics already attached.

### Value

- **Instant escalation**: Hardware team gets notified within minutes of failure
- **Complete diagnostics**: Every ticket has `rocm-smi`, `dmesg`, `ibstat`, test logs
- **No manual log collection**: Agent does it automatically
- **Accurate reproduction steps**: Exact CVS command that triggered the failure
- **Consistent ticket quality**: Every ticket follows the same structured format

### How It Works — Full Mechanism

```
         TEST FAILS WITH HARDWARE SIGNAL
                     |
                     v
    ┌────────────────────────────────────┐
    │  Agent detects hardware failure     │
    │  (GPU missing, ECC error, PCIe      │
    │   degraded, IB down, RAS errors)    │
    └────────────────┬───────────────────┘
                     |
                     v
    ┌────────────────────────────────────┐
    │  STEP 1: Collect Diagnostics       │
    │                                    │
    │  On affected node(s) via SSH:      │
    │  ┌──────────────────────────────┐  │
    │  │ rocm-smi --showallinfo       │  │
    │  │ rocm-smi --showrasinfo       │  │
    │  │ dmesg | tail -200            │  │
    │  │ lspci -vvv -d 1002:          │  │
    │  │ ibstat                       │  │
    │  │ rdma link show               │  │
    │  │ ethtool <mgmt_iface>         │  │
    │  │ cat /proc/driver/amdgpu/*    │  │
    │  └──────────────────────────────┘  │
    │                                    │
    │  Save to: ~/cvs_diag_<timestamp>/  │
    └────────────────┬───────────────────┘
                     |
                     v
    ┌────────────────────────────────────┐
    │  STEP 2: Create Jira Issue         │
    │                                    │
    │  Using Atlassian MCP tools:        │
    │  - Project: from cluster profile   │
    │  - Type: Bug                       │
    │  - Component: from cluster profile │
    │  - Priority: High (hardware)       │
    │  - Labels: cvs-automated,          │
    │            hardware-failure         │
    │                                    │
    │  Title format:                     │
    │  [CVS] <failure> on <node> —       │
    │        <cluster_name>              │
    │                                    │
    │  Description includes:             │
    │  - Summary of failure              │
    │  - Affected node(s) with hostname  │
    │  - Test suite and test case        │
    │  - Error message from logs         │
    │  - Reproduction command            │
    │  - Suggested action                │
    └────────────────┬───────────────────┘
                     |
                     v
    ┌────────────────────────────────────┐
    │  STEP 3: Attach Diagnostics        │
    │                                    │
    │  Files attached to the ticket:     │
    │  - rocm_smi_<node>.log             │
    │  - dmesg_<node>.log                │
    │  - ibstat_<node>.log               │
    │  - lspci_<node>.log                │
    │  - cvs_test_report.html            │
    │  - cvs_test.log                    │
    └────────────────┬───────────────────┘
                     |
                     v
    ┌────────────────────────────────────┐
    │  STEP 4: Continue Testing          │
    │                                    │
    │  - Log Jira ticket key (e.g.,      │
    │    DCGPU-456) in summary.txt       │
    │  - Skip further tests on the       │
    │    failed node (if multi-node)     │
    │  - Continue remaining suites       │
    │    on healthy nodes                │
    └────────────────────────────────────┘
```

### Example Jira Ticket (Auto-Generated)

> **Title**: [CVS] GPU HBM ECC error on 10.194.129.211 — dell300x-cluster
>
> **Summary**: CVS test `agfhc_cvs` failed on node 10.194.129.211
> (dell300x-pla-u14-33) during `test_hbm_stress` at 2026-06-19 03:14:22 UTC.
>
> **Failure Details**:
> - Test Suite: agfhc_cvs
> - Test Case: test_hbm_stress (GPU 3)
> - Node: 10.194.129.211 (dell300x-pla-u14-33)
> - Error: Uncorrectable ECC error detected on GPU 3, HBM bank 2
> - Cluster: dell300x-cluster (2 nodes, 16 GPUs)
> - CVS Version: 1.0.0 | ROCm Version: 7.2.0
>
> **Diagnostics Attached**: `rocm_smi.log`, `dmesg.log`, `ibstat.log`, `agfhc_report.html`
>
> **Reproduction**: `cvs run agfhc_cvs --cluster_file cluster.json --config_file health/mi300_health_config.json`
>
> **Suggested Action**: GPU 3 has uncorrectable HBM ECC errors. Check RAS
> counters (`rocm-smi --showrasinfo`). Consider page retirement or GPU replacement.
>
> *Auto-generated by CVS AI Agentic Solution during overnight cluster validation.*

### What Does NOT Trigger Jira

| Issue | Why No Jira |
|-------|------------|
| Wrong `mpi_oob_port` config | Agent auto-fixes this |
| Wrong env script for NIC type | Agent auto-fixes this |
| SSH key permissions | Agent auto-fixes (`chmod 600`) |
| `<changeme>` in config | Agent fills in correct values |
| NUMA balancing enabled | Agent auto-fixes (`echo 0 > ...`) |
| Docker image not pulled | Agent auto-fixes (`docker pull`) |
| Single-node RCCL bus_bw=0 | Expected behavior, not a failure |
| CVS parser limitation (IB format) | Known upstream issue, not hardware |

---

## 3. Connection Resilience (tmux Wrapping)

### Why This Exists

Engineers typically SSH from their laptop to the head node to run CVS tests.
If the laptop sleeps, VPN reconnects, WiFi drops, or the SSH session times
out — the CVS process receives SIGHUP and **dies**. A 4-hour AGFHC test at
hour 3 = completely wasted.

### Value

- **Tests survive disconnects**: VPN drop, WiFi loss, laptop sleep — test keeps running
- **Reconnect anytime**: `tmux attach` to see live output
- **No process management**: tmux handles it automatically
- **Multiple sessions**: Run different tests in parallel tmux sessions

### How It Works

```
    NORMAL (FRAGILE):
    Laptop ──SSH──> Head Node ──> CVS process
       |                              |
       X (disconnect)                 X (SIGHUP → process dies)


    WITH TMUX (RESILIENT):
    Laptop ──SSH──> Head Node ──> tmux session ──> CVS process
       |                              |                 |
       X (disconnect)                 |                 | (keeps running)
       |                              |                 |
    Reconnect ──SSH──> Head Node ──> tmux attach ──> see live output
```

The key insight: **tmux runs on the head node**, not on your laptop. When your
SSH connection drops, tmux keeps the CVS process alive because it's a separate
process on the server.

### Who Decides: Agent (Automatic)

The **user never needs to ask for tmux**. The agent automatically decides
based on estimated test duration. If runtime > 5 minutes → tmux wrapping.

| Test | Duration | tmux? | Agent Behavior |
|------|----------|-------|----------------|
| preflight | < 2 min | No | Run directly via SSH |
| host_configs | < 2 min | No | Run directly via SSH |
| RCCL single collective | 1-5 min | No | Run directly via SSH |
| RCCL full sweep | 10-30 min | **Auto** | Wraps in tmux, tells user: "Safe to disconnect" |
| AGFHC level 1 | 15-30 min | **Auto** | Wraps in tmux, tells user: "Safe to disconnect" |
| AGFHC level 3 | 2-8 hours | **Auto** | Wraps in tmux, tells user: "Safe to disconnect" |
| Training benchmarks | 30+ min | **Auto** | Wraps in tmux, tells user: "Safe to disconnect" |
| Full qualification | 1-4 hours | **Auto** | Wraps in tmux, tells user: "Safe to disconnect" |
| User says "overnight" | Hours | **Always** | Wraps in tmux + watchdog script |

### Scenario: What Happens When You Disconnect

```
11:00 PM  You: "Run AGFHC level 3 on all nodes"
          Agent: "This will take ~4 hours. Wrapping in tmux so it
                  survives if your connection drops. Safe to disconnect."
          Agent: launches test in tmux session 'cvs_agfhc'

11:30 PM  Your laptop sleeps / VPN drops / WiFi disconnects
          → Test keeps running on head node inside tmux

 7:00 AM  You reconnect, open Claude
          You: "What happened with the AGFHC test?"
          Agent: reads tmux output, downloads results
          Agent: "AGFHC completed at 3:14 AM. 15/16 GPUs passed.
                  GPU 3 on node .211 had HBM errors — Jira DCCS-6490
                  created with diagnostics. Report ready at
                  http://localhost:8888/agfhc_report.html"
```

---

## 4. First-Run Onboarding

### Why This Exists

This tool is designed to be **shared across teams**. Different engineers have
different SSH keys, different clusters, different Jira projects. Hardcoding
any of these would make the tool single-user.

### Value

- **Team-friendly**: Any engineer can use the tool with their own credentials
- **No secrets in git**: Credentials stay in `~/.cvs_agent/` (gitignored)
- **Multiple clusters**: Support profiles for different cluster environments
- **One-time setup**: Configure once, use forever (until credentials change)

### How It Works

```
    FIRST RUN:
    ┌────────────────────────────────────────────────┐
    │  Agent checks: does ~/.cvs_agent/ exist?        │
    │                                                  │
    │  NO → Start onboarding:                          │
    │    1. "What is the head node IP?"                │
    │    2. "What are the worker node IPs?"            │
    │    3. "What SSH user should I use?" (default:    │
    │        current user)                             │
    │    4. "Where is your SSH private key?" (default: │
    │        ~/.ssh/id_ed25519)                        │
    │    5. "What Jira project for escalations?"       │
    │       (e.g., DCGPU)                              │
    │    6. "What Jira component?" (optional)          │
    │                                                  │
    │  Save to ~/.cvs_agent/cluster_profile.json       │
    │                                                  │
    │  YES → Load existing profile, proceed            │
    └────────────────────────────────────────────────┘
```

### What's Stored vs What's NOT Stored

| Stored in Profile | NOT Stored (Never) |
|-------------------|--------------------|
| Head node IP | Passwords |
| Worker node IPs | API tokens |
| SSH username | Jira credentials (use MCP auth) |
| SSH key file path | Private key contents |
| Jira project key | Personal access tokens |
| Jira component | Any secrets |
| Cluster name/label | — (stored locally only) |
| Discovered mgmt interface | — (auto-discovered) |
| Discovered NIC type | — (auto-discovered) |

### Immediate Sanity Check

Right after onboarding, the agent runs a **9-point sanity check** to verify
everything works before any real test:

```
  Check                         Status
  ─────────────────────────────────────
  1. SSH to head node            PASS
  2. SSH head→self               PASS
  3. SSH head→worker(s)          PASS
  4. CVS installed               PASS (v1.0.0)
  5. Jira search                 PASS (DCCS accessible)
  6. Jira create test ticket     PASS (DCCS-6484 created+deleted)
  7. Confluence search           PASS (CVS pages found)
  8. Network interface discovery PASS (eno8303)
  9. RDMA hardware check         PASS (mlx5_0..mlx5_8)
```

If any check fails, the agent fixes it or guides the user before proceeding.
This prevents discovering permission issues at 2 AM during an overnight run.

### For Teams Without Atlassian MCP

If a new user doesn't have the Atlassian MCP server configured, the agent:
1. Warns that Jira escalation won't work
2. Guides them to set up Atlassian MCP (API token from id.atlassian.com)
3. All CVS tests still work — only Jira is skipped
4. Failures are logged locally instead of creating tickets

---

## 5. RCCL Pre-Run Validation

### Why This Exists

RCCL tests fail silently or with cryptic errors when the config doesn't match
the actual cluster hardware. In our field testing, we hit **3 separate config
issues** before RCCL ran successfully:

1. `mpi_dir=/usr/bin` → CVS appended `/bin/mpirun` → `/usr/bin/bin/mpirun` (not found)
2. `mpi_oob_port=eth0` → interface doesn't exist → "No network interfaces for OOB"
3. `thor2_env_script.sh` → references Broadcom NICs → "NCCL failure: invalid usage" on Mellanox

Each of these wasted 5-10 minutes of debugging. Now the agent discovers all
values **before** running.

### Value

- **First-time success**: RCCL tests run correctly on the first attempt
- **No guessing**: Agent discovers interfaces, NIC types, MPI paths automatically
- **Cross-platform**: Works with Mellanox, Broadcom Thor, AMD AINIC

### How It Works

```
    BEFORE RUNNING ANY RCCL TEST:

    1. Discover MPI path
       which mpirun → /usr/bin/mpirun → set mpi_dir=/usr

    2. Discover management interface
       ip route get 1 → dev eno8303 → set mpi_oob_port=eno8303

    3. Discover RDMA hardware
       ibdev2netdev → mlx5_0 port 1 ==> ibp28s0
                    → NIC type = Mellanox

    4. Validate env script
       Template has bnxt_re* (Broadcom) but cluster has mlx5_* (Mellanox)
       → Create new env script with correct NCCL_IB_HCA, NCCL_SOCKET_IFNAME

    5. Copy env script to ALL nodes
       scp env_script.sh → each worker node

    6. NOW run the RCCL test
```

---

## 6. Auto-Heal Playbook

### Why This Exists

Most CVS test failures are caused by **configuration issues**, not hardware
problems. NUMA balancing enabled, wrong interface name, Docker image not
pulled — these are all fixable without human intervention.

### Value

- **Reduces engineer intervention by 70%+** for common issues
- **Faster iteration**: Fix → re-run happens in seconds, not hours
- **Preserves overnight runs**: Fixable issues don't waste the entire night

### How It Works

```
    TEST FAILURE
         |
         v
    ┌────────────────┐
    │ Is it SAFE to   │
    │ auto-fix?       │
    └───────┬────────┘
        ┌───┴───┐
       YES      NO
        |        |
        v        v
    ┌────────┐  ┌────────────┐
    │AUTO-FIX│  │Is it a     │
    │& RE-RUN│  │MODERATE    │
    └────────┘  │fix?        │
                └─────┬──────┘
                  ┌───┴───┐
                 YES      NO
                  |        |
                  v        v
            ┌──────────┐ ┌──────────────┐
            │SUGGEST   │ │ESCALATE      │
            │fix to    │ │with          │
            │user      │ │diagnostics   │
            └──────────┘ │+ Jira ticket │
                         └──────────────┘

    SAFE auto-fixes (no user approval needed):
      - NUMA balancing: echo 0 > /proc/sys/kernel/numa_balancing
      - Docker pull: docker pull <image>
      - SSH key chmod: chmod 600 ~/.ssh/id_rsa
      - Config <changeme>: replace with discovered values
      - Wrong env script: generate correct one
      - Wrong mpi_oob_port: discover and set correct interface

    MODERATE (suggest to user):
      - Firewall disable for RDMA ports
      - GRUB config changes (iommu=pt)
      - ROCm version update

    CRITICAL (escalate + Jira):
      - GPU not detected
      - HBM/ECC errors
      - PCIe link degraded
      - IB port down
      - GPU reset/hang in dmesg
```

---

## 7. Smart Single-Node Handling

### Why This Exists

CVS RCCL baselines are calibrated for **multi-node** (2+ node) runs. When
running single-node RCCL tests, CVS always reports **FAILED** because:
- Bus bandwidth is 0 (it's an inter-node metric)
- The comparison against multi-node baselines fails

This is a **false negative** that confuses users.

### Value

- **No false alarms**: Single-node tests correctly reported as healthy
- **Right metrics**: AlgBW reported instead of meaningless BusBW
- **Clear communication**: "0 errors, RCCL healthy" instead of "FAILED"

### How It Works

| What CVS Reports | What Agent Reports |
|-----------------|-------------------|
| `FAILED` (exit code 1) | "RCCL communication healthy (single-node)" |
| `Avg bus bandwidth: 0` | "Peak AlgBW: 1,985 GB/s (XGMI intra-node)" |
| Baseline comparison fails | "Baselines N/A for single-node" |
| `#Wrong: 0` across all sizes | "Zero correctness errors" |

---

## 8. HTTP Report Delivery & Persistent Result Storage

### Why This Exists

CVS generates HTML reports with detailed test results, charts, and per-node
breakdowns. Two problems need solving:
1. On WSL or remote terminals, `xdg-open` and `firefox` don't work
2. Results stored in `/tmp` are lost on reboot — no way to review past tests

### Value

- **Works everywhere**: WSL, remote SSH, headless servers
- **One-click access**: Copy URL into browser, done
- **Never lose results**: Every test saved to `~/Downloads/cvs_results/` organized by date
- **Compare across days**: Review yesterday's RCCL bandwidth vs today's
- **Audit trail**: Full history of every validation run with timestamps

### How It Works

```
    1. scp report from head node → ~/Downloads/cvs_results/2026-06-18/<suite>/
    2. Copy to /tmp/ for HTTP serving
    3. python3 -m http.server 8888 (background)
    4. Present: http://localhost:8888/report.html
    5. User opens in browser → full interactive HTML report
    6. Results also persist in ~/Downloads/cvs_results/ for future review
```

### Folder Structure

Each run gets its own **timestamped folder** — multiple runs per day never overwrite:

```
~/Downloads/cvs_results/
├── 2026-06-18_173025_preflight_checks/
│   ├── report.html              ← open in browser anytime
│   └── test.log                 ← full test output
├── 2026-06-18_174510_host_configs_cvs/
│   ├── report.html
│   └── test.log
├── 2026-06-18_180730_rccl_perf_all_reduce/
│   ├── report.html
│   └── test.log
├── 2026-06-18_230000_full_qualification/    ← overnight run
│   ├── 01_preflight/
│   ├── 02_platform/
│   ├── 03_health/
│   ├── 04_rccl/
│   └── summary.txt
├── 2026-06-19_091500_rccl_perf_all_reduce/  ← next day comparison
│   ├── report.html
│   └── test.log
```

---

## 9. Pre-Built Workflows

### Why This Exists

Cluster validation requires running multiple test suites in a specific order
with conditional logic. Manually chaining `cvs run` commands is tedious and
error-prone.

### Value

- **One command, full pipeline**: "Run full qualification" triggers 5+ suites
- **Conditional logic**: Stop early if preflight fails
- **Consistent process**: Same sequence every time, nothing forgotten

### Available Workflows

| Workflow | Suites | Duration | Use When |
|----------|--------|----------|----------|
| Full Cluster Qualification | 5 suites | 1-4 hours | New cluster, post-maintenance |
| Quick Health Check | 2 suites | ~2 minutes | Daily spot-check |
| Network Validation | 3 suites | 15-30 min | After network changes |
| Pre-Training Readiness | 4+ suites | 30-60 min | Before training jobs |
| GPU Burn-In | 4 suites | 2-8 hours | New GPU, RMA replacement |
| Inference Readiness | 3 suites | 15-30 min | Before inference deployment |

---

## 10. Canary-First Pattern

### Why This Exists

Running a misconfigured test on 64 nodes wastes 64x the compute time. Testing
on one node first catches config errors immediately.

### Value

- **Fail fast**: Config errors caught in 2 minutes, not 2 hours
- **Resource efficient**: Don't burn GPU-hours on bad configs
- **Faster iteration**: Fix config on 1 node, then scale to fleet

### Who Decides: Agent (Automatic for Multi-Node)

For clusters with 2+ nodes, the agent automatically creates a canary
cluster file and tests one node first. User doesn't need to ask.

| Cluster Size | Canary? | Agent Behavior |
|-------------|---------|----------------|
| 1 node | No | Only one node — run directly |
| 2 nodes | **Auto** | Test node 1 first, then both |
| 4+ nodes | **Auto** | Test node 1 first, then full cluster |
| 64+ nodes | **Auto** | Test node 1 first, then full fleet |

### How It Works

```
    1. Create canary cluster.json (single node)
    2. Run test on canary node
    3. PASS → Run on full cluster
    4. FAIL → Fix issue, retry canary (not full cluster)
```

### Scenario

```
You: "Run RCCL on all 8 nodes"
Agent: "Running canary test on node 10.0.0.1 first..."
       (2 minutes later)
Agent: "Canary passed. Now running on all 8 nodes."
       vs.
Agent: "Canary FAILED — wrong mpi_oob_port. Fixing config..."
       "Fixed. Re-running canary..."
       "Canary passed. Now running on all 8 nodes."
       → Saved 8x the GPU-time by catching the error on 1 node
```

---

## 11. Prompt-Injection Defense

### Why This Exists

Cluster nodes may return output that contains text resembling instructions,
commands, or prompt fragments. This could be:
- Malicious injection via compromised node
- Accidental output from running processes
- Debug messages that look like commands

### Value

- **Security**: Agent never executes commands from cluster output
- **Reliability**: Cluster data is always treated as data, never instructions
- **Transparency**: Suspicious output is flagged to the user

### How It Works

All cluster output (stdout, stderr, log files) is treated as **DATA**.
The agent never parses cluster output as instructions to execute. If output
contains patterns that look like commands or prompt fragments, the agent
flags it to the user and ignores it.

---

## 12. Persistent Result Storage (OS-Aware)

### Why This Exists

Test results stored in `/tmp` are lost on every reboot. Engineers frequently
need to revisit previous validation runs to compare performance over time,
provide evidence for audits, or investigate regressions that surface days
after the original test.

### Value

- **Audit compliance**: Complete history of every validation run with timestamps
- **Regression detection**: Compare today's RCCL bandwidth against last week's baseline
- **Cross-platform transparency**: Results appear in Windows Explorer on WSL, or in native file manager on Linux
- **Zero configuration**: Auto-detects the operating system and selects the appropriate storage path

### Who Decides: Agent (Automatic — Every Test)

The agent **always** saves results after every test run. The user never
needs to ask. Storage location is auto-detected based on OS.

| Platform | Storage Path | How User Accesses |
|----------|-------------|-------------------|
| **WSL** | `C:\Users\<you>\Downloads\cvs_results\` | Windows Explorer |
| **Native Linux** | `~/Downloads/cvs_results/` | File manager or terminal |
| **Custom** | `$CVS_RESULTS_DIR` | User-defined via environment variable |

### How It Works

```
    After EVERY test:
    1. Agent detects OS (WSL? Linux? macOS?)
    2. Creates timestamped folder: YYYY-MM-DD_HHMMSS_<suite_name>/
    3. scp report.html + test.log from head node → local results folder
    4. Copies report.html to /tmp/ for HTTP serving
    5. Tells user: "Results saved to <path>. Report: http://localhost:8888/..."
```

### Scenario

```
Day 1:  Run RCCL all_reduce → saved to 2026-06-18_180730_rccl_perf/
Day 2:  Run RCCL all_reduce → saved to 2026-06-19_091500_rccl_perf/
Day 3:  "Why is bandwidth lower today?"
        → Open both report.html files side by side in browser
        → Compare bandwidth tables directly
```

---

## 13. Auto-Install CVS

### Why This Exists

CVS must be installed on the head node for any test to run. Requiring users
to SSH into the head node and manually run `pip install cvs` is an unnecessary
friction point that delays time-to-first-result.

### Value

- **Zero manual installation**: User provides the head node IP — agent handles the rest
- **Reduced onboarding time**: New engineers productive in minutes, not hours
- **Version awareness**: Agent checks for newer CVS versions and informs the user

### Who Decides: Agent (Automatic)

The agent checks on every first contact. If CVS is missing, it installs
automatically without asking (installation is always safe).

| Situation | Agent Action |
|-----------|-------------|
| CVS installed, up to date | Continue — note version |
| CVS installed, newer available | Inform user: "v1.3 available, want to upgrade?" |
| CVS **not installed** | Auto-install via `pip install cvs` |
| pip fails | Fallback: clone from source, install in virtualenv |

---

## 14. Magic Prompt (Single Entry Point)

### Why This Exists

New users face a cold-start problem: they don't know what prompt to type,
what information is needed, or what order things should happen. Without a
clear entry point, onboarding becomes a back-and-forth conversation.

### Value

- **Single prompt to production**: One paste replaces 10+ manual steps
- **Self-documenting**: The prompt template shows exactly what's needed
- **Repeatable**: Same prompt works for any cluster, any user, any team

### Who Decides: User Initiates, Agent Executes

The user pastes the magic prompt once. The agent then executes a 10-step
automated sequence without further input.

### The 10-Step Sequence

| Step | What Agent Does | Duration |
|------|----------------|----------|
| 1 | Save cluster profile locally | < 1 sec |
| 2 | SSH to head node, check CVS | 5 sec |
| 3 | Install CVS if missing | 30-60 sec |
| 4 | Set up SSH keys (head→self, head→workers) | 10 sec |
| 5 | Discover network interfaces | 5 sec |
| 6 | Discover RDMA hardware type | 5 sec |
| 7 | Verify Jira MCP connection | 5 sec |
| 8 | Run 9-point sanity check | 30 sec |
| 9 | Run preflight + platform health check | 2-3 min |
| 10 | Serve HTML report, present results | 5 sec |

**Total: ~5 minutes from paste to first result.**

---

## 15. 9-Point Sanity Check

### Why This Exists

Discovering that Jira permissions are wrong or SSH keys are broken at 2 AM
during an overnight run wastes the entire night. Every integration point
should be verified **upfront**, before any real test begins.

### Value

- **Fail fast on permissions**: Catches SSH, Jira, CVS issues in 30 seconds
- **Prevents overnight surprises**: All integration points verified before long runs
- **Clear pass/fail table**: User sees exactly what works and what needs fixing

### Who Decides: Agent (Automatic After Onboarding)

Runs automatically after first-run onboarding and before any overnight run.
User never needs to ask.

### The 9 Checks

| # | Check | What It Validates | If It Fails |
|---|-------|-------------------|-------------|
| 1 | SSH to head node | Can agent reach the cluster? | Fix SSH key or IP |
| 2 | SSH head→self | Can CVS parallel-SSH work? | Add key to own authorized_keys |
| 3 | SSH head→worker(s) | Can CVS reach all nodes? | Copy key to workers |
| 4 | CVS installed | Is CVS on the head node? | Auto-install |
| 5 | Jira search | Can agent query Jira? | Guide user to set up Atlassian MCP |
| 6 | Jira create+close | Can agent create tickets? | Check project permissions |
| 7 | Confluence search | Can agent find documentation? | Non-critical — skip |
| 8 | Network interface | What's the management interface? | Auto-discover |
| 9 | RDMA hardware | What NIC type (Mellanox/Broadcom)? | Auto-discover |

---

## Feature Summary Matrix

| # | Feature | Who Decides | Saves Time | Reduces Errors | Enables Overnight |
|---|---------|------------|-----------|---------------|-------------------|
| 1 | Overnight Autonomous Mode | User triggers | 8+ hours/night | Auto-heal fixes | Core feature |
| 2 | Jira Escalation | Agent (auto) | 1-2 hours/ticket | Complete diagnostics | Auto-creates tickets |
| 3 | Connection Resilience (tmux) | Agent (auto > 5 min) | 0-4 hours/disconnect | No lost work | Enables unattended |
| 4 | First-Run Onboarding | User triggers once | 30 min setup | No hardcoded creds | Stores profile |
| 5 | RCCL Pre-Run Validation | Agent (auto) | 15-30 min/attempt | First-time success | Prevents night failures |
| 6 | Auto-Heal Playbook | Agent (auto) | 5-30 min/fix | 70%+ auto-resolved | Keeps pipeline going |
| 7 | Smart Single-Node Handling | Agent (auto) | 10 min confusion | No false negatives | Correct overnight report |
| 8 | HTTP Report Delivery | Agent (auto) | 2 min/report | Works everywhere | Reports served |
| 9 | Pre-Built Workflows | User selects | 30+ min/sequence | Nothing forgotten | One-command overnight |
| 10 | Canary-First Pattern | Agent (auto > 1 node) | 0-2 hours | Catches config early | Saves overnight time |
| 11 | Prompt-Injection Defense | Agent (always) | N/A | Security | Safe overnight |
| 12 | Persistent Result Storage | Agent (auto, every test) | Audit trail | Never lose results | Morning review |
| 13 | Auto-Install CVS | Agent (auto if missing) | 30 min install | Zero manual steps | Ready for overnight |
| 14 | Magic Prompt | User triggers once | 5 min to first result | Single entry point | Any team member |
| 15 | 9-Point Sanity Check | Agent (auto after setup) | Catches issues in 30s | Fail fast on perms | No 2 AM surprises |
