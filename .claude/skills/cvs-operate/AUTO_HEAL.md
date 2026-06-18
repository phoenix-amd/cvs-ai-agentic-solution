# Auto-Heal Playbook

When a test fails, don't just report it — **attempt automatic remediation** before escalating to the user.

## Auto-Heal Decision Tree

```
Test Failed
  ├── Preflight: SSH failed
  │     → Verify IP is reachable (ping)
  │     → Check SSH key permissions (chmod 600)
  │     → Try alternate SSH port (2222)
  │     → ESCALATE if still failing
  │
  ├── Preflight: ROCm version mismatch
  │     → Report which nodes differ
  │     → Show exact versions per node
  │     → Suggest: "Run `sudo apt install rocm` on node X"
  │     → ESCALATE (don't auto-install)
  │
  ├── Preflight: RDMA connectivity failed
  │     → Check firewall status on failed nodes
  │     → Run: cvs exec --cmd "sudo ufw status" on failed nodes
  │     → If firewall active, suggest disabling for RDMA ports
  │     → ESCALATE
  │
  ├── Platform: IOMMU not in passthrough
  │     → Report exact GRUB config needed
  │     → Show: "Add iommu=pt to GRUB_CMDLINE_LINUX"
  │     → ESCALATE (requires reboot)
  │
  ├── Platform: NUMA balancing enabled
  │     → AUTO-FIX: cvs exec --cmd "echo 0 > /proc/sys/kernel/numa_balancing"
  │     → Re-run check to verify
  │
  ├── RCCL: Timeout / low bandwidth
  │     → Check NCCL/RCCL env vars
  │     → Verify network interfaces match config
  │     → Run: cvs exec --cmd "ibstat" to check IB state
  │     → Compare against known-good baseline
  │     → ESCALATE with diagnostic data
  │
  ├── Health: GPU not detected
  │     → Run: cvs exec --cmd "rocm-smi" on failed node
  │     → Run: cvs exec --cmd "lspci | grep -i amd" on failed node
  │     → ESCALATE with hardware info
  │
  └── Any: Container not found
        → AUTO-FIX: cvs exec --cmd "docker pull <image>"
        → Re-run the test
```

## Auto-Fix Rules

| Severity | Action | Example |
|----------|--------|---------|
| **Safe** (auto-fix) | Fix it, re-run, report | NUMA balancing, docker pull, chmod SSH key |
| **Moderate** (suggest) | Show the fix command, ask user | Firewall rules, env vars, GRUB config |
| **Critical** (escalate) | Report with diagnostics, never auto-fix | Reboot, driver install, hardware issues |

## Diagnostic Data Collection

On any failure, automatically collect:
```bash
# On failed nodes
cvs exec --cmd "rocm-smi --showallinfo"      # GPU status
cvs exec --cmd "ibstat"                        # IB status
cvs exec --cmd "dmesg | tail -50"             # Recent kernel messages
cvs exec --cmd "cat /etc/os-release"          # OS info
cvs exec --cmd "uname -r"                     # Kernel version
```

Bundle this into a diagnostic summary before escalating.
