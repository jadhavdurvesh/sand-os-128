# 20 — Novelty gap search

Goal: find what, if anything, in Veylith/Sigil is not already in the literature. Method: targeted searches in November 2026 plus reading the sources that came back. This is not a systematic review; a "not found" below means "not found in these searches".

## Result in one paragraph

The Sigil mechanism is **not novel as a mechanism**. Guarded pointers (Carter, Keckler, Dally, ASPLOS 1994) already had power-of-two segments, permissions, a log-size field, enter-pointer protected calls with no kernel involvement, and a single shared address space; they used a tag bit. Tag-free replacements for the tag exist (an Intel 2017 patent on crypto-enforced capabilities, Cryptographic Capability Computing, Graz's sealed pointers). CHERI has sealing, otype-matched domain crossing, and published cost numbers for a software-handler and a hypothetical hardware crossing. Per-object revocation in capability hardware is also covered by Intel patents. What remains is narrower and is listed below with evidence status.

## Candidate gaps, ranked

| # | Candidate | Prior art found | Evidence we can produce | Verdict |
|---|---|---|---|---|
| 1 | In-pointer authenticated capability at **128-bit width with no address bits given up** (full-width base, exponent, permissions, 40-bit MAC) | Prior in-pointer schemes are 64-bit and truncate or shorten the tag (20-bit MAC at 39-bit VA; 32 encrypted bits; 54-bit address) | Bit-budget table (done, in paper); forgery bound; implemented and tested | **Defensible but modest.** A design-point contribution, best framed as "guarded pointers revisited without the tag, at 128 bits" |
| 2 | **Whole-machine 128-bit** clean-sheet ISA hosting it | RV128I and QEMU RV128 widen RISC-V; CHERI is 128-bit capability on 64-bit core | Two implementations, differential fuzz, kernel | **Defensible.** Platform contribution; reproducibility is the real value |
| 3 | Cost of **exponent-only bounds** on real allocation traces | Guarded-pointer line of work discusses internal fragmentation; we did not find trace-based numbers for tag-free schemes | **Done** (tools/frag.py): 20-96% internal fragmentation, 60-283% buddy peak overhead; six mantissa bits cut waste to 0.8-2.0% | **Useful result and an honest design correction.** Not a headline claim; needs more traces and the mantissa variant implemented |
| 4 | Hardware gate with **optional register spill/clear** and its true cost accounting (Glyph count vs memory words moved) | CHERI trusted-stack CCall; guarded-pointer return segments | Measured: 6 Glyphs but 254 register words moved per isolated call | **Not novel as mechanism.** The accounting point (instruction count hides traffic) is worth stating |
| 5 | Re-keying policy against online forgery | PAC brute-force literature exists | Analysis shows re-keying does not help against independent random guesses; it only matters if guesses leak information | **Dropped.** No gap here |
| 6 | Per-object revocation | Amoeba check fields; Intel individually revocable capabilities (patent); many CHERI temporal-safety papers | Not implemented | **Crowded.** Not a place to claim novelty |
| 7 | Indexed capability access / compiler support | CHERI has register-offset forms | Found an ISA gap: Sigil offsets are immediates only | **Fix, not novelty** |

## What this means for the paper

- Frame it as a **revisit and an engineering/measurement study**, not an invention. Title and abstract already hedge; the positioning section now cites guarded pointers.
- The honest contribution list: (1) the 128-bit tag-free design point and its bit budget, (2) a reproducible two-implementation platform, (3) measured costs and limits, including the fragmentation correction.
- The **fragmentation finding is the one place where data changed our design**: exponent-only bounds are too lossy for real allocation sizes. The next iteration should spend the 8 bits freed by a 64-bit base on a length multiplier. That change is not implemented; do it before claiming anything about bounds.

## Not read in full (verify before citing)

C3 (ACM page unavailable), Intel patent US12306998B2 on domain isolation with cryptographic computing, the individually-revocable-capabilities patents, the CHERI temporal-safety papers (PICASSO, PoisonCap, CHERI-D), and the guarded-pointer patent US5845331. Reference years and author lists flagged "to be confirmed" in the paper still need checking.
