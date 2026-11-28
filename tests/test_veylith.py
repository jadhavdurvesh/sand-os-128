import json,os,unittest
from veylith import asm,image,isa,disk
from veylith.machine import Machine,CONSOLE_ADDR,GPU_WIDTH,GPU_HEIGHT
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
    def test_process_info_syscalls(self):
        m=self.boot("examples/process_info.s");o=m.console.decode();self.assertIn("PID syscall: OK",o);self.assertIn("Cycle counter syscall: OK",o);self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_desktop_framebuffer(self):
        m=self.boot("examples/hello.s");self.assertEqual((GPU_WIDTH,GPU_HEIGHT),(1280,720));self.assertEqual(len(m.framebuffer),1280*720*4);self.assertNotEqual(m.framebuffer[:4],b"\\0\\0\\0\\0");self.assertIn(b"\xf6\xee\xe8\xff",m.framebuffer);self.assertEqual(m.stop_reason,"halt")
    def test_hello(self):
        m=self.boot("examples/hello.s");self.assertIn("Hello from Veylith 128-Native v1!",m.console.decode());self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_native128_example(self):
        m=self.boot("examples/native128.s");self.assertIn("128-bit memory round-trip OK!",m.console.decode());self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_factorial(self):
        m=self.boot("examples/factorial.s");o=m.console.decode();self.assertIn("295232799039604140847618609643520000000",o);self.assertIn("170141183460469231731687303715884105728",o);self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_badptr(self):
        m=self.boot("examples/badptr.s");self.assertIn("user fault cause=5 tval=256",m.console.decode());self.assertEqual(m.exit_code,133)
    def test_threads_round_robin(self):
        m=self.boot("examples/pingpong.s");self.assertIn("ABABABAB\n",m.console.decode());self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_threads_send_recv_128_bit(self):
        m=self.boot("examples/threads.s");o=m.console.decode()
        for n in ("2432902008176640000","265252859812191058636308480000000","295232799039604140847618609643520000000","295233064292463953041110147960176640000"):self.assertIn(n,o)
        self.assertEqual(o.count("worker result:"),3);self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_thread_edge_cases(self):
        m=self.boot("examples/threadedge.s");self.assertIn("ok\n",m.console.decode());self.assertNotIn("FAIL",m.console.decode());self.assertEqual(m.exit_code,0)
    def test_deadlock_is_reported(self):
        m=self.boot("examples/threaddead.s");self.assertIn("deadlock: every task is blocked",m.console.decode());self.assertEqual(m.exit_code,200)
    def test_threads_keep_private_128_bit_registers(self):
        src=(".org 0x10000\n_start:\nli sp, 0x1F000\nla v2, other\nli v3, 0x1E000\nli v4, 0\nli v1, 6\nsys 0\nmv v20, v1\n"
             "li v128, 0x1111111111111111111111111111111\nli v1, 5\nsys 0\nli v9, 0x1111111111111111111111111111111\nbne v128, v9, bad\n"
             "mv v2, v20\nli v1, 7\nsys 0\nla v2, good\nli v3, 1\nli v1, 1\nsys 0\nli v2, 0\nli v1, 2\nsys 0\n"
             "bad:\nli v2, 1\nli v1, 2\nsys 0\nother:\nli v128, 0x2222222222222222222222222222222\nli v1, 5\nsys 0\nli v9, 0x2222222222222222222222222222222\nbne v128, v9, bad\nli v1, 2\nli v2, 0\nsys 0\ngood: .ascii \"G\"")
        m=Machine(1<<20);m.load(asm.assemble(read("kernel/kernelloom.s")));m.load(asm.assemble(src),set_entry=False);m.run(5_000_000)
        self.assertIn("G",m.console.decode());self.assertEqual(m.exit_code,0)
    def test_kernel_image_stays_below_its_scratch_area(self):
        segs,_=image.unpack(asm.assemble(read("kernel/kernelloom.s")));self.assertLessEqual(max(a+len(d) for a,d in segs),0x5800)   # kernel stack grows down from 0x6000; keep 2 KiB for it
    def test_high_register_preservation(self):
        src='.org 0x10000\n_start:\nli v128, 0x123456789ABCDEF0123456789ABCDEF\nli v1, 1\nla v2, msg\nli v3, 1\nsys 0\nmv v3, v128\nli v1, 2\nli v2, 0\nsys 0\nmsg: .ascii "X"'
        m=Machine(1<<20);m.load(asm.assemble(read("kernel/kernelloom.s")));m.load(asm.assemble(src),set_entry=False);m.run(5_000_000);self.assertEqual(m.v[3],0x123456789ABCDEF0123456789ABCDEF)
class Timer(unittest.TestCase):
    PRE="la v120, handler\ncsrw tvec, v120\nli v1, 0x4000\ncsrw abase, v1\ncsrw tpc, v1\nli v1, 0x1000\ncsrw alim, v1\nli v1, 1\ncsrw tpriv, v1\n"
    def test_timer_interrupts_user_code_once(self):
        src=self.PRE+"li v1, 100\ncsrw timecmp, v1\ntret\n.org 0x4000\nspin: jmp spin\nhandler:\ncsrr v121, tcause\ncsrr v122, tpc\ncsrr v123, timecmp\nhalt"
        m=run(src,steps=1000);self.assertEqual((m.v[121],m.v[122],m.v[123]),(isa.CAUSE_TIMER,0x4000,0));self.assertEqual(isa.CAUSES[7],"TIMER")
    def test_timer_never_interrupts_kernel(self):
        m=run("la v120, handler\ncsrw tvec, v120\nli v1, 5\ncsrw timecmp, v1\nli v2, 0\nl: addi v2, v2, 1\nli v3, 300\nbne v2, v3, l\nhalt\nhandler:\nli v2, 999\nhalt",steps=5000)
        self.assertEqual((m.stop_reason,m.v[2]),("halt",300))
    def test_timecmp_is_128_bit_and_deadline_is_respected(self):
        big=(1<<100)+5;m=run(f"li v1, {big}\ncsrw timecmp, v1\ncsrr v2, timecmp\nhalt");self.assertEqual(m.v[2],big)
        src=self.PRE+f"li v1, {big}\ncsrw timecmp, v1\ntret\n.org 0x4000\nli v5, 7\nsys 1\nhandler:\ncsrr v121, tcause\nhalt"
        self.assertEqual(run(src,steps=1000).v[121],isa.CAUSE_SYSCALL)       # a far deadline never fires
    def test_preemption_without_yield(self):
        m=Kernelloom.boot(Kernelloom,"examples/preempt.s");self.assertIn("preemption works: ok",m.console.decode());self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
class NativeMachine(unittest.TestCase):
    def test_c_machine_matches_python_machine(self):
        import shutil,subprocess,re,tempfile
        cc=shutil.which("gcc") or shutil.which("cc")
        if not cc:self.skipTest("no C compiler")
        with tempfile.TemporaryDirectory() as d:
            exe=os.path.join(d,"vvm");r=subprocess.run([cc,"-std=c11","-O2","-o",exe,"native/veylith-vm.c"],capture_output=True)
            if r.returncode:self.skipTest("C machine did not build")
            for ex in ("hello","factorial","native128","badptr","process_info","threads","pingpong","threadedge","threaddead","preempt","sigil","sigilforge","sigilraw","gate","gateswitch","gateiso"):
                img=os.path.join(d,ex+".img");
                with open(img,"wb") as f:f.write(disk.build(read("kernel/kernelloom.s"),read(f"examples/{ex}.s")))
                c=subprocess.run([exe,img],capture_output=True,text=True);m=Kernelloom.boot(Kernelloom,f"examples/{ex}.s")
                n=int(re.search(r"(\d+) Glyphs",c.stdout+c.stderr).group(1))
                self.assertEqual(n,m.cycles,ex);self.assertEqual(m.console.decode().rstrip(),c.stdout.rstrip().replace("\r",""),ex)
class Sigil(unittest.TestCase):
    """Sigil capabilities: 128-bit, tag-free, MAC-authenticated, hardware-checked (docs/18)."""
    KEY="li v1, 0x1234567890ABCDEF1234567890ABCDEF\ncsrw ckey, v1\n"
    MINT="li v2, 0x9000\nli v3, 0x0707\ncmint v4, v2, v3\n"             # base 0x9000, exp 7 (128 bytes), perms R|W|NARROW
    def test_mint_roundtrip_and_layout(self):
        m=run(self.KEY+self.MINT+"cinfo v5, v4\nhalt")
        self.assertEqual(m.v[5],(1<<127)|(7<<80)|(7<<72)|0x9000)
        self.assertEqual(m.v[4]&((1<<88)-1),(7<<80)|(7<<72)|0x9000);self.assertNotEqual(m.v[4]>>88,0)
    def test_every_single_bit_flip_invalidates(self):
        m=run(self.KEY+self.MINT+"halt");cap=m.v[4]
        for bit in range(128):
            m2=run(self.KEY+f"li v6, {cap^(1<<bit)}\ncinfo v5, v6\nhalt");self.assertEqual(m2.v[5],0,bit)
    def test_random_values_are_not_capabilities(self):
        import random;rng=random.Random(7);src=self.KEY+"li v7, 0\n"+"".join(f"li v6, {rng.getrandbits(128)}\ncinfo v5, v6\nor v7, v7, v5\n" for _ in range(300))+"halt"
        self.assertEqual(run(src,steps=20000).v[7],0)        # 300 guesses, each succeeds with probability 2^-40
    def test_changing_the_key_revokes_everything(self):
        m=run(self.KEY+self.MINT+"li v1, 99\ncsrw ckey, v1\ncinfo v5, v4\nhalt");self.assertEqual(m.v[5],0)
    def test_load_store_through_a_capability(self):
        m=run(self.KEY+self.MINT+"li v6, 0x1122334455667788AABBCCDDEEFF0011\ncsq [v4 + 16], v6\nclq v7, [v4 + 16]\nli v8, 0xAB\ncsb [v4 + 5], v8\nclb v9, [v4 + 5]\nlb v10, [v2 + 5]\nlq v11, [v2 + 16]\nhalt")
        self.assertEqual((m.v[7],m.v[9],m.v[10],m.v[11]),(0x1122334455667788AABBCCDDEEFF0011,0xAB,0xAB,0x1122334455667788AABBCCDDEEFF0011))
    def test_bounds_permissions_and_forgery_trap(self):
        for src in ("clq v7, [v4 + 128]","clq v7, [v4 + 120]","clb v7, [v4 + -1]","clb v7, [v4 + 128]","csb [v4 + 128], v0","li v6, 1\ncsb [v6 + 0], v0",
                    "li v5, 0x9000\nclb v7, [v5 + 0]"):
            self.assertEqual(trap(self.KEY+self.MINT+src)[0],isa.CAUSE_CAPABILITY,src)
        ro="li v2, 0x9000\nli v3, 0x0701\ncmint v4, v2, v3\n"             # read-only, exp 7, no NARROW
        self.assertEqual(trap(self.KEY+ro+"csb [v4 + 0], v0")[0],isa.CAUSE_CAPABILITY)
        self.assertEqual(run(self.KEY+ro+"clb v7, [v4 + 0]\nhalt").stop_reason,"halt")
        wo="li v2, 0x9000\nli v3, 0x0702\ncmint v4, v2, v3\n"
        self.assertEqual(trap(self.KEY+wo+"clb v7, [v4 + 0]")[0],isa.CAUSE_CAPABILITY)
        self.assertEqual(run(self.KEY+wo+"csb [v4 + 0], v0\nhalt").stop_reason,"halt")
    def test_narrowing_is_monotonic(self):
        # sub-region [0x9040, 0x9060): exp 5, offset 0x40, perms R only
        m=run(self.KEY+self.MINT+f"li v6, {1|5<<8|0x40<<16}\ncnarrow v7, v4, v6\ncinfo v8, v7\nhalt");self.assertEqual(m.v[8],(1<<127)|(1<<80)|(5<<72)|0x9040)
        for rb in (1|2<<8|0x40<<16 | 4<<0 | 8<<0, 8|5<<8|0x40<<16, 1|8<<8|0x40<<16, 1|5<<8|0x41<<16, 1|5<<8|0x80<<16, 1|6<<8|0x60<<16):
            self.assertEqual(trap(self.KEY+self.MINT+f"li v6, {rb}\ncnarrow v7, v4, v6")[0],isa.CAUSE_CAPABILITY,hex(rb))
        self.assertEqual(trap(self.KEY+self.MINT+f"li v6, {3|5<<8}\ncnarrow v7, v4, v6\ncnarrow v8, v7, v6")[0],isa.CAUSE_CAPABILITY)   # the narrowed cap lost NARROW
        self.assertEqual(trap(self.KEY+self.MINT+f"li v6, {7|7<<8}\ncnarrow v7, v4, v6\nli v6, {1|8<<8}\ncnarrow v8, v7, v6")[0],isa.CAUSE_CAPABILITY)   # cannot grow
    def test_mac_is_siphash24_reference_vector(self):
        from veylith.machine import siphash24
        key=int.from_bytes(bytes(range(16)),"little")
        self.assertEqual(siphash24(key,bytes(range(15))),0xa129ca6149be45e5)       # official SipHash-2-4 test vector (Aumasson and Bernstein)
        self.assertEqual(siphash24(key,b""),0x726fdb47dd0e0e31)
    def test_sealed_capability_is_an_opaque_token(self):
        m=run(self.KEY+self.MINT+"cseal v5, v4\ncinfo v6, v5\nhalt")
        self.assertEqual(m.v[6],(1<<127)|(0x87<<80)|(7<<72)|0x9000)
        for src in ("clb v7, [v5 + 0]","csb [v5 + 0], v0","li v6, 5\ncnarrow v7, v5, v6"):
            self.assertEqual(trap(self.KEY+self.MINT+"cseal v5, v4\n"+src)[0],isa.CAUSE_CAPABILITY,src)
        self.assertEqual(trap(self.KEY+"li v4, 5\ncseal v5, v4")[0],isa.CAUSE_CAPABILITY)        # cannot seal a forgery
    def test_only_the_kernel_can_unseal(self):
        m=run(self.KEY+self.MINT+"cseal v5, v4\ncunseal v6, v5\nhalt");self.assertEqual(m.v[6],m.v[4])
        self.assertEqual(trap(self.KEY+self.MINT+"cunseal v6, v4")[0],isa.CAUSE_CAPABILITY)      # not sealed
        src=Timer.PRE+"tret\n.org 0x4000\ncunseal v6, v5\nhalt\nhandler:\ncsrr v121, tcause\nhalt"
        pre="li v1, 0x77\ncsrw ckey, v1\nli v2, 0x4800\nli v3, 0x0707\ncmint v4, v2, v3\ncseal v5, v4\n"
        self.assertEqual(run(src.replace("tret",pre+"tret",1),steps=1000).v[121],isa.CAUSE_PRIVILEGE)
    def gate_machine(self,user,svc,perms=0x0F):
        pre=Timer.PRE.replace("tret","")+f"li v1, 0x77\ncsrw ckey, v1\nli v2, 0x4800\nli v3, {perms|8<<8}\ncmint v4, v2, v3\ncseal v5, v4\nli v1, 0x6000\ncsrw cstack, v1\ntret\n"
        src=pre+".org 0x4000\n"+user+"\nsys 1\n.org 0x4800\n"+svc+"\nhandler:\ncsrr v121, tcause\ncsrr v122, clink\nhalt"
        return run(src,steps=2000)
    def test_gate_call_and_return(self):
        m=self.gate_machine("ccall v6, v5\ncinfo v7, v6","li v9, 42\ncretn")
        self.assertEqual((m.v[9],m.v[121],m.v[122]),(42,isa.CAUSE_SYSCALL,0))        # the callee ran, control came back, the link is clear
        self.assertEqual(m.v[7],(1<<127)|(7<<80)|(8<<72)|0x4800)                      # callee's authority: the region, unsealed, no GATE bit
    def test_gate_faults(self):
        for name,user,svc,perms in (("unsealed","ccall v6, v4","cretn",0x0F),("forged","li v7, 5\nccall v6, v7","cretn",0x0F),
                                    ("sealed but not a gate","ccall v6, v5","cretn",0x07),("nested call","ccall v6, v5","ccall v6, v5\ncretn",0x0F),
                                    ("return with no call","cretn","cretn",0x0F)):
            m=self.gate_machine(user,svc,perms);self.assertEqual(m.v[121],isa.CAUSE_CAPABILITY,name)
    def test_isolated_call_hides_and_restores_registers(self):
        m=self.gate_machine("li v10, 0x77\nli v1, 3\nli v2, 4\nli v9, 0x99\nccalx v6, v5\nmv v11, v1\nmv v12, v2","mv v13, v10\nmv v14, v9\nadd v1, v1, v2\ncinfo v2, v6\nli v10, 0xBAD\ncretx")
        self.assertEqual((m.v[121],m.v[122]),(isa.CAUSE_SYSCALL,0))
        self.assertEqual((m.v[11],m.v[12]),(7,(1<<127)|(7<<80)|(8<<72)|0x4800))   # results travel back in v1 and v2; the callee held its own data capability
        self.assertEqual((m.v[10],m.v[9]),(0x77,0x99))           # the callee's clobbering is undone
        self.assertEqual((m.v[13],m.v[14]),(0,0))                # the callee saw no caller secrets
        self.assertEqual(m.v[6],0)                              # and rd is the caller's own value again after the return
    def test_isolated_and_shared_returns_do_not_mix(self):
        for name,user,svc in (("cretn after ccalx","ccalx v6, v5","cretn"),("cretx after ccall","ccall v6, v5","cretx"),("cretx with no call","cretx","cretx")):
            self.assertEqual(self.gate_machine(user,svc).v[121],isa.CAUSE_CAPABILITY,name)
    def test_isolated_call_needs_a_save_area(self):
        pre=Timer.PRE.replace("tret","")+"li v1, 0x77\ncsrw ckey, v1\nli v2, 0x4800\nli v3, 0x080F\ncmint v4, v2, v3\ncseal v5, v4\ntret\n"
        m=run(pre+".org 0x4000\nccalx v6, v5\nsys 1\n.org 0x4800\ncretx\nhandler:\ncsrr v121, tcause\nhalt",steps=2000)
        self.assertEqual(m.v[121],isa.CAUSE_CAPABILITY)
    def test_a_gate_exposes_only_its_entry_point(self):
        # a sealed gate cannot be used to load, store, narrow or jump anywhere but the region base
        for src in ("clb v7, [v5 + 0]","csb [v5 + 0], v0","li v6, 5\ncnarrow v7, v5, v6","jr v5"):
            self.assertEqual(self.gate_machine(src,"cretn").v[121]!=isa.CAUSE_SYSCALL,True,src)
    def test_kernelloom_gate_examples(self):
        for ex,msg in (("examples/gate.s","gate: ok\n"),("examples/gateswitch.s","gate switching: ok\n"),("examples/gateiso.s","gate isolation: ok\n")):
            m=Kernelloom.boot(Kernelloom,ex);self.assertIn(msg,m.console.decode(),ex);self.assertEqual((m.stop_reason,m.exit_code),("halt",0),ex)
    def test_only_the_kernel_can_mint(self):
        src=Timer.PRE+"tret\n.org 0x4000\nli v2, 0x4000\nli v3, 0x0707\ncmint v4, v2, v3\nhalt\nhandler:\ncsrr v121, tcause\nhalt"
        self.assertEqual(run(src,steps=1000).v[121],isa.CAUSE_PRIVILEGE)
    def test_capability_mode_forbids_raw_memory_access(self):
        pre=Timer.PRE.replace("tret","")
        body=(".org 0x4000\nli v5, 0x4800\n%s\nsys 1\nhandler:\ncsrr v121, tcause\ncsrr v122, tval\nhalt")
        k=pre+"li v1, 1\ncsrw cmode, v1\ntret\n"
        for raw in ("lb v6, [v5 + 0]","sq [v5 + 0], v0"):
            m=run(k+body%raw,steps=1000);self.assertEqual((m.v[121],m.v[122]),(isa.CAUSE_CAPABILITY,0x4800),raw)
        # the same access is fine when the mode is off, and a capability access is fine when it is on
        self.assertEqual(run(pre+"tret\n"+body%"lb v6, [v5 + 0]",steps=1000).v[121],isa.CAUSE_SYSCALL)
        mint="li v1, 0x55\ncsrw ckey, v1\nli v2, 0x4800\nli v3, 0x0707\ncmint v4, v2, v3\nli v1, 1\ncsrw cmode, v1\n"
        m=run(pre+mint+"tret\n"+".org 0x4000\nli v6, 9\ncsq [v4 + 32], v6\nclq v7, [v4 + 32]\nlq v8, [v5 + 0]\nsys 1\nhandler:\ncsrr v121, tcause\nhalt",steps=1000)
        self.assertEqual(m.v[7],9);self.assertEqual(m.v[121],isa.CAUSE_CAPABILITY)       # cap access ok, then the raw lq traps
    def test_kernelloom_capabilities_end_to_end(self):
        m=Kernelloom.boot(Kernelloom,"examples/sigil.s");o=m.console.decode()
        self.assertIn("Hi\n",o);self.assertIn("sigil capabilities: ok",o);self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_kernelloom_stops_forgery_and_raw_access_in_capability_mode(self):
        for ex,tval in (("examples/sigilforge.s",0x7F0000000000000000000000000000AA),("examples/sigilraw.s",None)):
            m=Kernelloom.boot(Kernelloom,ex);o=m.console.decode()
            self.assertIn("user fault cause=8",o,ex);self.assertEqual(m.exit_code,128+isa.CAUSE_CAPABILITY,ex)
            if tval:self.assertIn(f"tval={tval}",o)
    def test_capget_validates_regions_and_capability_mode_is_inherited(self):
        pre=".org 0x10000\n_start:\nli sp, 0x1F000\n"
        def sysc(n,*args):return "".join(f"li v{i+2}, {a}\n" for i,a in enumerate(args))+f"li v1, {n}\nsys 0\n"
        bad=[(0x10000,17,1),(0x10000,6,16),(0xF000,6,1),(0x10010,6,1),(0x1FFC0,7,1)]      # too big, bad perms, below aperture, misaligned, past the end
        src=pre+"".join(sysc(10,*a)+"li v9, -1\nbne v1, v9, wrong\n" for a in bad)+sysc(10,0x10000,6,7)+"cinfo v5, v1\nbeq v5, v0, wrong\nli v2, 0\nli v1, 2\nsys 0\nwrong:\nli v2, 1\nli v1, 2\nsys 0\n"
        m=Machine(1<<20);m.load(asm.assemble(read("kernel/kernelloom.s")));m.load(asm.assemble(src),set_entry=False);m.run(2_000_000);self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_length_multiplier_gives_tight_bounds(self):
        K="li v1, 0x77\ncsrw ckey, v1\n"
        mint=K+"li v2, 0x9000\nli v3, %d\ncmint v4, v2, v3\n"%(7|4<<8|24<<16)               # 400 bytes = 25 << 4, base aligned only to 16
        m=run(mint+"clq v6, [v4 + 384]\ncinfo v7, v4\nhalt")
        self.assertEqual(m.v[7],(1<<127)|(7<<80)|(4<<72)|(24<<64)|0x9000)
        self.assertEqual(trap(mint+"clq v6, [v4 + 400]")[0],isa.CAUSE_CAPABILITY)
        self.assertEqual(trap(mint+"clq v6, [v4 + 392]")[0],isa.CAUSE_CAPABILITY)           # 392 + 16 > 400
        narrow=mint+"li v5, %d\ncnarrow v8, v4, v5\n"%(3|4<<8|48<<16|1<<80)                  # 32 bytes at offset 48
        self.assertEqual(run(narrow+"clq v6, [v8 + 16]\nhalt").stop_reason,"halt")
        self.assertEqual(trap(narrow+"clq v6, [v8 + 32]")[0],isa.CAUSE_CAPABILITY)
        self.assertEqual(trap(mint+"li v5, %d\ncnarrow v8, v4, v5"%(3|4<<8|48<<16|25<<80))[0],isa.CAUSE_CAPABILITY)   # child would exceed the parent
        self.assertEqual(trap(K+"li v2, %d\nli v3, %d\ncmint v4, v2, v3"%((1<<64)-16,3|4<<8|1<<16))[0],isa.CAUSE_CAPABILITY)   # base + size wraps past 2^64
    def test_kernel_capget_with_length_multiplier(self):
        pre=".org 0x10000\n_start:\nli sp, 0x1F000\n"
        def sysc(n,*args):return "".join(f"li v{i+2}, {a}\n" for i,a in enumerate(args))+f"li v1, {n}\nsys 0\n"
        src=pre+sysc(10,0x10800,4|24<<8,3)+"mv v20, v1\nclq v6, [v20 + 384]\nli v7, 400\nli v8, 1\nsys 1\n".replace("sys 1\n","")+sysc(10,0x1FFF0,4|1<<8,3)+"li v9, -1\nbne v1, v9, wrong\nli v2, 0\nli v1, 2\nsys 0\nwrong:\nli v2, 1\nli v1, 2\nsys 0\n"
        m=Machine(1<<20);m.load(asm.assemble(read("kernel/kernelloom.s")));m.load(asm.assemble(src),set_entry=False);m.run(2_000_000);self.assertEqual((m.stop_reason,m.exit_code),("halt",0))
    def test_cap_cause_name(self):self.assertEqual(isa.CAUSES[8],"CAPABILITY")
class Trace(unittest.TestCase):
    def test_trace_width(self):
        m=Machine(1<<16);m.trace=[];m.load(asm.assemble("li v100, 1\n halt"));m.run(10);self.assertEqual(len(m.trace[0]["raw"])-2,32)
class Workload(unittest.TestCase):
    def test_sorting_network_sorts_raw_and_through_capabilities(self):
        import sys
        sys.path.insert(0,os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"tools"))
        import workloads
        a=workloads.run(workloads.build(False,3),3)[1];b=workloads.run(workloads.build(True,3),3)[1]
        self.assertEqual(a,sorted(a));self.assertEqual(a,b);self.assertEqual(len(workloads.PAIRS),63)
class Fragmentation(unittest.TestCase):
    def test_rounding_and_buddy(self):
        import sys
        sys.path.insert(0,os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"tools"))
        import frag
        self.assertEqual((frag.round_m(100,0),frag.round_m(100,8),frag.round_m(5,0),frag.round_m(1000,2)),(128,112,16,1024))
        self.assertEqual((frag.sigil_m_round(100),frag.sigil_m_round(256),frag.sigil_m_round(257),frag.sigil_m_round(100000)),(100,256,258,100352))
        b=frag.Buddy();a1,k1=b.alloc(100);a2,k2=b.alloc(100);self.assertEqual((k1,k2,a1%128,a2%128),(7,7,0,0))
        b.release(a1,k1);b.release(a2,k2);self.assertEqual(b.alloc(256)[0]%256,0)
if __name__=="__main__":unittest.main()
