"""Veylith v0 reference emulator: sequential, deterministic, single core."""
from . import isa
from .isa import MASK, to_signed, sext, CAUSE_ILLEGAL, CAUSE_PRIVILEGE, CAUSE_DIVZERO, CAUSE_MISALIGN, CAUSE_ACCESS, CAUSE_SYSCALL
from . import image as imagemod

CONSOLE_ADDR = (1 << 128) - 0x10000
VA_LIMIT = 1 << isa.VA_BITS
TRACE_VERSION = 2


class Trap(Exception):
    def __init__(self, cause, tval=0, tpc=None):
        self.cause, self.tval, self.tpc = cause, tval, tpc


class Machine:
    def __init__(self, ram_size=1 << 20):
        if ram_size <= 0 or ram_size % 16 or ram_size >= CONSOLE_ADDR:
            raise ValueError("ram_size must be a positive multiple of 16 and below the console window")
        self.ram = bytearray(ram_size)
        self.reset()

    def reset(self):
        for i in range(len(self.ram)):
            self.ram[i] = 0
        self.v = [0] * isa.NUM_VEYLS
        self.pc = 0
        self.priv = 0
        self.csr = {n: 0 for n in isa.CSRS.values()}
        self.console = bytearray()
        self.halted = False
        self.exit_code = None
        self.stop_reason = None
        self.cycles = 0
        self.trace = None
        self._mem_log = []

    # ---- image loading ----------------------------------------------------
    def load(self, blob, set_entry=True):
        segs, entry = imagemod.unpack(blob)
        for addr, data in segs:
            if addr + len(data) > len(self.ram):
                raise imagemod.ImageError(f"segment at 0x{addr:x} does not fit in RAM")
        for addr, data in segs:
            self.ram[addr:addr + len(data)] = data
        if set_entry:
            self.pc = entry

    # ---- memory -----------------------------------------------------------
    def _check(self, addr, size, kind):
        """kind: 'r', 'w' or 'x'. Raises Trap. Priority: ACCESS(canonical) > MISALIGN > ACCESS(region)."""
        if not 0 <= addr < VA_LIMIT:
            raise Trap(CAUSE_ACCESS, addr)
        if addr % size:
            raise Trap(CAUSE_MISALIGN, addr)
        end = addr + size
        if end > VA_LIMIT:
            raise Trap(CAUSE_ACCESS, addr)
        if self.priv == 1:
            base, lim = self.csr[6], self.csr[7]
            if not (base <= addr and end <= base + lim):
                raise Trap(CAUSE_ACCESS, addr)
            if end > len(self.ram):
                raise Trap(CAUSE_ACCESS, addr)
            return "ram"
        if end <= len(self.ram):
            return "ram"
        if kind == "w" and addr == CONSOLE_ADDR and size == 1:
            return "console"
        raise Trap(CAUSE_ACCESS, addr)

    def _load(self, addr, size):
        self._check(addr, size, "r")
        return int.from_bytes(self.ram[addr:addr + size], "little")

    def _store(self, addr, size, value):
        region = self._check(addr, size, "w")
        value &= (1 << (size * 8)) - 1
        if region == "console":
            self.console.append(value)
        else:
            self.ram[addr:addr + size] = value.to_bytes(size, "little")
        self._mem_log.append((addr, size, value))

    # ---- execution --------------------------------------------------------
    def _write(self, rd, value):
        if rd:
            self.v[rd] = value & MASK

    def step(self):
        """Execute one glyph. Returns False once the machine has stopped."""
        if self.halted:
            return False
        pc = self.pc
        self._mem_log = []
        before = list(self.v) if self.trace is not None else None
        raw, name, trap = None, None, None
        try:
            raw = self._fetch(pc)
            dec = isa.decode(raw)
            if dec is None:
                raise Trap(CAUSE_ILLEGAL, raw & MASK)
            name = dec[0]
            self._execute(dec, pc)
            self.cycles += 1
        except Trap as t:
            trap = t
            if t.tpc is None:
                t.tpc = pc
            self._enter_trap(t)
        if self.trace is not None:
            self.trace.append(self._record(pc, raw, name, trap, before))
        return not self.halted

    def _fetch(self, pc):
        if pc >= VA_LIMIT:
            raise Trap(CAUSE_ACCESS, pc)
        if pc % isa.GLYPH_BYTES:
            raise Trap(CAUSE_MISALIGN, pc)
        self._check(pc, isa.GLYPH_BYTES, "x")
        return int.from_bytes(self.ram[pc:pc + isa.GLYPH_BYTES], "little")

    def _enter_trap(self, t):
        c = self.csr
        if c[1] == 0:
            self.halted = True
            self.stop_reason = f"unhandled trap {isa.CAUSES[t.cause]} at pc=0x{t.tpc:x} tval=0x{t.tval:x}"
            return
        c[2], c[3], c[4], c[5] = t.tpc, t.cause, t.tval & MASK, self.priv
        self.priv = 0
        self.pc = c[1]

    def _execute(self, dec, pc):
        name, rd, ra, rb, imm = dec
        v = self.v
        a, b = v[ra], v[rb]
        simm = sext(imm, isa.IMM_BITS) & MASK
        nxt = (pc + isa.GLYPH_BYTES) & MASK
        newpc = nxt
        if name == "nop":
            pass
        elif name == "halt":
            self._need_kernel()
            self.halted, self.exit_code, self.stop_reason = True, v[1], "halt"
        elif name in _ALU3:
            self._write(rd, _ALU3[name](a, b))
        elif name in _ALUI:
            self._write(rd, _ALUI[name](a, simm, imm))
        elif name == "ldk":
            self._write(rd, simm)
        elif name == "shk":
            self._write(rd, ((v[rd] & ((1 << 40) - 1)) << isa.IMM_BITS) | imm)
        elif name == "clz":
            self._write(rd, 128 - a.bit_length())
        elif name == "popc":
            self._write(rd, bin(a).count("1"))
        elif name in _LOADS:
            size, signed = _LOADS[name]
            val = self._load((a + simm) & MASK, size)
            self._write(rd, sext(val, size * 8) if signed else val)
        elif name in _STORES:
            self._store((a + simm) & MASK, _STORES[name], b)
        elif name == "jmp":
            newpc = (pc + isa.GLYPH_BYTES * to_signed(simm)) & MASK
        elif name == "jal":
            newpc = (pc + isa.GLYPH_BYTES * to_signed(simm)) & MASK
            self._write(rd, nxt)
        elif name == "jr":
            newpc = (a + simm) & MASK
            self._write(rd, nxt)
        elif name in _BRANCH:
            if _BRANCH[name](a, b):
                newpc = (pc + isa.GLYPH_BYTES * to_signed(simm)) & MASK
        elif name == "sys":
            raise Trap(CAUSE_SYSCALL, imm, tpc=nxt)
        elif name == "tret":
            self._need_kernel()
            self.priv = self.csr[5] & 1
            newpc = self.csr[2]
        elif name == "csrr":
            self._need_kernel()
            if imm not in self.csr and imm != 8:
                raise Trap(CAUSE_ILLEGAL, imm)
            self._write(rd, self.cycles if imm == 8 else self.csr[imm])
        elif name == "csrw":
            self._need_kernel()
            if imm not in self.csr or imm in isa.CSR_READONLY:
                raise Trap(CAUSE_ILLEGAL, imm)
            self.csr[imm] = a
        else:  # pragma: no cover - decode() only yields table names
            raise Trap(CAUSE_ILLEGAL, 0)
        self.pc = newpc

    def _need_kernel(self):
        if self.priv != 0:
            raise Trap(CAUSE_PRIVILEGE, 0)

    def run(self, max_steps=1_000_000):
        n = 0
        while not self.halted and n < max_steps:
            self.step()
            n += 1
        if not self.halted:
            self.stop_reason = "step limit"
        return self.stop_reason

    # ---- Tracebook --------------------------------------------------------
    def _record(self, pc, raw, name, trap, before):
        rec = {"tracebook": TRACE_VERSION, "n": self.cycles, "pc": f"0x{pc:x}"}
        rec["raw"] = None if raw is None else f"0x{raw:032x}"
        rec["op"] = name
        rec["regs"] = {f"v{i}": f"0x{self.v[i]:x}" for i in range(isa.NUM_VEYLS) if self.v[i] != before[i]}
        rec["mem"] = [{"addr": f"0x{a:x}", "size": s, "value": f"0x{x:x}"} for a, s, x in self._mem_log]
        rec["trap"] = None if trap is None else {"cause": isa.CAUSES[trap.cause], "tval": f"0x{trap.tval:x}"}
        rec["next_pc"] = f"0x{self.pc:x}"
        rec["priv"] = self.priv
        return rec


def _div(a, b, signed, rem):
    if b == 0:
        raise Trap(CAUSE_DIVZERO, 0)
    if not signed:
        return (a % b) if rem else (a // b)
    x, y = to_signed(a), to_signed(b)
    q = abs(x) // abs(y)
    if (x < 0) != (y < 0):
        q = -q
    if q == (1 << 127):  # MIN / -1 wraps to MIN
        q = -(1 << 127)
    return (x - y * q) & MASK if rem else q & MASK


def _rol(a, n):
    n %= 128
    return ((a << n) | (a >> (128 - n))) & MASK if n else a


_ALU3 = {
    "add": lambda a, b: a + b, "sub": lambda a, b: a - b, "mul": lambda a, b: a * b,
    "mulh": lambda a, b: (a * b) >> 128,
    "udiv": lambda a, b: _div(a, b, False, False), "sdiv": lambda a, b: _div(a, b, True, False),
    "urem": lambda a, b: _div(a, b, False, True), "srem": lambda a, b: _div(a, b, True, True),
    "and": lambda a, b: a & b, "or": lambda a, b: a | b, "xor": lambda a, b: a ^ b,
    "shl": lambda a, b: a << (b % 128), "shr": lambda a, b: a >> (b % 128),
    "sar": lambda a, b: to_signed(a) >> (b % 128),
    "rol": lambda a, b: _rol(a, b % 128), "ror": lambda a, b: _rol(a, 128 - (b % 128)),
    "slt": lambda a, b: int(to_signed(a) < to_signed(b)), "sltu": lambda a, b: int(a < b),
    "seq": lambda a, b: int(a == b),
}
_ALUI = {
    "addi": lambda a, s, i: a + s, "andi": lambda a, s, i: a & s, "ori": lambda a, s, i: a | s,
    "xori": lambda a, s, i: a ^ s, "shli": lambda a, s, i: a << (i % 128),
    "shri": lambda a, s, i: a >> (i % 128), "sari": lambda a, s, i: to_signed(a) >> (i % 128),
}
_LOADS = {"lb": (1, 0), "lh": (2, 0), "lw": (4, 0), "ld": (8, 0), "lq": (16, 0),
          "lbs": (1, 1), "lhs": (2, 1), "lws": (4, 1), "lds": (8, 1)}
_STORES = {"sb": 1, "sh": 2, "sw": 4, "sd": 8, "sq": 16}
_BRANCH = {"beq": lambda a, b: a == b, "bne": lambda a, b: a != b,
           "blt": lambda a, b: to_signed(a) < to_signed(b), "bge": lambda a, b: to_signed(a) >= to_signed(b),
           "bltu": lambda a, b: a < b, "bgeu": lambda a, b: a >= b}
