#!/usr/bin/env python3
"""Collect REAL run data for the Sigil Lab page: single-step traces of gate calls, capability tamper results, example output and
benchmark numbers. Everything comes from the emulator; nothing is hand-written except the commentary strings."""
import json, os, re, subprocess, shutil, sys, tempfile
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, root)
from veylith import asm, disk
from veylith.machine import Machine, sigil_make, sigil_parse, sigil_mac
from tests.test_veylith import Kernelloom
KEY = 0x77
SHOW = [1, 2, 6, 9, 10, 13, 14]
def scenario(call, ret, title):
    src = f"""
la v120, handler
csrw tvec, v120
li v1, 0x4000
csrw abase, v1
csrw tpc, v1
li v1, 0x1000
csrw alim, v1
li v1, 1
csrw tpriv, v1
li v1, {KEY}
csrw ckey, v1
li v2, 0x4800
li v3, {15 | 8 << 8}
cmint v4, v2, v3
cseal v5, v4
li v1, 0x6000
csrw cstack, v1
tret
.org 0x4000
li v9, 0x99
li v10, 0x77
li v1, 3
li v2, 4
{call} v6, v5
mv v11, v1
sys 1
.org 0x4800
mv v13, v10
mv v14, v9
add v1, v1, v2
li v10, 0xBAD
{ret}
handler:
halt
"""
    blob = asm.assemble(src); m = Machine(1 << 16); m.load(blob)
    steps = []; started = False
    for _ in range(400):
        pc = m.pc
        if pc == 0x4000: started = True
        if started:
            word = int.from_bytes(m.ram[pc:pc + 16], "little")
            text = asm.disassemble_word(word, pc)
            text = re.sub(r"^ldk (v\d+), (\d+)$", lambda g: f"li {g.group(1)}, {hex(int(g.group(2)))}", text.strip())
            text = re.sub(r"^addi (v\d+), (v\d+), 0$", r"mv \1, \2", text)
            steps.append({"pc": pc, "asm": text.strip(), "domain": "service" if pc >= 0x4800 else "caller", "priv": m.priv,
                          "clink": hex(m.csr[13]) if m.csr[13] else "0", "regs": {f"v{i}": hex(m.v[i]) for i in SHOW}})
        if not m.step(): break
        if started and m.pc < 0x4000: break
    # state after each executed step is what the next record shows; append the final state
    cut = next(i for i, x in enumerate(steps) if x["asm"].startswith("sys"))
    steps = steps[:cut + 1]
    steps.append({"pc": m.pc, "asm": "(trap: SYSCALL, back in the kernel)", "domain": "kernel", "priv": m.priv, "clink": hex(m.csr[13]) if m.csr[13] else "0",
                  "regs": {f"v{i}": hex(m.v[i]) for i in SHOW}})
    return {"title": title, "steps": steps}
def examples():
    out = {}
    with tempfile.TemporaryDirectory() as d:
        exe = os.path.join(d, "vvm")
        subprocess.run([shutil.which("gcc") or "cc", "-std=c11", "-O2", "-o", exe, os.path.join(root, "native/veylith-vm.c")], check=True, capture_output=True)
        for ex in ("gate", "gateswitch", "gateiso", "sigil", "sigilforge", "sigilraw"):
            m = Kernelloom.boot(Kernelloom, f"examples/{ex}.s"); txt = m.console.decode().rstrip()
            img = os.path.join(d, ex + ".img"); open(img, "wb").write(disk.build(open(os.path.join(root, "kernel/kernelloom.s")).read(), open(os.path.join(root, f"examples/{ex}.s")).read()))
            c = subprocess.run([exe, img], capture_output=True, text=True)
            out[ex] = {"console": txt, "glyphs": m.cycles, "exit": m.exit_code, "c_machine_identical": c.stdout.rstrip().replace("\r", "") == txt and f"{m.cycles} Glyphs" in c.stdout + c.stderr,
                       "source": open(os.path.join(root, f"examples/{ex}.s")).read()}
    return out
def inspector():
    cap = sigil_make(0x1234567890ABCDEF1234567890ABCDEF, 0x9000, 7, (4 << 8) | 24)
    key = 0x1234567890ABCDEF1234567890ABCDEF
    flips = [sigil_parse(key, cap ^ (1 << b)) is not None for b in range(128)]
    return {"key": hex(key), "cap": hex(cap), "region": [0x9000, 400], "valid": sigil_parse(key, cap) is not None, "tampered_bits_accepted": sum(flips)}
def main():
    ev = json.load(open(os.path.join(root, "docs/paper/evidence.json")))
    data = {"scenarios": {"isolated": scenario("ccalx", "cretx", "Isolated gate call (ccalx / cretx)"), "shared": scenario("ccall", "cretn", "Shared-register gate call (ccall / cretn)")},
            "examples": examples(), "inspector": inspector(), "bench": ev["bench"]["sigil_gate"], "unit_tests": ev["unit"]["tests"], "fuzz": ev["differential"]}
    json.dump(data, open(os.path.join(root, "web/sigil-lab-data.json"), "w"), indent=1); print("steps", {k: len(v["steps"]) for k, v in data["scenarios"].items()}, data["inspector"]["tampered_bits_accepted"])
if __name__ == "__main__": main()
