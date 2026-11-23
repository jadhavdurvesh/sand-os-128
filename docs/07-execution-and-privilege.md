# 07 — Execution and privilege

**Status:** Research draft

## 1. Execution-state contract

The architecture must define the complete architecturally visible state at instruction boundaries. At minimum this includes the instruction location, scalar registers, status state, memory-translation context, and privilege state.

The reference emulator should expose a deterministic single-step operation:
1. Fetch the next encoded instruction.
2. Validate fetch permissions and encoding.
3. Decode the instruction.
4. Check privilege and operand constraints.
5. Calculate its effects.
6. Commit the defined state changes, or enter the specified exception path.
7. Record a trace entry.

The specification must define whether faults can partially update state. The preferred initial rule is atomic architectural instruction retirement: either the instruction's specified effects occur, or the exception is taken with no unintended partial updates.

## 2. Privilege model

At least two protection domains are needed for a practical OS experiment:
- An unprivileged application domain.
- A privileged kernel domain.

The exact naming, number of levels, and transition mechanisms are open. The design must specify which instructions and registers are privileged and how transitions are validated.

## 3. Traps and exceptions

The architecture must distinguish synchronous exceptions (caused by the current instruction) from asynchronous interrupt events (delivered independently of the current instruction).

Candidate synchronous causes include:
- Invalid instruction encoding.
- Privilege violation.
- Arithmetic fault, if specified as trapping.
- Address translation fault.
- Alignment fault.
- Access permission violation.
- Explicit software trap.

The architecture must define vectoring, saved state, cause reporting, return behaviour, nesting rules, and priority.

## 4. Interrupts

Interrupt delivery requires a platform contract: source identification, masking, priority, pending state, and acknowledgement. A minimal emulator can model a small synthetic interrupt controller before real hardware is considered.

## 5. Reset and boot state

The initial processor state must be deterministic. The specification must state the initial instruction location, privilege state, register contents, translation state, and interrupt state. Unspecified reset values are a source of non-reproducible bugs and must be avoided.

## 6. Debug and tracing

The emulator should support deterministic single-step execution, breakpoints, architectural state inspection, and Tracebook output. Debug facilities must not alter normal instruction semantics.

## 7. Unresolved decisions

Exception vector format, context-save mechanism, interrupt controller interface, privilege transitions, and reset state remain open until recorded as accepted decisions.
