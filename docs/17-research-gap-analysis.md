# 17 — Research status and gap analysis

**Status:** Evidence-backed snapshot. Companion to the draft paper `docs/paper/veylith-128.tex` (PDF alongside).

## What is established (and how it is checked)

| Claim | Evidence |
|---|---|
| The machine is 128-bit in registers, Glyphs, addresses, PC, timer deadline | `tests/test_veylith.py` (Architecture, Addressing), spec doc 14 |
| Two independent implementations agree | `tests/test_differential.py`: 3000 random programs (~1.9 M retired Glyphs), 0 divergences in output hash or Glyph count; all 10 examples match to the Glyph (`NativeMachine` test) |
| Kernel multitasks and preempts without losing 128-bit state | `Kernelloom` and `Timer` tests, `examples/{threads,pingpong,preempt,threadedge,threaddead}.s` |
| Costs | `tools/bench.py` → `docs/paper/evidence.json` (Glyph counts, not time) |

Regenerate everything: `python tools/evidence.py && python tools/paper_numbers.py`, then `latexmk -pdf docs/paper/veylith-128.tex`.

## Findings

1. Native 128-bit multiply: 34! takes 107 Glyphs against 280 for a 64-bit-limb emulation (2.62×, a lower bound for a real 64-bit machine).
2. The dominant cost of the design is architectural-state size. A full task switch costs ~865 Glyphs (it was ~1900 with a copy loop; unrolling halved it). Preemption overhead is 22% at a 3000-Glyph quantum.

## Gaps (none of these is implemented)

Virtual memory (only aperture protection); cheaper context switching (dirty mask, banking, block moves); code-density study; pointer-footprint study (needs a compiler); atomics and a memory model; floating point/vectors; device interrupts; a compiler; a formal executable semantics from which machines and tables are generated; a threat model; any hardware claim. Details and the research agenda are in the paper, section 7.

## Limits of the evidence

Both machines come from one author and one specification, so agreement catches implementation slips, not specification mistakes. The fuzzer does not produce traps, privileged instructions or timer races. Counts are retired Glyphs on a deterministic model, not time. The kernel image sits just below a fixed scratch address (checked by a test, ~0x4DC4 of 0x5000).
