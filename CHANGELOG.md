# Changelog

All notable changes to the CVS AI Agentic Solution are documented here.

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

### Skill Updates

- **SKILL.md**: Added "First-Run Setup" section with credential collection flow
- **SKILL.md**: Added "Connection Resilience" section with tmux wrapping guide
- **SKILL.md**: Added "Overnight Autonomous Mode" section with watchdog script
- **SKILL.md**: Added "Jira Escalation for Hardware Failures" section with trigger table
- **SKILL.md**: Added 4 new Don't rules (#11-14)
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
