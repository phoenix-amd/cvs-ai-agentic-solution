# Agent Working Notes

## Upstream CVS Reference
- Repo: https://github.com/ROCm/cvs
- Docs: https://rocm.docs.amd.com/projects/cvs/en/latest/
- 34 test suites across 8 categories
- PyTest-based, parallel-SSH execution

## Key Decisions
- This project is a pure agent layer — no fork of CVS needed
- CVS is NOT on PyPI — always install from source (git clone + pip install -e .)
- All intelligence is in CLAUDE.md + skills + hooks
- Auto-heal only attempts safe fixes (no reboots, no installs without asking)
- Auto mode permissions configured in `settings.local.json` (not committed)
- Always clean /tmp before tests to avoid PermissionError from previous users
- Always print results in terminal as markdown tables, not just HTML reports

## Field-Tested Clusters

| Cluster | Nodes | GPUs | RDMA | Mgmt Interface | ROCm |
|---------|-------|------|------|----------------|------|
| dell300x 2N | 10.194.129.213, .211 | 40x MI300X/node | mlx5 IB (8 up, 1 down) | eno8303 | 7.2.0 |

## Lessons Learned (v1.5.0)
- `pip install cvs` fails — not on PyPI. Source-only install.
- `/tmp/preflight_checks_html/` must be cleaned before every run — stale files cause PermissionError
- RCCL test file is `rccl_perf.py`, not `rccl_multinode_cvs.py` (CVS 1.0 naming)
- Claude Code auto mode needs `autoMode.allow` rules in settings.local.json for SSH heredocs, inline python3, /tmp reads
- 25+ permission prompts eliminated by adding autoMode config

## TODO
- [x] Add Jira ticket auto-creation for failures (done in v1.2.0)
- [ ] Add result trending (compare current run vs historical baselines)
- [ ] Add Slack/Teams notification integration
- [ ] Add scheduled validation support (cron-based)
- [ ] Add multi-cluster support (switch between clusters by name)
