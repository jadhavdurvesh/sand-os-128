import json
import os
import struct
import unittest

from veylith import asm, image, isa
from veylith.isa import MASK
from veylith.machine import Machine, CONSOLE_ADDR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN = 1 << 127


def read(path):
    with open(path) as f:
        return f.read()


def run(src, steps=10000, ram=1 << 16, **kw):
    m = Machine(ram)
    m.load(asm.assemble(src))
    m.run(steps)
    return m


def reg(src, r="v3"):
    """Run src (a halt is appended) and return a register value."""
    m = run(src + "\n halt")
    assert m.stop_reason == "halt", m.stop_reason
    return m.v[int(r[1:])]


def trap_cause(src, user=False):
    """Run src in kernel mode with a trap handler that halts; return (cause, tval)."""
    m = run("""
    la v20, handler
    csrw tvec, v20
""" + src + """
    halt
handler:
    csrr v21, tcause
    csrr v22, tval
    halt
""")
    return m.v[21], m.v[22]


class Wide(unittest.TestCase):
    def test_li_all_widths(self):
        for val in (0, 1, -1, 2**31, 2**32, -2**31 - 1, 2**64 + 5, MASK, MIN, 0x0123456789ABCDEF0123456789ABCDEF):
            self.assertEqual(reg(f"li v3, {val}"), val & MASK, val)

    def test_add_wraps(self):
        self.assertEqual(reg(f"li v1, {MASK}\n li v2, 1\n add v3, v1, v2"), 0)
        self.assertEqual(reg("li v1, 0\n li v2, 1\n sub v3, v1, v2"), MASK)

    def test_mul_and_mulh(self):
        self.assertEqual(reg(f"li v1, {MASK}\n li v2, {MASK}\n mul v3, v1, v2"), 1)
        self.assertEqual(reg(f"li v1, {MASK}\n li v2, {MASK}\n mulh v3, v1, v2"), MASK - 1)

    def test_unsigned_divide(self):
        self.assertEqual(reg(f"li v1, {MASK}\n li v2, 10\n udiv v3, v1, v2"), MASK // 10)
        self.assertEqual(reg(f"li v1, {MASK}\n li v2, 10\n urem v3, v1, v2"), MASK % 10)

    def test_signed_divide_truncates_toward_zero(self):
        self.assertEqual(reg("li v1, -7\n li v2, 2\n sdiv v3, v1, v2"), (-3) & MASK)
        self.assertEqual(reg("li v1, -7\n li v2, 2\n srem v3, v1, v2"), (-1) & MASK)
        self.assertEqual(reg("li v1, 7\n li v2, -2\n sdiv v3, v1, v2"), (-3) & MASK)
        self.assertEqual(reg("li v1, 7\n li v2, -2\n srem v3, v1, v2"), 1)

    def test_signed_min_over_minus_one(self):
        self.assertEqual(reg(f"li v1, {MIN}\n li v2, -1\n sdiv v3, v1, v2"), MIN)
        self.assertEqual(reg(f"li v1, {MIN}\n li v2, -1\n srem v3, v1, v2"), 0)

    def test_shifts_use_count_mod_128(self):
        self.assertEqual(reg("li v1, 1\n li v2, 128\n shl v3, v1, v2"), 1)
        self.assertEqual(reg("li v1, 1\n li v2, 127\n shl v3, v1, v2"), MIN)
        self.assertEqual(reg(f"li v1, {MIN}\n li v2, 127\n shr v3, v1, v2"), 1)
        self.assertEqual(reg(f"li v1, {MIN}\n li v2, 127\n sar v3, v1, v2"), MASK)
        self.assertEqual(reg("li v1, 5\n sari v3, v1, 130"), 1)

    def test_rotates(self):
        self.assertEqual(reg(f"li v1, {MIN}\n li v2, 1\n rol v3, v1, v2"), 1)
        self.assertEqual(reg("li v1, 1\n li v2, 1\n ror v3, v1, v2"), MIN)
        self.assertEqual(reg("li v1, 77\n li v2, 0\n ror v3, v1, v2"), 77)

    def test_compare(self):
        self.assertEqual(reg("li v1, -1\n li v2, 1\n slt v3, v1, v2"), 1)
        self.assertEqual(reg("li v1, -1\n li v2, 1\n sltu v3, v1, v2"), 0)
        self.assertEqual(reg("li v1, 4\n li v2, 4\n seq v3, v1, v2"), 1)

    def test_clz_popc(self):
        self.assertEqual(reg("li v1, 0\n clz v3, v1"), 128)
        self.assertEqual(reg("li v1, 1\n clz v3, v1"), 127)
        self.assertEqual(reg(f"li v1, {MASK}\n popc v3, v1"), 128)

    def test_immediate_logic_sign_extends(self):
        self.assertEqual(reg("li v1, 0x1234\n andi v3, v1, -1"), 0x1234)
        self.assertEqual(reg("li v1, 0\n xori v3, v1, -1"), MASK)

    def test_v0_is_zero(self):
        self.assertEqual(reg("li v0, 99\n addi v3, v0, 0"), 0)

    def test_shk_builds_constants(self):
        self.assertEqual(reg("ldk v3, 1\n shk v3, 2\n shk v3, 3"), (1 << 64) | (2 << 32) | 3)


class Memory(unittest.TestCase):
    def test_widths_little_endian(self):
        m = run("li v1, 0x2000\n li v2, 0x0102030405060708090A0B0C0D0E0F10\n sq [v1 + 0], v2\n lb v3, [v1 + 0]\n lh v4, [v1 + 2]\n lq v5, [v1 + 0]\n halt")
        self.assertEqual(m.v[3], 0x10)
        self.assertEqual(m.v[4], 0x0D0E)
        self.assertEqual(m.v[5], 0x0102030405060708090A0B0C0D0E0F10)

    def test_sign_extending_loads(self):
        m = run("li v1, 0x2000\n li v2, 0xFF\n sb [v1 + 0], v2\n lb v3, [v1 + 0]\n lbs v4, [v1 + 0]\n halt")
        self.assertEqual((m.v[3], m.v[4]), (0xFF, MASK))

    def test_misaligned_traps(self):
        self.assertEqual(trap_cause("li v1, 0x2001\n lh v2, [v1 + 0]")[0], isa.CAUSE_MISALIGN)
        self.assertEqual(trap_cause("li v1, 0x2008\n lq v2, [v1 + 0]")[0], isa.CAUSE_MISALIGN)

    def test_out_of_ram_traps(self):
        self.assertEqual(trap_cause("li v1, 0x20000\n lb v2, [v1 + 0]")[0], isa.CAUSE_ACCESS)

    def test_noncanonical_address_traps(self):
        c, t = trap_cause("li v1, 1\n shli v1, v1, 100\n lb v2, [v1 + 0]")
        self.assertEqual((c, t), (isa.CAUSE_ACCESS, 1 << 100))

    def test_console_only_takes_byte_stores(self):
        m = run(f"li v1, {CONSOLE_ADDR}\n li v2, 65\n sb [v1 + 0], v2\n halt")
        self.assertEqual(bytes(m.console), b"A")
        self.assertEqual(trap_cause(f"li v1, {CONSOLE_ADDR}\n lb v2, [v1 + 0]")[0], isa.CAUSE_ACCESS)
        self.assertEqual(trap_cause(f"li v1, {CONSOLE_ADDR}\n sh [v1 + 0], v1")[0], isa.CAUSE_ACCESS)


class Control(unittest.TestCase):
    def test_loop_sums(self):
        self.assertEqual(reg("li v1, 10\n li v3, 0\nl: add v3, v3, v1\n addi v1, v1, -1\n bne v1, v0, l"), 55)

    def test_signed_and_unsigned_branches(self):
        src = "li v1, -1\n li v2, 1\n li v3, 0\n {op} v1, v2, t\n li v3, 5\nt: nop"
        self.assertEqual(reg(src.format(op="blt")), 0)
        self.assertEqual(reg(src.format(op="bltu")), 5)
        self.assertEqual(reg(src.format(op="bgeu")), 0)
        self.assertEqual(reg(src.format(op="bge")), 5)

    def test_call_and_ret(self):
        self.assertEqual(reg("call f\n addi v3, v3, 1\n halt\nf: li v3, 41\n ret"), 42)

    def test_jr_with_rd_equal_ra(self):
        self.assertEqual(reg("la v4, t\n jr v4, v4, 0\n li v3, 9\n halt\nt: li v3, 1"), 1)

    def test_branch_target_misaligned_fetch(self):
        c, t = trap_cause("li v1, 0x1003\n jr v1")
        self.assertEqual((c, t), (isa.CAUSE_MISALIGN, 0x1003))


class Traps(unittest.TestCase):
    def test_illegal_opcode(self):
        m = Machine(4096)
        m.load(image.pack([(0, struct.pack("<Q", 0xFF << 56))], 0))
        m.step()
        self.assertEqual(m.stop_reason, "unhandled trap ILLEGAL at pc=0x0 tval=0xff00000000000000")

    def test_reserved_bits_are_illegal(self):
        word = isa.encode("nop") | (1 << 32)
        self.assertIsNone(isa.decode(word))
        self.assertIsNone(isa.decode(isa.encode("add", 1, 2, 3) | 5))  # imm unused by rrr

    def test_divide_by_zero(self):
        self.assertEqual(trap_cause("li v1, 5\n udiv v2, v1, v0")[0], isa.CAUSE_DIVZERO)
        self.assertEqual(trap_cause("li v1, 5\n srem v2, v1, v0")[0], isa.CAUSE_DIVZERO)

    def test_csr_rules(self):
        self.assertEqual(trap_cause("li v1, 1\n csrw priv, v1")[0], isa.CAUSE_ILLEGAL)
        self.assertEqual(trap_cause("csrr v1, 77")[0], isa.CAUSE_ILLEGAL)
        self.assertEqual(reg("li v1, 7\n csrw scratch, v1\n csrr v3, scratch"), 7)

    def test_cycles_counts_retired(self):
        self.assertEqual(reg("nop\n nop\n csrr v3, cycles"), 2)

    def test_unhandled_trap_stops_machine(self):
        m = run("li v1, 1\n udiv v2, v1, v0")
        self.assertIn("unhandled trap DIVZERO", m.stop_reason)

    def test_step_limit(self):
        m = run("l: jmp l", steps=50)
        self.assertEqual(m.stop_reason, "step limit")


USER_PROLOGUE = """
    la v20, handler
    csrw tvec, v20
    li v1, 0x4000
    csrw abase, v1
    csrw tpc, v1
    li v1, 0x1000
    csrw alim, v1
    li v1, 1
    csrw tpriv, v1
    tret
handler:
    csrr v21, tcause
    csrr v22, tval
    csrr v23, tpc
    csrr v24, tpriv
    halt
.org 0x4000
"""


def user(body):
    return run(USER_PROLOGUE + body)


class Privilege(unittest.TestCase):
    def test_user_syscall_returns_to_next_glyph(self):
        m = user("sys 42\n nop")
        self.assertEqual((m.v[21], m.v[22], m.v[23], m.v[24]), (isa.CAUSE_SYSCALL, 42, 0x4008, 1))

    def test_user_cannot_halt_or_touch_csrs(self):
        for body in ("halt", "csrr v1, scratch", "csrw scratch, v1", "tret"):
            m = user(body)
            self.assertEqual(m.v[21], isa.CAUSE_PRIVILEGE, body)
            self.assertEqual(m.v[23], 0x4000)

    def test_user_confined_to_aperture(self):
        for body in ("li v1, 0x100\n lb v2, [v1 + 0]", "li v1, 0x5000\n lb v2, [v1 + 0]",
                     "li v1, 0x4FFF\n lb v2, [v1 + 0]\n li v1, 0x5000\n sb [v1 + 0], v2"):
            self.assertEqual(user(body).v[21], isa.CAUSE_ACCESS, body)

    def test_user_may_use_whole_aperture(self):
        m = user("li v1, 0x4FF0\n li v2, 9\n sq [v1 + 0], v2\n lq v3, [v1 + 0]\n sys 1")
        self.assertEqual(m.v[3], 9)
        self.assertEqual(m.v[21], isa.CAUSE_SYSCALL)

    def test_user_cannot_use_console(self):
        self.assertEqual(user(f"li v1, {CONSOLE_ADDR}\n li v2, 65\n sb [v1 + 0], v2").v[21], isa.CAUSE_ACCESS)

    def test_user_cannot_run_outside_aperture(self):
        self.assertEqual(user("li v1, 0x5000\n jr v1").v[21], isa.CAUSE_ACCESS)

    def test_trap_returns_to_kernel_privilege(self):
        m = user("sys 0")
        self.assertEqual(m.priv, 0)


class Toolchain(unittest.TestCase):
    def test_disassembly_reassembles_to_same_bytes(self):
        src = "li v1, 5\n add v2, v1, v1\n lq v3, [v2 + 16]\n sq [v2 + -8], v3\n beq v1, v2, e\n csrw tvec, v1\n csrr v4, cycles\n sys 3\ne: jr v5, v6, 4\n halt"
        blob = asm.assemble(src)
        again = asm.assemble(asm.disassemble_image(blob).replace("; entry", ";entry"))
        self.assertEqual(blob, again)

    def test_assembler_errors(self):
        bad = ["bogus v1", "add v1, v2", "add v1, v2, v99", "li v1, nope", "jmp missing", ".org 3\n nop", "x: nop\nx: nop",
               "addi v1, v2, 99999999999", "lb v1, v2", ".weird 1"]
        for src in bad:
            with self.assertRaises(asm.AsmError, msg=src):
                asm.assemble(src)

    def test_image_validation(self):
        good = image.pack([(0, b"\0" * 8)], 0)
        self.assertEqual(image.unpack(good), ([(0, b"\0" * 8)], 0))
        for blob in (b"", b"XXXX" + good[4:], good[:-1], good + b"x", good[:4] + b"\x09\x00" + good[6:]):
            with self.assertRaises(image.ImageError):
                image.unpack(blob)

    def test_segment_outside_ram_rejected(self):
        m = Machine(4096)
        with self.assertRaises(image.ImageError):
            m.load(image.pack([(4090, b"\0" * 16)], 0))

    def test_glyph_table_file_is_current(self):
        with open(os.path.join(ROOT, "architecture", "veylith-v0-glyphs.json")) as f:
            self.assertEqual(f.read(), isa.table_json())

    def test_every_glyph_roundtrips_through_decode(self):
        for name, (code, fmt, _) in isa.BY_NAME.items():
            kw = {"rd": 1 if "rd" in isa.FORMATS[fmt] else 0, "ra": 2 if "ra" in isa.FORMATS[fmt] else 0,
                  "rb": 3 if "rb" in isa.FORMATS[fmt] else 0, "imm": 7 if "imm" in isa.FORMATS[fmt] else 0}
            d = isa.decode(isa.encode(name, **kw))
            self.assertEqual((d[0], d[1], d[2], d[3], d[4]), (name, kw["rd"], kw["ra"], kw["rb"], kw["imm"]))


class Determinism(unittest.TestCase):
    def test_same_program_same_tracebook(self):
        def trace():
            m = Machine(1 << 16)
            m.trace = []
            m.load(asm.assemble("li v1, 3\nl: addi v1, v1, -1\n bne v1, v0, l\n halt"))
            m.run(100)
            return json.dumps(m.trace)
        self.assertEqual(trace(), trace())

    def test_tracebook_records_are_versioned(self):
        m = Machine(1 << 16)
        m.trace = []
        m.load(asm.assemble("li v1, 3\n halt"))
        m.run(10)
        self.assertEqual(m.trace[0]["tracebook"], 1)
        self.assertEqual(m.trace[0]["regs"], {"v1": "0x3"})
        self.assertEqual(m.trace[0]["op"], "ldk")


class Kernelloom(unittest.TestCase):
    def boot(self, user_src):
        m = Machine(1 << 20)
        m.load(asm.assemble(read(os.path.join(ROOT, "kernel", "kernelloom.s"))))
        m.load(asm.assemble(read(os.path.join(ROOT, user_src))), set_entry=False)
        m.run(2_000_000)
        return m

    def test_factorial_prints_exact_128_bit_values(self):
        m = self.boot("examples/factorial.s")
        out = m.console.decode()
        self.assertIn("295232799039604140847618609643520000000\n", out)
        self.assertIn("170141183460469231731687303715884105728\n", out)
        self.assertTrue(out.endswith("[kernelloom] user exit 0\n"))
        self.assertEqual((m.stop_reason, m.exit_code), ("halt", 0))

    def test_user_fault_is_reported_and_stops(self):
        m = self.boot("examples/badptr.s")
        self.assertIn("user fault cause=5 tval=256", m.console.decode())
        self.assertEqual(m.exit_code, 128 + isa.CAUSE_ACCESS)

    def test_write_rejects_buffers_outside_aperture(self):
        src = "li v1, 1\n li v2, 0x100\n li v3, 8\n sys 0\n mv v9, v1\n li v1, 2\n mv v2, v9\n sys 0\n"
        path = os.path.join(ROOT, "tests", "_tmp_user.s")
        try:
            with open(path, "w") as f:
                f.write(".org 0x10000\n" + src)
            m = self.boot("tests/_tmp_user.s")
        finally:
            os.remove(path)
        self.assertIn("user exit 340282366920938463463374607431768211455", m.console.decode())

    def test_unknown_syscall_returns_minus_one(self):
        path = os.path.join(ROOT, "tests", "_tmp_user2.s")
        try:
            with open(path, "w") as f:
                f.write(".org 0x10000\n li v1, 99\n sys 0\n mv v2, v1\n li v1, 2\n sys 0\n")
            m = self.boot("tests/_tmp_user2.s")
        finally:
            os.remove(path)
        self.assertIn(str(MASK), m.console.decode())


if __name__ == "__main__":
    unittest.main()
