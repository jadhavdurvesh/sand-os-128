# 02 — Architecture overview

**Status:** Proposed architecture outline  
**Architecture codename:** Veylith

## 1. Architectural layers

Veylith is the provisional name for the machine architecture being designed by SAND-128. It is a specification, not a processor implementation.

The design is divided into layers so that decisions at one layer do not accidentally dictate unrelated decisions at another.

1. **Value model** — scalar widths, integer representation, register semantics.
2. **Instruction model** — operations, operands, encoding, decode rules.
3. **Execution model** — sequencing, control transfer, traps, and architectural state.
4. **Memory model** — address spaces, translation, permissions, ordering, and faults.
5. **Protection model** — privilege domains and controlled transitions.
6. **Platform contract** — reset state, boot hand-off, interrupts, timers, and devices.
7. **Software contract** — object format, calling convention, system-call ABI, and runtime.

## 2. Proposed machine profile

The first profile is deliberately modest:

- 128-bit general-purpose scalar registers.
- Native 128-bit integer arithmetic.
- A deterministic, precisely specified execution model.
- A software reference emulator before physical hardware work.
- A minimal privileged execution model for kernel experiments.
- Address width and instruction encoding selected only after documenting trade-offs.

The number of registers, instruction length, status-register design, and exact addressing scheme are not frozen in this revision.

## 3. Architectural state

The emulator will model all state that software can observe. Candidate state groups include:

- General-purpose scalar registers.
- Instruction-location state.
- Processor status and condition state, if the final ISA uses it.
- Memory-translation context.
- Privilege and exception state.
- Interrupt-control state.
- Optional extension state.

The specification must define which state is visible to unprivileged programs, which state is privileged, and what happens to state during reset, trap entry, and return.

## 4. Execution model

The first implementation should be sequential and deterministic. Parallel execution, out-of-order execution, speculative behaviour, cache coherence, and multicore consistency are deferred until the sequential architectural contract is stable.

An implementation may internally use any microarchitecture as long as its externally visible behaviour conforms to the ISA.

## 5. Addressing is not register width

A 128-bit register can hold values wider than any practical physical address. Veylith must define address formation and validation explicitly. It must never assume every bit pattern in a 128-bit register is a valid address.

Virtual and physical address widths will be selected as implementation parameters in an architecture profile, with canonical-address rules, translation structures, and fault behaviour specified independently.

## 6. Profiles and extensions

The project may eventually define named profiles, but the base architecture should remain small. An extension must specify:
- New architectural state, if any.
- Instruction encodings and decode priority.
- Feature discovery.
- Reset and privilege behaviour.
- Emulator and conformance tests.
- Compatibility rules for future revisions.

No extension name is reserved as stable until its design record is accepted.

## 7. Open architectural questions

See [the decision register](12-decision-register.md). The most important unresolved topics are instruction encoding, register count, address widths, endianness, flags versus explicit-result operations, privilege transitions, and interrupt delivery.
