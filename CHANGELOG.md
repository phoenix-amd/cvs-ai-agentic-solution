# Changelog

All notable changes to the CVS AI Agentic Solution are documented here.

## [1.3.0] - 2026-06-18

### Magic Prompt, Auto-Install, JSON Fork Compatibility

### New Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Magic Prompt** | Single entry-point prompt for new users — handles profile creation, CVS install, SSH setup, sanity check, and first health check in one shot |
| 2 | **Auto-Install CVS** | If CVS is missing on head node, agent automatically installs via `pip install cvs` or from source — no manual step needed |
| 3 | **JSON Fork Detection** | Detects if a JSON-enhanced CVS fork is installed; automatically uses `cvs run-json`, `cvs list-json`, `cvs compare` when available |
| 4 | **Executive README** | Added impact metrics table, problem/solution framing, updated architecture diagram showing Jira/Confluence integration |
| 5 | **New User Guide** | Step-by-step setup guide (6 steps from clone to first result) for sharing with teams |

### Relationship with JSON-Enhanced CVS Forks

This skill is **complementary** to JSON-enhanced CVS forks:
- JSON forks add machine-readable CLI to CVS (better parsing)
- This skill adds autonomous operational workflows (better brain)
- When used together: JSON output → reliable agent parsing + overnight mode + Jira escalation

### Skill Updates

- **SKILL.md**: Added "Magic Prompt" section — 10-step automated onboarding sequence
- **SKILL.md**: Added auto-install logic for CVS missing on head node
- **SKILL.md**: Added JSON fork detection and JSON command preference table
- **README.md**: Executive summary with impact metrics at the top
- **README.md**: Magic prompt example in Quick Start
- **README.md**: Updated architecture diagram with Jira/Confluence

---

## [1.2.0] - 2026-06-18

### Overnight Autonomous Mode, Jira Escalation, Connection Resilience

Major feature release adding enterprise-grade capabilities for team use.

### New Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Overnight Autonomous Mode** | Agent wraps tests in tmux, runs suites sequentially, auto-heals failures, re-runs, collects diagnostics, writes summary — results ready in the morning |
| 2 | **Jira Escalation for Hardware Failures** | Auto-creates Jira tickets with diagnostics (rocm-smi, dmesg, ibstat) attached when real hardware issues are detected (GPU missing, HBM errors, PCIe degraded, IB down) |
| 3 | **Connection Resilience (tmux wrapping)** | Long-running tests wrapped in tmux on head node — survives laptop disconnects, VPN drops, SSH timeouts |
| 4 | **First-Run Onboarding** | Collects SSH credentials, node IPs, Jira project keys on first use; stores in local profile (`~/.cvs_agent/`); supports multiple cluster profiles |
| 5 | **"Why Use This" Section** | Added clear value proposition table comparing with/without the tool |

### Verified Integration

Jira integration tested end-to-end on `amd.atlassian.net`:
- **Project**: DCCS (DPEG Fleet Services)
- **Issue type**: "Issue" (verified — DCCS does not use "Bug")
- **Component**: "Cluster Administration" (auto-assigned)
- **Labels**: `cvs-automated`, `sanity-check` (applied correctly)
- **Test ticket**: DCCS-6484 created successfully with full markdown description

### New: 9-Point Sanity Check

Runs immediately after first-run onboarding to verify all permissions:
SSH (head, self, workers), CVS install, Jira create/search, Confluence,
network interface discovery, RDMA hardware check. Catches issues before
any real test runs.

### Skill Updates

- **SKILL.md**: Added "First-Run Setup" section with credential collection flow
- **SKILL.md**: Added "Sanity Check" routine (9-point verification)
- **SKILL.md**: Added verified Jira configuration (DCCS project, Issue type, labels)
- **SKILL.md**: Added Atlassian MCP setup guide for new users
- **SKILL.md**: Added "Connection Resilience" section with tmux wrapping guide
- **SKILL.md**: Added "Overnight Autonomous Mode" section with watchdog script
- **SKILL.md**: Added "Jira Escalation for Hardware Failures" section with trigger table
- **SKILL.md**: Added 4 new Don't rules (#11-14)
- **FEATURES.md**: Created comprehensive feature docs with flow diagrams
- **FEATURES.md**: Added sanity check details and MCP setup guide
- **README.md**: Added "Why Use This" value proposition table
- **README.md**: Updated comparison table with 4 new rows
- **README.md**: Added feature descriptions for overnight mode, Jira, connection resilience

---

## [1.1.0] - 2026-06-18

### Field-Tested on Real Cluster

First live deployment on a 2-node MI300X cluster (Dell 300X, Ubuntu 22.04,
ROCm 7.2.0, Mellanox ConnectX IB). Every fix below was discovered and
validated during an end-to-end session.

### Bug Fixes

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | **`/usr/bin/bin/mpirun` not found** | CVS appends `/bin/mpirun` to the `mpi_dir` config value. Setting `mpi_dir=/usr/bin` produced invalid path `/usr/bin/bin/mpirun` | Skill now documents: set `mpi_dir` to the **parent** of the `bin/` dir (e.g., `/usr` if mpirun is at `/usr/bin/mpirun`) |
| 2 | **MPI "No network interfaces for OOB"** | Default RCCL config uses `mpi_oob_port=eth0`, but cluster nodes use `eno8303` (or other non-`eth0` names) | Added mandatory pre-run step: discover actual mgmt interface via `ip -o link show` before any RCCL test |
| 3 | **RCCL `invalid usage` NCCL failure** | Template `thor2_env_script.sh` references Broadcom Thor NICs (`bnxt_re*`, `NCCL_NET_PLUGIN=none`) but cluster has Mellanox IB (`mlx5_*`) | Added env script validation: check `ibdev2netdev`, match NIC type, create correct env script |
| 4 | **`NCCL_SOCKET_IFNAME=eth1,eth0` failure** | Env script hardcodes socket interface names that don't exist on the target cluster | Env script validation now checks `NCCL_SOCKET_IFNAME` matches actual interfaces |
| 5 | **CVS AuthenticationError on head node** | CVS parallel-SSH targets ALL nodes including the head node itself; head node couldn't SSH to itself | Skill now ensures head node's SSH key is in its own `authorized_keys` |
| 6 | **Preflight `rdma link` parse crash** | CVS regex expects RoCE format (`netdev <iface>`) but InfiniBand outputs `subnet_prefix ... lid ...` format | Documented as known CVS limitation; skill reports it as known issue, not cluster failure |
| 7 | **Single-node RCCL reports FAILED** | CVS baselines are for multi-node; single-node bus_bw=0 is expected but triggers baseline comparison failure | Added single-node vs multi-node section: ignore bus_bw, report AlgBW and #Wrong instead |
| 8 | **`xdg-open` doesn't work for HTML reports** | Running on WSL2 — `xdg-open` can't launch Windows browsers | All reports now served via `python3 -m http.server` with `http://localhost:PORT/` link |
| 9 | **`MPI_HOME=<changeme>` in env script** | Template env scripts contain unresolved `<changeme>` placeholders | Pre-run validation now scans env scripts for `<changeme>` fields |
| 10 | **`UCX_NET_DEVICES` mismatch** | Env script lists Broadcom netdev names that don't exist on Mellanox cluster | Env script validation cross-references `ibdev2netdev` output with script variables |

### New Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **RCCL Pre-Run Validation** | Mandatory discovery steps before any RCCL test: interface detection, mpi_dir verification, env script validation against actual hardware |
| 2 | **Env Script Auto-Detection** | Matches NIC type (Mellanox mlx5 / Broadcom bnxt_re / AMD AINIC) to correct env script template; creates custom script when no template matches |
| 3 | **Single-Node Result Interpretation** | Correctly handles single-node RCCL results: reports AlgBW instead of BusBW, zero #Wrong errors as pass criteria, avoids false-negative FAIL verdict |
| 4 | **HTTP Report Serving** | After every test, automatically copies HTML report locally, starts HTTP server, provides browser-ready `http://localhost:PORT/report.html` link |
| 5 | **Head Node Self-SSH Setup** | Automatically detects and fixes head-node-to-self SSH connectivity during cluster setup |
| 6 | **InfiniBand Awareness** | Recognizes IB vs RoCE output formats; reports IB preflight parse errors as known CVS limitations rather than cluster failures |

### Skill Updates (`cvs-operate`)

- **SKILL.md**: Added "RCCL Pre-Run Validation" section (interface discovery, env script validation)
- **SKILL.md**: Added "Single-Node vs Multi-Node RCCL Tests" section
- **SKILL.md**: Added "Report Delivery" section (HTTP server pattern)
- **SKILL.md**: Added 6 new entries to Error Handling table
- **SKILL.md**: Added 5 new rules to Don't list
- **WORKFLOWS.md**: Unchanged (workflows remain valid)
- **AUTO_HEAL.md**: Unchanged

### Known Issues (Upstream CVS)

| Issue | Impact | Workaround |
|-------|--------|-----------|
| `rdma link` regex doesn't handle InfiniBand format | Preflight interface check crashes on IB clusters | Skip or report as known issue; cluster health is unaffected |
| Single-node RCCL baseline comparison always fails | False negative: test reports FAIL even when communication is healthy | Interpret AlgBW and #Wrong manually; ignore CVS verdict |
| `rccl-tests` JSON output (`-Z json -x`) incompatible with some builds | Some older rccl-tests builds reject `-x` flag | CVS detects "OLD" vs "NEW" builds; ensure rccl-tests is up to date |

## [1.0.0] - 2026-06-17

### Initial Release

- Natural language interface for CVS cluster validation
- 34 test suite coverage with auto-config generation
- Guided first-contact flow (6-step setup wizard)
- Auto-heal playbook for common failures
- 5 pre-built validation workflows
- Canary-first execution pattern
- Prompt-injection defense
- Safety model (allow/ask/deny tiers)
