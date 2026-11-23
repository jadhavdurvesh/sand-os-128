# 04 — Register and data model

**Accepted Veylith 128-Native v1 parameters**

- Scalar register width: 128 bits.
- General-purpose register count: 128 registers, v0–v127.
- Register-file capacity: 16,384 bits.
- v0 is hardwired to zero; v126 aliases sp; v127 aliases lr.
- Register indices are seven bits; all register values are 128-bit bit-vectors.
- Unsigned integer range: 0 to 2^128−1.
- Signed two's-complement range: −2^127 to 2^127−1.
- Arithmetic results wrap modulo 2^128 unless an instruction defines otherwise.

The 128-bit register file does not imply a particular floating-point, decimal, sexagesimal, vector, or residue-number format. Those are separately specified numerical-system tracks under SNSR. All emulator operations must mask results to 128 bits.
