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
- **Status:** Open
- **Question:** Should the first profile use a narrower implemented virtual-address width while retaining 128-bit scalar registers?
- **Evaluation:** Translation complexity, useful emulator bounds, pointer ABI, and future extensibility.

### V128-003 — Instruction encoding
- **Status:** Open
- **Question:** Fixed-length, variable-length, or a structured hybrid encoding?
- **Evaluation:** Decode simplicity, code density, immediate values, extension space, and compiler complexity.

### V128-004 — Register count and special registers
- **Status:** Open
- **Question:** How many scalar registers should be visible, and how should control state be represented?
- **Evaluation:** Compiler register pressure, encoding space, context-switch cost, and implementation complexity.

### V128-005 — Condition state
- **Status:** Open
- **Question:** Global condition flags, predicate registers, or explicit comparison results?
- **Evaluation:** Code generation, interrupt preservation, instruction regularity, and state complexity.

### V128-006 — Endianness
- **Status:** Open
- **Question:** Little-endian, big-endian, or a specified canonical data encoding with platform constraints?
- **Evaluation:** Simplicity, interoperability at file boundaries, and implementation choices.

### V128-007 — Privilege model
- **Status:** Open
- **Question:** What privilege domains and transition operations are necessary for the first kernel?
- **Evaluation:** Smallest secure model that supports kernel and user isolation.

### V128-008 — Memory translation
- **Status:** Open
- **Question:** What page-table structure, page sizes, and invalidation contract should the first profile use?
- **Evaluation:** Emulator simplicity, protection, and future hardware plausibility.

### V128-009 — Base atomicity and memory ordering
- **Status:** Open
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
