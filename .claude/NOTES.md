# Agent Working Notes

## Upstream CVS Reference
- Repo: https://github.com/ROCm/cvs
- Docs: https://rocm.docs.amd.com/projects/cvs/en/latest/
- 34 test suites across 8 categories
- PyTest-based, parallel-SSH execution

## Key Decisions
- This project is a pure agent layer — no fork of CVS needed
- Works with upstream CVS installed via pip
- All intelligence is in CLAUDE.md + skills + hooks
- Auto-heal only attempts safe fixes (no reboots, no installs without asking)

## TODO
- [ ] Add result trending (compare current run vs historical baselines)
- [ ] Add Slack/Teams notification integration
- [ ] Add Jira ticket auto-creation for failures
- [ ] Add scheduled validation support (cron-based)
- [ ] Add multi-cluster support (switch between clusters by name)
