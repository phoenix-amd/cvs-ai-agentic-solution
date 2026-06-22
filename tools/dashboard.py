#!/usr/bin/env python3
"""
CVS AI Agentic Solution — Interactive Cluster Dashboard Generator
Grafana-inspired dark theme with gauges, charts, and interactive tables.

Usage:
    python3 dashboard.py --input cluster_data.json --output dashboard.html
"""

import argparse
import json
import os
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


def generate_dashboard(data: dict, output_path: str) -> str:
    title = data.get("title", "CVS Cluster Dashboard")
    ts = data.get("timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    cluster = data.get("cluster_name", "Unknown")
    ver = data.get("agent_version", "1.4.0")
    nodes = data.get("nodes", {})
    target = data.get("target_config", {})
    tests = data.get("test_results", [])
    rccl = data.get("rccl_results", [])

    n_nodes = len(nodes)
    gpu_total = sum(int(n.get("gpu_count", 0)) for n in nodes.values() if str(n.get("gpu_count","0")).isdigit())
    passed = sum(1 for t in tests if t.get("status") == "PASS")
    failed = sum(1 for t in tests if t.get("status") == "FAIL")
    total = len(tests)
    pct = int(passed / total * 100) if total else 0

    # Gauge SVG generator
    def gauge_svg(value, max_val, label, unit="", color="#00a85a", size=120):
        pct_val = min(value / max_val * 100, 100) if max_val else 0
        dash = pct_val * 2.51
        if pct_val > 80: color = "#00a85a"
        elif pct_val > 50: color = "#ff8c00"
        else: color = "#ff4444" if pct_val < 30 else "#ff8c00"
        return f'''<div style="text-align:center;">
            <svg width="{size}" height="{size}" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="40" fill="none" stroke="#2a2a3a" stroke-width="8"/>
                <circle cx="50" cy="50" r="40" fill="none" stroke="{color}" stroke-width="8"
                    stroke-dasharray="{dash} 251" stroke-dashoffset="0"
                    transform="rotate(-90 50 50)" stroke-linecap="round"/>
                <text x="50" y="46" text-anchor="middle" fill="{color}" font-size="18" font-weight="700">{value}</text>
                <text x="50" y="60" text-anchor="middle" fill="#888" font-size="9">{unit}</text>
            </svg>
            <div style="color:#aaa; font-size:11px; margin-top:-5px;">{label}</div>
        </div>'''

    # Node rows
    node_rows = ""
    for ip, info in nodes.items():
        def cell(val, key):
            exp = target.get(key, "")
            if not exp: return f'<td class="v">{val}</td>'
            if str(val) == str(exp): return f'<td class="p">{val}</td>'
            return f'<td class="f">{val}<br><small class="exp">exp: {exp}</small></td>'

        role = info.get("role", "worker")
        node_rows += f'''<tr>
            <td class="ip">{ip}</td>
            <td class="v">{info.get("hostname","")}</td>
            <td class="{'hd' if role=='head' else 'v'}">{role.upper()}</td>
            {cell(info.get("os",""), "os")}
            {cell(info.get("kernel",""), "kernel")}
            {cell(info.get("bios",""), "bios")}
            {cell(info.get("rocm",""), "rocm")}
            {cell(info.get("gpu_count",""), "gpu_count")}
            <td class="v">{info.get("gpu_type","")}</td>
            <td class="v">{info.get("memory","")}</td>
            <td class="v">{info.get("nic_type","")}</td>
            <td class="{'p' if info.get('rdma_status')=='ACTIVE' else 'f'}">{info.get("rdma_status","")}</td>
        </tr>'''

    # Test rows
    test_rows = ""
    for t in tests:
        s = t.get("status","")
        sc = "p" if s == "PASS" else ("f" if s == "FAIL" else "w")
        test_rows += f'''<tr>
            <td class="v">{t.get("suite","")}</td>
            <td class="v">{t.get("test","")}</td>
            <td class="v">{t.get("node","all")}</td>
            <td class="{sc}"><span class="badge {sc}">{s}</span></td>
            <td class="v dtl">{t.get("detail","")}</td>
            <td class="v">{t.get("duration","")}</td>
        </tr>'''

    # RCCL rows + chart data
    rccl_rows = ""
    max_bw = max((float(r.get("busbw_oop", 0)) for r in rccl), default=1)
    rccl_bars = ""
    for r in rccl:
        bw = float(r.get("busbw_oop", 0))
        w = int(bw / max_bw * 100) if max_bw else 0
        err = int(r.get("errors", 0))
        rccl_rows += f'''<tr>
            <td class="v">{r.get("size","")}</td>
            <td class="v">{r.get("algbw_oop","")}</td>
            <td class="v bw">{r.get("busbw_oop","")}</td>
            <td class="v">{r.get("algbw_ip","")}</td>
            <td class="v bw">{r.get("busbw_ip","")}</td>
            <td class="{'p' if err==0 else 'f'}">{err}</td>
        </tr>'''
        rccl_bars += f'''<div class="brow">
            <span class="bl">{r.get("size","")}</span>
            <div class="btrack"><div class="bfill" style="width:{w}%"></div></div>
            <span class="bv">{r.get("busbw_oop","")} GB/s</span>
        </div>'''

    # Peak RCCL
    peak_bw = max((float(r.get("busbw_oop", 0)) for r in rccl), default=0)
    avg_bw = sum(float(r.get("busbw_oop", 0)) for r in rccl) / len(rccl) if rccl else 0

    html = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:#0d0d1a;color:#ddd;min-height:100vh}}
/* Header */
.hdr{{background:linear-gradient(135deg,#12122a,#1a1a3a);padding:16px 32px;border-bottom:3px solid #ed1c24;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap}}
.hdr h1{{font-size:22px;color:#fff}}.hdr .sub{{color:#777;font-size:12px}}
.hdr .tags{{display:flex;gap:16px;flex-wrap:wrap}}.hdr .tags span{{font-size:12px;color:#666}}
.hdr .tags b{{color:#00c896}}
/* Tabs */
.tabs{{display:flex;background:#111128;border-bottom:1px solid #252540;padding:0 32px;overflow-x:auto}}
.tab{{padding:12px 20px;cursor:pointer;color:#666;font-size:13px;font-weight:600;border-bottom:3px solid transparent;white-space:nowrap;transition:.2s}}
.tab:hover{{color:#fff;background:#1a1a30}}.tab.a{{color:#ed1c24;border-color:#ed1c24}}
/* Content */
.cnt{{padding:20px 32px}}.pnl{{display:none}}.pnl.a{{display:block}}
/* Cards row */
.cds{{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:20px}}
.cd{{background:#161630;border-radius:8px;padding:16px;border-top:3px solid #ed1c24;text-align:center}}
.cd .vl{{font-size:28px;font-weight:800}}.cd .lb{{font-size:11px;color:#777;margin-top:4px}}
.cd.g .vl{{color:#00c896}}.cd.r .vl{{color:#ff5555}}.cd.b .vl{{color:#4488ff}}.cd.o .vl{{color:#ff8c00}}
/* Gauges row */
.gauges{{display:flex;gap:16px;justify-content:center;flex-wrap:wrap;margin:20px 0;padding:20px;background:#161630;border-radius:8px}}
/* Section */
.stl{{font-size:17px;color:#fff;margin:20px 0 12px;padding-bottom:6px;border-bottom:2px solid #252540}}
/* Tables */
table{{width:100%;border-collapse:collapse;background:#161630;border-radius:8px;overflow:hidden;margin-bottom:16px}}
thead th{{background:#1e1e38;color:#bbb;padding:10px 12px;text-align:left;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;position:sticky;top:0;z-index:1}}
td{{padding:8px 12px;border-bottom:1px solid #1e1e30;font-size:12px}}
tr:hover{{background:#1a1a35}}.ip{{font-weight:700;color:#4488ff}}.hd{{color:#ff8c00;font-weight:700}}
.p{{color:#00c896;font-weight:600}}.f{{color:#ff5555;font-weight:600}}.w{{color:#ff8c00;font-weight:600}}
.v{{color:#bbb}}.exp{{color:#ff8888;font-size:10px}}.bw{{color:#00c896;font-weight:700}}.dtl{{max-width:300px}}
/* Badge */
.badge{{display:inline-block;padding:2px 10px;border-radius:10px;font-size:10px;font-weight:700}}
.badge.p{{background:#0a2a15;color:#00c896}}.badge.f{{background:#2a0a0a;color:#ff5555}}
/* Filter */
.flt{{display:flex;gap:10px;margin-bottom:12px;align-items:center}}
.flt input,.flt select{{background:#1a1a30;border:1px solid #333;color:#fff;padding:7px 12px;border-radius:6px;font-size:12px}}
.flt input{{width:240px}}
/* RCCL bars */
.brow{{display:flex;align-items:center;gap:8px;margin:3px 0}}
.bl{{min-width:70px;font-size:11px;color:#777;text-align:right}}
.btrack{{flex:1;height:20px;background:#1a1a30;border-radius:4px;overflow:hidden}}
.bfill{{height:100%;background:linear-gradient(90deg,#00a85a,#00e6aa);border-radius:4px;transition:width .6s}}
.bv{{min-width:80px;font-size:11px;color:#00c896;font-weight:600}}
/* Status grid */
.sgrid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:8px;margin:16px 0}}
.scard{{display:flex;align-items:center;gap:10px;background:#161630;padding:10px 14px;border-radius:6px;border-left:3px solid #333}}
.scard.sp{{border-color:#00c896}}.scard.sf{{border-color:#ff5555}}
.scard .sname{{flex:1;font-size:12px;color:#bbb}}.scard .sst{{font-size:11px;font-weight:700}}
/* Footer */
.ftr{{text-align:center;padding:16px;color:#444;font-size:11px;border-top:1px solid #1a1a30;margin-top:30px}}
.ftr a{{color:#4488ff}}
@media(max-width:768px){{.cnt{{padding:12px}}.cds{{grid-template-columns:1fr 1fr}}.gauges{{flex-direction:column;align-items:center}}}}
</style></head><body>

<div class="hdr">
<div><h1>{title}</h1><div class="sub">CVS AI Agentic Solution Dashboard</div></div>
<div class="tags">
<span>Cluster: <b>{cluster}</b></span>
<span>Nodes: <b>{n_nodes}</b></span>
<span>GPUs: <b>{gpu_total}</b></span>
<span>Agent: <b>v{ver}</b></span>
<span>{ts}</span>
</div></div>

<div class="tabs">
<div class="tab a" onclick="sp('ov',this)">Overview</div>
<div class="tab" onclick="sp('nd',this)">Nodes ({n_nodes})</div>
<div class="tab" onclick="sp('ts',this)">Tests ({passed}/{total})</div>
<div class="tab" onclick="sp('rc',this)">RCCL Performance</div>
</div>

<div class="cnt">

<!-- OVERVIEW -->
<div id="ov" class="pnl a">
<div class="cds">
<div class="cd b"><div class="vl">{n_nodes}</div><div class="lb">Cluster Nodes</div></div>
<div class="cd b"><div class="vl">{gpu_total}</div><div class="lb">Total GPUs</div></div>
<div class="cd g"><div class="vl">{passed}</div><div class="lb">Tests Passed</div></div>
<div class="cd r"><div class="vl">{failed}</div><div class="lb">Tests Failed</div></div>
<div class="cd o"><div class="vl">{total}</div><div class="lb">Total Tests</div></div>
</div>

<div class="gauges">
{gauge_svg(pct, 100, "Pass Rate", "%", "#00c896" if pct>80 else "#ff8c00")}
{gauge_svg(n_nodes, max(n_nodes,8), "Nodes Online", "nodes")}
{gauge_svg(gpu_total, max(gpu_total, 16), "GPUs Active", "GPUs")}
{gauge_svg(int(peak_bw), max(int(peak_bw),200), "Peak BusBW", "GB/s") if rccl else gauge_svg(0, 100, "Peak BusBW", "N/A")}
{gauge_svg(int(avg_bw), max(int(avg_bw),200), "Avg BusBW", "GB/s") if rccl else gauge_svg(0, 100, "Avg BusBW", "N/A")}
{gauge_svg(passed, total, "Health Score", f"{passed}/{total}")}
</div>

<h3 class="stl">Test Results</h3>
<div class="sgrid">
{''.join(f'''<div class="scard s{'p' if t['status']=='PASS' else 'f'}">
<span class="sname">{t.get('test','')[:40]}</span>
<span class="sst {'p' if t['status']=='PASS' else 'f'}">{t['status']}</span>
</div>''' for t in tests)}
</div>

<h3 class="stl">Target Configuration</h3>
<table><thead><tr><th>Property</th><th>Expected Value</th></tr></thead>
<tbody>{''.join(f"<tr><td class='v'>{k}</td><td class='p'>{v}</td></tr>" for k,v in target.items())}</tbody></table>
</div>

<!-- NODES -->
<div id="nd" class="pnl">
<h3 class="stl">Per-Node Hardware & Software Comparison</h3>
<div class="flt"><input placeholder="Filter nodes..." onkeyup="ft('nt',this.value)"></div>
<div style="overflow-x:auto"><table id="nt"><thead><tr>
<th>IP</th><th>Hostname</th><th>Role</th><th>OS</th><th>Kernel</th><th>BIOS</th>
<th>ROCm</th><th>GPUs</th><th>GPU Type</th><th>Memory</th><th>NIC</th><th>RDMA</th>
</tr></thead><tbody>{node_rows}</tbody></table></div>
</div>

<!-- TESTS -->
<div id="ts" class="pnl">
<h3 class="stl">Detailed Test Results</h3>
<div class="flt">
<input placeholder="Filter tests..." onkeyup="ft('tt',this.value)">
<select onchange="fs('tt',this.value)"><option value="">All</option><option value="PASS">PASS</option><option value="FAIL">FAIL</option></select>
</div>
<table id="tt"><thead><tr><th>Suite</th><th>Test</th><th>Node</th><th>Status</th><th>Detail</th><th>Duration</th></tr></thead>
<tbody>{test_rows}</tbody></table>
</div>

<!-- RCCL -->
<div id="rc" class="pnl">
<h3 class="stl">RCCL Collective Performance — Bus Bandwidth</h3>
{'<p style="color:#666;margin:20px 0">No RCCL data. Run an RCCL test to populate.</p>' if not rccl else ''}
{f'''<div class="cds" style="margin-bottom:20px">
<div class="cd g"><div class="vl">{peak_bw:.1f}</div><div class="lb">Peak BusBW (GB/s)</div></div>
<div class="cd b"><div class="vl">{avg_bw:.1f}</div><div class="lb">Avg BusBW (GB/s)</div></div>
<div class="cd g"><div class="vl">0</div><div class="lb">Total Errors</div></div>
<div class="cd o"><div class="vl">{len(rccl)}</div><div class="lb">Message Sizes</div></div>
</div>
<h3 class="stl">Bandwidth by Message Size</h3>
<div style="max-width:700px;margin-bottom:20px">{rccl_bars}</div>
<h3 class="stl">Detailed Results</h3>
<table><thead><tr><th>Size</th><th>AlgBW OOP (GB/s)</th><th>BusBW OOP (GB/s)</th><th>AlgBW IP (GB/s)</th><th>BusBW IP (GB/s)</th><th>#Wrong</th></tr></thead>
<tbody>{rccl_rows}</tbody></table>''' if rccl else ''}
</div>

</div>

<div class="ftr">CVS AI Agentic Solution v{ver} | {ts} | <a href="https://github.com/phoenix-amd/cvs-ai-agentic-solution">GitHub</a></div>

<script>
function sp(id,el){{document.querySelectorAll('.pnl').forEach(p=>p.classList.remove('a'));document.querySelectorAll('.tab').forEach(t=>t.classList.remove('a'));document.getElementById(id).classList.add('a');el.classList.add('a')}}
function ft(tid,q){{document.getElementById(tid).querySelectorAll('tbody tr').forEach(r=>{{r.style.display=r.textContent.toLowerCase().includes(q.toLowerCase())?'':'none'}})}}
function fs(tid,s){{document.getElementById(tid).querySelectorAll('tbody tr').forEach(r=>{{if(!s){{r.style.display='';return}}r.style.display=Array.from(r.querySelectorAll('td')).some(c=>c.textContent.trim()===s)?'':'none'}})}}
</script></body></html>'''

    with open(output_path, 'w') as f:
        f.write(html)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="CVS Cluster Dashboard Generator")
    parser.add_argument("--input", "-i", help="Cluster data JSON file")
    parser.add_argument("--output", "-o", default="dashboard.html", help="Output HTML file")
    parser.add_argument("--serve", "-s", type=int, help="Start HTTP server on port")
    args = parser.parse_args()

    if args.serve:
        os.chdir(Path(args.output).parent if args.output != "dashboard.html" else Path.cwd())
        print(f"Serving at http://localhost:{args.serve}/")
        HTTPServer(("", args.serve), SimpleHTTPRequestHandler).serve_forever()
    elif args.input:
        with open(args.input) as f:
            data = json.load(f)
        out = generate_dashboard(data, args.output)
        print(f"Dashboard: {out}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
