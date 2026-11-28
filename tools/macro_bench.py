#!/usr/bin/env python3
"""Larger benchmarks for the capability study (footprints up to ~300 KiB, up to ~10^6 instructions each).

  * five compiler-generated programs (tools/vcc.py): merge sort, sparse matrix-vector product (CSR), breadth-first search,
    longest common subsequence (dynamic programming), and a stencil sweep;
  * one pointer-rich program: a binary search tree whose child links ARE Sigil capabilities, built on the host and probed by
    4096 lookups, so every hop loads an unverified capability register from memory.
Every result is checked against ordinary Python. Output: docs/paper/macro.json."""
import json, os, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, root); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compiled_study as cs, cyclemodel
from compiled_study import rnd
from veylith import asm
from veylith.machine import Machine, sigil_make

N_SORT, N_ROWS, NNZ, N_BFS, M_BFS, LCS = 2048, 512, 4096, 1024, 4096, 96
def csr(rows, nnz, ncols, seed):
    cols = rnd(nnz, ncols, seed); per = nnz // rows
    return list(range(0, nnz + 1, per))[:rows + 1], cols
xadj, col = csr(N_ROWS, NNZ, N_ROWS, 11)
bfs_adj = rnd(M_BFS, N_BFS, 5); bfs_x = list(range(0, M_BFS + 1, M_BFS // N_BFS))[:N_BFS + 1]
PROGRAMS = {
    "merge sort (2048)": ("""
n = 2048
w = 1
while w < n:
    i = 0
    while i < n:
        mid = i + w
        hi = i + 2 * w
        l = i
        r = mid
        k = i
        while k < hi:
            if l < mid:
                if r < hi:
                    x = a[l]
                    y = a[r]
                    if x <= y:
                        b[k] = x
                        l += 1
                    else:
                        b[k] = y
                        r += 1
                else:
                    b[k] = a[l]
                    l += 1
            else:
                b[k] = a[r]
                r += 1
            k += 1
        i += 2 * w
    for j in range(n):
        a[j] = b[j]
    w = w * 2
""", {"a": (N_SORT, rnd(N_SORT, 1 << 30, 21)), "b": (N_SORT, [])}),
    "sparse mat-vec, CSR (512 rows, 4096 nnz, x4)": ("""
for rep in range(4):
    for i in range(512):
        s = 0
        for k in range(xa[i], xa[i + 1]):
            s += val[k] * x[cl[k]]
        y[i] = s
""", {"xa": (len(xadj), xadj), "cl": (NNZ, col), "val": (NNZ, rnd(NNZ, 9, 12)), "x": (N_ROWS, rnd(N_ROWS, 9, 13)), "y": (N_ROWS, [])}),
    "breadth-first search (1024 nodes, 4096 edges)": ("""
for v in range(1024):
    d[v] = 99999
d[0] = 0
q[0] = 0
head = 0
tail = 1
while head < tail:
    u = q[head]
    head += 1
    for e in range(xa[u], xa[u + 1]):
        v = adj[e]
        if d[v] == 99999:
            d[v] = d[u] + 1
            q[tail] = v
            tail += 1
""", {"xa": (len(bfs_x), bfs_x), "adj": (M_BFS, bfs_adj), "d": (N_BFS, []), "q": (N_BFS, [])}),
    "longest common subsequence (96 x 96)": ("""
for i in range(1, 97):
    for j in range(1, 97):
        if sa[i - 1] == sb[j - 1]:
            t[i * 97 + j] = t[(i - 1) * 97 + j - 1] + 1
        else:
            u = t[(i - 1) * 97 + j]
            v = t[i * 97 + j - 1]
            if u > v:
                t[i * 97 + j] = u
            else:
                t[i * 97 + j] = v
best = t[96 * 97 + 96]
""", {"sa": (96, rnd(96, 4, 31)), "sb": (96, rnd(96, 4, 32)), "t": (97 * 97, [])}),
    "3-point stencil (4096 cells, 6 sweeps)": ("""
for sweep in range(6):
    for i in range(1, 4095):
        o[i] = (g[i - 1] + 2 * g[i] + g[i + 1]) // 4
    for i in range(1, 4095):
        g[i] = o[i]
""", {"g": (4096, rnd(4096, 1000, 41)), "o": (4096, [])}),
}

# ---- binary search tree with capability links -----------------------------------------------------------------------
NODE_BASE, QBASE, NODES, NQ, KEY = 0x30000, 0x70000, 4096, 4096, 0x77
NODE_PERMS, NODE_SHAPE = 1, (4 << 8) | 2          # 48-byte node = 3 << 4


def bst_build(cap):
    keys = rnd(NODES, 1 << 40, 51); keys = list(dict.fromkeys(keys)); n = len(keys)
    left, right = [None] * n, [None] * n
    for i in range(1, n):
        c = 0
        while True:
            side = left if keys[i] < keys[c] else right
            if side[c] is None:
                side[c] = i; break
            c = side[c]
    mem = {}
    link = lambda i: 0 if i is None else (sigil_make(KEY, NODE_BASE + 48 * i, NODE_PERMS, NODE_SHAPE) if cap else NODE_BASE + 48 * i)
    for i in range(n):
        a = NODE_BASE + 48 * i
        mem[a] = keys[i]; mem[a + 16] = link(left[i]); mem[a + 32] = link(right[i])
    qs = [keys[(i * 7) % n] if i % 2 == 0 else rnd(1, 1 << 40, 900 + i)[0] for i in range(NQ)]
    expect = sum(1 for q in qs if q in set(keys))
    for i, q in enumerate(qs):
        mem[QBASE + 16 * i] = q
    return mem, expect, n


def bst_program(cap):
    pre = ["li v1, 0x77", "csrw ckey, v1", f"li v2, {NODE_BASE}", "li v3, %d" % (NODE_PERMS | NODE_SHAPE << 8 if False else NODE_PERMS | (4 << 8) | (2 << 16)),
           f"li v4, {QBASE}", "li v13, %d" % (3 | 8 << 8 | 255 << 16)]
    pre += ["cmint v5, v2, v3", "cmint v6, v4, v13"] if cap else ["mv v5, v2", "mv v6, v4"]
    ld_q = ["shli v7, v20, 4", "clqx v10, v6, v7"] if cap else ["shli v7, v20, 4", "add v8, v6, v7", "lq v10, [v8 + 0]"]
    ld = lambda d, off: f"{'clq' if cap else 'lq'} {d}, [v11 + {off}]"
    body = ["li v20, 0", "li v26, 0", "qloop:"] + ld_q + ["mv v11, v5", "walk:", "beq v11, v0, done", ld("v12", 0), "beq v12, v10, hit", "bltu v10, v12, goleft",
            ld("v11", 32), "jmp walk", "goleft:", ld("v11", 16), "jmp walk", "hit:", "addi v26, v26, 1", "done:", "addi v20, v20, 1", f"li v21, {NQ}", "bne v20, v21, qloop", "halt"]
    return "\n".join(pre + body)


def run_bst(cap, flags=True, log=False, quantum=None):
    mem, expect, _ = bst_build(cap)
    m = Machine(1 << 20); m.use_vok = flags; m.access_log = [] if log else None
    m.load(asm.assemble(bst_program(cap)))
    for a, v in mem.items():
        m.ram[a:a + 16] = v.to_bytes(16, "little")
    quanta = []
    if quantum:
        m.dirty = m.touched = 0
        while not m.halted and m.cycles < 40_000_000:
            m.step()
            if m.cycles % quantum == 0:
                quanta.append((bin(m.dirty).count("1"), bin(m.touched & ~1).count("1"))); m.dirty = m.touched = 0
    else:
        m.run(40_000_000)
    assert m.stop_reason == "halt" and m.v[26] == expect, (m.stop_reason, m.v[26], expect)
    return m, quanta


def row(name, raw, quanta, on, off, extra=None):
    log = on.access_log; d = [q[0] for q in quanta] or [0]
    r = {"workload": name, "glyphs_raw": raw.cycles, "glyphs_cap": on.cycles, "cap_uses": on.cstats["uses"], "macs_flags": on.cstats["macs"],
         "macs_noflags": off.cstats["macs"], "data_accesses": len(log), "footprint_bytes": len({a // 16 for _, a, _ in log}) * 16,
         "tag_misses": {str(s): cyclemodel.tag_misses(log, s) for s in (1, 2, 4, 16, 64)},
         "quanta": len(quanta), "dirty_mean": round(sum(d) / len(d), 1), "dirty_max": max(d)}
    assert on.cycles == off.cycles
    return r


def study():
    rows = []
    for name, (src, arrays) in PROGRAMS.items():
        raw, comp, quanta, _ = cs.one(src, arrays, False, quantum=3000)
        on, comp, _, _ = cs.one(src, arrays, True, True, log=True)
        off, _, _, _ = cs.one(src, arrays, True, False)
        for m in (raw, on, off):
            cs.check(m, comp, src, arrays)
        rows.append(row(name, raw, quanta, on, off)); print(rows[-1]["workload"], rows[-1]["glyphs_cap"], rows[-1]["cap_uses"], rows[-1]["macs_flags"], flush=True)
    raw, quanta = run_bst(False, quantum=3000); on, _ = run_bst(True, True, log=True); off, _ = run_bst(True, False)
    rows.append(row("binary search tree (4096 nodes, capability links)", raw, quanta, on, off))
    print(rows[-1]["workload"], rows[-1]["glyphs_cap"], rows[-1]["cap_uses"], rows[-1]["macs_flags"], flush=True)
    return rows


def main():
    rows = study()
    json.dump({"rows": rows, "model": cyclemodel.model(rows)}, open(os.path.join(root, "docs/paper/macro.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
