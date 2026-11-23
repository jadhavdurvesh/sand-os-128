# 14 — Veylith v0 base profile

**Status:** Accepted for v0; implemented in the Python reference emulator; verified by `tests/test_veylith.py`  
**Scope:** The smallest complete machine that can run a kernel and an isolated user program. Everything not listed here is out of v0.

This document is the written contract. The glyph table below is generated from `veylith/isa.py`, which the assembler, disassembler and emulator all share; `architecture/veylith-v0-glyphs.json` is the same table in machine-readable form and a test fails if the two drift.

## 1. State

| State | Definition |
|---|---|
| Veyls | 32 registers `v0..v31`, 128 bits each. `v0` always reads zero; writes to it are discarded. |
| Glyph location (`pc`) | 128-bit. Must be 8-aligned and below 2^48 to fetch. |
| Privilege | 0 = kernel, 1 = user. Reset state is kernel. |
| CSRs | `priv`(0, read-only), `tvec`(1), `tpc`(2), `tcause`(3), `tval`(4), `tpriv`(5), `abase`(6), `alim`(7), `cycles`(8, read-only, glyphs retired), `scratch`(9). Each is 128 bits. |
| Memory | Flat RAM at address 0 (size is a machine parameter, multiple of 8 bytes) and a one-byte console port at `0xF0000000`. |

Reset: all veyls, CSRs and RAM are zero, `pc` = 0 (or the first image's entry), privilege = kernel.

## 2. Glyph encoding

Fixed 64 bits, little-endian in memory: `op[63:56] rd[55:51] ra[50:46] rb[45:41] reserved[40:32] imm[31:0]`.
Each format uses only some fields; unused fields and the reserved field must be zero, otherwise the glyph is ILLEGAL (it never executes as another operation). `imm` is sign-extended to 128 bits unless a glyph says otherwise.

## 3. Memory and protection

- Access sizes: 1, 2, 4, 8, 16 bytes. Natural alignment is required.
- Check order: address >= 2^48 → ACCESS; misaligned → MISALIGN; region check → ACCESS. `tval` is the full 128-bit address.
- Kernel: may access all of RAM; may store single bytes to the console port. Loads from the console and any other store width there trap ACCESS.
- User: every fetch, load and store must lie wholly inside `[abase, abase + alim)` and inside RAM; the console is never reachable.
- No address translation in v0 (see decision V128-008).

## 4. Traps

Causes: 1 ILLEGAL, 2 PRIVILEGE, 3 DIVZERO, 4 MISALIGN, 5 ACCESS, 6 SYSCALL.

On a trap the machine sets `tpc` (the faulting glyph; for `sys`, the next glyph), `tcause`, `tval` (faulting address, raw glyph for ILLEGAL, `sys` immediate, 0 otherwise) and `tpriv` (the privilege before the trap), enters kernel privilege and jumps to `tvec`. A trapping glyph retires nothing and changes no veyl or memory. If `tvec` is 0 the machine stops with an "unhandled trap" reason, so a kernel bug during early boot is visible instead of looping. A trap inside the kernel overwrites `tpc`; v0 does not provide nested trap state.

## 5. Arithmetic rules

Add, subtract and multiply wrap modulo 2^128. `mulh` is the high half of the unsigned 256-bit product. Division and remainder by zero trap DIVZERO. Signed division truncates toward zero; the one overflow case `-2^127 / -1` yields `-2^127` with remainder 0. Shift and rotate counts are taken modulo 128. `clz` of zero is 128.

## 6. Glyph table

| Glyph | Opcode | Format | Behaviour |
|---|---|---|---|
| `nop` | 0x00 | none | no operation |
| `halt` | 0x01 | none | stop the machine (kernel only); exit code = low 64 bits of v1 |
| `add` | 0x10 | rrr | rd = ra + rb (wraps mod 2^128) |
| `sub` | 0x11 | rrr | rd = ra - rb (wraps) |
| `mul` | 0x12 | rrr | rd = low 128 bits of ra * rb |
| `mulh` | 0x13 | rrr | rd = high 128 bits of unsigned ra * rb |
| `udiv` | 0x14 | rrr | rd = ra / rb unsigned; rb == 0 traps DIVZERO |
| `sdiv` | 0x15 | rrr | rd = ra / rb signed, truncated toward zero; MIN / -1 = MIN; rb == 0 traps |
| `urem` | 0x16 | rrr | rd = ra % rb unsigned; rb == 0 traps DIVZERO |
| `srem` | 0x17 | rrr | rd = ra - rb * (ra sdiv rb); MIN rem -1 = 0; rb == 0 traps |
| `and` | 0x18 | rrr | rd = ra & rb |
| `or` | 0x19 | rrr | rd = ra | rb |
| `xor` | 0x1A | rrr | rd = ra ^ rb |
| `shl` | 0x1B | rrr | rd = ra << (rb mod 128) |
| `shr` | 0x1C | rrr | rd = ra >> (rb mod 128), zero fill |
| `sar` | 0x1D | rrr | rd = ra >> (rb mod 128), sign fill |
| `rol` | 0x1E | rrr | rd = ra rotated left by rb mod 128 |
| `ror` | 0x1F | rrr | rd = ra rotated right by rb mod 128 |
| `addi` | 0x20 | rri | rd = ra + sext(imm) |
| `andi` | 0x21 | rri | rd = ra & sext(imm) |
| `ori` | 0x22 | rri | rd = ra | sext(imm) |
| `xori` | 0x23 | rri | rd = ra ^ sext(imm) |
| `shli` | 0x24 | rri | rd = ra << (imm mod 128) |
| `shri` | 0x25 | rri | rd = ra >> (imm mod 128), zero fill |
| `sari` | 0x26 | rri | rd = ra >> (imm mod 128), sign fill |
| `slt` | 0x28 | rrr | rd = 1 if ra < rb signed else 0 |
| `sltu` | 0x29 | rrr | rd = 1 if ra < rb unsigned else 0 |
| `seq` | 0x2A | rrr | rd = 1 if ra == rb else 0 |
| `ldk` | 0x30 | ri | rd = sext(imm) |
| `shk` | 0x31 | ri | rd = (rd << 32) | zext(imm) |
| `clz` | 0x32 | rr | rd = count of leading zero bits of ra (128 for zero) |
| `popc` | 0x33 | rr | rd = number of set bits of ra |
| `lb` | 0x40 | ld | rd = zext(mem8[ra + sext(imm)]) |
| `lh` | 0x41 | ld | rd = zext(mem16[...]) |
| `lw` | 0x42 | ld | rd = zext(mem32[...]) |
| `ld` | 0x43 | ld | rd = zext(mem64[...]) |
| `lq` | 0x44 | ld | rd = mem128[...] |
| `lbs` | 0x45 | ld | rd = sext(mem8[...]) |
| `lhs` | 0x46 | ld | rd = sext(mem16[...]) |
| `lws` | 0x47 | ld | rd = sext(mem32[...]) |
| `lds` | 0x48 | ld | rd = sext(mem64[...]) |
| `sb` | 0x50 | st | mem8[ra + sext(imm)] = rb |
| `sh` | 0x51 | st | mem16[...] = rb |
| `sw` | 0x52 | st | mem32[...] = rb |
| `sd` | 0x53 | st | mem64[...] = rb |
| `sq` | 0x54 | st | mem128[...] = rb |
| `jmp` | 0x60 | j | pc = pc + 8 * sext(imm) |
| `jal` | 0x61 | jal | rd = pc + 8; pc = pc + 8 * sext(imm) |
| `jr` | 0x62 | jr | t = ra + sext(imm); rd = pc + 8; pc = t |
| `beq` | 0x63 | br | if ra == rb: pc = pc + 8 * sext(imm) |
| `bne` | 0x64 | br | if ra != rb: branch |
| `blt` | 0x65 | br | if ra < rb signed: branch |
| `bge` | 0x66 | br | if ra >= rb signed: branch |
| `bltu` | 0x67 | br | if ra < rb unsigned: branch |
| `bgeu` | 0x68 | br | if ra >= rb unsigned: branch |
| `sys` | 0x70 | j | trap SYSCALL; tval = imm; tpc = pc + 8 |
| `tret` | 0x71 | none | kernel only: priv = tpriv; pc = tpc |
| `csrr` | 0x72 | csrr | kernel only: rd = csr[imm] |
| `csrw` | 0x73 | csrw | kernel only: csr[imm] = ra |

Assembler pseudo-ops (not glyphs): `li rd, const` (one to four glyphs), `la rd, label`, `call label`, `ret`, `mv`, `not`, `neg`.

## 7. Image format (VYLI v1)

Header: magic `VYLI`, u16 version (1), u16 segment count (≤ 64), u64 entry. Then per segment: u64 address, u64 size, bytes. Readers reject bad magic, other versions, truncated data and trailing bytes; the machine rejects segments that do not fit in RAM.

## 8. Tracebook (v1)

With tracing on, the emulator records one JSON object per step: `tracebook` (version), `n` (glyphs retired), `pc`, `raw`, `op`, changed `regs`, `mem` writes, `trap` (cause and tval, or null), `next_pc`, `priv`. The same image and initial state always produce an identical trace.

## 9. Kernelloom v0 and its calling convention

`kernel/kernelloom.s` is written in Veylith assembly. It installs `tvec`, sets the user aperture to `[0x10000, 0x20000)`, enters a user program through `tret`, saves all 31 user veyls on every trap, and implements:

| Call (v1) | Arguments | Result |
|---|---|---|
| 1 write | v2 = pointer, v3 = length | length written, or -1 if the buffer is not wholly inside the aperture |
| 2 exit | v2 = code | prints the code, halts with it |
| other | | -1 |

A user fault prints its cause and address and halts with `128 + cause`. The frame is a fixed area, so Kernelloom v0 is single-core and not re-entrant.

## 10. Not in v0

Page tables and multiple address spaces, interrupts and timers, atomics and multicore ordering, floating point and vectors, a compiler, a linker, a filesystem, devices other than the console, and any hardware implementation. The emulator is written in Python; speed was not a goal.
