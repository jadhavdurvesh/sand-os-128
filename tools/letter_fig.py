#!/usr/bin/env python3
"""Figure for the letter: modelled slowdown vs MAC latency L, from docs/paper/cyclemodel.json (no new measurements)."""
import json, os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(root, "docs/paper/cyclemodel.json")))
rows = {r["workload"].split(" (")[0]: r for r in d["rows"]}
m = json.load(open(os.path.join(root, "docs/paper/macro.json")))
tree = [r for r in m["rows"] if r["workload"].startswith("binary search tree")][0]
Ls = list(range(0, 17))
def curve(r, flags): return [100 * L * (r["macs_flags"] if flags else r["macs_noflags"]) / r["glyphs_cap"] for L in Ls]
fig, ax = plt.subplots(figsize=(3.4, 2.35), dpi=300)
arr = rows["matrix multiply"]; lst = rows["linked list"]; big = rows["large list"]
ax.plot(Ls, curve(arr, False), color="#c0392b", lw=1.5, label="array code, no bit")
ax.plot(Ls, curve(big, True), color="#2c6fbb", lw=1.5, label="512 KiB cap. list, bit")
ax.plot(Ls, curve(tree, True), color="#8e44ad", lw=1.3, ls="--", label="capability BST, bit")
ax.plot(Ls, curve(arr, True), color="#2e8b57", lw=2.2, zorder=5, label="array code, bit (0 MACs)")
for lines, c, lab in ((4, "#555", "tag cache, 4 lines, 512 KiB list"), (64, "#999", "tag cache, 64 lines")):
    v = 100 * 30 * big["tag_misses"][str(lines)] / big["glyphs_cap"]
    ax.axhline(v, color=c, lw=0.9, ls=":"); ax.text(6.0, v + 4, lab, fontsize=5.5, color=c)
ax.axvspan(12, 17, color="#f2e3b3", alpha=0.6, lw=0); ax.text(12.2, 235, "gate-depth\nestimate", fontsize=5.5, va="top")
ax.set_xlim(0, 16.5); ax.set_ylim(-8, 250)
ax.set_xlabel("MAC latency L (cycles)", fontsize=7); ax.set_ylabel("modelled slowdown (%)", fontsize=7)
ax.tick_params(labelsize=6); ax.legend(fontsize=5.5, frameon=False, loc="upper left", bbox_to_anchor=(0.0, 0.88))
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.tight_layout(pad=0.3); fig.savefig(os.path.join(root, "docs/paper/letter-fig.pdf"))
