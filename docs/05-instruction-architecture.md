# 05 — Instruction architecture

**Accepted profile:** Veylith 128-Native v1.  
**Instruction unit:** Glyph, fixed 128 bits (16 bytes).

| Field | Bits | Width |
|---|---|---:|
| Opcode | 127:112 | 16 |
| rd | 111:104 | 8 |
| ra | 103:96 | 8 |
| rb | 95:88 | 8 |
| Immediate | 87:0 | 88 |

Register fields address v0–v128; v0 is the zero constant and v1–v128 are writable GPRs. All bits in the 128-bit Glyph are assigned. Any operand fields unused by an opcode must be zero. Illegal encodings trap. Glyphs are little-endian and aligned to 16-byte boundaries.

Most immediate operands are signed 88-bit values. ldk sign-extends its immediate. shk combines the destination's low 40 bits shifted left by 88 with the unsigned 88-bit immediate, allowing li to synthesize any 128-bit value in at most two Glyphs.

Relative branch and jump offsets are measured in Glyph units and multiplied by 16. Link addresses advance by 16 bytes. The authoritative opcode definitions are generated from veylith/isa.py and mirrored in architecture/veylith-v0-glyphs.json.
