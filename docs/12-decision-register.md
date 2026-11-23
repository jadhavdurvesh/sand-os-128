# 12 — Architecture decision register

**Status:** Open decisions  
This register prevents provisional assumptions from becoming accidental specifications.

## Decision statuses

- **Open:** no choice has been made.
- **Proposed:** a candidate is under consideration.
- **Accepted:** selected for the current architecture revision.
- **Superseded:** replaced by a later decision.
- **Rejected:** considered and not selected.

## Current decisions

### V128-000 — Project scope
- **Status:** Accepted
- **Decision:** SAND-128 is an independent experimental architecture and OS research project. SAND OS 64 remains separate and primary.
- **Reason:** Preserve freedom to explore without destabilising the established project.

### V128-001 — Scalar register target
- **Status:** Proposed
- **Decision:** The initial architecture should use 128-bit general-purpose scalar registers.
- **Reason:** This is the core experimental premise.
- **Caveat:** Register count, names, and exact operations remain open.

### V128-002 — Address width
- **Status:** Accepted for v0 (implemented, verified in the emulator)
- **Decision:** Implemented virtual address width is 48 bits. A 128-bit address with any of bits 127:48 set raises ACCESS with the full 128-bit value in `tval`. Physical memory is a flat RAM window starting at 0 plus a one-byte console port. Pointers in the v0 ABI are the full 128-bit veyl value.
- **Question:** Should the first profile use a narrower implemented virtual-address width while retaining 128-bit scalar registers?
- **Evaluation:** Translation complexity, useful emulator bounds, pointer ABI, and future extensibility.

### V128-003 — Instruction encoding
- **Status:** Accepted for v0 (implemented, verified)
- **Decision:** Fixed-length 64-bit glyphs: `op[63:56] rd[55:51] ra[50:46] rb[45:41] reserved[40:32] imm[31:0]`. Reserved and unused fields must be zero, otherwise ILLEGAL. 128-bit constants are built with `ldk` (sign-extended 32 bits) followed by `shk` (shift in 32 bits); the assembler `li` pseudo-op expands to the shortest sequence.
- **Question:** Fixed-length, variable-length, or a structured hybrid encoding?
- **Evaluation:** Decode simplicity, code density, immediate values, extension space, and compiler complexity.

### V128-004 — Register count and special registers
- **Status:** Accepted for v0 (implemented, verified)
- **Decision:** 32 veyls `v0..v31`, `v0` reads as zero and ignores writes. Control state lives in ten CSRs reached only through `csrr`/`csrw` (priv, tvec, tpc, tcause, tval, tpriv, abase, alim, cycles, scratch). Assembler aliases: `sp`=v30, `lr`=v31 (software convention only).
- **Question:** How many scalar registers should be visible, and how should control state be represented?
- **Evaluation:** Compiler register pressure, encoding space, context-switch cost, and implementation complexity.

### V128-005 — Condition state
- **Status:** Accepted for v0 (implemented, verified)
- **Decision:** No condition flags. `slt`, `sltu`, `seq` write 0 or 1 to a veyl; branches compare two veyls directly. Nothing extra to save on a trap.
- **Question:** Global condition flags, predicate registers, or explicit comparison results?
- **Evaluation:** Code generation, interrupt preservation, instruction regularity, and state complexity.

### V128-006 — Endianness
- **Status:** Accepted for v0 (implemented, verified)
- **Decision:** Little-endian byte order for memory, images and the glyph encoding, independent of the host.
- **Question:** Little-endian, big-endian, or a specified canonical data encoding with platform constraints?
- **Evaluation:** Simplicity, interoperability at file boundaries, and implementation choices.

### V128-007 — Privilege model
- **Status:** Accepted for v0 (implemented, verified)
- **Decision:** Two privilege domains: kernel (0) and user (1). Traps always enter kernel at `tvec`. `tret` returns to the domain stored in `tpriv`; the kernel starts a user program by setting `tpc`, `tpriv`=1 and executing `tret`.
- **Question:** What privilege domains and transition operations are necessary for the first kernel?
- **Evaluation:** Smallest secure model that supports kernel and user isolation.

### V128-008 — Memory translation
- **Status:** Accepted for v0 as an interim model (implemented, verified); paging deferred
- **Decision:** v0 uses a single user *aperture* (`abase`, `alim`): in user mode every fetch, load and store must lie wholly inside it, otherwise ACCESS. There is no translation yet; page tables, multiple address spaces and TLB rules remain future work.
- **Question:** What page-table structure, page sizes, and invalidation contract should the first profile use?
- **Evaluation:** Emulator simplicity, protection, and future hardware plausibility.

### V128-009 — Base atomicity and memory ordering
- **Status:** Accepted for v0 (implemented, verified); atomics and multicore deferred
- **Decision:** Single core, sequential, deterministic. Natural alignment is required for every access (MISALIGN otherwise). No atomic operations or ordering rules are defined; they are needed only once there is more than one core.
- **Question:** What atomic operations and memory consistency guarantees belong in the base architecture?
- **Evaluation:** Single-core first implementation versus future multicore design.

### V128-010 — Floating point and vector support
- **Status:** Deferred
- **Decision:** Keep these out of the first scalar integer milestone.
- **Reason:** Establish a correct integer core before expanding architectural state.

## How to add a decision

Each new entry should include:
- Unique decision ID.
- Status.
- Context and constraints.
- Options considered.
- Selected option and rationale, if accepted.
- Consequences and migration implications.
- Tests or specification sections affected.

A decision is accepted only when the relevant specification and conformance tests are updated.
