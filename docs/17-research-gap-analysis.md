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

Both machines come from one author and one specification, so agreement catches implementation slips, not specification mistakes. The fuzzer does not produce traps, privileged instructions or timer races. Counts are retired Glyphs on a deterministic model, not time. The kernel image sits below the kernel stack (checked by a test, now ~0x5174, limit 0x5800 so the stack at 0x6000 keeps 2 KiB).

## Novelty and Sigil

A short prior-art search (RV128I, QEMU RV128, CHERI, Arm PAC, Amoeba, Mungi, AS/400) found no published design combining a clean-sheet all-128-bit machine, hardware-checked capabilities with bounds, and no tag memory. The Sigil mechanism ([docs/18](18-sigil-capabilities.md)) is built around that combination. The survey is not exhaustive, so this is a limited claim, not proof of novelty. Open items: a vetted MAC, sealed capabilities, per-object revocation, MAC latency, paging interaction.
