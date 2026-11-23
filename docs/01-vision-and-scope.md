# 01 — Vision and scope

**Status:** Initial project charter  
**Architecture codename:** Veylith (provisional)

## 1. Purpose

SAND-128 is a clean-sheet experiment in computer architecture and operating-system design. Its purpose is to explore a coherent 128-bit machine model, define an original instruction-set architecture (ISA), and eventually build a reference emulator and experimental kernel for that ISA.

The project is educational and experimental. It is not a product roadmap, a claim that current computers need 128-bit addressing, or a promise of performance improvements.

## 2. Design objectives

1. Define the machine contract before writing a kernel.
2. Give the architecture its own terminology, instruction semantics, encoding rules, and execution model.
3. Treat register width, arithmetic width, pointer width, virtual-address width, physical-address width, and instruction width as distinct design choices.
4. Make every architectural behaviour testable in a reference implementation.
5. Prefer a small, internally consistent first revision over a large collection of speculative features.
6. Keep the experimental implementation separate from SAND OS 64.

## 3. Non-goals

- Replacing SAND OS 64.
- Requiring or claiming compatibility with x86-64, AArch64, RISC-V, or their ABIs.
- Claiming that a 128-bit register automatically produces a faster computer.
- Claiming a 128-bit virtual address space is physically implementable in full.
- Designing commercial hardware or a mass-market processor.
- Promising binary compatibility with another architecture.
- Implementing every planned subsystem before the ISA is stable.

## 4. What “128-bit” means here

The initial research target is a 128-bit general-purpose scalar register model and native 128-bit integer operations. Other widths are separate choices:

| Property | Meaning | Initial direction |
|---|---|---|
| Scalar register width | Width of general-purpose registers | 128 bits |
| Integer operation width | Width supported by native integer instructions | 128 bits at minimum |
| Pointer width | Width of pointers in an ABI | Open |
| Virtual address width | Implemented virtual address bits | Open; need not be 128 |
| Physical address width | Implemented physical address bits | Open |
| Instruction encoding width | Number of bits used to encode instructions | Open |
| Vector width | Width of packed/vector operations | Open |

This separation is fundamental. A design can use 128-bit registers while supporting narrower pointers and address spaces.

## 5. Design principles

### Clarity over novelty theatre
A new name is useful only when it identifies a well-defined concept. Names must not conceal borrowed behaviour or make the design harder to understand.

### Specify before implementing
Every instruction needs defined operands, result behaviour, flags or status effects, exceptions, and edge cases before it enters the accepted ISA.

### Emulator as executable specification
The reference emulator should be the authority for deterministic instruction behaviour. The written ISA and tests must agree with it.

### Explicit status
Documents and features use these labels:
- **Proposed:** a candidate design, open to revision.
- **Accepted:** a design decision approved for the current architecture revision.
- **Implemented:** code exists.
- **Verified:** tests demonstrate the specified behaviour.
- **Deferred:** intentionally postponed.
- **Rejected:** considered and not selected.

## 6. Relationship to SAND OS 64

SAND OS 64 remains the primary operating-system project. SAND-128 is a separate research repository and may share ideas, lessons, or high-level tooling conventions, but it must not silently inherit an existing architecture's ABI or machine model.

## 7. Success criteria

The first meaningful success is not a bootable desktop. It is a reviewed architecture document set, a minimal executable specification, and a small emulator that passes hand-authored conformance tests for the first instruction subset.
