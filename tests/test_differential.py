"""Differential conformance: random Veylith programs must behave identically on two independent machines.

The Python reference machine (arbitrary-precision integers) and the compiled C machine (native unsigned __int128)
share no execution code. Each random program runs in kernel mode, folds all data registers and a memory window into a
128-bit hash, prints it, and halts. Console output and the retired-Glyph count must match exactly.
"""
import os, random, re, shutil, subprocess, tempfile, unittest
from veylith import asm, disk
from veylith.machine import Machine

MASK = (1 << 128) - 1
EDGE = [0, 1, 2, 3, MASK, MASK - 1, 1 << 127, (1 << 127) - 1, 1 << 64, (1 << 64) - 1, 1 << 63, 1 << 88, (1 << 88) - 1,
        1 << 87, (1 << 87) - 1, 1 << 40, (1 << 40) - 1, 0x123456789ABCDEF0123456789ABCDEF, 10, 127, 128, 255, 256]
DATA = list(range(1, 13))            # v1..v12: data registers
RRR = ["add", "sub", "and", "or", "xor", "shl", "shr", "sar", "rol", "ror", "mul", "mulh", "slt", "sltu", "seq"]
DIV = ["udiv", "sdiv", "urem", "srem"]
RRI = ["addi", "andi", "ori", "xori", "shli", "shri", "sari"]
LOADS = {"lb": 1, "lbs": 1, "lh": 2, "lhs": 2, "lw": 4, "lws": 4, "ld": 8, "lds": 8, "lq": 16}
STORES = {"sb": 1, "sh": 2, "sw": 4, "sd": 8, "sq": 16}
MEM = 0x8000
CAPS = [20, 21, 22, 23]


def value(rng):
    r = rng.random()
    if r < 0.45:
        return rng.choice(EDGE)
    if r < 0.6:
        return rng.choice(EDGE) ^ (1 << rng.randrange(128))
    return rng.getrandbits(rng.choice([8, 32, 64, 100, 128]))


def program(seed, length=220):
    rng = random.Random(seed)
    L = []
    reg = lambda: f"v{rng.choice(DATA)}"
    for r in DATA:
        L.append(f"li v{r}, {value(rng)}")
    L.append(f"li v16, {MEM}")
    L += ["la v14, trapped", "csrw tvec, v14", "li v18, 0", f"li v13, {rng.getrandbits(128)}", "csrw ckey, v13"]     # trap handler counts faults and skips them
    for cr, (base, perms, exp) in zip(CAPS, [(MEM, 7, 8), (MEM + 64, 7, 6), (MEM, 1, 8), (MEM + 128, 6, 7)]):
        L += [f"li v13, {base}", f"li v14, {perms | exp << 8 | rng.randrange(0, 4) << 16}", f"cmint v{cr}, v13, v14"]    # length multiplier 1..4
    n = 0
    while n < length:
        k = rng.random()
        if rng.random() < 0.22:                                       # Sigil capability operations (valid and invalid)
            cr = lambda: f"v{rng.choice(CAPS)}"
            j = rng.random()
            if j < 0.3:
                rb = rng.randrange(8) | rng.randrange(0, 10) << 8 | rng.randrange(0, 256, 1 << rng.randrange(0, 6)) << 16 | rng.randrange(0, 3) << 80
                L += [f"li v13, {rb}", f"cnarrow {rng.choice([cr(), reg()])}, {cr()}, v13"]
            elif j < 0.37:
                L.append(f"{rng.choice(['cseal', 'cunseal'])} {rng.choice([cr(), reg()])}, {rng.choice([cr(), reg()])}")
            elif j < 0.45:
                L.append(f"cinfo {reg()}, {rng.choice([cr(), reg()])}")
            elif j < 0.55:
                L.append(f"li v13, {rng.choice([rng.randrange(0, 280), -1, 1 << 100])}")
                op = rng.choice(["clbx", "clqx", "csbx", "csqx"])
                L.append(f"{op} {reg()}, {cr()}, v13")
            elif j < 0.8:
                op = rng.choice(["clb", "clq"]); w = 1 if op == "clb" else 16
                L.append(f"{op} {reg()}, [{cr()} + {rng.choice([rng.randrange(0, 280, w), -w, 260])}]")
            else:
                op = rng.choice(["csb", "csq"]); w = 1 if op == "csb" else 16
                L.append(f"{op} [{cr()} + {rng.choice([rng.randrange(0, 280, w), -w, 260])}], {reg()}")
            n += 1
            continue
        if k < 0.30:
            L.append(f"{rng.choice(RRR)} {reg()}, {reg()}, {reg()}")
        elif k < 0.38:
            L.append(f"ori v13, {reg()}, 1")                        # force a non-zero divisor
            L.append(f"{rng.choice(DIV)} {reg()}, {reg()}, v13"); n += 1
        elif k < 0.52:
            op = rng.choice(RRI); imm = rng.randrange(128) if op in ("shli", "shri", "sari") else rng.choice([0, 1, -1, 7, -128, 1 << 40, -(1 << 40), (1 << 87) - 1, -(1 << 87)])
            L.append(f"{op} {reg()}, {reg()}, {imm}")
        elif k < 0.58:
            L.append(f"li {reg()}, {value(rng)}")
        elif k < 0.63:
            L.append(f"{rng.choice(['clz', 'popc'])} {reg()}, {reg()}")
        elif k < 0.75:
            op = rng.choice(list(STORES)); w = STORES[op]
            L.append(f"{op} [v16 + {rng.randrange(0, 256, w)}], {reg()}")
        elif k < 0.86:
            op = rng.choice(list(LOADS)); w = LOADS[op]
            L.append(f"{op} {reg()}, [v16 + {rng.randrange(0, 256, w)}]")
        elif k < 0.95:
            skip = rng.randint(1, 3); op = rng.choice(["beq", "bne", "blt", "bge", "bltu", "bgeu"])
            L.append(f"{op} {reg()}, {reg()}, skip{n}")
            for _ in range(skip):
                L.append(f"{rng.choice(RRR)} {reg()}, {reg()}, {reg()}")
            L.append(f"skip{n}:")
        else:
            L.append(f"seq {reg()}, {reg()}, {reg()}")
        n += 1
    # fold every data register and a 256-byte memory window into one 128-bit hash, then print it as 32 hex digits
    L += ["li v14, 0", "li v15, 0x9E3779B97F4A7C15F39CC0605CEDC835"]
    for r in DATA + [18] + CAPS:
        L += [f"rol v14, v14, v15", f"xor v14, v14, v{r}", "mul v14, v14, v15"]
    for q in range(16):
        L += [f"lq v13, [v16 + {q * 16}]", "rol v14, v14, v15", "xor v14, v14, v13", "mul v14, v14, v15"]
    L += ["li v11, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF0000", "li v12, 32", "hex:", "shri v10, v14, 124", "li v9, 10",
          "bltu v10, v9, digit", "addi v10, v10, 87", "jmp put", "digit:", "addi v10, v10, 48", "put:", "sb [v11 + 0], v10",
          "shli v14, v14, 4", "addi v12, v12, -1", "bne v12, v0, hex", "li v1, 0", "halt",
          "trapped:", "csrr v19, tpc", "addi v19, v19, 16", "csrw tpc, v19", "addi v18, v18, 1", "tret"]
    return "\n".join(L) + "\n"


def run_python(src):
    m = Machine(1 << 20); m.load(asm.assemble(src)); m.run(200000)
    return m.console.decode(), m.cycles, m.stop_reason


@unittest.skipUnless(shutil.which("gcc") or shutil.which("cc"), "no C compiler")
class Differential(unittest.TestCase):
    N = int(os.environ.get("VEYLITH_FUZZ_N", "150"))

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.exe = os.path.join(cls.dir.name, "vvm")
        r = subprocess.run([shutil.which("gcc") or shutil.which("cc"), "-std=c11", "-O2", "-o", cls.exe, "native/veylith-vm.c"], capture_output=True)
        if r.returncode:
            raise unittest.SkipTest("C machine did not build")

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def run_c(self, src, name):
        img = os.path.join(self.dir.name, name + ".img")
        with open(img, "wb") as f:
            f.write(disk.build(src, ".org 0x20000\nhalt\n", 1 << 17))
        out = subprocess.run([self.exe, img], capture_output=True, text=True)
        return out.stdout.replace("\r", ""), int(re.search(r"(\d+) Glyphs", out.stdout + out.stderr).group(1))

    def test_random_programs_agree(self):
        for seed in range(self.N):
            src = program(seed)
            py_out, py_cycles, reason = run_python(src)
            self.assertEqual(reason, "halt", f"seed {seed}")
            c_out, c_cycles = self.run_c(src, f"p{seed}")
            self.assertRegex(py_out, r"^[0-9a-f]{32}$", f"seed {seed}")
            self.assertEqual(c_out.strip(), py_out.strip(), f"hash differs, seed {seed}")
            self.assertEqual(c_cycles, py_cycles, f"Glyph count differs, seed {seed}")

    def test_programs_are_not_degenerate(self):
        hashes = {run_python(program(s))[0] for s in range(20)}
        self.assertEqual(len(hashes), 20)                           # different seeds give different results
        self.assertNotEqual(run_python(program(0))[0], "0" * 32)


if __name__ == "__main__":
    unittest.main()
