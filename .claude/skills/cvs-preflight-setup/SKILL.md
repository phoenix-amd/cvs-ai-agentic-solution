---
name: cvs-preflight-setup
description: >
  Run before any CVS preflight or cluster health check. Handles all
  first-time setup friction: CVS install, SSH key propagation, GPU
  availability, RDMA discovery, and preflight config auto-population.
  Leaves cvs-operate a clean, ready-to-run environment.
user_invocable: true
---

# CVS Preflight Setup

Load this skill **before** running `cvs-operate`'s preflight step whenever:
- CVS has never been run on this head node before
- The preflight config still has `<changeme>` fields
- SSH from head to workers is not yet verified
- A new cluster profile is being created

Run all 7 checks in order. Stop at the first blocking failure and tell the
user exactly what to do. Never silently skip a check.

---

## Quick Reference — What This Skill Owns

| Concern | This skill | cvs-operate |
|---------|-----------|-------------|
| CVS install & venv | ✓ | — |
| SSH connectivity (laptop→head, head→self, head→workers) | ✓ | — |
| GPU driver availability | ✓ | — |
| RDMA detection & link-layer classification | ✓ | — |
| Preflight config auto-population | ✓ | — |
| Downed port reporting | ✓ | — |
| Running actual preflight tests | — | ✓ |
| RCCL / training / inference config | — | ✓ |
| Jira escalation | — | ✓ |

---

## Check 1 — CVS Install

Note: define `SSH_OPTS` and `SSH_HEAD` before Check 1 (see Check 2 preamble).
All `ssh` calls below use `$SSH_HEAD` (laptop→head) or `ssh $SSH_OPTS` (head→node).

```bash
$SSH_HEAD 'which cvs && cvs --version' 2>&1
```

| Result | Action |
|--------|--------|
| `cvs: 1.x.x` | Done — note version, continue |
| `command not found` | Install from source (pip package does not exist on PyPI) |
| SSH fails | Fix SSH first (Check 2), then retry |

### Install from source (always use this — pip will fail)

```bash
$SSH_HEAD '
  git clone https://github.com/ROCm/cvs.git ~/cvs 2>&1 | tail -3 &&
  cd ~/cvs &&
  python3 -m venv .cvs_venv &&
  source .cvs_venv/bin/activate &&
  pip3 install -r requirements.txt 2>&1 | tail -5 &&
  pip3 install -e . 2>&1 | tail -3 &&
  echo "---VERIFY---" &&
  cvs --version
'
```

After install, add venv activation to `.bashrc` so future SSH sessions have `cvs` in PATH:

```bash
$SSH_HEAD 'grep -q "cvs_venv" ~/.bashrc || echo "source ~/cvs/.cvs_venv/bin/activate" >> ~/.bashrc'
```

Update cluster profile with CVS paths:
```json
{
  "cvs_dir": "~/cvs",
  "cvs_venv": "~/cvs/.cvs_venv",
  "cluster_json": "~/cvs/cvs/input/cluster_file/cluster.json"
}
```

### Working directory for all CVS commands

Always `cd ~/cvs` before running `pytest` or `cvs` commands. Config templates
and test scripts are resolved relative to the source root. Running from any
other directory causes "No config files found" errors.

---

## Check 2 — SSH Connectivity & Key Propagation

Run all steps in sequence. Each must pass before the next.

### No-prompt SSH pattern

All SSH commands in this skill use these options to prevent interactive prompts:

```
-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10
```

- `StrictHostKeyChecking=no` — never ask the user to confirm a new host key
- `UserKnownHostsFile=/dev/null` — suppress "Permanently added…" noise; known_hosts is irrelevant for cluster automation
- `ConnectTimeout=10` — fail fast instead of hanging

Define a reusable alias at the start of every shell session or script block:

```bash
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10"
SSH_HEAD="ssh $SSH_OPTS -i <initial_key> <ssh_user>@<head_node>"
```

Use `$SSH_HEAD` and `$SSH_OPTS` in all commands below.

### 2a. Laptop → Head node

**If SSH user is unknown:** ask the user. Offer only common cluster usernames
(`root`, `ubuntu`). **Never** derive options from the local working directory
path or local username — these are unrelated to the remote cluster user.

```bash
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10"
ssh $SSH_OPTS -i <initial_key> <ssh_user>@<head_node> 'hostname'
```

**If this fails:** wrong IP, sshd down, or key not registered. For AMD Conductor
clusters, verify the key is authorized via the Conductor portal.

### 2b. Generate CVS SSH keypair on head node

Generate a dedicated RSA keypair on the head node for CVS and MPI operations.
Using `~/.ssh/id_rsa` is important: CVS references it explicitly via `cluster.json`,
and MPI spawns worker daemons via SSH **without** a `-i` flag — it falls back to
`~/.ssh/id_rsa` automatically. Both requirements are satisfied by a single key.

```bash
ssh $SSH_OPTS -i <initial_key> <ssh_user>@<head_node> '
  [ -f ~/.ssh/id_rsa ] || ssh-keygen -t rsa -b 4096 -N "" -f ~/.ssh/id_rsa -q
  cat ~/.ssh/id_rsa.pub
'
```

### 2c. Propagate to head node self (head → self)

CVS uses parallel-SSH on all nodes including the head node itself. This **must** work.

```bash
ssh $SSH_OPTS -i <initial_key> <ssh_user>@<head_node> "
  grep -qF \"\$(cat ~/.ssh/id_rsa.pub)\" ~/.ssh/authorized_keys 2>/dev/null || \
    cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
  chmod 600 ~/.ssh/authorized_keys
  ssh $SSH_OPTS <head_ip> hostname
"
```

### 2d. Propagate to each worker node

Push the head's public key into each worker's `authorized_keys` using whatever
key currently reaches the worker (the user's initial access key). Do this for
every worker node.

```bash
HEAD_PUBKEY=$(ssh $SSH_OPTS -i <initial_key> <ssh_user>@<head_node> 'cat ~/.ssh/id_rsa.pub')

# Repeat for each worker:
ssh $SSH_OPTS -i <initial_key> <ssh_user>@<worker_ip> \
  "grep -qF '$HEAD_PUBKEY' ~/.ssh/authorized_keys 2>/dev/null || \
   echo '$HEAD_PUBKEY' >> ~/.ssh/authorized_keys; \
   chmod 600 ~/.ssh/authorized_keys; echo OK"
```

### 2e. Verify head → each worker

```bash
ssh $SSH_OPTS -i <initial_key> <ssh_user>@<head_node> \
  "ssh $SSH_OPTS <worker_ip> hostname"
```

**If this fails:** the worker's sshd may restrict key type/user. Check
`/etc/ssh/sshd_config` on the worker and confirm `~/.ssh/authorized_keys`
contains the head's public key.

**Update cluster profile and cluster.json after all SSH checks pass:**
```json
{
  "ssh_key_on_head": "~/.ssh/id_rsa"
}
```

`cluster.json` `priv_key_file` should be the **full expanded path**:
`/home/<ssh_user>/.ssh/id_rsa`

---

## Check 3 — GPU Availability

Run on **all** nodes via CVS parallel-SSH (or loop over nodes individually).

```bash
# On each node (use $SSH_HEAD for head, ssh $SSH_OPTS for workers)
$SSH_HEAD 'amd-smi version 2>&1'
ssh $SSH_OPTS -i <initial_key> <ssh_user>@<worker_ip> 'amd-smi version 2>&1'
```

Parse the output:

| Output | Meaning | Action |
|--------|---------|--------|
| `ROCm version: X.Y.Z` | GPUs visible | Record version, continue |
| `amdgpu not found` or empty GPU list | Driver not loaded | Attempt `sudo modprobe amdgpu`, retry once |
| `command not found` | amd-smi not installed | Check ROCm install: `ls /opt/rocm*/bin/amd-smi` |
| Still no GPUs after modprobe | Hardware issue | Flag for physical inspection; do not block preflight |

```bash
# Attempt to load amdgpu driver
ssh $SSH_OPTS -i <initial_key> <ssh_user>@<node> 'sudo modprobe amdgpu 2>&1; sleep 3; amd-smi version 2>&1'
```

**Record in profile:**
```json
{
  "rocm_version": "7.2.0"
}
```

---

## Check 4 — RDMA Detection & Link-Layer Classification

Use `rdma link` (not `ibdev2netdev`) — it works across all vendor NICs
(Mellanox, Broadcom Thor, AMD Pensando AINIC, etc.).

Run on the **head node** only to classify link layer. Check the **first**
device returned — the link layer is uniform across the cluster.

```bash
$SSH_HEAD 'rdma link 2>&1'
```

Also discover the management network interface (needed for RCCL `mpi_oob_port`):

```bash
$SSH_HEAD "ip route get 1 | grep -oP 'dev \K\S+' | head -1"
# Typical output: eno8303
```

Store this as `mgmt_interface` in the cluster profile.

### Parsing rules

**InfiniBand** — output contains `subnet_prefix` (no `netdev` field):
```
link mlx5_0/1 subnet_prefix fe80:0000:0000:0000 lid 38 ... state ACTIVE physical_state LINK_UP
```

**RoCEv2** — output contains `netdev`:
```
link mlx5_0/1 state ACTIVE physical_state LinkUp netdev ens3f0np0
```

### Classification table

| Detected field | Link layer | GID index | RCCL env script |
|----------------|-----------|-----------|-----------------|
| `subnet_prefix` in first line | InfiniBand | `0` | Create new mlx5 script |
| `netdev` in first line + `mlx5_*` device | RoCEv2 (Mellanox) | `3` | `cx7_env_script.sh` |
| `netdev` in first line + `bnxt_re*` device | RoCEv2 (Broadcom) | `3` | `thor2_env_script.sh` |

### Collect active RDMA devices

From `rdma link` output, collect all device names where:
- `state ACTIVE` **and** `physical_state LINK_UP` (or `LinkUp`)

Exclude any device/port that is `DOWN`, `DISABLED`, or `POLLING`.

```python
# Pseudo-logic for the agent
active_devices = []
down_devices = []
for line in rdma_link_output.splitlines():
    if not line.startswith("link"):
        continue
    device = line.split("/")[0].replace("link ", "").strip()
    if "state ACTIVE" in line and ("LINK_UP" in line or "LinkUp" in line):
        active_devices.append(device)
    else:
        down_devices.append(device)
```

**Record in profile:**
```json
{
  "link_layer": "InfiniBand",
  "gid_index": "0",
  "active_rdma_devices": ["mlx5_0","mlx5_1","mlx5_2","mlx5_3","mlx5_4","mlx5_6","mlx5_7","mlx5_8"],
  "down_rdma_devices": ["mlx5_5"],
  "mgmt_interface": "eno8303",
  "nic_type": "mellanox-mlx5"
}
```

---

## Check 5 — Preflight Config Auto-Population

The preflight config template has three `<changeme>` fields. Auto-populate
all three before running any tests. Never run preflight with `<changeme>`
still present.

**Config path:** `~/cvs/cvs/input/config_file/preflight/preflight_config.json`

### Fields to populate

| Field | How to discover | IB value | RoCEv2 value |
|-------|----------------|----------|--------------|
| `gid_index` | Link layer from Check 4 | `"0"` | `"3"` |
| `expected_rocm_version` | `amd-smi version` from Check 3 | e.g. `"7.2.0"` | same |
| `rdma_interfaces` | Active devices from Check 4 | e.g. `["mlx5_0","mlx5_1",...]` | e.g. `["mlx5_0","mlx5_1",...]` |

```python
# Agent applies this update
import json

path = "/home/<user>/cvs/cvs/input/config_file/preflight/preflight_config.json"
with open(path) as f:
    cfg = json.load(f)

cfg["preflight"]["node_check"]["gid_index"] = gid_index          # "0" or "3"
cfg["preflight"]["node_check"]["expected_rocm_version"] = rocm_version
cfg["preflight"]["node_check"]["rdma_interfaces"] = active_devices  # list, no DOWN ports

with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
```

**Validate:** after writing, confirm no `<changeme>` remains:
```bash
grep -c "<changeme>" ~/cvs/cvs/input/config_file/preflight/preflight_config.json
# Must print 0
```

---

## Check 6 — InfiniBand Workaround

The CVS `get_rdma_nic_dict()` parser in `linux_utils.py` expects RoCEv2
`rdma link` output (with `netdev <iface>` at line end). InfiniBand output
omits `netdev`, which causes an unguarded `match.group(1)` crash.

**Detection:** link layer is InfiniBand (from Check 4).

**Workaround (no code patching):** set `connectivity_mode` to `skip` in
the preflight config before running:

```python
cfg["preflight"]["connectivity_check"]["rdma"]["connectivity_mode"] = "skip"
```

Tell the user:

> "RDMA connectivity test skipped — CVS's rdma link parser does not support
> InfiniBand output format. The 8 active IB ports were verified via `rdma link`
> and all show ACTIVE/LINK_UP. Manual validation: run `ibping` or check IB
> switch fabric health separately."

**Do NOT silently skip.** The user must know RDMA mesh connectivity was not
validated by CVS on this run.

**This workaround is NOT needed for RoCEv2 clusters.** Only apply when
link layer is InfiniBand.

---

## Check 7 — Downed Port Report

Run `rdma link` on **all nodes** (head + each worker) and collect every
port that is not `ACTIVE/LINK_UP`. Report as a named hardware issue —
not a test failure.

```bash
# Run on each node and collect downed ports
$SSH_HEAD   'rdma link 2>&1 | grep -v "ACTIVE.*LINK_UP\|ACTIVE.*LinkUp"'
ssh $SSH_OPTS -i <initial_key> <ssh_user>@<worker1> \
              'rdma link 2>&1 | grep -v "ACTIVE.*LINK_UP\|ACTIVE.*LinkUp"'
```

```
⚠️  Downed IB ports detected:

  Node              Device   Port  State   Physical State
  ──────────────────────────────────────────────────────
  <head_ip>         mlx5_5   1     DOWN    DISABLED
  <worker_ip>       mlx5_5   1     DOWN    DISABLED

  Consistent across all nodes → likely cable or switch port issue.
  Impact: 1/9 IB ports offline per node (~11% capacity reduction).
  Action: Physical inspection of the cable/switch port for mlx5_5.
```

**Rules:**
- Down port on **all** nodes → likely cable or switch issue → flag for physical inspection
- Down port on **one** node only → likely NIC/firmware issue on that node → collect `dmesg | grep mlx5_5` from that node

**Do NOT mark the cluster as unhealthy** solely because of downed ports —
if the remaining ports pass preflight, the cluster is usable (at reduced capacity).

---

## Output — Sanity Check Table

When all 7 checks complete, print a pass/fail table:

```
CVS Preflight Setup — Sanity Check

  Check                          Result   Detail
  ───────────────────────────────────────────────────────────────────
  CVS install                    PASS     v1.0.0 at ~/cvs
  SSH laptop → head              PASS     <head-hostname>
  SSH head → self                PASS
  SSH head → workers             PASS     <worker-hostname(s)>
  GPU availability               PASS     8x MI300X, ROCm 7.2.0
  RDMA detection                 PASS     8 active (mlx5_0–4,6–8), 1 DOWN (mlx5_5)
  Preflight config populated     PASS     gid=0, rocm=7.2.0, 8 interfaces
  IB workaround applied          INFO     RDMA mesh test skipped (IB cluster)
  ───────────────────────────────────────────────────────────────────
  ⚠️  mlx5_5 DOWN on all nodes — physical inspection recommended
```

Then hand off:

> "Setup complete. Ready to run preflight — say 'run preflight' or 'check
> cluster health' to continue."

---

## Profile Schema (full)

`~/.cvs_agent/cluster_profile.json` after a successful setup run:

```json
{
  "profile_name": "default",
  "head_node": "10.0.0.1",
  "worker_nodes": ["10.0.0.2"],
  "ssh_user": "<ssh-user>",
  "ssh_key": "<initial-key-used-to-reach-head>",
  "ssh_key_on_head": "~/.ssh/id_rsa",
  "jira_project": "DCCS",
  "jira_component": "Cluster Administration",
  "cvs_dir": "~/cvs",
  "cvs_venv": "~/cvs/.cvs_venv",
  "cluster_json": "~/cvs/cvs/input/cluster_file/cluster.json",
  "rocm_version": "7.2.0",
  "link_layer": "InfiniBand",
  "gid_index": "0",
  "mgmt_interface": "eno8303",
  "nic_type": "mellanox-mlx5",
  "active_rdma_devices": ["mlx5_0","mlx5_1","mlx5_2","mlx5_3","mlx5_4","mlx5_6","mlx5_7","mlx5_8"],
  "down_rdma_devices": ["mlx5_5"],
  "results_dir": null
}
```

---

## Pre-Run /tmp Cleanup (MANDATORY)

Before handing off to `cvs-operate` for any test execution, clean stale `/tmp`
artifacts from previous users or previous runs on the head node. This prevents
`PermissionError` when CVS writes HTML reports.

```bash
$SSH_HEAD '
  sudo rm -rf /tmp/preflight_checks_html /tmp/preflight.html /tmp/preflight.log 2>/dev/null
  sudo rm -rf /tmp/rccl_*_html /tmp/host_configs_*_html /tmp/agfhc_*_html 2>/dev/null
  rm -rf /tmp/preflight_checks_html /tmp/preflight.html /tmp/preflight.log 2>/dev/null
  rm -rf /tmp/rccl_*_html /tmp/host_configs_*_html /tmp/agfhc_*_html 2>/dev/null
  echo "Pre-run /tmp cleanup done"
'
```

**Why**: CVS writes sub-reports to `/tmp/<suite>_html/`. If these dirs exist
from a different user, the current run gets `PermissionError` and HTML report
generation fails — even though the actual tests pass. Always clean before running.

---

## What This Skill Does NOT Do

- Does **not** patch CVS source code
- Does **not** run preflight tests (`cvs-operate` does that)
- Does **not** configure RCCL, training, or inference suites
- Does **not** create Jira tickets
- Does **not** run on every test invocation — only on first setup or when
  profile is missing/stale

---

## Known Limitations

| Limitation | Workaround |
|------------|-----------|
| IB `rdma link` crashes CVS interface parser | Set `connectivity_mode: skip` (Check 6) |
| `amd-smi` shows 0 GPUs without `modprobe amdgpu` | Auto-attempt `sudo modprobe amdgpu` (Check 3) |
| `cvs` not on PyPI | Always install from GitHub source (Check 1) |
| CVS must run from `~/cvs` working directory | `cd ~/cvs` before every pytest / cvs command |
| Head node needs SSH to itself for parallel-SSH | Append head's own pubkey to its `authorized_keys` (Check 2b) |
| MPI orted spawns without `-i` flag | `~/.ssh/id_rsa` on head must be authorized on all workers — otherwise RCCL daemon startup fails silently (Check 2d) |
