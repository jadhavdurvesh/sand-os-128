#!/usr/bin/env python3
"""Run compiler-generated programs (tools/vcc.py) through raw and Sigil back ends and measure capability behaviour.
Every program's final variables and arrays are checked against ordinary Python execution of the same source.
Output: docs/paper/compiled.json."""
import json, os, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, root); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vcc, cyclemodel
from veylith import asm
from veylith.machine import Machine


def rnd(n, mod, seed=7):
    x, out = seed, []
    for _ in range(n):
        x = (x * 6364136223846793005 + 1442695040888963407) & (1 << 64) - 1
        out.append((x >> 33) % mod)
    return out


PROGRAMS = {
    "sieve (n=1500)": ("""
n = 1500
i = 2
while i * i < n:
    if p[i] == 0:
        j = i * i
        while j < n:
            p[j] = 1
            j += i
    i += 1
count = 0
for k in range(2, n):
    if p[k] == 0:
        count += 1
""", {"p": (1500, [])}),
    "bubble sort (48)": ("""
n = 48
for i in range(n):
    for j in range(n - 1 - i):
        x = a[j]
        y = a[j + 1]
        if x > y:
            a[j] = y
            a[j + 1] = x
""", {"a": (48, rnd(48, 1000))}),
    "matrix multiply (6x6)": ("""
for i in range(6):
    for j in range(6):
        s = 0
        for k in range(6):
            s += a[i * 6 + k] * b[k * 6 + j]
        c[i * 6 + j] = s
""", {"a": (36, rnd(36, 50, 1)), "b": (36, rnd(36, 50, 2)), "c": (36, [])}),
    "histogram (1024 -> 16 bins)": ("""
for i in range(1024):
    v = d[i] % 16
    h[v] = h[v] + 1
""", {"d": (1024, rnd(1024, 4096)), "h": (16, [])}),
    "binary search (200 lookups)": ("""
found = 0
for q in range(200):
    key = k[q]
    lo = 0
    hi = 256
    while lo < hi:
        mid = (lo + hi) // 2
        if s[mid] < key:
            lo = mid + 1
        else:
            hi = mid
    if lo < 256:
        if s[lo] == key:
            found += 1
""", {"s": (256, sorted(rnd(256, 100000))), "k": (200, rnd(200, 100000, 3)[:100] + [sorted(rnd(256, 100000))[i] for i in range(0, 200, 2)])}),
    "knapsack DP (30 items, cap 120)": ("""
for i in range(30):
    w = wt[i]
    v = val[i]
    c = 120
    while c >= w:
        t = dp[c - w] + v
        if t > dp[c]:
            dp[c] = t
        c -= 1
best = dp[120]
""", {"wt": (30, [x + 1 for x in rnd(30, 30)]), "val": (30, rnd(30, 100)), "dp": (121, [])}),
}


def one(src, arrays, cap, flags=True, log=False, quantum=None):
    text, comp = vcc.compile_program(src, arrays, cap)
    m = Machine(1 << 20); m.use_vok = flags; m.access_log = [] if log else None
    m.load(asm.assemble(text))
    for name, (n, init) in arrays.items():
        a = comp.layout[name][1]
        for i, v in enumerate(init):
            m.ram[a + 16 * i:a + 16 * i + 16] = v.to_bytes(16, "little")
    quanta = []
    if quantum:
        m.dirty = m.touched = 0
        while not m.halted and m.cycles < 5_000_000:
            m.step()
            if m.cycles % quantum == 0:
                quanta.append((bin(m.dirty).count("1"), bin(m.touched & ~1).count("1"))); m.dirty = m.touched = 0
    else:
        m.run(5_000_000)
    assert m.stop_reason == "halt", m.stop_reason
    return m, comp, quanta, len(text.splitlines())


def check(m, comp, src, arrays):
    import ast
    ref = vcc.reference(src, arrays)
    loopvars = {n.target.id for n in ast.walk(ast.parse(src)) if isinstance(n, ast.For)}      # range() leaves the index differently
    for name, (n, _) in arrays.items():
        a = comp.layout[name][1]
        got = [int.from_bytes(m.ram[a + 16 * i:a + 16 * i + 16], "little") for i in range(n)]
        assert got == ref[name], f"array {name} differs"
    for var, reg in comp.vars.items():
        if var in ref and var not in loopvars and not var.startswith("__") and not isinstance(ref[var], list):
            assert m.v[reg] == ref[var], f"variable {var}: {m.v[reg]} != {ref[var]}"


def study():
    rows = []
    for name, (src, arrays) in PROGRAMS.items():
        raw, comp, quanta, nlines = one(src, arrays, False, quantum=3000)
        on, comp, _, _ = one(src, arrays, True, True, log=True)
        off, _, _, _ = one(src, arrays, True, False)
        for m in (raw, on, off):
            check(m, comp, src, arrays)
        log = on.access_log
        d = [q[0] for q in quanta] or [0]
        rows.append({"workload": name, "asm_lines": nlines, "glyphs_raw": raw.cycles, "glyphs_cap": on.cycles, "cap_uses": on.cstats["uses"],
                     "macs_flags": on.cstats["macs"], "macs_noflags": off.cstats["macs"], "data_accesses": len(log),
                     "footprint_bytes": len({a // 16 for _, a, _ in log}) * 16,
                     "tag_misses": {str(s): cyclemodel.tag_misses(log, s) for s in (1, 2, 4, 16, 64)},
                     "quanta": len(quanta), "dirty_mean": round(sum(d) / len(d), 1), "dirty_max": max(d)})
    return rows


def main():
    rows = study()
    json.dump({"rows": rows, "model": cyclemodel.model(rows)}, open(os.path.join(root, "docs/paper/compiled.json"), "w"), indent=1)
    for r in rows:
        print(f"{r['workload']:34s} raw {r['glyphs_raw']:>7} cap {r['glyphs_cap']:>7} uses {r['cap_uses']:>6} macs {r['macs_flags']}/{r['macs_noflags']} "
              f"tagmiss {r['tag_misses']['4']} dirty {r['dirty_mean']}/{r['dirty_max']}")


if __name__ == "__main__":
    main()
