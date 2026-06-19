# Feature Guide — CVS AI Agentic Solution

Detailed documentation of every feature: **why** it exists, the **value** it
provides, and **how** it works under the hood.

---

## Table of Contents

1. [Overnight Autonomous Mode](#1-overnight-autonomous-mode)
2. [Jira Escalation for Hardware Failures](#2-jira-escalation-for-hardware-failures)
3. [Connection Resilience](#3-connection-resilience-tmux-wrapping)
4. [First-Run Onboarding](#4-first-run-onboarding)
5. [RCCL Pre-Run Validation](#5-rccl-pre-run-validation)
6. [Auto-Heal Playbook](#6-auto-heal-playbook)
7. [Smart Single-Node Handling](#7-smart-single-node-handling)
8. [HTTP Report Delivery](#8-http-report-delivery)
9. [Pre-Built Workflows](#9-pre-built-workflows)
10. [Canary-First Pattern](#10-canary-first-pattern)
11. [Prompt-Injection Defense](#11-prompt-injection-defense)

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

```
Title: [CVS] GPU HBM ECC error on 10.194.129.211 — dell300x-cluster

## Summary
CVS test `agfhc_cvs` failed on node 10.194.129.211 (dell300x-pla-u14-33)
during `test_hbm_stress` at 2026-06-19 03:14:22 UTC.

## Failure Details
- **Test Suite**: agfhc_cvs
- **Test Case**: test_hbm_stress (GPU 3)
- **Node**: 10.194.129.211 (dell300x-pla-u14-33)
- **Error**: Uncorrectable ECC error detected on GPU 3, HBM bank 2
- **Cluster**: dell300x-cluster (2 nodes, 16 GPUs)
- **CVS Version**: 1.0.0
- **ROCm Version**: 7.2.0

## Diagnostics Collected
See attached files:
- `rocm_smi_10.194.129.211.log` — full GPU status
- `dmesg_10.194.129.211.log` — kernel log with error context
- `ibstat_10.194.129.211.log` — network state
- `agfhc_report.html` — CVS HTML test report

## Reproduction
```bash
cvs run agfhc_cvs --cluster_file cluster.json \
  --config_file health/mi300_health_config.json
```

## Suggested Action
GPU 3 on node 10.194.129.211 has uncorrectable HBM ECC errors.
- Check RAS error counters: `rocm-smi --showrasinfo`
- Consider page retirement or GPU replacement
- Isolate this GPU from workloads until resolved

## Auto-Generated
This ticket was created automatically by CVS AI Agentic Solution
during an overnight cluster validation run.
```

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

### When tmux Is Used Automatically

| Test Duration | tmux? | Reason |
|--------------|-------|--------|
| < 5 minutes | No | Quick enough, reconnect is easy |
| 5-30 minutes | **Yes** | Risk of disconnect is real |
| 30+ minutes | **Always** | Cannot afford to lose progress |
| Overnight mode | **Always** | Entire point is unattended execution |

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
| Cluster name/label | |
| Discovered mgmt interface | |
| Discovered NIC type | |

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

## 8. HTTP Report Delivery

### Why This Exists

CVS generates HTML reports with detailed test results, charts, and per-node
breakdowns. On WSL or remote terminals, `xdg-open` and `firefox` don't work.
Engineers need to **see** these reports in a browser.

### Value

- **Works everywhere**: WSL, remote SSH, headless servers
- **One-click access**: Copy URL into browser, done
- **All reports served**: Multiple test reports accessible from same server

### How It Works

```
    1. scp report from head node → /tmp/report.html
    2. python3 -m http.server 8888 (background)
    3. Present: http://localhost:8888/report.html
    4. User opens in browser → full interactive HTML report
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

### How It Works

```
    1. Create canary cluster.json (single node)
    2. Run test on canary node
    3. PASS → Run on full cluster
    4. FAIL → Fix issue, retry canary (not full cluster)
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

## Feature Summary Matrix

| Feature | Saves Time | Reduces Errors | Enables Overnight | Team-Friendly |
|---------|-----------|---------------|-------------------|---------------|
| Overnight Autonomous Mode | 8+ hours/night | Auto-heal fixes | Core feature | Results for everyone |
| Jira Escalation | 1-2 hours/ticket | Complete diagnostics | Auto-creates tickets | Shared project |
| Connection Resilience | 0-4 hours/disconnect | No lost work | Enables unattended | Works for all |
| First-Run Onboarding | 30 min setup | No hardcoded creds | Stores profile | Multi-user |
| RCCL Pre-Run Validation | 15-30 min/attempt | First-time success | Prevents night failures | Auto-discovers |
| Auto-Heal Playbook | 5-30 min/fix | 70%+ auto-resolved | Keeps pipeline going | Consistent fixes |
| Smart Single-Node | 10 min confusion | No false negatives | Correct overnight report | Clear for all |
| HTTP Report Delivery | 2 min/report | Works everywhere | Reports served | Any browser |
| Pre-Built Workflows | 30+ min/sequence | Nothing forgotten | One-command overnight | Standardized |
| Canary-First | 0-2 hours | Catches config early | Saves overnight time | Best practice |
| Prompt-Injection Defense | N/A | Security | Safe overnight | Trust boundary |
