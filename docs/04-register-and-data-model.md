# 04 — Register and data model

**Status:** Research draft  
**Core target:** 128-bit scalar registers

## 1. Width terminology

A *bit* is a binary digit. An *octet* is exactly eight bits. A 128-bit value therefore contains 16 octets.

The architecture must distinguish:
- Register width.
- Integer operation width.
- Memory access width.
- Pointer width.
- Virtual and physical address widths.
- Instruction encoding width.

These widths are related by explicit rules, not by assumption.

## 2. Candidate scalar bank

The initial design target is a bank of 128-bit general-purpose registers. The final register count and register naming convention remain open.

For the first specification, each scalar register is treated as an unsigned 128-bit bit-vector for storage. Individual instructions interpret that bit-vector as unsigned, two's-complement signed, or another explicitly documented representation.

A 128-bit bit-vector has (2^{128}) possible patterns. Its unsigned range is 0 through (2^{128}-1). If interpreted as two's-complement signed, its range is (-2^{127}) through (2^{127}-1).

## 3. Arithmetic semantics

Every arithmetic instruction must define:
- Operand interpretation.
- Result width.
- Whether overflow wraps, traps, or sets defined status.
- Carry and borrow semantics, if exposed.
- Division-by-zero behaviour.
- Signed division corner cases.
- Shift-count interpretation.
- Whether the destination may alias a source.

The base design should avoid relying on host-language overflow behaviour in the emulator. Use explicit 128-bit arithmetic helpers or a well-defined multi-limb representation.

## 4. Loads and stores

Memory operations need an explicit list of supported widths and alignment rules. A 128-bit register does not imply every load or store transfers 128 bits.

The specification must define:
- Supported access sizes.
- Alignment requirements.
- Unaligned access behaviour.
- Byte order.
- Sign and zero extension.
- Atomicity guarantees.
- Fault behaviour for invalid or protected memory.

## 5. Status and condition state

It remains open whether the architecture uses a conventional condition-code register, explicit predicate registers, or instructions that write results without global flags.

The choice must consider compiler quality, interrupt preservation, instruction complexity, and emulator simplicity.

## 6. Floating point and vectors

Floating-point and vector processing are separate extensions. Their formats, rounding modes, exception behaviour, and state-management costs must be specified independently. The initial scalar integer core should not depend on them.

## 7. Serialization

The architecture must define a canonical byte representation for memory and executable files. Host endianness must never affect emulator behaviour or file interpretation.

## 8. Current decisions

- **Proposed:** general-purpose scalar register width is 128 bits.
- **Open:** register count, register names, special-register layout, condition-state design, floating-point format, vector model, and endianness.
- **Required:** deterministic semantics independent of host CPU behaviour.
