#!/usr/bin/env python3
"""A small realistic workload run twice: through raw loads/stores and through Sigil capabilities.
16-element odd-even merge sorting network over 128-bit values (every compare-exchange index is a compile-time constant, which
matters: capability loads take an immediate offset only, so array code with run-time indices is NOT expressible without extra
instructions; see docs/19). Glyph counts are identical per access by construction in this model, so the useful output is a
SENSITIVITY table: if a capability access costs k extra cycles (MAC check), how much slower does the workload get?"""
import json, os, random, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, root)
from veylith import asm
from veylith.machine import Machine
N = 16
def network(n):
    pairs = []
    def merge(lo, hi, r):
        step = r * 2
        if step < hi - lo:
            merge(lo, hi, step); merge(lo + r, hi, step)
            pairs.extend((i, i + r) for i in range(lo + r, hi - r, step))
        else:
            pairs.append((lo, lo + r))
    def sort(lo, hi):
        if hi - lo >= 1:
            mid = lo + (hi - lo) // 2
            sort(lo, mid); sort(mid + 1, hi); merge(lo, hi, 1)
    sort(0, n - 1)
    return pairs
PAIRS = network(N)
def build(cap, arrays):
    ld, st, base = ("clq", "csq", "v5") if cap else ("lq", "sq", "v2")
    L = ["li v1, 0x77", "csrw ckey, v1", "li v2, 0x9000", "li v3, %d" % (3 | 8 << 8), "cmint v5, v2, v3",
         "li v20, %d" % arrays, "li v21, 0x123456789ABCDEF0123456789ABCDEF", "li v22, 0x5851F42D4C957F2D14057B7EF767814F", "outer:"]
    for i in range(N):
        L += ["mul v21, v21, v22", "addi v21, v21, 12345", "sq [v2 + %d], v21" % (16 * i)]
    for n, (i, j) in enumerate(PAIRS):
        L += [f"{ld} v10, [{base} + {16 * i}]", f"{ld} v11, [{base} + {16 * j}]", f"bgeu v11, v10, skip{n}",
              f"{st} [{base} + {16 * i}], v11", f"{st} [{base} + {16 * j}], v10", f"skip{n}:"]
    L += ["addi v20, v20, -1", "bne v20, v0, outer", "halt"]
    return "\n".join(L)
def run(src, arrays):
    m = Machine(1 << 20); m.load(asm.assemble(src)); m.run(5_000_000)
    assert m.stop_reason == "halt", m.stop_reason
    vals = [int.from_bytes(m.ram[0x9000 + 16 * i:0x9000 + 16 * i + 16], "little") for i in range(N)]
    return m, vals
def main():
    arrays = 40
    mr, vr = run(build(False, arrays), arrays); mc, vc = run(build(True, arrays), arrays)
    assert vr == sorted(vr) and vc == sorted(vc) and vr == vc, "sort wrong"
    fill_src = "\n".join(["li v2, 0x9000", "li v20, %d" % arrays, "li v21, 0x123456789ABCDEF0123456789ABCDEF", "li v22, 0x5851F42D4C957F2D14057B7EF767814F", "outer:"] +
                         sum([["mul v21, v21, v22", "addi v21, v21, 12345", "sq [v2 + %d], v21" % (16 * i)] for i in range(N)], []) + ["addi v20, v20, -1", "bne v20, v0, outer", "halt"])
    mf, _ = run(fill_src, arrays)
    # capability accesses executed by the sorting part: count from a trace of one build
    mt = Machine(1 << 20); mt.trace = []; mt.load(asm.assemble(build(True, arrays))); mt.run(5_000_000)
    cap_ops = sum(1 for r in mt.trace if r.get("op") in ("clq", "csq"))
    sort_glyphs = mc.cycles - mf.cycles
    res = {"elements": N, "compare_exchanges": len(PAIRS), "arrays_sorted": arrays, "glyphs_raw": mr.cycles, "glyphs_capability": mc.cycles,
           "glyphs_fill_only": mf.cycles, "sort_glyphs": sort_glyphs, "capability_accesses": cap_ops,
           "capability_access_fraction_of_sort": round(cap_ops / sort_glyphs, 3),
           "sensitivity_percent_slowdown_if_each_capability_access_costs_k_extra_cycles": {str(k): round(100 * k * cap_ops / sort_glyphs, 1) for k in (0, 1, 2, 4, 8)}}
    print(json.dumps(res, indent=1)); json.dump(res, open(os.path.join(root, "docs/paper/workloads.json"), "w"), indent=1)
if __name__ == "__main__": main()
