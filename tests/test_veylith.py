import json,os,unittest
from veylith import asm,image,isa
from veylith.machine import Machine,CONSOLE_ADDR
MAX=(1<<128)-1;MIN=1<<127
def read(p):
    with open(p,encoding="utf-8") as f:return f.read()
def run(src,steps=10000,ram=1<<16):
    m=Machine(ram);m.load(asm.assemble(src));m.run(steps);return m
def reg(src,name="v3"):
    m=run(src+"\n halt");assert m.stop_reason=="halt",m.stop_reason;return m.v[int(name[1:])]
def trap(src):
    m=run("la v120, handler\n csrw tvec, v120\n"+src+"\nhalt\nhandler:\n csrr v121, tcause\n csrr v122, tval\n halt")
    return m.v[121],m.v[122]
class Architecture(unittest.TestCase):
    def test_parameters(self):self.assertEqual((isa.WIDTH,isa.NUM_GPRS,isa.GLYPH_BYTES*8,isa.VA_BITS),(128,128,128,128))
    def test_all_registers(self):
        for i in range(1,129):self.assertEqual(isa.decode(isa.encode("addi",rd=i,ra=i,imm=1))[1:3],(i,i))
        self.assertEqual(reg("li v100, 9","v100"),9);self.assertEqual(reg("li v128, 7","v128"),7)
    def test_glyph_reserved(self):
        self.assertEqual(len(isa.encode("halt").to_bytes(16,"little")),16);self.assertIsNone(isa.decode(isa.encode("nop")|(1<<88)))
        self.assertIsNone(isa.decode(isa.encode("addi",rd=1,ra=2,imm=0)|(129<<104)))
    def test_opcode_roundtrip(self):
        for n,(_,fmt,_) in isa.BY_NAME.items():
            kw={"rd":100 if "rd" in isa.FORMATS[fmt] else 0,"ra":101 if "ra" in isa.FORMATS[fmt] else 0,"rb":102 if "rb" in isa.FORMATS[fmt] else 0,"imm":7 if "imm" in isa.FORMATS[fmt] else 0}
            self.assertEqual(isa.decode(isa.encode(n,**kw)),(n,kw["rd"],kw["ra"],kw["rb"],kw["imm"]))
class Arithmetic(unittest.TestCase):
    def test_full_width_li(self):
        for n in [0,1,-1,2**87,2**88,2**100+7,MIN,MAX,0x123456789ABCDEF0123456789ABCDEF]:self.assertEqual(reg(f"li v90, {n}","v90"),n&MAX)
    def test_add_mul(self):
        self.assertEqual(reg(f"li v1, {MAX}\n li v2, 1\n add v3, v1, v2"),0)
        self.assertEqual(reg(f"li v1, {MAX}\n li v2, {MAX}\n mul v3, v1, v2"),1)
        self.assertEqual(reg(f"li v1, {MAX}\n li v2, {MAX}\n mulh v3, v1, v2"),MAX-1)
    def test_division(self):
        self.assertEqual(reg(f"li v1, {MAX}\n li v2, 10\n udiv v3, v1, v2"),MAX//10)
        self.assertEqual(reg("li v1, -7\n li v2, 2\n sdiv v3, v1, v2"),(-3)&MAX)
    def test_shift_popcount(self):
        self.assertEqual(reg("li v1, 1\n li v2, 127\n shl v3, v1, v2"),MIN);self.assertEqual(reg(f"li v1, {MAX}\n popc v3, v1"),128)
class Addressing(unittest.TestCase):
    def test_128_bit_pointer_math(self):
        n=(1<<127)+123;self.assertEqual(reg(f"li v1, {n}\n addi v3, v1, 9"),n+9)
    def test_high_address_fault(self):
        n=(1<<120)+0x1234;self.assertEqual(trap(f"li v1, {n}\n lb v2, [v1 + 0]"),(isa.CAUSE_ACCESS,n))
    def test_128_bit_memory(self):
        n=0x123456789ABCDEF0123456789ABCDEF;self.assertEqual(run(f"li v1, 0x2000\n li v2, {n}\n sq [v1 + 0], v2\n lq v3, [v1 + 0]\n halt").v[3],n)
    def test_high_mmio(self):self.assertEqual(bytes(run(f"li v1, {CONSOLE_ADDR}\n li v2, 65\n sb [v1 + 0], v2\n halt").console),b"A")
    def test_alignment(self):self.assertEqual(trap("li v1, 0x2001\n lh v2, [v1 + 0]")[0],isa.CAUSE_MISALIGN)
class Control(unittest.TestCase):
    def test_branch_call(self):
        self.assertEqual(reg("li v1, 5\n li v2, 0\nl: add v2, v2, v1\n addi v1, v1, -1\n bne v1, v0, l\n mv v3, v2"),15)
        self.assertEqual(reg("call f\n addi v3, v3, 1\n halt\nf: li v3, 41\n ret"),42)
    def test_divzero(self):self.assertEqual(trap("li v1, 3\n udiv v2, v1, v0")[0],isa.CAUSE_DIVZERO)
    def test_user_syscall(self):
        src="la v120, handler\ncsrw tvec, v120\nli v1, 0x4000\ncsrw abase, v1\ncsrw tpc, v1\nli v1, 0x1000\ncsrw alim, v1\nli v1, 1\ncsrw tpriv, v1\ntret\n.org 0x4000\nsys 42\nhalt\nhandler:\ncsrr v121, tcause\ncsrr v122, tval\ncsrr v123, tpc\nhalt"
        m=run(src);self.assertEqual((m.v[121],m.v[122],m.v[123]),(isa.CAUSE_SYSCALL,42,0x4010))
class Toolchain(unittest.TestCase):
    def test_vyli_v2(self):
        a=(1<<120)+0x1000;b=image.pack([(a,b"abc")],a);self.assertEqual(image.unpack(b),([(a,b"abc")],a));self.assertEqual(int.from_bytes(b[8:24],"little"),a)
    def test_v1_rejected(self):
        with self.assertRaises(image.ImageError):image.unpack(b"VYLI"+(1).to_bytes(2,"little")+b"\0"*18)
    def test_roundtrip(self):
        s="li v128, 0x123456789ABCDEF0123456789ABCDEF\nadd v99, v100, v127\nlq v3, [v99 + 16]\nsq [v99 + -16], v3\nbeq v100, v99, end\nend: halt"
        b=asm.assemble(s);self.assertEqual(asm.assemble(asm.disassemble_image(b)),b)
    def test_v129_rejected(self):
        with self.assertRaises(asm.AsmError):asm.assemble("li v129, 1")
class DiskImage(unittest.TestCase):
    def test_build_and_unpack(self):
        blob=disk.build(read("kernel/kernelloom.s"),read("examples/hello.s"));self.assertEqual(len(blob),2<<20);payload=disk.unpack(blob);segs,entry=image.unpack(payload);self.assertEqual(entry,0);self.assertTrue(any(a==0x10000 for a,_ in segs))
    def test_checksum_rejects_corruption(self):
        blob=bytearray(disk.build(read("kernel/kernelloom.s"),read("examples/hello.s")));blob[600]^=1
        with self.assertRaises(disk.DiskError):disk.unpack(blob)
class Kernelloom(unittest.TestCase):
    def boot(self,example):
        m=Machine(1<<20);m.load(asm.assemble(read("kernel/kernelloom.s")));m.load(asm.assemble(read(example)),set_entry=False);m.run(5_000_000);return m
    def test_hello(self):
        m=self.boot("examples/hello.s");self.assertIn("Hello from Veylith 128-Native v1!",m.console.decode());self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_native128_example(self):
        m=self.boot("examples/native128.s");self.assertIn("128-bit memory round-trip OK!",m.console.decode());self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_factorial(self):
        m=self.boot("examples/factorial.s");o=m.console.decode();self.assertIn("295232799039604140847618609643520000000",o);self.assertIn("170141183460469231731687303715884105728",o);self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_badptr(self):
        m=self.boot("examples/badptr.s");self.assertIn("user fault cause=5 tval=256",m.console.decode());self.assertEqual(m.exit_code,133)
    def test_high_register_preservation(self):
        src='.org 0x10000\n_start:\nli v128, 0x123456789ABCDEF0123456789ABCDEF\nli v1, 1\nla v2, msg\nli v3, 1\nsys 0\nmv v3, v128\nli v1, 2\nli v2, 0\nsys 0\nmsg: .ascii "X"'
        m=Machine(1<<20);m.load(asm.assemble(read("kernel/kernelloom.s")));m.load(asm.assemble(src),set_entry=False);m.run(5_000_000);self.assertEqual(m.v[3],0x123456789ABCDEF0123456789ABCDEF)
class Trace(unittest.TestCase):
    def test_trace_width(self):
        m=Machine(1<<16);m.trace=[];m.load(asm.assemble("li v100, 1\n halt"));m.run(10);self.assertEqual(len(m.trace[0]["raw"])-2,32)
if __name__=="__main__":unittest.main()
