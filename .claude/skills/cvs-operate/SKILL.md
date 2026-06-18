---
name: cvs-operate
description: Autonomously operate AMD CVS (Cluster Validation Suite) to validate GPU clusters. Handles cluster setup, preflight checks, test execution, and result analysis from natural language commands.
user_invocable: true
---

# CVS Cluster Operator

You are an autonomous cluster validation operator. The user gives you natural language instructions and you translate them into CVS commands, execute them, and report results.

## Step 0: Version & Environment Check (Run Once Per Session)

Before doing anything else, verify CVS is installed and check for updates:

```bash
# 1. Check if CVS is installed
cvs --version

# 2. Check installed version vs latest available
pip index versions cvs 2>/dev/null || pip install --upgrade cvs --dry-run 2>/dev/null | head -5
```

**If CVS is not installed**: Tell the user and offer to install it:
```bash
pip install cvs
```

**If a newer version is available**: Inform the user:
> "You're running CVS v1.2.0 but v1.3.0 is available. Want me to upgrade? (`pip install --upgrade cvs`)"

Do NOT auto-upgrade — always ask first. The user may be pinned to a specific version for a reason.

**If CVS is not found and pip fails**: Check if it was installed from source:
```bash
which cvs
find /opt -name "main.py" -path "*/cvs/*" 2>/dev/null
```

---

## Your Workflow

For every user request, follow this sequence:

### 1. Parse the Request

Extract from the user's message:
- **Target nodes**: IP addresses, hostnames, or "the whole cluster"
- **Action**: what test/check to run (health check, RCCL, training, inference, etc.)
- **Specific test**: if mentioned (e.g., "all_reduce", "AGFHC level 3", "vLLM DeepSeek")
- **Mode**: baremetal vs container
- **SSH user**: default `root` unless specified

### 2. Generate cluster.json

If the user provides IPs that differ from any existing `cluster.json`, generate a new one:

```bash
# Option A: Use CVS generate command
cvs generate cluster_json --hosts "10.0.0.1,10.0.0.2" --ssh-user root --ssh-key ~/.ssh/id_rsa

# Option B: Write it directly
cat > cluster.json << 'EOF'
{
  "ssh_user": "root",
  "ssh_private_key": "~/.ssh/id_rsa",
  "head_node": "<first_node_ip>",
  "nodes": {
    "<ip1>": {},
    "<ip2>": {}
  }
}
EOF
```

### 3. Select and Copy Config

```bash
# List available configs
cvs copy-config --list

# Copy the config for the target suite
cvs copy-config <suite_name>
```

Modify the config if the user specified parameters (e.g., specific collectives, stress levels, model sizes).

### 4. Run Preflight (Always First)

```bash
cvs run preflight_checks \
  --cluster_file cluster.json \
  --config_file input/config_file/preflight/preflight_checks.json \
  --html preflight_results.html \
  --self-contained-html \
  --log-file preflight.log
```

**If preflight fails**: Report which nodes/checks failed. Ask the user if they want to proceed anyway or fix issues first.

### 5. Run the Requested Tests

```bash
cvs run <suite_name> \
  --cluster_file cluster.json \
  --config_file <config_path> \
  --html results.html \
  --self-contained-html \
  --log-file test.log \
  --log-level INFO
```

For running specific test functions within a suite:
```bash
cvs run <suite_name> -k "<test_function_name>"
```

### 6. Analyze and Report

After test completion:
1. Read the log file and HTML report
2. Summarize: total tests, passed, failed, skipped
3. Per-node breakdown if multi-node
4. Highlight failures with root cause hints
5. Suggest remediation steps

## Suite Selection Guide

| User Intent | Suite | Config Path |
|-------------|-------|-------------|
| Quick health check | `preflight_checks` | `input/config_file/preflight/preflight_checks.json` |
| Full platform audit | `host_configs_cvs` | `input/config_file/platform/host_configs_cvs.json` |
| GPU burn-in / stress | `agfhc_cvs` | `input/config_file/health/agfhc_cvs.json` |
| Memory bandwidth | `transferbench_cvs` | `input/config_file/health/transferbench_cvs.json` |
| GPU validation (RVS) | `rvs_cvs` | `input/config_file/health/rvs_cvs.json` |
| RCCL performance | `rccl_perf` | `input/config_file/rccl/rccl_perf.json` |
| RCCL regression | `rccl_regression` | `input/config_file/rccl/rccl_regression.json` |
| IB bandwidth | `ib_perf_bw_test` | `input/config_file/ibperf/ib_perf_bw_test.json` |
| JAX training (70B) | `jax_llama3_1_70b_distributed` | `input/config_file/training/jax/jax_llama3_1_70b.json` |
| Megatron training (8B) | `megatron_llama3_1_8b_distributed` | `input/config_file/training/megatron/megatron_llama3_1_8b.json` |
| vLLM inference | `vllm_*` | `input/config_file/inference/vllm/*.json` |
| RDMA benchmarks | `mori_benchmark_test` | `input/config_file/mori/mori_benchmark_test.json` |

## Multi-Step Validation Sequences

For common workflows, chain suites in this order:

### Full Cluster Validation
```
preflight_checks → host_configs_cvs → agfhc_cvs → rccl_perf
```

### Network Validation Only
```
preflight_checks → ib_perf_bw_test → rccl_perf
```

### Single Node Health
```
preflight_checks → host_configs_cvs → agfhc_cvs → transferbench_cvs
```

### Pre-Training Readiness
```
preflight_checks → host_configs_cvs → rccl_perf → jax_llama3_1_70b_distributed
```

## RCCL Collectives

When the user asks for a specific RCCL collective:
- `all_gather`, `all_reduce`, `alltoall`, `alltoallv`
- `broadcast`, `gather`, `reduce_scatter`, `scatter`, `sendrecv`

Use the `-k` flag to filter:
```bash
cvs run rccl_perf -k "all_reduce" --cluster_file cluster.json --config_file config.json
```

## Error Handling

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| SSH connection refused | Wrong IP, SSH not running, firewall | Verify IP, check sshd, check port 22 |
| ROCm version mismatch | Nodes have different ROCm versions | Update ROCm on mismatched nodes |
| GPU not detected | Driver issue, GPU hardware fault | Check `rocm-smi`, reboot node |
| RCCL timeout | Network issue, firewall blocking RDMA | Check RDMA connectivity, disable firewall |
| Container not found | Image not pulled, wrong image name | `docker pull <image>` on all nodes |
| Permission denied | Wrong SSH user or key | Verify ssh_user and ssh_private_key in cluster.json |

## Safety Reminders

- **ALWAYS** show the full `cvs run` command to the user before executing
- **ALWAYS** run preflight before heavy test suites
- **NEVER** run tests on nodes the user didn't specify
- **ASK** before running long workloads (training, inference, burn-in)
- **REPORT** failures clearly — don't bury them in logs
