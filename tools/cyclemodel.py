#!/usr/bin/env python3
"""Cycle-model study of Sigil capability checks.

Six workloads with RUN-TIME indices (insertion sort, 8x8 matrix multiply, open-addressing hash table, byte checksum,
linked-list walk where the `next` field IS a Sigil capability, and a pointer-heavy tree-free worst case) are each run twice on
the Python reference machine: through raw loads/stores and through Sigil capabilities (indexed clqx/csqx/clbx/csbx).
Measured, not modelled: Glyph counts, capability uses, MAC computations with and without verified-register flags,
data-access address streams, registers written/touched per scheduler quantum.
Modelled (parametric, stated openly): MAC latency L, and a CHERI-style tag cache with miss penalty M. Every
modelled number is a function of those parameters; the tables print the whole range rather than one chosen value.
Output: docs/paper/cyclemodel.json."""
import json, os, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, root)
from veylith import asm
from veylith.machine import Machine

MASK = (1 << 128) - 1
LCG_A, LCG_C = 0x5851F42D4C957F2D14057B7EF767814F, 12345
SEED = 0x123456789ABCDEF0123456789ABCDEF
BASE = 0x10000
PRE_CAP = ["li v1, 0x77", "csrw ckey, v1", f"li v2, {BASE}", "li v3, %d" % (3 | 12 << 8 | 15 << 16), "cmint v5, v2, v3"]
PRE_RAW = ["li v1, 0x77", "csrw ckey, v1", f"li v2, {BASE}"]
LCG_INIT = [f"li v21, {SEED}", f"li v22, {LCG_A}"]


class Emit:
    """Emits the same algorithm through raw addressing or through indexed capability accesses."""
    def __init__(self, cap):
        self.cap = cap
        self.L = list(PRE_CAP if cap else PRE_RAW) + LCG_INIT
        self.n = 0

    def add(self, *lines):
        self.L.extend(lines)

    def label(self, p="l"):
        self.n += 1
        return f"{p}{self.n}"

    def ld(self, dst, off):                       # 128-bit load, byte offset in register `off`
        if self.cap:
            self.L.append(f"clqx {dst}, v5, {off}")
        else:
            self.L += [f"add v9, v2, {off}", f"lq {dst}, [v9 + 0]"]

    def st(self, src, off):
        if self.cap:
            self.L.append(f"csqx {src}, v5, {off}")
        else:
            self.L += [f"add v9, v2, {off}", f"sq [v9 + 0], {src}"]

    def ldb(self, dst, off):
        if self.cap:
            self.L.append(f"clbx {dst}, v5, {off}")
        else:
            self.L += [f"add v9, v2, {off}", f"lb {dst}, [v9 + 0]"]

    def stb(self, src, off):
        if self.cap:
            self.L.append(f"csbx {src}, v5, {off}")
        else:
            self.L += [f"add v9, v2, {off}", f"sb [v9 + 0], {src}"]

    def text(self):
        return "\n".join(self.L + ["halt"])


def lcg(e):
    e.add("mul v21, v21, v22", f"addi v21, v21, {LCG_C}")


# ---- workloads ------------------------------------------------------------------------------------------------------
def insertion_sort(cap, passes, n=64):
    e = Emit(cap); o, f, s = e.label("outer"), e.label("fill"), e.label("isort")
    e.add(f"li v20, {passes}", f"{o}:", "li v6, 0", f"{f}:"); lcg(e)
    e.add("shli v7, v6, 4"); e.st("v21", "v7")
    e.add("addi v6, v6, 1", f"li v8, {n}", f"bne v6, v8, {f}", "li v6, 1", f"{s}:", "shli v7, v6, 4"); e.ld("v10", "v7")
    inner, place = e.label("inner"), e.label("place")
    e.add("addi v11, v6, -1", f"{inner}:", f"blt v11, v0, {place}", "shli v12, v11, 4"); e.ld("v13", "v12")
    e.add(f"bgeu v10, v13, {place}", "addi v14, v12, 16"); e.st("v13", "v14")
    e.add("addi v11, v11, -1", f"jmp {inner}", f"{place}:", "addi v14, v11, 1", "shli v14, v14, 4"); e.st("v10", "v14")
    e.add("addi v6, v6, 1", f"li v8, {n}", f"bne v6, v8, {s}", "addi v20, v20, -1", f"bne v20, v0, {o}")
    return e.text()


def check_sort(m, n=64):
    v = [int.from_bytes(m.ram[BASE + 16 * i:BASE + 16 * i + 16], "little") for i in range(n)]
    return v == sorted(v)


def matmul(cap, passes):
    e = Emit(cap); o, fa, il, jl, kl = (e.label(x) for x in ("outer", "fill", "i", "j", "k"))
    e.add(f"li v20, {passes}", f"{o}:", "li v6, 0", f"{fa}:"); lcg(e)
    e.add("andi v23, v21, 0xFFFF", "shli v7, v6, 4"); e.st("v23", "v7")
    e.add("addi v6, v6, 1", "li v8, 128", f"bne v6, v8, {fa}", "li v6, 0", f"{il}:", "li v7, 0", f"{jl}:", "li v8, 0", "li v15, 0", f"{kl}:")
    e.add("shli v12, v6, 3", "add v12, v12, v8", "shli v12, v12, 4"); e.ld("v13", "v12")
    e.add("shli v14, v8, 3", "add v14, v14, v7", "shli v14, v14, 4", "addi v14, v14, 1024"); e.ld("v16", "v14")
    e.add("mul v13, v13, v16", "add v15, v15, v13", "addi v8, v8, 1", "li v17, 8", f"bne v8, v17, {kl}")
    e.add("shli v12, v6, 3", "add v12, v12, v7", "shli v12, v12, 4", "addi v12, v12, 2048"); e.st("v15", "v12")
    e.add("addi v7, v7, 1", f"bne v7, v17, {jl}", "addi v6, v6, 1", f"bne v6, v17, {il}", "addi v20, v20, -1", f"bne v20, v0, {o}")
    return e.text()


def check_matmul(m):
    rd = lambda i: int.from_bytes(m.ram[BASE + 16 * i:BASE + 16 * i + 16], "little")
    A, B = [rd(i) for i in range(64)], [rd(64 + i) for i in range(64)]
    return all(rd(128 + 8 * i + j) == sum(A[8 * i + k] * B[8 * k + j] for k in range(8)) & MASK for i in range(8) for j in range(8))


def hash_table(cap, passes, keys=192):
    e = Emit(cap); o, z, ins, probe, put, look, lp, hit, miss = (e.label(x) for x in ("outer", "z", "ins", "probe", "put", "look", "lp", "hit", "miss"))
    e.add(f"li v20, {passes}", "li v26, 0", f"li v24, {LCG_A ^ 0x1D1D1D1D1D1D1D1D}", f"{o}:", "li v6, 0", f"{z}:", "shli v7, v6, 4"); e.st("v0", "v7")
    e.add("addi v6, v6, 1", "li v8, 256", f"bne v6, v8, {z}", f"li v21, {SEED}", "li v6, 0", f"{ins}:"); lcg(e)
    e.add("ori v23, v21, 1", "mul v25, v23, v24", "shri v25, v25, 120", f"{probe}:", "shli v7, v25, 4"); e.ld("v10", "v7")
    e.add(f"beq v10, v0, {put}", "addi v25, v25, 1", "andi v25, v25, 255", f"jmp {probe}", f"{put}:"); e.st("v23", "v7")
    e.add("addi v6, v6, 1", f"li v8, {keys}", f"bne v6, v8, {ins}", f"li v21, {SEED}", "li v6, 0", f"{look}:"); lcg(e)
    e.add("ori v23, v21, 1", "mul v25, v23, v24", "shri v25, v25, 120", f"{lp}:", "shli v7, v25, 4"); e.ld("v10", "v7")
    e.add(f"beq v10, v23, {hit}", f"beq v10, v0, {miss}", "addi v25, v25, 1", "andi v25, v25, 255", f"jmp {lp}", f"{hit}:", "addi v26, v26, 1", f"{miss}:",
          "addi v6, v6, 1", f"li v8, {keys}", f"bne v6, v8, {look}", "addi v20, v20, -1", f"bne v20, v0, {o}")
    return e.text()


def byte_checksum(cap, passes, size=2048):
    e = Emit(cap); o, f, c = e.label("outer"), e.label("fill"), e.label("sum")
    e.add(f"li v20, {passes}", "li v30, 5", f"{o}:", "li v6, 0", f"{f}:"); lcg(e)
    e.stb("v21", "v6")
    e.add("addi v6, v6, 1", f"li v8, {size}", f"bne v6, v8, {f}", "li v6, 0", "li v15, 0", f"{c}:"); e.ldb("v10", "v6")
    e.add("add v15, v15, v10", "rol v15, v15, v30", "addi v6, v6, 1", f"bne v6, v8, {c}", "addi v20, v20, -1", f"bne v20, v0, {o}")
    return e.text()


def check_checksum(m, size=2048):
    x, s, acc = SEED, 0, 0
    for _ in range(size):
        x = (x * LCG_A + LCG_C) & MASK
        acc = (acc + (x & 255)) & MASK
        acc = ((acc << 5) | (acc >> 123)) & MASK
    return m.v[15] == acc


def list_walk(cap, passes, nodes=128):
    """Nodes are 32 bytes: payload at +0, `next` at +16. In the capability build `next` is a Sigil capability for the next
    node, so every hop loads a register that is NOT yet verified (worst case for the verified flag, one MAC per node)."""
    L = ["li v1, 0x77", "csrw ckey, v1", f"li v2, {BASE}", "li v3, %d" % (1 | 5 << 8), "li v6, 0", "build:", "shli v7, v6, 5", "add v7, v7, v2",
         "addi v8, v6, 1", "sq [v7 + 0], v8", "addi v9, v6, 37", f"andi v9, v9, {nodes - 1}", "shli v9, v9, 5", "add v9, v9, v2"]
    L += ["cmint v10, v9, v3", "sq [v7 + 16], v10"] if cap else ["sq [v7 + 16], v9"]
    L += ["addi v6, v6, 1", f"li v11, {nodes}", "bne v6, v11, build", f"li v20, {passes}", "li v15, 0", "outer:", "li v6, 0",
          "cmint v5, v2, v3" if cap else "mv v5, v2", "walk:"]
    L += ["clq v7, [v5 + 0]", "add v15, v15, v7", "clq v5, [v5 + 16]"] if cap else ["lq v7, [v5 + 0]", "add v15, v15, v7", "lq v5, [v5 + 16]"]
    L += ["addi v6, v6, 1", f"li v11, {nodes}", "bne v6, v11, walk", "addi v20, v20, -1", "bne v20, v0, outer", "halt"]
    return "\n".join(L)


WORKLOADS = {
    "insertion sort (64 x 128-bit)": (insertion_sort, 6, lambda m, p: check_sort(m)),
    "matrix multiply (8x8, 128-bit)": (matmul, 3, lambda m, p: check_matmul(m)),
    "hash table (192 keys / 256 slots)": (hash_table, 6, lambda m, p: m.v[26] == 192 * p),
    "byte checksum (2 KiB)": (byte_checksum, 4, lambda m, p: check_checksum(m)),
    "linked list (cap in node)": (list_walk, 40, lambda m, p: m.v[15] == p * 8256),
    "large list (16384 nodes, 512 KiB)": (lambda cap, p: list_walk(cap, p, 16384), 2, lambda m, p: m.v[15] == p * (16384 * 16385 // 2)),
}


# ---- measurement ----------------------------------------------------------------------------------------------------
def execute(src, flags=True, log=False, quantum=None, limit=20_000_000):
    m = Machine(1 << 20); m.use_vok = flags; m.access_log = [] if log else None
    m.load(asm.assemble(src))
    quanta = []
    if quantum is None:
        m.run(limit)
    else:
        m.dirty = m.touched = 0
        while not m.halted and m.cycles < limit:
            m.step()
            if m.cycles % quantum == 0:
                quanta.append((bin(m.dirty).count("1"), bin(m.touched & ~1).count("1"))); m.dirty = m.touched = 0
    assert m.stop_reason == "halt", m.stop_reason
    return m, quanta


def tag_misses(log, lines, line_bytes=8192):
    """Fully associative LRU cache of tag lines. One 64-byte tag line (512 tags of 1 bit per 16-byte capability granule) covers
    8 KiB of data. Every data load and store consults it, as in a CHERI tag controller."""
    cache, misses = [], 0
    for _, addr, size in log:
        for line in {addr // line_bytes, (addr + size - 1) // line_bytes}:
            if line in cache:
                cache.remove(line)
            else:
                misses += 1
                if len(cache) >= lines:
                    cache.pop(0)
            cache.append(line)
    return misses


def study(quantum=3000):
    rows = []
    for name, (gen, passes, check) in WORKLOADS.items():
        raw, quanta = execute(gen(False, passes), quantum=quantum)
        cap_on, _ = execute(gen(True, passes), flags=True, log=True)
        cap_off, _ = execute(gen(True, passes), flags=False)
        assert check(raw, passes) and check(cap_on, passes) and check(cap_off, passes), name
        assert cap_on.cycles == cap_off.cycles
        uses, macs_on, macs_off = cap_on.cstats["uses"], cap_on.cstats["macs"], cap_off.cstats["macs"]
        assert macs_off == uses
        log = cap_on.access_log
        d = [q[0] for q in quanta] or [0]; t = [q[1] for q in quanta] or [0]
        rows.append({"workload": name, "glyphs_raw": raw.cycles, "glyphs_cap": cap_on.cycles, "cap_uses": uses, "macs_flags": macs_on,
                     "macs_noflags": macs_off, "data_accesses": len(log), "footprint_bytes": len({a // 16 for _, a, _ in log}) * 16,
                     "tag_misses": {str(s): tag_misses(log, s) for s in (1, 2, 4, 16, 64)},
                     "quanta": len(quanta), "dirty_mean": round(sum(d) / len(d), 1), "dirty_max": max(d),
                     "touched_mean": round(sum(t) / len(t), 1), "touched_max": max(t)})
    return rows


def model(rows, Ls=(1, 2, 4, 8, 12), Ms=(10, 30, 100)):
    """Percent slowdown relative to the same capability code with free checks (L = 0, no tag cost)."""
    out = []
    for r in rows:
        g = r["glyphs_cap"]
        out.append({"workload": r["workload"],
                    "sigil_flags": {str(L): round(100 * L * r["macs_flags"] / g, 2) for L in Ls},
                    "sigil_noflags": {str(L): round(100 * L * r["macs_noflags"] / g, 2) for L in Ls},
                    "tagcache_4lines": {str(M): round(100 * M * r["tag_misses"]["4"] / g, 2) for M in Ms},
                    "tagcache_64lines": {str(M): round(100 * M * r["tag_misses"]["64"] / g, 2) for M in Ms},
                    "tagcache_1line": {str(M): round(100 * M * r["tag_misses"]["1"] / g, 2) for M in Ms}})
    return out


def main():
    rows = study(); mod = model(rows)
    res = {"quantum_glyphs": 3000, "registers": 128, "rows": rows, "model": mod}
    json.dump(res, open(os.path.join(root, "docs/paper/cyclemodel.json"), "w"), indent=1)
    for r, mo in zip(rows, mod):
        print(f"{r['workload']:36s} raw {r['glyphs_raw']:>8} cap {r['glyphs_cap']:>8} uses {r['cap_uses']:>7} macs {r['macs_flags']:>6}/{r['macs_noflags']:>7}"
              f"  tagmiss {r['tag_misses']['4']:>3}  dirty {r['dirty_mean']}/{r['dirty_max']} touched {r['touched_mean']}/{r['touched_max']}  L=4: {mo['sigil_flags']['4']}% vs {mo['sigil_noflags']['4']}%")


if __name__ == "__main__":
    main()
