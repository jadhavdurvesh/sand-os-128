# 19 — Prior art, claims, and publication readiness

Written after a literature check in November 2026. It is not a complete survey. Every row below was read from the source named; items marked *unverified* were not retrieved in full.

## What exists (verified from the sources)

| Work | Relevant facts | Source |
|---|---|---|
| CHERI | 128-bit capabilities on a 64-bit core, out-of-band 1-bit tag per capability-sized word; sealed capabilities, object types, `CInvoke`/CCall domain transitions in the ISA | Cambridge TR-987 (CHERI ISA v9) |
| CHERI domain crossing | CCall = hardware checks (seal, permissions, otype) then exception to a software handler with a trusted stack, unseal, register clearing. Reported ≈500 cycles over a function call; a hypothetical single-cycle hardware crossing would save a further 145 cycles; pipe-style IPC > 17,000 cycles | Watson et al., *Fast Protection-Domain Crossing in the CHERI Capability-System Architecture*, IEEE Micro |
| Intel crypto-enforced capabilities | 64-bit capability: 1 permanence bit, 6-bit size, 57-bit pointer with the upper 32 bits encrypted; tweak includes a 32-bit protection-domain ID; validated by decryption, no tag memory; permissions only as an optional extension. Filed 2017-09-29, granted as US10706164B2 | Google Patents |
| Cryptographic Capability Computing (C3) | Tag-free cryptographic capability work, MICRO 2021 (ACM DOI 10.1145/3466752.3480076). *Page not retrievable; authors and details unverified* | ACM DL |
| Cryptographically sealed pointers | MAC over upper address bits, radix (size) and a memory tag; 20-bit MAC for 39-bit VA, 11-bit for 48-bit VA; needs per-granule memory tags (4–16 bits); no permissions; no compartment mechanism. Unterguggenberger, Schrammel, Lamster, Nasahl, Mangard, ACM CCS 2023 | TU Graz PDF |
| Arm PAC, RV128I, QEMU RV128, Amoeba, Mungi, AS/400 | As cited in the paper; from earlier, shorter search | see paper |

## What this means for our claims

**Not novel, do not claim:** tag-free authenticated pointers; capabilities with power-of-two bounds; sealing; a hardware domain-crossing call; register clearing on crossing.

**Defensible, narrower claims:**
1. A uniformly 128-bit machine lets an in-pointer capability carry a full 72-bit base, exponent, permissions and a 40-bit MAC with no address bits taken or encrypted; prior in-pointer schemes live inside 64 bits and give something up (shorter MAC, truncated address, no permissions).
2. A reproducible platform: two independent implementations, differential fuzzing, kernel, examples; all numbers regenerate from the repository.
3. One concrete gate design point (single-instruction call, per-task return link, optional hardware-spilled isolation) with its costs measured in the model, including the limits (no nesting; 254 words of register traffic per isolated call).

**Found while preparing this:** capability loads and stores take only an immediate offset, so run-time array indexing is not expressible without a new Glyph or a `cnarrow` per element. This is a real ISA gap (paper §Sigil, "Immediate-offset limitation").

## What `tools/workloads.py` shows

A 16-element sorting network (63 compare-exchanges, constant indices) sorts correctly through raw and through capability accesses. 76% of its Glyphs are capability accesses, so if the MAC check costs k extra cycles per access the slowdown is about 76% × k. That is a sensitivity table, not a result: it needs a real latency.

## Readiness checklist

| Item | State |
|---|---|
| Reproducible artifact | Done |
| Honest limits stated | Done |
| Literature review of in-pointer crypto capabilities | Started (this document); C3 and several others still to read in full |
| Real baseline on one microarchitecture (CHERI-style vs Sigil) | **Missing.** Our Glyph counts are not comparable to CHERI's cycle counts |
| Threat model and forgery analysis | Paper has a basic one; no attack experiments, no key management, no side channels |
| Realistic workloads | One micro-workload; no compiler, no indexed capability access |
| Hardware or cycle-accurate model of MAC latency | **Missing** |
| Reference verification (authors, years, venues) | Several entries flagged "to be confirmed" in the bibliography |

## Suggested path

1. Post the current paper to arXiv as a technical report (verify the category and endorsement rules yourself).
2. Read C3 and the sealed-pointer paper in full; adjust the positioning table.
3. Add an indexed capability access Glyph and re-run the workload.
4. Build a small cycle model (even a simple in-order pipeline with a parameterised MAC latency) and run both Sigil and a CHERI-style tag model on it.
5. Then target a workshop or short-paper track.
