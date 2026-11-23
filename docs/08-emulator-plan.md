# 08 — Emulator plan

**Status:** Planned; not implemented

## 1. Purpose

The reference emulator will be the first executable form of Veylith. It should prioritise correctness, observability, and reproducibility over speed.

## 2. Core components

- **Image reader:** validates the test image and its declared format.
- **Decoder:** converts encoded instruction bytes into Glyph operations.
- **Architectural state:** stores registers, instruction location, status, and control state.
- **Memory model:** provides bounded memory and access validation.
- **Executor:** applies the exact specified instruction semantics.
- **Exception engine:** implements defined traps and faults.
- **Tracebook writer:** records instruction, inputs, outputs, and state changes.
- **Test harness:** runs conformance programs and compares expected outcomes.

## 3. Implementation discipline

Do not use the host machine's native integer width as an implicit specification. Use explicit helpers for 128-bit values. A two-limb representation (for example, high and low 64-bit halves) is a portable implementation option when the host language does not provide a suitable unsigned 128-bit type.

The emulator must define wrapping, signed interpretation, shifts, division, and comparison explicitly. Host-language undefined behaviour must not leak into guest execution.

## 4. Determinism

Given the same image, initial state, and event sequence, the emulator should produce the same architectural trace. External input, timers, and interrupts must be explicit inputs to the execution model.

## 5. Testing layers

1. Unit tests for 128-bit arithmetic helpers.
2. Decoder tests for valid and invalid encodings.
3. Per-instruction semantic tests.
4. Boundary tests for zero, maximum values, sign boundaries, and overflow.
5. Memory permission and address-fault tests.
6. Trap and privilege tests.
7. Full-program integration tests.
8. Differential tests between the written specification, emulator, and any future second implementation.

## 6. Tracebook format

A trace record should include the instruction location, raw encoding, decoded operation, source values, destination values, memory effects, status changes, and any exception. The trace format itself must be versioned.

## 7. Milestones

- M0: arithmetic helper tests.
- M1: empty machine state and deterministic step API.
- M2: first accepted instructions.
- M3: memory and control-flow tests.
- M4: trap and privilege model.
- M5: load and run a tiny test image.

The emulator is not started until the basic instruction and state contracts are sufficiently stable.
