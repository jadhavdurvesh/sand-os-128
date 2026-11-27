#!/usr/bin/env python3
"""Run Kernelloom examples on BOTH machines (Python reference and compiled C), then render the real output to PNG screenshots.
Output goes to docs/screenshots/. Needs gcc and Playwright (chromium). Nothing here is mocked: every line shown is captured output."""
import html, json, os, re, shutil, subprocess, sys, tempfile
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, root)
from veylith import disk
from tests.test_veylith import Kernelloom
read = lambda p: open(os.path.join(root, p)).read()
SCENES = [
 ("gate", "examples/gate.s", "Call gate: protected counter service", "A sealed GATE capability is the only way in. The client runs in capability mode and cannot touch the counter; each call is ccall + service body + cretn with no kernel trap."),
 ("gateiso", "examples/gateiso.s", "Isolated gate call: registers hidden and restored", "ccalx spills the caller's registers outside its aperture and clears them; the service reports what it could see (nothing), trashes its registers, and cretx restores the caller's."),
 ("gateswitch", "examples/gateswitch.s", "Gate calls survive context switches", "Two tasks call the same service, which yields mid-call. Each returns to its own caller because the return link is saved per task."),
 ("sigilforge", "examples/sigilforge.s", "Forged capability is stopped", "A made-up 128-bit value is not a capability: the MAC fails and the hardware raises CAPABILITY (cause 8). Exit 136 is the expected result."),
 ("sigil", "examples/sigil.s", "Capability handed to a worker", "A narrowed 128-bit capability travels as one register value to a worker that can reach memory only through it."),
]
def build_c(d):
    exe = os.path.join(d, "vvm")
    subprocess.run([shutil.which("gcc") or "cc", "-std=c11", "-O2", "-o", exe, os.path.join(root, "native/veylith-vm.c")], check=True, capture_output=True)
    return exe
def run_both(exe, d, ex):
    m = Kernelloom.boot(Kernelloom, ex); py = m.console.decode().rstrip()
    img = os.path.join(d, os.path.basename(ex) + ".img")
    open(img, "wb").write(disk.build(read("kernel/kernelloom.s"), read(ex)))
    c = subprocess.run([exe, img], capture_output=True, text=True)
    n = int(re.search(r"(\d+) Glyphs", c.stdout + c.stderr).group(1))
    return {"out": py, "glyphs": m.cycles, "exit": m.exit_code, "c_same": c.stdout.rstrip().replace("\r", "") == py and n == m.cycles}
CSS = """:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0b0e14;color:#d7dde8;font:15px/1.5 ui-monospace,Menlo,Consolas,monospace;padding:32px}
.card{max-width:980px;margin:0 auto;background:#121722;border:1px solid #243049;border-radius:14px;overflow:hidden}
.bar{display:flex;gap:8px;align-items:center;padding:12px 16px;background:#0f1420;border-bottom:1px solid #243049;color:#8a97ad;font-size:13px}
.dot{width:11px;height:11px;border-radius:50%;background:#2a3550}.t{padding:22px 24px}h1{font:600 22px system-ui,sans-serif;margin:0 0 6px;color:#fff}
p{font:15px/1.5 system-ui,sans-serif;color:#9fb0c8;margin:0 0 16px}pre{margin:0;background:#080b11;border:1px solid #1d2740;border-radius:10px;padding:16px;white-space:pre-wrap;word-break:break-all;color:#b8f5c8}
.cmd{color:#7aa2ff}.meta{display:flex;gap:12px;margin-top:16px;flex-wrap:wrap}.pill{padding:6px 12px;border-radius:999px;background:#1a2338;color:#cfe0ff;font-size:13px}
.ok{background:#12301f;color:#7ff0a8}.bar2{display:flex;align-items:center;gap:12px;margin:10px 0}.lab{width:230px;color:#b9c6dc;font-size:14px}.b{height:22px;border-radius:5px;background:#5b8cff;min-width:3px}.v{color:#fff;font-size:14px}"""
def page(body): return f"<!doctype html><meta charset=utf-8><style>{CSS}</style><body>{body}</body>"
def scene_html(ex, title, blurb, r):
    out = html.escape(r["out"])
    return page(f'<div class=card><div class=bar><i class=dot></i><i class=dot></i><i class=dot></i>&nbsp;Veylith 128-Native · Kernelloom</div><div class=t><h1>{html.escape(title)}</h1><p>{html.escape(blurb)}</p>'
        f'<pre><span class=cmd>$ python3 -m veylith boot {ex}</span>\n{out}</pre><div class=meta><span class=pill>{r["glyphs"]} Glyphs retired</span><span class=pill>exit code {r["exit"]}</span>'
        f'<span class="pill ok">C machine: identical output and Glyph count</span></div></div></div>' if r["c_same"] else "")
def bench_html(b):
    g = b["sigil_gate"]; rows = [("Gate call + return (empty service)", g["glyphs_per_gate_call_empty_service"]), ("Gate call + return (counter service)", g["glyphs_per_gate_call_counter_service"]),
        ("Null system call (kernel round trip)", g["glyphs_per_null_syscall_round_trip"]), ("Yield (context switch)", g["glyphs_per_yield_context_switch"])]
    top = max(v for _, v in rows)
    bars = "".join(f'<div class=bar2><span class=lab>{html.escape(k)}</span><div class=b style="width:{max(3, 560 * v / top):.0f}px"></div><span class=v>{v}</span></div>' for k, v in rows)
    return page(f'<div class=card><div class=bar><i class=dot></i><i class=dot></i><i class=dot></i>&nbsp;tools/bench.py</div><div class=t><h1>Cross-domain call cost (Glyphs)</h1><p>Measured on the Python reference machine; fewer is better. '
        f'The gate path skips the kernel entirely; the kernel figures are the cheapest possible kernel-mediated call. The gate service shares the register file (no clearing) and MAC latency is not modelled.</p>{bars}</div></div>')
def main():
    from playwright.sync_api import sync_playwright
    out = os.path.join(root, "docs/screenshots"); os.makedirs(out, exist_ok=True)
    bench = json.load(open(os.path.join(root, "docs/paper/evidence.json")))["bench"]
    pages = []
    with tempfile.TemporaryDirectory() as d:
        exe = build_c(d)
        for name, ex, title, blurb in SCENES:
            r = run_both(exe, d, ex); assert r["c_same"], ex; pages.append((name, scene_html(ex, title, blurb, r)))
    pages.append(("gate-cost", bench_html(bench)))
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page(viewport={"width": 1100, "height": 600}, device_scale_factor=2)
        for name, h in pages:
            pg.set_content(h); pg.locator(".card").screenshot(path=os.path.join(out, name + ".png")); print("wrote docs/screenshots/%s.png" % name)
        br.close()
if __name__ == "__main__": main()
