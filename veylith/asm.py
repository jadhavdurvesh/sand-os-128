"""Veylith assembler and disassembler.

Syntax: one statement per line, `;` starts a comment, `label:` defines a label.
Registers v0..v127 (aliases: zero=v0, sp=v126, lr=v127). CSR names: priv tvec tpc tcause tval tpriv abase alim cycles scratch.
Directives: .org .equ .align .space .byte .half .word .quad .oct .ascii .asciz
Pseudo-ops: li rd, const   la rd, label   call label   ret   mv rd, ra   not rd, ra   neg rd, ra
"""
import ast
import re
from . import isa, image

class AsmError(Exception):
    pass


_REG = re.compile(r"^(?:v(\d+)|zero|sp|lr)$")


def parse_reg(tok):
    t = tok.strip().lower()
    if t in isa.REG_ALIASES:
        return isa.REG_ALIASES[t]
    m = re.fullmatch(r"v(\d+)", t)
    if m and int(m.group(1)) < isa.NUM_VEYLS:
        return int(m.group(1))
    raise AsmError(f"bad register '{tok}'")


def is_reg(tok):
    try:
        parse_reg(tok)
        return True
    except AsmError:
        return False


_BIN = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
        ast.FloorDiv: lambda a, b: a // b, ast.LShift: lambda a, b: a << b, ast.RShift: lambda a, b: a >> b,
        ast.BitOr: lambda a, b: a | b, ast.BitAnd: lambda a, b: a & b, ast.BitXor: lambda a, b: a ^ b}


def evaluate(expr, symbols):
    try:
        tree = ast.parse(expr.strip(), mode="eval").body
    except SyntaxError:
        raise AsmError(f"bad expression '{expr}'")

    def ev(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, int):
            return n.value
        if isinstance(n, ast.Name):
            if n.id in symbols:
                return symbols[n.id]
            raise KeyError(n.id)
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN:
            return _BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            if isinstance(n.op, ast.USub):
                return -v
            if isinstance(n.op, ast.UAdd):
                return v
            if isinstance(n.op, ast.Invert):
                return ~v
        raise AsmError(f"unsupported expression '{expr}'")
    return ev(tree)


def strip_comment(line):
    out, q = [], None
    for ch in line:
        if q:
            out.append(ch)
            if ch == q:
                q = None
        elif ch in "\"'":
            q = ch
            out.append(ch)
        elif ch == ";":
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def split_ops(text):
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def li_words(value):
    """Return one or two chunks sufficient to construct any 128-bit value."""
    value &= isa.MASK
    if isa.sext(value, isa.IMM_BITS) & isa.MASK == value:
        return [isa.sext(value, isa.IMM_BITS)]
    return [(value >> isa.IMM_BITS) & ((1 << 40) - 1), value & isa.IMM_MASK]


class Assembler:
    def __init__(self):
        self.symbols = dict(isa.CSRS)
        self.items = []  # (addr, kind, payload, lineno)
        self.defined = {}

    def assemble(self, text):
        lines = text.splitlines()
        addr, entry_first = 0, None
        for no, raw in enumerate(lines, 1):
            line = strip_comment(raw)
            while True:
                m = re.match(r"^([A-Za-z_.][\w.]*):\s*(.*)$", line)
                if not m:
                    break
                self._label(m.group(1), addr, no)
                line = m.group(2)
            if not line:
                continue
            try:
                addr = self._pass1(line, addr, no)
            except KeyError as e:
                raise AsmError(f"line {no}: symbol {e} must be defined before this use") from None
            except AsmError as e:
                raise AsmError(f"line {no}: {e}") from None
            if entry_first is None and self.items:
                entry_first = self.items[0][0]
        segments = self._pass2()
        entry = self.symbols.get("_start", entry_first or 0)
        return image.pack(segments, entry)

    def _label(self, name, addr, no):
        if name in self.defined:
            raise AsmError(f"line {no}: duplicate label '{name}'")
        self.defined[name] = no
        self.symbols[name] = addr

    def _pass1(self, line, addr, no):
        head, _, rest = line.partition(" ")
        head = head.lower()
        rest = rest.strip()
        sym = self.symbols
        if head.startswith("."):
            return self._directive(head, rest, addr, no)
        if addr % isa.GLYPH_BYTES:
            raise AsmError("instruction at unaligned address (use .align 16 after data)")
        ops = split_ops(rest)
        if head == "li":
            if len(ops) != 2:
                raise AsmError("li rd, const")
            words = li_words(evaluate(ops[1], sym))
            rd = parse_reg(ops[0])
            self.items.append((addr, "glyphs", [("ldk", rd, 0, 0, words[0])] + [("shk", rd, 0, 0, w) for w in words[1:]], no))
            return addr + isa.GLYPH_BYTES * len(words)
        self.items.append((addr, "inst", (head, ops), no))
        return addr + isa.GLYPH_BYTES

    def _directive(self, d, rest, addr, no):
        sym = self.symbols
        if d == ".org":
            return evaluate(rest, sym)
        if d == ".equ":
            name, _, expr = rest.partition(",")
            sym[name.strip()] = evaluate(expr, sym)
            return addr
        if d == ".align":
            n = evaluate(rest, sym)
            pad = (-addr) % n
            self.items.append((addr, "data", bytes(pad), no))
            return addr + pad
        if d == ".space":
            n = evaluate(rest, sym)
            self.items.append((addr, "data", bytes(n), no))
            return addr + n
        if d in (".ascii", ".asciz"):
            s = ast.literal_eval(rest)
            data = s.encode("utf-8") + (b"\0" if d == ".asciz" else b"")
            self.items.append((addr, "data", data, no))
            return addr + len(data)
        widths = {".byte": 1, ".half": 2, ".word": 4, ".quad": 8, ".oct": 16}
        if d in widths:
            w, data = widths[d], b""
            for e in split_ops(rest):
                data += (evaluate(e, sym) & ((1 << (8 * w)) - 1)).to_bytes(w, "little")
            self.items.append((addr, "data", data, no))
            return addr + len(data)
        raise AsmError(f"unknown directive {d}")

    def _pass2(self):
        chunks = []
        for addr, kind, payload, no in self.items:
            try:
                if kind == "data":
                    blob = payload
                elif kind == "glyphs":
                    blob = b"".join(isa.encode(n, rd, ra, rb, imm).to_bytes(isa.GLYPH_BYTES, "little") for n, rd, ra, rb, imm in payload)
                else:
                    blob = self._encode(addr, *payload).to_bytes(isa.GLYPH_BYTES, "little")
            except KeyError as e:
                raise AsmError(f"line {no}: undefined symbol {e}") from None
            except (AsmError, ValueError) as e:
                raise AsmError(f"line {no}: {e}") from None
            chunks.append((addr, blob))
        segs = []
        for addr, blob in sorted(chunks, key=lambda c: c[0]):
            if not blob:
                continue
            if segs and segs[-1][0] + len(segs[-1][1]) == addr:
                segs[-1] = (segs[-1][0], segs[-1][1] + blob)
            elif segs and addr < segs[-1][0] + len(segs[-1][1]):
                raise AsmError(f"overlapping output at 0x{addr:x}")
            else:
                segs.append((addr, blob))
        return segs

    def _imm(self, tok):
        return evaluate(tok, self.symbols)

    def _target(self, tok, addr):
        t = self._imm(tok)
        if (t - addr) % isa.GLYPH_BYTES:
            raise AsmError("branch target is not 128-bit glyph-aligned")
        return (t - addr) // isa.GLYPH_BYTES

    def _mem(self, tok):
        m = re.fullmatch(r"\[\s*([^\]+\-]+?)\s*(?:([+-])\s*(.+?))?\s*\]", tok)
        if not m:
            raise AsmError(f"bad memory operand '{tok}'")
        base = parse_reg(m.group(1))
        off = 0
        if m.group(2):
            off = self._imm(m.group(3))
            if m.group(2) == "-":
                off = -off
        return base, off

    def _encode(self, addr, name, ops):
        sym = self.symbols
        if name == "la":
            return isa.encode("ldk", parse_reg(ops[0]), 0, 0, self._imm(ops[1]))
        if name == "call":
            return isa.encode("jal", 127, 0, 0, self._target(ops[0], addr))
        if name == "ret":
            return isa.encode("jr", 0, 127, 0, 0)
        if name == "mv":
            return isa.encode("addi", parse_reg(ops[0]), parse_reg(ops[1]), 0, 0)
        if name == "not":
            return isa.encode("xori", parse_reg(ops[0]), parse_reg(ops[1]), 0, -1)
        if name == "neg":
            return isa.encode("sub", parse_reg(ops[0]), 0, parse_reg(ops[1]), 0)
        if name not in isa.BY_NAME:
            raise AsmError(f"unknown mnemonic '{name}'")
        _, fmt, _ = isa.BY_NAME[name]
        n = {"rrr": 3, "rri": 3, "ld": 2, "ri": 2, "rr": 2, "st": 2, "br": 3, "j": 1, "jal": 2,
             "none": 0, "csrr": 2, "csrw": 2}.get(fmt)
        if fmt == "jr":
            if len(ops) == 1:
                return isa.encode("jr", 0, parse_reg(ops[0]), 0, 0)
            n = 3
        if len(ops) != n:
            raise AsmError(f"{name} expects {n} operand(s), got {len(ops)}")
        if fmt == "rrr":
            return isa.encode(name, parse_reg(ops[0]), parse_reg(ops[1]), parse_reg(ops[2]))
        if fmt == "rri":
            return isa.encode(name, parse_reg(ops[0]), parse_reg(ops[1]), 0, self._imm(ops[2]))
        if fmt == "ld":
            base, off = self._mem(ops[1])
            return isa.encode(name, parse_reg(ops[0]), base, 0, off)
        if fmt == "st":
            base, off = self._mem(ops[0])
            return isa.encode(name, 0, base, parse_reg(ops[1]), off)
        if fmt == "ri":
            return isa.encode(name, parse_reg(ops[0]), 0, 0, self._imm(ops[1]))
        if fmt == "rr":
            return isa.encode(name, parse_reg(ops[0]), parse_reg(ops[1]))
        if fmt == "br":
            return isa.encode(name, 0, parse_reg(ops[0]), parse_reg(ops[1]), self._target(ops[2], addr))
        if fmt == "j":
            if name == "sys":
                return isa.encode(name, 0, 0, 0, self._imm(ops[0]))
            return isa.encode(name, 0, 0, 0, self._target(ops[0], addr))
        if fmt == "jal":
            return isa.encode(name, parse_reg(ops[0]), 0, 0, self._target(ops[1], addr))
        if fmt == "jr":
            return isa.encode(name, parse_reg(ops[0]), parse_reg(ops[1]), 0, self._imm(ops[2]))
        if fmt == "none":
            return isa.encode(name)
        if fmt == "csrr":
            return isa.encode(name, parse_reg(ops[0]), 0, 0, self._imm(ops[1]))
        if fmt == "csrw":
            return isa.encode(name, 0, parse_reg(ops[1]), 0, self._imm(ops[0]))
        raise AsmError("unhandled format")  # pragma: no cover


def assemble(text):
    return Assembler().assemble(text)


# ---- disassembler -------------------------------------------------------------
_CSR_NAMES = {v: k for k, v in isa.CSRS.items()}


def disassemble_word(word, addr=0):
    d = isa.decode(word)
    if d is None:
        return f".glyph 0x{word:032x}  ; illegal"
    name, rd, ra, rb, imm = d
    simm = isa.sext(imm, isa.IMM_BITS)
    fmt = isa.BY_NAME[name][1]
    r = lambda i: f"v{i}"
    if fmt == "rrr":
        return f"{name} {r(rd)}, {r(ra)}, {r(rb)}"
    if fmt == "rri":
        return f"{name} {r(rd)}, {r(ra)}, {simm}"
    if fmt == "ld":
        return f"{name} {r(rd)}, [{r(ra)} + {simm}]"
    if fmt == "st":
        return f"{name} [{r(ra)} + {simm}], {r(rb)}"
    if fmt == "ri":
        return f"{name} {r(rd)}, {simm if name == 'ldk' else imm}"
    if fmt == "rr":
        return f"{name} {r(rd)}, {r(ra)}"
    if fmt == "br":
        return f"{name} {r(ra)}, {r(rb)}, 0x{(addr + isa.GLYPH_BYTES * simm) & isa.MASK:x}"
    if fmt == "j":
        return f"{name} {imm}" if name == "sys" else f"{name} 0x{(addr + isa.GLYPH_BYTES * simm) & isa.MASK:x}"
    if fmt == "jal":
        return f"{name} {r(rd)}, 0x{(addr + isa.GLYPH_BYTES * simm) & isa.MASK:x}"
    if fmt == "jr":
        return f"{name} {r(rd)}, {r(ra)}, {simm}"
    if fmt == "csrr":
        return f"{name} {r(rd)}, {_CSR_NAMES.get(imm, imm)}"
    if fmt == "csrw":
        return f"{name} {_CSR_NAMES.get(imm, imm)}, {r(ra)}"
    return name


def disassemble_image(blob):
    segs, entry = image.unpack(blob)
    out = [f"; entry 0x{entry:x}"]
    for addr, data in segs:
        out.append(f".org 0x{addr:x}")
        for off in range(0, len(data) - (isa.GLYPH_BYTES - 1), isa.GLYPH_BYTES):
            w = int.from_bytes(data[off:off + isa.GLYPH_BYTES], "little")
            out.append(f"  {disassemble_word(w, addr + off)}")
        if len(data) % isa.GLYPH_BYTES:
            out.append(f"  ; {len(data) % isa.GLYPH_BYTES} trailing data byte(s)")
    return "\n".join(out) + "\n"
