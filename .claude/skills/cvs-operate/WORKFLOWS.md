# Pre-Built Validation Workflows

Smart workflows that chain multiple CVS suites with conditional logic.

## Workflow: Full Cluster Qualification

Use when: New cluster, post-maintenance, or periodic health check.

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

## Workflow: Quick Health Check

Use when: Spot-checking a few nodes, daily monitoring.

```
1. preflight_checks (basic mode) — ~30 seconds
2. host_configs_cvs — ~1 minute
3. Summary: healthy/unhealthy nodes
```

## Workflow: Network Validation

Use when: After network changes, new NICs, RDMA issues.

```
1. preflight_checks (full_mesh mode) — tests all node pairs
2. ib_perf_bw_test — IB bandwidth benchmarks
3. rccl_perf (all_reduce only) — multi-node GPU communication
4. Generate network health report
```

## Workflow: Pre-Training Readiness

Use when: Before launching a distributed training job.

```
1. preflight_checks (basic)
2. host_configs_cvs
3. rccl_perf (all_reduce + all_gather)
4. If target is JAX: jax_llama3_1_70b_single (single-node smoke test)
5. If target is Megatron: megatron_llama3_1_8b_single (single-node smoke test)
6. Report: "Cluster is ready/not ready for distributed training"
```

## Workflow: GPU Burn-In

Use when: New GPU installation, RMA replacement, hardware qualification.

```
1. preflight_checks
2. rvs_cvs (GPU enumeration + basic tests)
3. agfhc_cvs (level 3 - full stress)
4. transferbench_cvs (all modes)
5. Report: per-GPU health status with pass/fail/warning
```

## Workflow: Inference Readiness

Use when: Before deploying inference workloads.

```
1. preflight_checks
2. host_configs_cvs
3. Single-node inference smoke test (vllm or sglang)
4. Report: node ready for inference deployment
```
