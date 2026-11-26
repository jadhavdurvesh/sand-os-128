"""Veylith v0 instruction table: the single source for the assembler, disassembler and emulator."""
import json
import sys

WIDTH = 128
MASK = (1 << WIDTH) - 1
SIGN = 1 << (WIDTH - 1)
GLYPH_BYTES = 16
VA_BITS = 128
NUM_GPRS = 128
NUM_VEYLS = NUM_GPRS + 1
REG_BITS = 8
IMM_BITS = 88
IMM_MASK = (1 << IMM_BITS) - 1

# Glyph layout (128 bits): op[127:112] rd[111:104] ra[103:96] rb[95:88] imm[87:0]
# Which fields a format uses; every unused field must be zero or the glyph is illegal.
FORMATS = {
    "rrr": ("rd", "ra", "rb"),
    "rri": ("rd", "ra", "imm"),
    "ld": ("rd", "ra", "imm"),
    "ri": ("rd", "imm"),
    "rr": ("rd", "ra"),
    "st": ("ra", "rb", "imm"),
    "br": ("ra", "rb", "imm"),
    "j": ("imm",),
    "jal": ("rd", "imm"),
    "jr": ("rd", "ra", "imm"),
    "none": (),
    "csrr": ("rd", "imm"),
    "csrw": ("ra", "imm"),
}

_T = [
    # name, code, fmt, summary
    ("nop", 0x00, "none", "no operation"),
    ("halt", 0x01, "none", "stop the machine (kernel only); exit code = v1"),
    ("add", 0x10, "rrr", "rd = ra + rb (wraps mod 2^128)"),
    ("sub", 0x11, "rrr", "rd = ra - rb (wraps)"),
    ("mul", 0x12, "rrr", "rd = low 128 bits of ra * rb"),
    ("mulh", 0x13, "rrr", "rd = high 128 bits of unsigned ra * rb"),
    ("udiv", 0x14, "rrr", "rd = ra / rb unsigned; rb == 0 traps DIVZERO"),
    ("sdiv", 0x15, "rrr", "rd = ra / rb signed, truncated toward zero; MIN / -1 = MIN; rb == 0 traps"),
    ("urem", 0x16, "rrr", "rd = ra % rb unsigned; rb == 0 traps DIVZERO"),
    ("srem", 0x17, "rrr", "rd = ra - rb * (ra sdiv rb); MIN rem -1 = 0; rb == 0 traps"),
    ("and", 0x18, "rrr", "rd = ra & rb"),
    ("or", 0x19, "rrr", "rd = ra | rb"),
    ("xor", 0x1A, "rrr", "rd = ra ^ rb"),
    ("shl", 0x1B, "rrr", "rd = ra << (rb mod 128)"),
    ("shr", 0x1C, "rrr", "rd = ra >> (rb mod 128), zero fill"),
    ("sar", 0x1D, "rrr", "rd = ra >> (rb mod 128), sign fill"),
    ("rol", 0x1E, "rrr", "rd = ra rotated left by rb mod 128"),
    ("ror", 0x1F, "rrr", "rd = ra rotated right by rb mod 128"),
    ("addi", 0x20, "rri", "rd = ra + sext(imm)"),
    ("andi", 0x21, "rri", "rd = ra & sext(imm)"),
    ("ori", 0x22, "rri", "rd = ra | sext(imm)"),
    ("xori", 0x23, "rri", "rd = ra ^ sext(imm)"),
    ("shli", 0x24, "rri", "rd = ra << (imm mod 128)"),
    ("shri", 0x25, "rri", "rd = ra >> (imm mod 128), zero fill"),
    ("sari", 0x26, "rri", "rd = ra >> (imm mod 128), sign fill"),
    ("slt", 0x28, "rrr", "rd = 1 if ra < rb signed else 0"),
    ("sltu", 0x29, "rrr", "rd = 1 if ra < rb unsigned else 0"),
    ("seq", 0x2A, "rrr", "rd = 1 if ra == rb else 0"),
    ("ldk", 0x30, "ri", "rd = sext(imm)"),
    ("shk", 0x31, "ri", "rd = ((rd & ((1 << 40) - 1)) << 88) | zext(imm[87:0])"),
    ("clz", 0x32, "rr", "rd = count of leading zero bits of ra (128 for zero)"),
    ("popc", 0x33, "rr", "rd = number of set bits of ra"),
    ("lb", 0x40, "ld", "rd = zext(mem8[ra + sext(imm)])"),
    ("lh", 0x41, "ld", "rd = zext(mem16[...])"),
    ("lw", 0x42, "ld", "rd = zext(mem32[...])"),
    ("ld", 0x43, "ld", "rd = zext(mem64[...])"),
    ("lq", 0x44, "ld", "rd = mem128[...]"),
    ("lbs", 0x45, "ld", "rd = sext(mem8[...])"),
    ("lhs", 0x46, "ld", "rd = sext(mem16[...])"),
    ("lws", 0x47, "ld", "rd = sext(mem32[...])"),
    ("lds", 0x48, "ld", "rd = sext(mem64[...])"),
    ("sb", 0x50, "st", "mem8[ra + sext(imm)] = rb"),
    ("sh", 0x51, "st", "mem16[...] = rb"),
    ("sw", 0x52, "st", "mem32[...] = rb"),
    ("sd", 0x53, "st", "mem64[...] = rb"),
    ("sq", 0x54, "st", "mem128[...] = rb"),
    ("jmp", 0x60, "j", "pc = pc + 16 * sext(imm)"),
    ("jal", 0x61, "jal", "rd = pc + 16; pc = pc + 16 * sext(imm)"),
    ("jr", 0x62, "jr", "t = ra + sext(imm); rd = pc + 16; pc = t"),
    ("beq", 0x63, "br", "if ra == rb: pc = pc + 16 * sext(imm)"),
    ("bne", 0x64, "br", "if ra != rb: branch"),
    ("blt", 0x65, "br", "if ra < rb signed: branch"),
    ("bge", 0x66, "br", "if ra >= rb signed: branch"),
    ("bltu", 0x67, "br", "if ra < rb unsigned: branch"),
    ("bgeu", 0x68, "br", "if ra >= rb unsigned: branch"),
    ("sys", 0x70, "j", "trap SYSCALL; tval = imm; tpc = pc + 16"),
    ("tret", 0x71, "none", "kernel only: priv = tpriv; pc = tpc"),
    ("csrr", 0x72, "csrr", "kernel only: rd = csr[imm]"),
    ("csrw", 0x73, "csrw", "kernel only: csr[imm] = ra"),
]
BY_NAME = {n: (c, f, s) for n, c, f, s in _T}
BY_CODE = {c: (n, f, s) for n, c, f, s in _T}
assert len(BY_NAME) == len(BY_CODE) == len(_T)

CSRS = {"priv": 0, "tvec": 1, "tpc": 2, "tcause": 3, "tval": 4, "tpriv": 5,
        "abase": 6, "alim": 7, "cycles": 8, "scratch": 9, "timecmp": 10}
CSR_READONLY = {0, 8}

CAUSES = {1: "ILLEGAL", 2: "PRIVILEGE", 3: "DIVZERO", 4: "MISALIGN", 5: "ACCESS", 6: "SYSCALL", 7: "TIMER"}
CAUSE_ILLEGAL, CAUSE_PRIVILEGE, CAUSE_DIVZERO, CAUSE_MISALIGN, CAUSE_ACCESS, CAUSE_SYSCALL, CAUSE_TIMER = 1, 2, 3, 4, 5, 6, 7

REG_ALIASES = {"zero": 0, "sp": 127, "lr": 128}


def sext(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value >> (bits - 1) else value


def to_signed(v):
    v &= MASK
    return v - (1 << WIDTH) if v & SIGN else v


def encode(name, rd=0, ra=0, rb=0, imm=0):
    code, fmt, _ = BY_NAME[name]
    used = FORMATS[fmt]
    vals = {"rd": rd, "ra": ra, "rb": rb, "imm": imm}
    for field, value in vals.items():
        if field not in used and value != 0:
            raise ValueError(f"{name}: field {field} is not used by this glyph")
    for field in ("rd", "ra", "rb"):
        if not 0 <= vals[field] < NUM_VEYLS:
            raise ValueError(f"{name}: register out of range (v0..v128)")
    if not -(1 << (IMM_BITS - 1)) <= imm < (1 << IMM_BITS):
        raise ValueError(f"{name}: immediate does not fit {IMM_BITS} bits")
    return (code << 112) | (rd << 104) | (ra << 96) | (rb << 88) | (imm & IMM_MASK)


def decode(word):
    if not 0 <= word <= MASK:
        return None
    code = (word >> 112) & 0xFFFF
    if code not in BY_CODE:
        return None
    name, fmt, _ = BY_CODE[code]
    rd, ra, rb = (word >> 104) & 0xFF, (word >> 96) & 0xFF, (word >> 88) & 0xFF
    if any(index >= NUM_VEYLS for index in (rd, ra, rb)):
        return None
    imm = word & IMM_MASK
    used = FORMATS[fmt]
    for field, value in (("rd", rd), ("ra", ra), ("rb", rb), ("imm", imm)):
        if field not in used and value != 0:
            return None
    return name, rd, ra, rb, imm


def table_json():
    return json.dumps({
        "architecture": "Veylith", "profile": "128-native-v1", "register_width_bits": WIDTH, "register_count": NUM_GPRS, "register_slots_including_zero": NUM_VEYLS, "register_index_bits": REG_BITS, "virtual_address_bits": VA_BITS, "glyph_bits": 128,
        "fields": {"op": "127:112", "rd": "111:104", "ra": "103:96", "rb": "95:88", "imm": "87:0 (88-bit immediate)"},
        "glyphs": [{"name": n, "opcode": f"0x{c:02X}", "format": f, "summary": s} for n, c, f, s in _T],
        "csrs": CSRS, "causes": {str(k): v for k, v in CAUSES.items()},
    }, indent=2) + "\n"


if __name__ == "__main__":
    sys.stdout.write(table_json())
