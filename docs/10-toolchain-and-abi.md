# 10 — Toolchain and ABI

**Status:** Planned; not implemented  
**Working term:** Forgepath (provisional)

## 1. Toolchain components

The project will eventually need:
- An assembler for the Veylith instruction set.
- A disassembler for inspection and debugging.
- An object-file and executable-image format.
- A linker and relocation model.
- A compiler backend or a small compiler experiment.
- Runtime and system library conventions.
- Emulator integration and conformance tests.

## 2. Build sequence

The recommended sequence is:
1. Define encodings and instruction semantics.
2. Write a small assembler for the first accepted subset.
3. Write a disassembler and round-trip tests.
4. Define object and executable formats.
5. Add a linker for a minimal image.
6. Add compiler support only after the ABI is stable.

## 3. ABI decisions

The application binary interface must define:
- Pointer width and representation.
- Argument and return-value locations.
- Register preservation rules.
- Stack layout and alignment.
- Structure layout and padding.
- System-call convention.
- Relocation types.
- Exception and unwind conventions, if supported.
- Symbol naming and object-file metadata.

A 128-bit register width does not automatically mean pointers are 128 bits or that every function argument occupies a full register.

## 4. Object and executable format

The format should be self-identifying and versioned. It should specify architecture identity, ABI version, endianness, entry point, segments, permissions, relocations, and optional feature requirements. The project should not reuse another format's machine identifier or claim compatibility without a deliberate mapping.

## 5. Compiler strategy

A compiler backend can target an established intermediate representation if that reduces work, but the target description, register model, calling convention, instruction selection, and object format must represent Veylith accurately. Compiler support is not evidence that physical hardware exists.

## 6. Testing

Required tests include assembler/disassembler round trips, relocation checks, ABI conformance programs, emulator execution, malformed image rejection, and compatibility checks between toolchain versions.
