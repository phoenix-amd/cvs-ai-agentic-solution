# Changelog

All notable changes to the CVS AI Agentic Solution are documented here.
Each version builds on the previous — scroll to the bottom for v1.0.0.

---

## [1.6.0] - 2026-06-30 — Latest Release

**What's new since v1.5.0**: SSH banner noise eliminated, RCCL `-Z json`
compatibility detection, and dynamic localhost dashboards.

### Highlights
- **SSH wrapper (`cssh`)**: Strips AMD Conductor 18-line banner from all SSH output — clean agent parsing
- **RCCL `-Z json` detection**: Auto-detects rccl-tests version before running; prevents silent 6-second exit on OLD binaries
- **Dynamic localhost dashboard**: Always generated fresh from real results, served on port 7788, clickable link in Claude — no GitHub push needed
- **Standardized port 7788**: All dashboard/report serving uses `http://localhost:7788/`

### New Files

| File | Purpose |
|------|---------|
| `tools/cssh.sh` | SSH wrapper — strips Conductor banner (ASCII logo, auth reminders, 18 lines of noise) |

### Bug Fixes

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | **Conductor banner pollutes SSH output** | AMD Conductor prints 18-line banner on every SSH connection | Created `cssh.sh` wrapper that filters banner via grep; SKILL.md mandates its use |
| 2 | **RCCL silent exit with `-Z json -x`** | Older rccl-tests builds don't support `-Z json`; binary exits in ~6 seconds with no output | Added mandatory `-Z json` detection step; if unsupported, remove `rccl_result_file` from config |
| 3 | **Dashboard required GitHub push** | Previous design pushed HTML to GitHub Pages for a public URL | Dashboard now served locally on port 7788; agent prints localhost link directly |

### Files Changed

| File | What Changed |
|------|-------------|
| `tools/cssh.sh` | **NEW** — SSH wrapper script |
| `CLAUDE.md` | Added cssh rule, `-Z json` detection rule, localhost:7788 dashboard rule |
| `.claude/skills/cvs-operate/SKILL.md` | SSH wrapper section, `-Z json` detection step, dashboard port 7788 |
| `README.md` | Updated dashboard section (localhost:7788), project structure (cssh.sh) |
| `FEATURES.md` | Updated all port references (8888 → 7788) |
| `ARCHITECTURE.md` | Added cssh.sh to file reference |
| `CHANGELOG.md` | This entry |

---

## [1.5.0] - 2026-06-30

**What's new since v1.4.0**: Autonomous mode now runs fully unattended — zero
permission prompts from the Claude Code harness. Three operational bugs fixed
from real-world testing on dell300x 2-node MI300X cluster.

### Highlights
- **Zero-prompt auto mode**: `settings.local.json` `autoMode` rules allow all CVS/SSH/pytest patterns
- **Pre-run /tmp cleanup**: Prevents `PermissionError` from stale files left by other users
- **Source-only CVS install**: Removed `pip install cvs` — not on PyPI, always install from source
- **Terminal results output**: Agent always prints pass/fail table in conversation, not just HTML

### Bug Fixes

| # | Issue | Root Cause | Fix |
|---|-------|-----------|-----|
| 1 | **25+ permission prompts in auto mode** | Claude Code heuristics flagged heredocs, SSH with `-o` flags, inline python3, `/tmp` reads, `#` comments | Added `autoMode.allow` + `autoMode.environment` rules in `settings.local.json` covering all CVS patterns |
| 2 | **PermissionError on /tmp/preflight_checks_html/** | Previous user (wmliu) left files in `/tmp` owned by their UID | Added mandatory Step 3.5: clean stale `/tmp` dirs before every test run |
| 3 | **`pip install cvs` fails** | CVS package not on PyPI | Removed pip option from all docs, source-only install everywhere |
| 4 | **Results only visible in HTML report** | Agent didn't print summary in terminal | Made terminal markdown table mandatory after every test (Step 6 updated) |

### Files Changed

| File | What Changed |
|------|-------------|
| `.claude/settings.local.json` | Added 28 permission allow rules + `autoMode` config (18 allow, 5 deny, 6 environment) |
| `.claude/skills/cvs-operate/SKILL.md` | Step 3.5 (/tmp cleanup), Step 6 (terminal output), source-only install |
| `.claude/skills/cvs-operate/WORKFLOWS.md` | Pre-run cleanup + terminal results sections added to all workflows |
| `.claude/skills/cvs-operate/AUTO_HEAL.md` | Added /tmp PermissionError as auto-healable issue |
| `.claude/skills/cvs-preflight-setup/SKILL.md` | Added /tmp cleanup section before handoff to cvs-operate |
| `CLAUDE.md` | ALWAYS rules: /tmp cleanup, terminal output, source-only install |
| `CHANGELOG.md` | This entry |

### Field Test (dell300x 2-Node MI300X)

- **Head**: `10.194.129.213` (dell300x-pla-u14-27)
- **Worker**: `10.194.129.211` (dell300x-pla-u14-33)
- **GPUs**: 40x MI300X per node (8 visible to RCCL per node)
- **RDMA**: Mellanox ConnectX InfiniBand (mlx5_0..8), 8 up / 1 down (mlx5_5)
- **Mgmt interface**: `eno8303`
- **ROCm**: 7.2.0
- **Preflight**: 5/7 PASS (2 failed due to /tmp PermissionError — now fixed)
- **RCCL all_reduce**: PASSED, 0 errors, busBW=109 GB/s (single-node view), 1m48s

---

## [1.4.0] - 2026-06-22

**What's new since v1.3.0**: Interactive Grafana-style dashboard and
automatic self-update version checking. The agent now generates beautiful
dark-themed HTML dashboards with 4 interactive tabs, and checks GitHub for
newer skill versions on every session start.

### Highlights
- **Interactive Dashboard**: Grafana-style dark theme with Overview, Node Comparison, Test Results, RCCL Performance tabs
- **Self-Update Check**: Agent checks GitHub for newer versions on session start, offers to update
- **Dashboard tools**: `tools/dashboard.py` generates self-contained HTML from cluster data JSON
- **Version tracking**: `version.txt` + `tools/version_check.py` for automated version management

### New Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Interactive Dashboard** | Grafana-style HTML dashboard: 4 tabs (Overview, Nodes, Tests, RCCL), interactive filtering, actual-vs-expected comparison, bandwidth charts, summary cards, dark AMD theme |
| 2 | **Self-Update Check** | Agent checks `version.txt` against latest GitHub tag on every session. Informs user if update available, never auto-updates |

### New Files

| File | Purpose |
|------|---------|
| `tools/dashboard.py` | Dashboard HTML generator — reads cluster data JSON, produces self-contained interactive HTML |
| `tools/version_check.py` | Version checker — compares local vs GitHub, supports `--check`, `--update`, `--current` |
| `version.txt` | Current version number (used by version checker) |

### Dashboard Capabilities

- 4 interactive tabs: Overview, Node Comparison, Test Results, RCCL Performance
- Text search filtering across all tables
- Pass/Fail status filtering dropdown
- Actual vs Expected value comparison (green = match, red = mismatch)
- RCCL bandwidth bar chart visualization
- Summary cards: node count, GPU count, pass rate, test totals
- Self-contained HTML — no external dependencies, works offline
- Dark AMD-branded theme inspired by Grafana

---

## [1.3.0] - 2026-06-18

**What's new since v1.2.0**: Zero-friction onboarding for new users. One
prompt sets up everything — CVS installation, SSH keys, Jira, sanity check.
Architecture documentation added. Professional-grade README for executive review.

### Highlights
- **3-step setup**: Clone → Launch Claude → Paste magic prompt (agent does the rest)
- **Auto-install CVS**: Agent installs CVS on head node if missing — no manual step
- **Architecture docs**: Pure agent layer vs fork comparison with technical rationale
- **Executive-ready README**: Impact metrics, value proposition, clear quick start

### New Features

| # | Feature | Description |
|---|---------|-------------|
| 1 | **Magic Prompt** | Single entry-point prompt for new users — handles profile creation, CVS install, SSH setup, sanity check, and first health check in one shot |
| 2 | **Auto-Install CVS** | If CVS is missing on head node, agent automatically installs from source (git clone + pip install -e .) — no manual step needed |
| 3 | **JSON Fork Detection** | Detects if a JSON-enhanced CVS fork is installed; automatically uses `cvs run-json`, `cvs list-json`, `cvs compare` when available |
| 4 | **Executive README** | Added impact metrics table, problem/solution framing, updated architecture diagram showing Jira/Confluence integration |
| 5 | **New User Guide** | Step-by-step setup guide (6 steps from clone to first result) for sharing with teams |
| 6 | **Persistent Result Storage** | Every test result saved to `~/Downloads/cvs_results/<date>/<suite>/` — never lost on reboot, reviewable anytime, organized by date and test suite |

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

---

## [1.2.0] - 2026-06-18

**What's new since v1.1.0**: Enterprise-grade operational capabilities.
Tests run overnight unattended with auto-heal. Hardware failures auto-escalate
to Jira with full diagnostics. Tests survive laptop disconnects via tmux.

### Highlights
- **Overnight mode**: Launch before leaving → results ready at 8 AM
- **Jira integration**: Hardware failures create tickets with `rocm-smi`, `dmesg`, `ibstat` attached
- **Connection resilience**: tmux wrapping — VPN drops don't kill tests
- **9-point sanity check**: Validates SSH, CVS, Jira, RDMA before any test

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

---

## [1.1.0] - 2026-06-18

**What's new since v1.0.0**: Field-tested on a real 2-node MI300X cluster.
10 bugs discovered and fixed. RCCL tests now work first-try on any cluster
through automatic hardware discovery and env script validation.

### Highlights
- **10 field-tested bug fixes**: Every issue discovered on live MI300X hardware
- **RCCL pre-run validation**: Auto-discovers interfaces, NIC type, MPI paths
- **Smart single-node handling**: No more false-negative RCCL failures
- **HTTP report serving**: HTML reports viewable in browser from WSL/remote

### Field Test Environment
- **Cluster**: 2x Dell 300X nodes, 16x AMD Instinct MI300X GPUs
- **OS**: Ubuntu 22.04.2 LTS, Kernel 6.8.0-110-generic
- **ROCm**: 7.2.0
- **Network**: Mellanox ConnectX InfiniBand (mlx5_0 through mlx5_8)

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

---

## [1.0.0] - 2026-06-17

**Initial release**: Pure agent layer for AMD CVS cluster validation.
Natural language interface over 34 test suites with zero fork maintenance.

### Highlights
- **Natural language**: "Check if the cluster is healthy" → agent runs the right tests
- **34 test suites**: Platform, health, RCCL, training, inference all mapped
- **Auto-heal**: Fixes NUMA balancing, docker pull, SSH keys automatically
- **6 pre-built workflows**: Full qualification, network validation, pre-training, GPU burn-in
- **Canary-first**: Tests one node before running fleet-wide
- **Safety model**: Allow/Ask/Deny permission tiers
- **Prompt-injection defense**: Cluster output treated as data, never instructions
- **Pure agent layer**: Works with unmodified upstream CVS — zero fork maintenance
