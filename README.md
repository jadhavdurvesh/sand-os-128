# SAND-128

**An experimental clean-sheet computing architecture and operating-system research project.**

SAND-128 explores what a deliberately designed 128-bit computing architecture could look like when its instruction set, machine model, tooling, and operating system are designed together rather than inherited from an existing desktop architecture.

This repository is an independent experiment in the SAND ecosystem. It does not replace or redirect the main 64-bit SAND OS project.

> **Research status:** The Veylith v0 base profile is specified and has a working Python reference emulator, assembler/disassembler and a small kernel (Kernelloom v0) written in Veylith assembly. There is no hardware, no compiler and no performance claim. Everything else in the docs remains a proposal.

SAND-128 is pure 128-bit and standalone: its kernel is written for the Veylith ISA and runs on the Veylith emulator. It is not built on, and shares no code with, the 64-bit SAND OS.

## Project principles

- **Clean-sheet design:** define the machine model instead of cloning x86, ARM, or RISC-V.
- **Coherent terminology:** use SAND-128's own names for architectural concepts where useful.
- **Explicit contracts:** specify behaviour, encodings, exceptions, and invariants before implementation.
- **Emulation first:** validate the architecture in a deterministic software model before considering physical hardware.
- **Measured claims:** distinguish proposals, implemented features, and verified behaviour.
- **Independent evolution:** keep this project separate from the primary SAND OS 64-bit codebase.

## Initial design direction

The project will investigate a 128-bit general-purpose register model and native wide arithmetic. Address width, pointer representation, instruction encoding, floating-point behaviour, privilege levels, and memory translation are separate design decisions; none should be assumed merely from the phrase “128-bit”.

The initial architecture is intentionally not frozen. The documents in [docs/](docs/) establish a vocabulary and a decision process. Any proposed encoding or behaviour remains provisional until specified precisely and covered by tests.

## SAND Universal Architecture Foundation

All architectures in the SAND family follow the shared [SAND Universal Architecture Foundation (SUAF)](docs/00-sand-universal-architecture-foundation.md). It establishes common engineering principles and terminology while preserving independent instruction sets, register models, memory contracts, execution semantics, and ABIs.

## Documentation

| Document | Purpose |
|---|---|
| [Vision and scope](docs/01-vision-and-scope.md) | Goals, non-goals, principles, and project boundaries |
| [Architecture overview](docs/02-architecture-overview.md) | Machine model and major architectural layers |
| [Core vocabulary](docs/03-core-vocabulary.md) | Project-specific names and terminology |
| [Register and data model](docs/04-register-and-data-model.md) | Register classes, values, and data representation |
| [Instruction architecture](docs/05-instruction-architecture.md) | Instruction design goals and encoding questions |
| [Memory architecture](docs/06-memory-architecture.md) | Addressing, translation, protection, and memory model |
| [Execution and privilege](docs/07-execution-and-privilege.md) | Execution states, traps, and privilege model |
| [Emulator plan](docs/08-emulator-plan.md) | Reference emulator scope and validation strategy |
| [Kernel architecture](docs/09-kernel-architecture.md) | Kernel responsibilities and boot strategy |
| [Toolchain and ABI](docs/10-toolchain-and-abi.md) | Assembler, compiler, object format, and calling convention |
| [Roadmap](docs/11-roadmap.md) | Research milestones and exit criteria |
| [Decision register](docs/12-decision-register.md) | Open decisions and accepted design records |
| [Originality and naming policy](docs/13-originality-and-naming-policy.md) | Rules for custom design and project terminology |
| [Veylith v0 base profile](docs/14-veylith-v0-spec.md) | The accepted, implemented v0 machine contract |
| [Decision-record template](docs/templates/decision-record-template.md) | Reusable format for future architecture decisions |

## Try it

Requires Python 3.9+ and nothing else.

```bash
python3 -m veylith boot                       # Kernelloom boots examples/factorial.s on the emulator
python3 -m veylith boot examples/badptr.s     # a user fault caught by the kernel
python3 -m veylith asm prog.s -o prog.vyl     # assemble
python3 -m veylith dis prog.vyl               # disassemble
python3 -m veylith run kernel.vyl user.vyl --trace trace.jsonl
python3 -m unittest discover -s tests         # 50 tests
```

## Repository layout

```text
.
├── docs/                 Architecture specifications and design records
├── architecture/         Machine-readable glyph table (generated from veylith/isa.py)
├── veylith/              Reference emulator, assembler/disassembler, image format, CLI
├── kernel/               Kernelloom v0 (Veylith assembly)
├── examples/             User programs for Kernelloom
├── tests/                Conformance and integration tests
├── boot/ toolchain/      (future)
└── README.md
```

## Development status

| Area | Status |
|---|---|
| Project charter | Drafted |
| Veylith v0 base profile | Accepted; implemented; verified in the emulator |
| Reference emulator | Implemented (Python, single core, deterministic, Tracebook) |
| Assembler / disassembler / image format | Implemented |
| Kernelloom v0 | Implemented: user mode, aperture protection, 2 syscalls, fault reporting |
| Paging, interrupts, atomics, floating point | Not implemented |
| Compiler, filesystem, devices beyond a console | Not implemented |
| Hardware | Not planned |

## Contributing to the design

Before implementing a subsystem:

1. Describe the problem and design constraints.
2. Record alternatives and trade-offs.
3. Specify observable behaviour and failure conditions.
4. Add examples and conformance tests.
5. Mark the decision as proposed, accepted, implemented, or verified.

See [the decision register](docs/12-decision-register.md) for the current design questions and [CONTRIBUTING.md](CONTRIBUTING.md) for the design workflow.

## License

No license has been selected yet. Until a license file is added, all rights are reserved by the repository owner; do not assume the code or documentation may be reused, redistributed, or modified under an open-source license.
