# 05 — Instruction architecture

**Status:** Research draft  
**Terminology:** A decoded operation is provisionally called a *Glyph*.

## 1. Design goals

The Veylith instruction set should be:
- Small enough to implement in a reference emulator.
- Precise enough to support conformance tests.
- Regular enough for an assembler and compiler backend.
- Extensible without ambiguous decoding.
- Designed around the 128-bit scalar model without assuming every operation must consume or produce 128 bits.

## 2. Instruction families to investigate

These are candidate groups, not an accepted opcode list:

| Family | Intended responsibility |
|---|---|
| Data movement | Register copies, immediate values, memory transfers |
| Integer arithmetic | Addition, subtraction, multiplication, division |
| Bit operations | Boolean operations, shifts, rotates, bit tests |
| Comparison | Signed and unsigned comparisons |
| Control transfer | Branches, calls, returns |
| Privileged control | State transitions and control-register access |
| Memory ordering | Explicit ordering and synchronization operations |
| System interface | Traps or system-call entry |
| Extension operations | Optional floating-point or vector work |

## 3. Encoding questions

The architecture has not selected fixed-length or variable-length instructions. The decision record must compare:
- Decode simplicity.
- Code density.
- Immediate operand size.
- Extension space.
- Alignment and fetch behaviour.
- Disassembler complexity.
- Emulator and compiler implementation cost.

No numeric opcode assignments are stable in this draft.

## 4. Semantic contract

Each accepted Glyph specification must contain:

1. Mnemonic and stable identifier.
2. Binary encoding and field definitions.
3. Operand count, types, and legal register classes.
4. Exact result calculation.
5. Architectural state read and written.
6. Status effects.
7. Exceptions and priority when multiple faults are possible.
8. Privilege requirements.
9. Execution examples.
10. Positive, negative, boundary, and aliasing tests.

## 5. Immediate values

The design must explain how constants are represented, how they are extended to 128 bits, and how larger constants are constructed. It must avoid silently truncating values.

## 6. Control flow

Branches must define their target calculation, alignment, range, and behaviour when the target is invalid. Call and return semantics must specify where return state is stored and how privilege boundaries are enforced.

## 7. Reserved encodings

Reserved and unsupported encodings must have deterministic behaviour, preferably a specified illegal-instruction exception. They must not accidentally execute as a different operation.

## 8. First instruction subset

The first emulator milestone should implement only a minimal set sufficient for arithmetic tests, register movement, memory access, a conditional branch, and a controlled halt or trap mechanism. Exact opcodes will be added only after encoding decisions are accepted.
