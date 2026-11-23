# SAND-128

**An experimental clean-sheet computing architecture and operating-system research project.**

SAND-128 explores what a deliberately designed 128-bit computing architecture could look like when its instruction set, machine model, tooling, and operating system are designed together rather than inherited from an existing desktop architecture.

This repository is an independent experiment in the SAND ecosystem. It does not replace or redirect the main 64-bit SAND OS project.

> **Research status:** The Veylith 128-Native v1 base profile is specified and has a working Python reference emulator, assembler/disassembler and a small kernel (Kernelloom v0) written in Veylith assembly. There is no physical hardware, production compiler, or performance claim yet. Features not explicitly marked as implemented remain research proposals.

SAND-128 is pure 128-bit and standalone: its kernel is written for the Veylith ISA and runs on the Veylith emulator. It is not built on, and shares no code with, the 64-bit SAND OS.

## Project principles

- **Clean-sheet design:** define the machine model instead of cloning x86, ARM, or RISC-V.
- **Coherent terminology:** use SAND-128's own names for architectural concepts where useful.
- **Explicit contracts:** specify behaviour, encodings, exceptions, and invariants before implementation.
- **Emulation first:** validate the architecture in a deterministic software model before considering physical hardware.
- **Measured claims:** distinguish proposals, implemented features, and verified behaviour.
- **Independent evolution:** keep this project separate from the primary SAND OS 64-bit codebase.

## Initial design direction

**Veylith 128-Native v1 is the active implementation profile:** 128 general-purpose registers of 128 bits each, 128-bit instruction Glyphs, 128-bit virtual addresses and pointers, and a 128-bit program counter. Instructions are 16-byte aligned and executable images use VYLI v2. The emulator models the full 128-bit virtual address domain over bounded physical RAM; virtual width does not imply physically installed memory of that size.

## SAND Universal Architecture Foundation

All architectures in the SAND family follow the shared [SAND Universal Architecture Foundation (SUAF)](docs/00-sand-universal-architecture-foundation.md). It establishes common engineering principles and terminology while preserving independent instruction sets, register models, memory contracts, execution semantics, and ABIs.


## Numerical Systems Research

The shared [SAND Numerical Systems Research (SNSR)](docs/22-sand-numerical-systems-research.md) programme investigates alternative radices and numeric representations, including **sexagesimal (base-60)**, balanced ternary, decimal/BCD, fixed- and floating-point, and residue number systems. These are research topics, not claims that every format is implemented in the ISA.

## Documentation

| Document | Purpose |
|---|---|
| [Vision and scope](docs/01-vision-and-scope.md) | Goals, non-goals, principles, and project boundaries |
| [Architecture overview](docs/02-architecture-overview.md) | Machine model and major architectural layers |
| [Core vocabulary](docs/03-core-vocabulary.md) | Project-specific names and terminology |
| [Register and data model](docs/04-register-and-data-model.md) | Register classes, values, and data representation |
| [Instruction architecture](docs/05-instruction-architecture.md) | 128-bit Glyph encoding, operand rules, and execution semantics |
| [Memory architecture](docs/06-memory-architecture.md) | 128-bit virtual addressing, bounded physical memory, and protection model |
| [Execution and privilege](docs/07-execution-and-privilege.md) | Execution states, traps, and privilege model |
| [Emulator plan](docs/08-emulator-plan.md) | Reference emulator scope and validation strategy |
| [Kernel architecture](docs/09-kernel-architecture.md) | Kernel responsibilities and boot strategy |
| [Toolchain and ABI](docs/10-toolchain-and-abi.md) | Assembler, compiler, object format, and calling convention |
| [Roadmap](docs/11-roadmap.md) | Research milestones and exit criteria |
| [Decision register](docs/12-decision-register.md) | Open decisions and accepted design records |
| [Originality and naming policy](docs/13-originality-and-naming-policy.md) | Rules for custom design and project terminology |
| [Veylith 128-Native v1 base profile](docs/14-veylith-v0-spec.md) | The accepted, implemented v0 machine contract |
| [Decision-record template](docs/templates/decision-record-template.md) | Reusable format for future architecture decisions |

## Try it

Requires Python 3.11+ and nothing else.

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


## Run Veylith locally

Requires Python 3.11+ and no third-party packages.

```bash
# Print every architectural and machine parameter
python -m veylith info

# Boot the simple user-mode hello program under Kernelloom
python -m veylith boot examples/hello.s

# Run the 128-bit arithmetic demonstration
python -m veylith boot examples/factorial.s

# Exercise the user/kernel memory protection boundary
python -m veylith boot examples/badptr.s

# Configure RAM, execution budget, and a JSONL instruction trace
python -m veylith boot examples/factorial.s --ram 1048576 --max-steps 5000000 --trace tracebook.jsonl

# Run the full test suite
python -W error -m unittest discover -s tests -v
```

## Runtime parameters and machine configuration

The emulator exposes its machine profile with `python -m veylith info`. The runtime prints the selected profile to the GitHub Actions log before booting. See [the GitHub Actions runtime guide](docs/15-github-actions-runtime.md) for parameter meanings, constraints, defaults, and examples.

## GitHub Actions

The **Veylith CI** workflow runs the conformance suite on Python 3.11, 3.12, and 3.13, checks that the machine-readable opcode table matches the implementation, and boots a user program under Kernelloom.

Use **Actions → Veylith CI → Run workflow** to select a scenario and runtime parameters. The workflow prints the selected parameters and the complete Veylith machine profile. Optional Tracebook output is uploaded as a workflow artifact.

## Development status

| Area | Status |
|---|---|
| Project charter | Drafted |
| Veylith 128-Native v1 base profile | Accepted; implemented; verified in the emulator |
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
