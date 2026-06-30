# Pre-Built Validation Workflows

Smart workflows that chain multiple CVS suites with conditional logic.
All prompts are typed directly into Claude — the agent asks which mode
(Interactive / Autonomous / Batch) before proceeding.

## Pre-Run Cleanup (EVERY Workflow)

**Before every workflow**, the agent MUST clean stale `/tmp` files from
previous users/runs on the head node. This prevents `PermissionError`
on HTML report generation.

```bash
ssh <headnode> '
  sudo rm -rf /tmp/preflight_checks_html /tmp/preflight.html /tmp/preflight.log 2>/dev/null
  sudo rm -rf /tmp/rccl_*_html /tmp/host_configs_*_html /tmp/agfhc_*_html /tmp/transferbench_*_html 2>/dev/null
  rm -rf /tmp/preflight_checks_html /tmp/preflight.html /tmp/preflight.log 2>/dev/null
  rm -rf /tmp/rccl_*_html /tmp/host_configs_*_html /tmp/agfhc_*_html /tmp/transferbench_*_html 2>/dev/null
'
```

## Terminal Results (EVERY Workflow)

After every test suite completes, the agent MUST print results as a markdown
table in the terminal. The user should never need to open an HTML report to
see basic pass/fail status.

---

## Workflow: Full Cluster Qualification

Use when: New cluster, post-maintenance, or periodic health check.

**Paste into Claude:**
```
Run full cluster qualification on 10.194.129.213 with worker 10.194.129.211.
SSH user root, key ~/.ssh/id_rsa.
Escalate hardware failures to Jira DCCS.
```

**Execution sequence:**
```
1. preflight_checks (basic mode)
   ├── PASS → continue
   └── FAIL → auto-heal → retry once → escalate if still failing

2. host_configs_cvs
   ├── PASS → continue
   └── FAIL → report non-compliant nodes, suggest fixes

3. agfhc_cvs (level 1 - quick)
   ├── PASS → continue
   └── FAIL → isolate bad GPUs, report affected nodes

4. transferbench_cvs (healthcheck mode)
   ├── PASS → continue
   └── FAIL → flag bandwidth issues per GPU

5. rccl_perf (all collectives)
   ├── PASS → generate performance report
   └── FAIL → compare against baseline, identify degraded nodes

6. Generate summary report
   → Total nodes tested
   → Pass/fail per suite
   → Nodes requiring attention
   → Performance vs baseline
```

---

## Workflow: Quick Health Check

Use when: Spot-checking a few nodes, daily monitoring.

**Paste into Claude:**
```
Quick health check on 10.194.129.213 and 10.194.129.211.
SSH user root, key ~/.ssh/id_rsa.
```

**Execution sequence:**
```
1. preflight_checks (basic mode) — ~30 seconds
2. host_configs_cvs — ~1 minute
3. Summary: healthy/unhealthy nodes
```

---

## Workflow: Network Validation

Use when: After network changes, new NICs, RDMA issues.

**Paste into Claude:**
```
Validate network on 10.194.129.213 and 10.194.129.211.
Check RDMA, IB bandwidth, and RCCL.
SSH user root, key ~/.ssh/id_rsa.
```

**Execution sequence:**
```
1. preflight_checks (full_mesh mode) — tests all node pairs
2. ib_perf_bw_test — IB bandwidth benchmarks
3. rccl_perf (all_reduce only) — multi-node GPU communication
4. Generate network health report
```

---

## Workflow: Pre-Training Readiness

Use when: Before launching a distributed training job.

**Paste into Claude:**
```
Is the cluster 10.194.129.213 with worker 10.194.129.211 ready for distributed training?
SSH user root, key ~/.ssh/id_rsa. Target framework: Megatron.
```

**Execution sequence:**
```
1. preflight_checks (basic)
2. host_configs_cvs
3. rccl_perf (all_reduce + all_gather)
4. If target is JAX: jax_llama3_1_70b_single (single-node smoke test)
5. If target is Megatron: megatron_llama3_1_8b_single (single-node smoke test)
6. Report: "Cluster is ready/not ready for distributed training"
```

---

## Workflow: GPU Burn-In

Use when: New GPU installation, RMA replacement, hardware qualification.

**Paste into Claude:**
```
Run GPU burn-in on 10.194.129.213 and 10.194.129.211.
SSH user root, key ~/.ssh/id_rsa.
Escalate hardware failures to Jira DCCS.
```

**Execution sequence:**
```
1. preflight_checks
2. rvs_cvs (GPU enumeration + basic tests)
3. agfhc_cvs (level 3 - full stress)
4. transferbench_cvs (all modes)
5. Report: per-GPU health status with pass/fail/warning
```

---

## Workflow: Inference Readiness

Use when: Before deploying inference workloads.

**Paste into Claude:**
```
Check if 10.194.129.213 is ready for vLLM inference.
SSH user root, key ~/.ssh/id_rsa.
```

**Execution sequence:**
```
1. preflight_checks
2. host_configs_cvs
3. Single-node inference smoke test (vllm or sglang)
4. Report: node ready for inference deployment
```

---

## Workflow: Overnight Autonomous Run

Use when: Leaving for the night, want results by morning.

**Paste into Claude (select "Autonomous" when asked):**
```
Run full cluster qualification overnight on 10.194.129.213 with worker 10.194.129.211.
SSH user root, key ~/.ssh/id_rsa.
Auto-heal what you can, escalate hardware failures to Jira project DCCS.
```

**Execution sequence:**
```
1. Wrap all work in tmux on head node (survives SSH disconnect)
2. Run full qualification workflow (preflight → platform → health → RCCL)
3. On failure: auto-heal safe issues → re-run failed tests
4. On hardware failure: collect diagnostics → create Jira ticket
5. Generate consolidated summary report
6. Results ready in the morning
```

---

## Mode Behavior Per Workflow

After pasting any prompt above, the agent asks: **"Which mode?"**

| Mode | Effect on Workflows |
|------|-------------------|
| **Interactive** | Agent confirms before each suite runs. Good for first time on a new cluster. |
| **Autonomous** | Agent logs each suite and proceeds. Ideal for overnight runs and routine validation. |
| **Batch** | Agent runs silently, reports consolidated results at the end. |

## Terminal Launchers (CI/CD Only)

For cron jobs and CI pipelines where there is no interactive Claude session:

```bash
# One-shot headless execution (from terminal, not inside Claude)
cvs-ai-headless "Run full cluster qualification on 10.194.129.213 with worker 10.194.129.211. SSH user root, key ~/.ssh/id_rsa."

# Pipe from a script
echo "GPU burn-in on 10.194.129.213. SSH user root, key ~/.ssh/id_rsa." | cvs-ai-headless
```
