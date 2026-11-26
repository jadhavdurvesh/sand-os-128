# Veylith 128-Native v1 — Architectural Specification

**Status:** Implemented reference profile; software-emulated and under active research.  
**Profile identifier:** `128-native-v1`

## 1. Architectural parameters

| Parameter | Definition |
|---|---:|
| General-purpose register width | 128 bits |
| General-purpose register count | 128 writable (v1–v128), plus zero slot v0 |
| General-purpose register file | 16,384 bits |
| Instruction Glyph width | 128 bits (16 bytes) |
| Virtual address width | 128 bits |
| Pointer width | 128 bits |
| Program counter width | 128 bits |
| Scalar integer arithmetic | modulo 2^128 |
| Instruction alignment | 16 bytes |
| Immediate field | 88 bits |
| Register index | 8 bits |
| Endianness | Little-endian |
| Executable image | VYLI v2 |

This is a software-defined architecture profile, not a claim that physical silicon has been fabricated. The emulator uses arbitrary-precision host integers and bounded bytearray RAM.

## 2. Register file

There are 128 writable general-purpose registers, each 128 bits wide, addressed as v1–v128. v0 is a separate hardwired-zero operand slot and is not counted among the GPRs. The ABI names v127 as `sp` and v128 as `lr`; these remain members of the writable GPR file. Register indices are eight bits.

## 3. Integer model

Unsigned values range from 0 through 2^128−1. Two's-complement signed values range from −2^127 through 2^127−1. Arithmetic wraps modulo 2^128. Division by zero traps DIVZERO. Signed division truncates toward zero; MIN / −1 returns MIN.

## 4. 128-bit instruction Glyph

Every instruction is a fixed 128-bit Glyph stored in 16 little-endian bytes.

| Field | Bit positions | Width |
|---|---|---:|
| Opcode | 127:112 | 16 |
| Destination register | 111:104 | 8 |
| Source register A | 103:96 | 8 |
| Source register B | 95:88 | 8 |
| Reserved | 90:88 | 3 |
| Immediate | 87:0 | 88 |

Unused fields and reserved bits must be zero or the encoding is illegal. Arithmetic, memory offsets and relative branches use signed 88-bit immediates. `shk` consumes the immediate as an unsigned bit pattern. Relative control-flow offsets are measured in Glyphs and multiplied by 16; instruction targets must be 16-byte aligned.

### Full-width constants

`ldk` sign-extends an 88-bit immediate. `shk` combines the low 40 bits already held in the destination with the low 88-bit immediate:

`rd = ((rd & (2^40 - 1)) << 88) | imm[87:0]`

The `li` pseudo-op emits one Glyph when a value fits signed 88 bits, otherwise two Glyphs. This constructs every 128-bit bit pattern.

## 5. 128-bit addressing and physical memory

Pointers, effective-address calculations, PC, trap PC and trap values are 128-bit. The virtual address domain is 0 through 2^128−1. The emulator does not allocate a 2^128-byte array: physical RAM is bounded and configurable (default 1 MiB). Addresses are valid only if the access maps to implemented RAM or defined MMIO.

Console MMIO is a byte-store register at `0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF0000`. The console accepts byte stores only. Address overflow, unmapped memory and permission violations trap ACCESS. Transfers must be naturally aligned. The initial memory model is flat bounded RAM, not paging; physical capacity is independent of virtual address width.

## 6. Memory transfers

Byte, halfword, word, 64-bit and 128-bit transfers are supported. `lq`/`sq` transfer 128 bits. Narrow loads zero-extend unless the mnemonic requests sign extension. All transfers are little-endian.

## 7. Privilege and Kernelloom

The model has kernel privilege 0 and user privilege 1. Kernelloom configures a user aperture, enters user mode with `tret`, and receives traps through `tvec`. It saves/restores all 127 writable general-purpose registers (v1–v128) in a 16-byte-aligned frame across syscalls. It remains single-core and non-reentrant.

## 8. VYLI v2 image format

The fixed header is 24 bytes: magic `VYLI`, u16 version 2, u16 segment count, and 16-byte little-endian entry address. Each segment has a 32-byte header: 16-byte address, 16-byte byte length, then segment data. VYLI v1 images are intentionally rejected because this is a breaking 128-bit redesign.

## 9. Tracebook v2

Trace records contain a 128-bit PC and a 32-hex-digit raw Glyph. Register values, memory addresses and trap values use full-width hexadecimal strings. Trace version is 2.

## 10. Implementation boundary

The Python emulator, assembler, disassembler, image format, Kernelloom, examples and CI target this profile. CI tests Python 3.11–3.13. This is a deterministic sequential single-core software model, not cycle-accurate hardware and not a physical memory-capacity claim.

## 11. Timer interrupt (profile addendum, `128-native-v1` + TIMER)

The first asynchronous event. It adds one CSR and one trap cause; no Glyph changes.

| Item | Definition |
|---|---|
| CSR 10 `timecmp` | 128-bit, kernel read/write. 0 = disarmed. A non-zero value is a deadline against the retired-Glyph counter (`cycles`, CSR 8). |
| Cause 7 `TIMER` | Reported in `tcause`; `tval` = 0. |
| Delivery rule | Before fetching a Glyph, if `priv` = 1 (user), `timecmp` ≠ 0, `tvec` ≠ 0 and `cycles` ≥ `timecmp`: `timecmp` is cleared (one-shot) and the machine traps with `tpc` = the PC of the Glyph that has **not** executed. `tpriv` = 1. |
| Masking | Implicit: the timer is never delivered in kernel privilege. Trap entry sets privilege 0, so there is no nesting and the non-reentrant kernel needs no interrupt-enable bit. A deadline that passes while the kernel runs fires at the first user Glyph after `tret`. |
| Priority | The timer check precedes fetch, so a due timer wins over a fault the next Glyph would have raised; that Glyph is re-executed after `tret` and raises its own fault then. |
| Determinism | The deadline is measured in retired Glyphs, not wall-clock time, so every run is reproducible. A trapped Glyph does not retire. The Python and C machines are tested to agree to the Glyph on every example. |
| Time width | `cycles`/`timecmp` compare as full 128-bit values; the C machine's counter is 64-bit, which is not reachable within any bounded run. |

Kernelloom arms `timecmp = cycles + QUANTUM` (3000 Glyphs) at boot and on every return to user mode, and treats cause 7 as a preemption: the interrupted task's registers and `tpc` are saved untouched (including `v1`) and the next READY task runs. Threads therefore no longer need to yield. Tested by `Timer` in `tests/test_veylith.py`, the `preempt` example and the CI `preempt` scenario.
