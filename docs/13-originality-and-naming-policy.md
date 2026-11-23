# 13 — Originality and naming policy

**Status:** Project policy

## 1. Intent

SAND-128 is intended to become a genuinely custom architecture, not an existing ISA with a new logo or renamed instructions. The project will define its own machine contract, instruction semantics, encoding, register conventions, exception model, memory-management contract, and software ABI.

## 2. What must be designed independently

The following are architectural decisions and must be specified for Veylith rather than inherited by default:

- Instruction encoding and decode rules.
- Instruction semantics, operand rules, and exception behaviour.
- Register inventory and special-state layout.
- Arithmetic overflow, shift, division, and comparison rules.
- Control-flow and call/return behaviour.
- Privilege levels and protected transitions.
- Trap, interrupt, and reset behaviour.
- Address representation and translation format.
- Memory access, atomicity, and ordering rules.
- Executable format, calling convention, and system-call ABI.

A design may choose a familiar solution after analysis. Originality does not require making every choice bizarre; it requires deliberate specification rather than accidental cloning.

## 3. Reference research

Existing architectures, operating systems, compiler designs, and academic papers may be studied to understand trade-offs. When a specific design is materially derived from a source, document the source and the adaptation. Do not copy proprietary text, code, diagrams, or specifications into this repository.

## 4. Naming system

The initial project vocabulary is:

| Project term | Intended meaning |
|---|---|
| Veylith | SAND-128's proposed architecture |
| Veyl | A proposed 128-bit general-purpose scalar register |
| Veylset | The complete scalar-register bank |
| Glyph | A decoded instruction operation |
| Glyphstream | A sequence of encoded instructions |
| Kernelloom | The proposed privileged kernel environment |
| Tracebook | Deterministic machine-execution trace |
| Forgepath | Toolchain path from source or assembly to executable image |

These names are provisional. A term can be changed if it proves confusing, collides with another project, or is difficult to use consistently. The repository does not assert that these words are globally unique or legally available as trademarks.

## 5. Naming rules

- Use a term for one concept only.
- Keep standard technical vocabulary where it is clearer.
- Avoid names that intentionally imitate existing vendor branding.
- Record definitions centrally.
- Do not use a name as evidence that a feature exists.
- Version externally visible names only when compatibility depends on them.

## 6. Originality is demonstrated by artefacts

The evidence of a custom architecture will be the published specification, machine-readable ISA definitions, independent emulator, conformance tests, assembler/disassembler, and ABI documentation. A unique collection of names alone is not sufficient.

## 7. Implementation status honesty

Every public description must distinguish conceptual proposals from tested implementation. The project must not claim a working processor, bootable kernel, 128-bit physical address space, or performance advantage until there is evidence.
