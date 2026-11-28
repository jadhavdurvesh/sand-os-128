"""Veylith v0 reference emulator: sequential, deterministic, single core."""
from . import isa
from .isa import MASK, to_signed, sext, CAUSE_ILLEGAL, CAUSE_PRIVILEGE, CAUSE_DIVZERO, CAUSE_MISALIGN, CAUSE_ACCESS, CAUSE_SYSCALL, CAUSE_TIMER, CAUSE_CAPABILITY
from . import image as imagemod

CONSOLE_ADDR = (1 << 128) - 0x10000
VA_LIMIT = 1 << isa.VA_BITS
TRACE_VERSION = 2
GPU_BASE = (1 << 128) - 0x2000
GPU_WIDTH, GPU_HEIGHT = 1280, 720
GPU_REG_BYTES = 96
GPU_FONT = {"0":[14,17,19,21,25,17,14],"1":[4,12,4,4,4,4,14],"2":[14,17,1,2,4,8,31],"3":[30,1,1,14,1,1,30],"4":[2,6,10,18,31,2,2],"5":[31,16,16,30,1,1,30],"6":[14,16,16,30,17,17,14],"7":[31,1,2,4,8,8,8],"8":[14,17,17,14,17,17,14],"9":[14,17,17,15,1,1,14],"A":[14,17,17,31,17,17,17],"B":[30,17,17,30,17,17,30],"C":[14,17,16,16,16,17,14],"D":[30,17,17,17,17,17,30],"E":[31,16,16,30,16,16,31],"F":[31,16,16,30,16,16,16],"G":[14,17,16,23,17,17,15],"H":[17,17,17,31,17,17,17],"I":[14,4,4,4,4,4,14],"J":[7,2,2,2,18,18,12],"K":[17,18,20,24,20,18,17],"L":[16,16,16,16,16,16,31],"M":[17,27,21,21,17,17,17],"N":[17,25,21,19,17,17,17],"O":[14,17,17,17,17,17,14],"P":[30,17,17,30,16,16,16],"Q":[14,17,17,17,21,18,13],"R":[30,17,17,30,20,18,17],"S":[15,16,16,14,1,1,30],"T":[31,4,4,4,4,4,4],"U":[17,17,17,17,17,17,14],"V":[17,17,17,17,17,10,4],"W":[17,17,17,21,21,21,10],"X":[17,17,10,4,10,17,17],"Y":[17,17,10,4,4,4,4],"Z":[31,1,2,4,8,16,31],".":[0,0,0,0,0,12,12],":":[0,12,12,0,12,12,0],"-":[0,0,0,31,0,0,0],"/":[1,2,2,4,8,8,16],"'":[12,12,8,0,0,0,0]}


# ---- Sigil capabilities: a 128-bit, tag-free, MAC-authenticated capability --------------------------------------
# [127:88] MAC (40) | [87:80] perms (bit0 READ, bit1 WRITE, bit2 NARROW) | [79:72] exp (region = 2**exp bytes) | [71:0] base (aligned to 2**exp)
SIGIL_K = 0x9E3779B97F4A7C15F39CC0605CEDC835
SIGIL_BODY = (1 << 88) - 1
SIGIL_PERMS = 0x8F
SIGIL_GATE = 0x08
SIGIL_SEALED = 0x80


def _rotl(x, b):
    return ((x << b) | (x >> (64 - b))) & 0xFFFFFFFFFFFFFFFF


def siphash24(key, data):
    """SipHash-2-4 (Aumasson and Bernstein, 2012) with a 128-bit key; returns the 64-bit tag."""
    M = 0xFFFFFFFFFFFFFFFF
    k0, k1 = key & M, (key >> 64) & M
    v0, v1 = k0 ^ 0x736F6D6570736575, k1 ^ 0x646F72616E646F6D
    v2, v3 = k0 ^ 0x6C7967656E657261, k1 ^ 0x7465646279746573

    def rnd(v0, v1, v2, v3):
        v0 = (v0 + v1) & M; v1 = _rotl(v1, 13); v1 ^= v0; v0 = _rotl(v0, 32)
        v2 = (v2 + v3) & M; v3 = _rotl(v3, 16); v3 ^= v2
        v0 = (v0 + v3) & M; v3 = _rotl(v3, 21); v3 ^= v0
        v2 = (v2 + v1) & M; v1 = _rotl(v1, 17); v1 ^= v2; v2 = _rotl(v2, 32)
        return v0, v1, v2, v3
    n = len(data)
    for i in range(0, n - n % 8, 8):
        m = int.from_bytes(data[i:i + 8], "little")
        v3 ^= m
        v0, v1, v2, v3 = rnd(*rnd(v0, v1, v2, v3))
        v0 ^= m
    m = (n << 56) | int.from_bytes(data[n - n % 8:], "little")
    v3 ^= m
    v0, v1, v2, v3 = rnd(*rnd(v0, v1, v2, v3))
    v0 ^= m
    v2 ^= 0xFF
    for _ in range(4):
        v0, v1, v2, v3 = rnd(v0, v1, v2, v3)
    return v0 ^ v1 ^ v2 ^ v3


def sigil_mac(key, body):
    """40-bit MAC: top 40 bits of SipHash-2-4 over the 88-bit body (11 bytes, little endian), 128-bit key."""
    return siphash24(key, body.to_bytes(11, "little")) >> 24


def sigil_size(shape):
    """Region size in bytes for a shape field (exp << 8 | length-multiplier-minus-one): (lenm1 + 1) << exp."""
    return ((shape & 0xFF) + 1) << (shape >> 8)


def sigil_make(key, base, perms, shape):
    """shape = exp << 8 | lenm1.  Body layout: perms [87:80], exp [79:72], lenm1 [71:64], base [63:0]."""
    body = (perms << 80) | (shape << 64) | base
    return (sigil_mac(key, body) << 88) | body


def sigil_parse(key, cap):
    """(base, perms, exp) if the capability is well formed and its MAC verifies under key, else None."""
    body = cap & SIGIL_BODY
    if (cap >> 88) != sigil_mac(key, body):
        return None
    perms, shape, base = (cap >> 80) & 0xFF, (cap >> 64) & 0xFFFF, cap & ((1 << 64) - 1)
    exp = shape >> 8
    if perms & ~SIGIL_PERMS or exp > 56 or base & ((1 << exp) - 1) or base + sigil_size(shape) > 1 << 64:
        return None
    return base, perms, shape


def sigil_parse_trusted(cap):
    """Field decode without the MAC check, for registers whose capability was verified (or minted) earlier."""
    shape = (cap >> 64) & 0xFFFF
    return cap & ((1 << 64) - 1), (cap >> 80) & 0xFF, shape


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
        self.vok = [False] * isa.NUM_VEYLS      # microarchitectural: register holds a capability whose MAC is already verified
        self.pc = 0
        self.priv = 0
        self.csr = {n: 0 for n in isa.CSRS.values()}
        self.console = bytearray()
        self.halted = False
        self.exit_code = None
        self.stop_reason = None
        self.cycles = 0
        self.use_vok = True                      # False = verify the MAC on every use (flag-free baseline)
        self.vok_audit = False                   # True = assert every flag hit is really a valid capability
        self.cstats = {"uses": 0, "macs": 0}     # capability uses vs MAC computations
        self.opcount = {}                        # executed Glyphs by mnemonic
        self.access_log = None                   # optional list of (kind, addr, size) for memory-system models
        self.trace = None
        self._mem_log = []
        self.framebuffer = bytearray(GPU_WIDTH * GPU_HEIGHT * 4)
        self._gpu_regs = [0] * 6

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
        if GPU_BASE <= addr < GPU_BASE + GPU_REG_BYTES:
            if self.priv != 0 or kind != 'w' or size != 16 or (addr - GPU_BASE) % 16:
                raise Trap(CAUSE_ACCESS, addr)
            return 'gpu'
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
        if self.access_log is not None:
            self.access_log.append(("r", addr, size))
        return int.from_bytes(self.ram[addr:addr + size], "little")

    def _store(self, addr, size, value):
        region = self._check(addr, size, "w")
        if self.access_log is not None:
            self.access_log.append(("w", addr, size))
        value &= (1 << (size * 8)) - 1
        if region == "console":
            self.console.append(value)
        elif region == "gpu":
            self._gpu_write(addr, value)
        else:
            self.ram[addr:addr + size] = value.to_bytes(size, "little")
        self._mem_log.append((addr, size, value))


    def _gpu_write(self, addr, value):
        index = (addr - GPU_BASE) // 16
        if index < 5:
            self._gpu_regs[index] = value
            return
        self._gpu_regs[5] = value
        if value == 2:
            x, y, ptr, length, color = self._gpu_regs[:5]
            if ptr >= len(self.ram) or length > 128 or length > len(self.ram) - ptr:
                return
            for i, char in enumerate(self.ram[ptr:ptr + length]):
                rows = GPU_FONT.get(chr(char).upper(), [0] * 7)
                for ry, bits in enumerate(rows):
                    for rx in range(5):
                        if bits & (1 << (4 - rx)):
                            for sy in range(2):
                                for sx in range(2):
                                    px, py = x + i * 12 + rx * 2 + sx, y + ry * 2 + sy
                                    if px < GPU_WIDTH and py < GPU_HEIGHT:
                                        off = (py * GPU_WIDTH + px) * 4
                                        self.framebuffer[off:off + 4] = int(color & 0xFFFFFFFF).to_bytes(4, "little")
            return
        if value != 1:
            return
        x, y, width, height, color = self._gpu_regs[:5]
        if x >= GPU_WIDTH or y >= GPU_HEIGHT:
            return
        width, height = min(width, GPU_WIDTH - x), min(height, GPU_HEIGHT - y)
        rgba = int(color & 0xFFFFFFFF).to_bytes(4, "little")
        row = rgba * width
        for yy in range(y, y + height):
            start = (yy * GPU_WIDTH + x) * 4
            self.framebuffer[start:start + len(row)] = row

    # ---- execution --------------------------------------------------------
    def _write(self, rd, value):
        if rd:
            self.v[rd] = value & MASK
            self.vok[rd] = False

    def _cp(self, rd, value):
        """Write a capability the machine itself just minted: its MAC is valid by construction."""
        self._write(rd, value)
        if rd:
            self.vok[rd] = self.use_vok

    def _cparse(self, ra, a):
        """Parse capability register ra, computing the MAC only when the register is not already verified."""
        self.cstats["uses"] += 1
        if self.vok[ra] and ra:
            if self.vok_audit:
                assert sigil_parse(self.csr[11], a) is not None, f"stale verified flag on v{ra}"
            return sigil_parse_trusted(a)
        self.cstats["macs"] += 1
        p = sigil_parse(self.csr[11], a)
        if p is not None and ra:
            self.vok[ra] = self.use_vok
        return p

    def step(self):
        """Execute one glyph. Returns False once the machine has stopped."""
        if self.halted:
            return False
        pc = self.pc
        self._mem_log = []
        before = list(self.v) if self.trace is not None else None
        raw, name, trap = None, None, None
        try:
            tc = self.csr[10]                      # timecmp: a 128-bit one-shot deadline against the retired-Glyph counter
            if self.priv == 1 and tc and self.csr[1] and self.cycles >= tc:
                self.csr[10] = 0                   # delivered only to user code, so the non-reentrant kernel is never interrupted
                raise Trap(CAUSE_TIMER, 0, tpc=pc) # tpc = the Glyph that has not executed yet
            raw = self._fetch(pc)
            dec = isa.decode(raw)
            if dec is None:
                raise Trap(CAUSE_ILLEGAL, raw & MASK)
            name = dec[0]
            self._execute(dec, pc)
            self.cycles += 1
            self.opcount[name] = self.opcount.get(name, 0) + 1
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
        elif name == "cmint":
            self._need_kernel()
            shape = (((b >> 8) & 0xFF) << 8) | ((b >> 16) & 0xFF)
            if b >> 24 or (b & 0xFF) & ~SIGIL_PERMS or (shape >> 8) > 56 or a >> 64 or a & ((1 << (shape >> 8)) - 1) or a + sigil_size(shape) > 1 << 64:
                raise Trap(CAUSE_CAPABILITY, a)
            self._cp(rd, sigil_make(self.csr[11], a, b & 0xFF, shape))
        elif name == "cnarrow":
            p = self._cparse(ra, a)
            if p is None:
                raise Trap(CAUSE_CAPABILITY, a)
            base, perms, shape = p
            np_, ne, off, nl = b & 0xFF, (b >> 8) & 0xFF, (b >> 16) & ((1 << 64) - 1), (b >> 80) & 0xFF   # nl: new length multiplier minus one
            nshape = (ne << 8) | nl
            if b >> 88 or perms & SIGIL_SEALED or (np_ & ~perms) or not perms & 4 or ne > (shape >> 8) or off & ((1 << ne) - 1) \
                    or off + sigil_size(nshape) > sigil_size(shape):
                raise Trap(CAUSE_CAPABILITY, a)
            self._cp(rd, sigil_make(self.csr[11], base + off, np_, nshape))
        elif name == "cseal":
            p = self._cparse(ra, a)
            if p is None:
                raise Trap(CAUSE_CAPABILITY, a)
            self._cp(rd, sigil_make(self.csr[11], p[0], p[1] | SIGIL_SEALED, p[2]))
        elif name == "ccall":
            p = self._cparse(ra, a)
            if p is None or p[1] & (SIGIL_SEALED | SIGIL_GATE) != (SIGIL_SEALED | SIGIL_GATE) or p[0] & 15 or sigil_size(p[2]) < 16 or self.csr[13]:
                raise Trap(CAUSE_CAPABILITY, a)
            self._cp(rd, sigil_make(self.csr[11], p[0], p[1] & ~(SIGIL_SEALED | SIGIL_GATE), p[2]))
            self.csr[13] = nxt
            newpc = p[0]
        elif name == "ccalx":
            p = self._cparse(ra, a)
            cs = self.csr[14]
            if p is None or p[1] & (SIGIL_SEALED | SIGIL_GATE) != (SIGIL_SEALED | SIGIL_GATE) or p[0] & 15 or sigil_size(p[2]) < 16 or self.csr[13] \
                    or cs == 0 or cs & 15 or cs + 2048 > len(self.ram):
                raise Trap(CAUSE_CAPABILITY, a)
            data = sigil_make(self.csr[11], p[0], p[1] & ~(SIGIL_SEALED | SIGIL_GATE), p[2])
            for i in range(1, 129):
                self.ram[cs + 16 * (i - 1):cs + 16 * i] = self.v[i].to_bytes(16, "little")
                if i > 4:
                    self.v[i] = 0
                    self.vok[i] = False
            self._cp(rd, data)
            self.csr[13] = nxt | (1 << 127)
            newpc = p[0]
        elif name == "cretx":
            cs = self.csr[14]
            if not self.csr[13] >> 127:
                raise Trap(CAUSE_CAPABILITY, 0)
            for i in range(3, 129):                 # v1 and v2 carry the results back; everything else is the caller's again
                self.v[i] = int.from_bytes(self.ram[cs + 16 * (i - 1):cs + 16 * i], "little")
                self.vok[i] = False
            newpc, self.csr[13] = self.csr[13] & ((1 << 127) - 1), 0
        elif name == "cretn":
            if not self.csr[13] or self.csr[13] >> 127:
                raise Trap(CAUSE_CAPABILITY, 0)
            newpc, self.csr[13] = self.csr[13], 0
        elif name == "cunseal":
            self._need_kernel()
            p = self._cparse(ra, a)
            if p is None or not p[1] & SIGIL_SEALED:
                raise Trap(CAUSE_CAPABILITY, a)
            self._cp(rd, sigil_make(self.csr[11], p[0], p[1] & ~SIGIL_SEALED, p[2]))
        elif name == "cinfo":
            p = self._cparse(ra, a)
            self._write(rd, 0 if p is None else (1 << 127) | (a & SIGIL_BODY))
        elif name in _CLOADS or name in _CSTORES:
            size = _CLOADS[name] if name in _CLOADS else _CSTORES[name]
            p = self._cparse(ra, a)
            idx = name in _INDEXED
            off = b if idx else to_signed(simm)
            need = 1 if name in _CLOADS else 2
            if p is None or p[1] & SIGIL_SEALED or not p[1] & need or off < 0 or off + size > sigil_size(p[2]):
                raise Trap(CAUSE_CAPABILITY, a)
            if name in _CLOADS:
                self._write(rd, self._load(p[0] + off, size))
            else:
                self._store(p[0] + off, size, v[rd] if idx else b)
        elif name in _LOADS or name in _STORES:
            if self.priv == 1 and self.csr[12]:
                raise Trap(CAUSE_CAPABILITY, (a + simm) & MASK)       # capability mode: raw memory access is forbidden
            if name in _LOADS:
                size, signed = _LOADS[name]
                val = self._load((a + simm) & MASK, size)
                self._write(rd, sext(val, size * 8) if signed else val)
            else:
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
            if imm == 11:
                self.vok = [False] * isa.NUM_VEYLS      # a new key invalidates every cached verification
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
_CLOADS = {"clb": 1, "clq": 16, "clbx": 1, "clqx": 16}
_CSTORES = {"csb": 1, "csq": 16, "csbx": 1, "csqx": 16}
_INDEXED = {"clbx", "clqx", "csbx", "csqx"}
_STORES = {"sb": 1, "sh": 2, "sw": 4, "sd": 8, "sq": 16}
_BRANCH = {"beq": lambda a, b: a == b, "bne": lambda a, b: a != b,
           "blt": lambda a, b: to_signed(a) < to_signed(b), "bge": lambda a, b: to_signed(a) >= to_signed(b),
           "bltu": lambda a, b: a < b, "bgeu": lambda a, b: a >= b}
