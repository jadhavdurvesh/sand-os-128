#!/usr/bin/env python3
"""Reproducible measurements for the SAND-128 / Veylith paper. Counts are retired Glyphs on the deterministic reference
machine (not wall-clock time). Usage: python3 tools/bench.py [--json docs/paper/results.json]"""
import argparse, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from veylith import asm, isa
from veylith.machine import Machine

KERNEL = open("kernel/kernelloom.s").read()


def boot(user_src, steps=20_000_000, trace=False):
    m = Machine(1 << 20)
    if trace:
        m.trace = []
    m.load(asm.assemble(KERNEL)); m.load(asm.assemble(user_src), set_entry=False); m.run(steps)
    assert m.stop_reason == "halt" and m.exit_code == 0, (m.stop_reason, m.exit_code)
    return m


def raw(src, steps=5_000_000):
    m = Machine(1 << 20); m.load(asm.assemble(src)); m.run(steps)
    assert m.stop_reason == "halt", m.stop_reason
    return m


def factorial_native(n):
    return f"""li v4, 1
li v5, 1
li v6, {n}
loop:
mul v4, v4, v5
addi v5, v5, 1
bge v6, v5, loop
mv v7, v4
halt"""


def factorial_limbs(n):
    """n! using only 64-bit limbs (lo, hi), i.e. what a 64-bit-register machine has to do for a 128-bit result."""
    return f"""li v4, 1
li v3, 0
li v5, 1
li v6, {n}
li v9, 0xFFFFFFFFFFFFFFFF
loop:
mul v10, v4, v5
and v4, v10, v9
shri v11, v10, 64
mul v12, v3, v5
add v12, v12, v11
and v3, v12, v9
addi v5, v5, 1
bge v6, v5, loop
shli v7, v3, 64
or v7, v7, v4
halt"""


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json"); a = ap.parse_args()
    R = {}
    # 1. 128-bit arithmetic versus 64-bit-limb emulation
    n = 34
    nat, lim = raw(factorial_native(n)), raw(factorial_limbs(n))
    assert nat.v[7] == lim.v[7]
    R["factorial_34"] = {"native128_glyphs": nat.cycles, "limb64_glyphs": lim.cycles, "ratio": round(lim.cycles / nat.cycles, 2), "same_result": True}
    # 2. constant materialisation
    R["constants"] = {"li_small_glyphs": 1, "li_full128_glyphs": 2, "immediate_bits": isa.IMM_BITS, "bytes_per_glyph": isa.GLYPH_BYTES}
    # 3. syscall round trip
    k = 1000
    sc = f"""li v9, {k}
l:
li v1, 3
sys 0
addi v9, v9, -1
bne v9, v0, l
li v1, 2
li v2, 0
sys 0"""
    base = f"""li v9, {k}
l:
li v1, 3
addi v9, v9, -1
bne v9, v0, l
li v1, 2
li v2, 0
sys 0"""
    R["syscall_getpid"] = {"extra_glyphs_per_call": round((boot(".org 0x10000\n" + sc).cycles - boot(".org 0x10000\n" + base).cycles) / k, 1)}
    # 4. context switch cost (yield) and preemption cost
    yl = 500
    yielder = f""".org 0x10000
li sp, 0x1F000
la v2, other
li v3, 0x1E000
li v4, 0
li v1, 6
sys 0
li v9, {yl}
a:
li v1, 5
sys 0
addi v9, v9, -1
bne v9, v0, a
li v1, 2
li v2, 0
sys 0
other:
li v9, {yl}
b:
li v1, 5
sys 0
addi v9, v9, -1
bne v9, v0, b
li v1, 2
li v2, 0
sys 0"""
    noyield = yielder.replace("li v1, 5\nsys 0\n", "")
    y, ny = boot(yielder), boot(noyield)
    R["yield_context_switch"] = {"extra_glyphs_per_yield": round((y.cycles - ny.cycles) / (2 * yl), 1), "register_frame_bytes": 129 * 16, "quads_copied_per_switch": 2 * 129}
    m = boot(open("examples/preempt.s").read(), trace=True)
    first_user = next(i for i, r in enumerate(m.trace) if int(r["pc"], 16) >= 0x10000)
    runs = {}                                        # kernel Glyphs executed between each trap and the next return to user code
    t = m.trace
    for i in range(first_user, len(t)):
        if t[i]["trap"]:
            j = i + 1
            while j < len(t) and int(t[j]["pc"], 16) < 0x10000 and not (t[j]["op"] == "halt"):
                j += 1
            runs.setdefault(t[i]["trap"]["cause"], []).append(j - i - 1)
    avg = lambda v: round(sum(v) / len(v), 1) if v else None
    R["preemption"] = {"total_glyphs": m.cycles, "boot_glyphs_before_first_user_glyph": first_user, "timer_traps": len(runs.get("TIMER", [])),
                       "kernel_glyphs_per_timer_trap": avg(runs.get("TIMER", [])), "quantum_glyphs": 3000,
                       "overhead_fraction": round(avg(runs.get("TIMER", [])) / (3000 + avg(runs.get("TIMER", []))), 3)}
    # 5. image sizes
    kb = asm.assemble(KERNEL)
    R["images"] = {"kernel_image_bytes": len(kb), "kernel_syscalls": 9, "veylith_opcodes": len(isa.BY_NAME)}
    txt = json.dumps(R, indent=2)
    print(txt)
    if a.json:
        with open(a.json, "w") as f:
            f.write(txt + "\n")


if __name__ == "__main__":
    main()
