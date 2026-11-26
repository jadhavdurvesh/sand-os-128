# 18 — Sigil capabilities (Veylith profile addendum)

**Status:** Implemented in the Python and C machines and in Kernelloom. Experimental; the MAC is SipHash-2-4, a published keyed PRF, truncated to 40 bits; the hardware latency of computing it is not modelled.

## 1. The idea

A **Sigil** is a complete memory capability that fits in *one* 128-bit register or *one* 128-bit memory word, with **no tag memory**. Unforgeability does not come from a hidden tag bit (as in CHERI) but from a 40-bit keyed MAC stored inside the capability and checked by hardware on every use. Because nothing lives outside the 128 bits, a Sigil can be copied by any ordinary instruction, stored in any memory, sent through the 128-bit mailbox, or serialised, without special tagged-memory support.

```
 127            88 87      80 79     72 71                         0
 +----------------+----------+---------+---------------------------+
 |   MAC (40)     | perms(8) | exp (8) |        base (72)          |
 +----------------+----------+---------+---------------------------+
 perms: bit0 READ, bit1 WRITE, bit2 NARROW   region = [base, base + 2^exp), base aligned to 2^exp, exp <= 72
 MAC  : top 40 bits of F(ckey, bits[87:0])
```

## 2. Instructions, CSRs, cause

| Item | Definition |
|---|---|
| `cmint rd, ra, rb` | **Kernel only.** `ra` = base, `rb` = perms \| exp<<8. Produces a Sigil. Misaligned or out-of-range arguments trap `CAPABILITY`. |
| `cnarrow rd, ra, rb` | `rb` = perms \| exp<<8 \| offset<<16. New perms must be a subset, region must be inside the old one and aligned; the source needs `NARROW`. Any violation, or an invalid source, traps. Monotonic: authority never grows. |
| `cinfo rd, ra` | Never traps. `rd` = `1<<127 \| bits[87:0]` if the MAC verifies, otherwise 0. Lets software read a capability's base/size/perms and test validity safely. |
| `clb`/`clq rd, [ra + imm]`, `csb`/`csq [ra + imm], rb` | Access through Sigil `ra`. Needs READ (loads) or WRITE (stores), `0 <= imm` and `imm + size <= 2^exp`. The effective address is `base + imm` and the normal checks (alignment, aperture, RAM) still apply. |
| CSR 11 `ckey` | 128-bit MAC key, kernel read/write. Changing it revokes every outstanding Sigil. |
| CSR 12 `cmode` | Non-zero = **capability mode** for user code: every raw load/store traps `CAPABILITY`; only `c*` accesses reach memory. |
| Cause 8 `CAPABILITY` | `tval` = the offending capability (or the raw effective address in capability mode). |

`F` = SipHash-2-4 (Aumasson and Bernstein, 2012) with the 128-bit `ckey` as key over the 88-bit body as 11 little-endian bytes; the MAC is the top 40 bits of the 64-bit tag. The implementation is checked against the official test vectors (`test_mac_is_siphash24_reference_vector`) and both machines agree on it under differential fuzzing.

## 3. Kernelloom integration (syscalls 10-12)

`capget(base, exp, perms)` mints a Sigil for a region inside the caller's aperture (else -1). `cmode()` puts the calling task into capability mode for good, and its spawned threads inherit it. `cwrite(cap, len)` prints through a READ Sigil instead of a raw pointer. A capability can be passed as a spawn argument or a mailbox message: a whole capability is one 128-bit value. `ckey` is set at boot from a constant so every run is reproducible; a real machine would need an entropy source.

## 4. Security properties and their evidence

| Property | Argument / test |
|---|---|
| Unforgeable (probabilistic) | A random 128-bit value verifies with probability about 2^-40. 300 000 random guesses: 0 accepted (`tools/bench.py`); 300 guesses in `test_random_values_are_not_capabilities`. |
| Tamper-evident | Flipping any one of the 128 bits invalidates a capability (`test_every_single_bit_flip_invalidates`). Avalanche of the stand-in MAC: 19.98 of 40 bits flip on average for a one-bit change (ideal 20). |
| Monotonic | `cnarrow` can only shrink perms and region; NARROW is dropped by default in handed-out capabilities (`test_narrowing_is_monotonic`). |
| Bounds and permission checked in hardware | `test_bounds_permissions_and_forgery_trap`. |
| Confinement | In capability mode raw access traps, so a task reaches only the regions it was handed (`test_capability_mode_forbids_raw_memory_access`, `examples/sigil{,forge,raw}.s`). |
| Revocation | Changing `ckey` invalidates all capabilities (`test_changing_the_key_revokes_everything`). Per-object revocation is not provided. |
| Two machines agree | The differential fuzzer includes capability operations, valid and invalid, with a trap handler (about 33 capability faults per program); 3000 programs, 0 divergences. |
| No extra instructions | A capability load costs the same Glyph count as a raw load in the loop benchmark (hardware MAC latency is not modelled). |

## 5. Trade-offs against nearby designs (honest)

* **Versus CHERI** (tagged 128-bit capabilities on a 64-bit machine): CHERI's tag makes forgery impossible and supports arbitrary bounds through compression; Sigil needs no tag storage and survives arbitrary byte-level copying, but forgery is only improbable, regions are power-of-two aligned, and a MAC must be computed on every use.
* **Versus Arm pointer authentication**: PAC puts a short MAC in the unused bits of a 64-bit pointer to protect a pointer's integrity; the 128-bit width lets Sigil carry a 40-bit MAC *plus* bounds and permissions, making the object a capability rather than just a signed pointer.
* **Versus Mungi/Amoeba password capabilities**: those are software-checked sparse capabilities; here the check is an instruction-level, load/store-path hardware check inside the machine model.

## 6. Limits

SipHash is a vetted short-input PRF, but truncating it to 40 bits is our design choice and its hardware latency is unstudied; 40-bit tag means about 2^39 expected online guesses, so the kernel must punish a failed use (Kernelloom halts); constant boot key; no per-object revocation; power-of-two regions waste memory; the MAC check latency is unmodelled; no sealed/entry (call-gate) capabilities; no paging interaction defined.


## Sealed capabilities

`cseal rd, ra` sets perm bit 0x80 (SEALED) on a valid capability and re-MACs it. A sealed capability is an opaque token: it can be copied, stored and sent in a mailbox, but loads, stores and `cnarrow` through it trap (cause 8). `cunseal rd, ra` is kernel-only and clears the bit, so only a trusted service can turn a token it was handed back into authority (`cunseal` on an unsealed or invalid value traps). This gives handle-style capabilities without a separate object table. It is not yet a full call gate: there is no entry-point binding, and the kernel has no `unseal` syscall yet.
