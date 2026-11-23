# 11 — Research roadmap

**Status:** Initial roadmap; dates intentionally omitted  
**Rule:** A milestone is complete only when its exit criteria are met.

## Stage A — Charter and vocabulary

**Work**
- Define goals and non-goals.
- Establish provisional architecture terminology.
- Separate register, arithmetic, pointer, address, and instruction widths.
- Record unresolved decisions.

**Exit criteria**
- Project charter reviewed.
- Core vocabulary documented.
- No unsupported claims of implementation or performance.

## Stage B — Machine specification

**Work**
- Select register count and special state.
- Specify instruction encoding and decode rules.
- Specify arithmetic and control-flow semantics.
- Define reset, trap, and privilege behaviour.
- Define memory and address-space rules.

**Exit criteria**
- Versioned specification for the initial base subset.
- Every instruction has precise semantics and edge cases.
- Open questions are recorded rather than silently assumed.

## Stage C — Reference emulator

**Work**
- Implement 128-bit arithmetic helpers.
- Implement machine state, decoder, and execution loop.
- Add deterministic memory and fault behaviour.
- Add Tracebook output and conformance tests.

**Exit criteria**
- All accepted base instructions pass boundary and negative tests.
- Same inputs produce reproducible architectural traces.

## Stage D — Assembler and executable image

**Work**
- Implement assembler and disassembler.
- Define a versioned image format.
- Add linker or image builder.
- Run assembled programs in the emulator.

**Exit criteria**
- Round-trip and malformed-input tests pass.
- At least one small program executes end-to-end.

## Stage E — Privileged environment

**Work**
- Define boot hand-off and virtual platform.
- Implement trap entry and return.
- Implement minimal privileged kernel.
- Add a simple console output mechanism.

**Exit criteria**
- Emulator boots the experimental kernel.
- Kernel can report status and handle a controlled exception.

## Stage F — Expansion and evaluation

Possible later topics:
- Compiler backend.
- Better virtual memory.
- Floating-point and vector extensions.
- Multiple cores and memory consistency.
- Device model and storage.
- Physical implementation exploration, if useful.

Each extension requires a design record, specification, and tests. There is no obligation to implement every topic.

## Project status snapshot

| Area | Status |
|---|---|
| Charter and initial docs | Drafted |
| Veylith machine specification | v0 base profile accepted (doc 14); later profiles open |
| Emulator | Implemented for v0 |
| Assembler / disassembler | Implemented for v0 |
| Compiler backend | Not implemented |
| Bootloader | Not implemented (the emulator loads images directly) |
| Kernel | Kernelloom v0 implemented; no paging, interrupts or filesystem |
| Hardware | Not planned / not required |

## Guiding rule

Do not race toward a boot screen. A small, mathematically precise and testable ISA is a better achievement than a large kernel built on an undefined architecture.
