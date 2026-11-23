# Veylith 128-Native v1 — GitHub Actions runtime guide

This guide documents the reproducible development runtime for SAND-128 (Veylith). The workflow executes the Python reference emulator; it does not run on a physical 128-bit processor.

## 1. What CI does

The `Veylith CI` workflow has two jobs:

1. **Conformance:** runs unit and integration tests on Python 3.11, 3.12, and 3.13, then checks that the generated opcode table exactly matches the committed machine-readable table.
2. **Runtime demonstration:** boots a selected user program through Kernelloom, prints the complete configured machine profile, checks the expected output, and optionally uploads a Tracebook execution trace.

Pushes to `main` and pull requests run the default demonstration. A manual workflow dispatch exposes runtime inputs.

## 2. Workflow inputs

| Input | Default | Accepted values / constraints | Meaning |
|---|---:|---|---|
| `scenario` | `hello` | `hello`, `factorial`, `badptr` | User program loaded by the kernel |
| `python_version` | `3.12` | `3.11`, `3.12`, `3.13` | Python runtime for the demonstration job |
| `ram_bytes` | `1048576` | Integer, at least 131072, multiple of 16, below 4026531840 | Emulated RAM capacity in bytes |
| `max_steps` | `5000000` | Positive integer | Maximum execution steps before the emulator stops with a step-limit reason |
| `trace` | `false` | Boolean | Whether to save Tracebook JSONL output as a workflow artifact |

The minimum RAM is 131072 bytes (128 KiB) because Kernelloom uses fixed kernel and user-memory regions. RAM must be a multiple of 16 bytes. Console MMIO is mapped near the top of the 128-bit virtual address space; this is independent of the bounded RAM allocation.

These constraints describe the current v0 demonstration platform, not a universal limitation on all future Veylith designs.

## 3. Machine parameters printed by the runtime

The `info` command and every execution print:

- Architecture and profile: SAND-128 / Veylith 128-Native v1.
- Emulator software version.
- Register width, register count, and total architectural register-file bits.
- Instruction glyph width in bits and bytes.
- Virtual address width.
- Program-counter width.
- Endianness.
- Configured RAM in bytes and MiB.
- Console MMIO address.
- Configured maximum execution steps.
- Execution model (deterministic, sequential, single-core).

The runtime summary additionally prints the selected workload, number of loaded images, trace status, stop reason, exit code, retired glyph count, final PC, and final privilege level.

The register-file bit count is the sum of architectural register widths (128 × 128). It is not a claim about physical silicon area or total processor state.

## 4. Scenarios

### hello

A minimal user-mode application. It invokes Kernelloom's write system call, prints `Hello from Veylith 128-Native v1!`, then exits with code zero.

### factorial

Demonstrates native 128-bit integer operations by computing 34! and printing the 128-bit boundary value 2^127. It exits with code zero.

### badptr

Attempts to access memory outside the user aperture. Kernelloom should catch the ACCESS fault, report cause 5 and address 256, then halt with exit code 133 (128 + cause 5). This is an expected fault demonstration; the workflow treats the expected nonzero emulator exit as a successful test.

## 5. Run locally

From the repository root:

```bash
python -m veylith info
python -m veylith info --ram 2097152 --max-steps 8000000 --json
python -m veylith boot examples/hello.s
python -m veylith boot examples/factorial.s --ram 1048576 --max-steps 5000000 --trace tracebook.jsonl
python -m veylith boot examples/badptr.s
python -W error -m unittest discover -s tests -v
```

## 6. Run from GitHub

1. Open the repository's **Actions** tab.
2. Select **Veylith CI**.
3. Choose **Run workflow**.
4. Select the scenario and Python version.
5. Set RAM bytes and maximum steps.
6. Enable Tracebook if an instruction-by-instruction JSONL trace is wanted.
7. Start the workflow and inspect the job logs.
8. If tracing was enabled, download the `veylith-tracebook` artifact from the completed run (artifact name includes the run number).

## 7. Interpreting results

- **Conformance success** means the current emulator, assembler, image reader, kernel integration tests, and opcode-table consistency tests passed on the listed Python versions.
- **Runtime success** means the selected scenario produced its expected output and exit behaviour.
- **Step limit** means the configured execution budget was reached before the guest halted. Increase `max_steps` only when the workload is expected to require more work; do not hide an infinite loop by simply raising the limit.
- **Tracebook** is a deterministic execution record for debugging. It is not a hardware performance trace.

## 8. Scope and limitations

This CI system runs a software reference model. It does not synthesize RTL, emulate cycle-accurate hardware, boot on a physical CPU, or establish that a physical 128-bit processor exists. The emulator is sequential and single-core; paging, interrupts, atomics, floating point, a compiler, filesystem, and physical hardware remain outside the v0 profile.
