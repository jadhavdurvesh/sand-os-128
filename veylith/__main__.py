"""Veylith 128-Native v1 command-line tools."""
import argparse,json,sys
from . import asm,image,isa,VERSION
from .machine import Machine,CONSOLE_ADDR
def positive_int(value):
    try:n=int(value,0)
    except ValueError as exc:raise argparse.ArgumentTypeError("expected an integer") from exc
    if n<=0:raise argparse.ArgumentTypeError("must be greater than zero")
    return n
def machine_profile(ram,max_steps):
    return {"architecture":"SAND-128 / Veylith","profile":"128-native-v1","emulator_version":VERSION,"register_width_bits":isa.WIDTH,"general_purpose_register_count":isa.NUM_GPRS,"general_purpose_register_file_bits":isa.WIDTH*isa.NUM_GPRS,"register_slots_including_zero":isa.NUM_VEYLS,"instruction_glyph_width_bits":isa.GLYPH_BYTES*8,"instruction_glyph_bytes":isa.GLYPH_BYTES,"immediate_field_bits":isa.IMM_BITS,"virtual_address_bits":isa.VA_BITS,"pointer_width_bits":isa.WIDTH,"program_counter_width_bits":isa.WIDTH,"endianness":"little","ram_bytes":ram,"ram_mib":round(ram/(1024*1024),3),"console_mmio_address":f"0x{CONSOLE_ADDR:032X}","default_max_steps":max_steps,"execution_model":"deterministic, sequential, single-core","image_format":f"VYLI v{image.VERSION}","physical_memory_model":"bounded emulated RAM; independent of virtual address width"}
def print_profile(ram,max_steps,as_json=False):
    data=machine_profile(ram,max_steps)
    if as_json:print(json.dumps(data,indent=2))
    else:
        print("[Veylith 128-Native machine configuration]",file=sys.stderr)
        for k,v in data.items():print(f"  {k}: {v}",file=sys.stderr)
def main(argv=None):
    p=argparse.ArgumentParser(prog="veylith",description="Veylith 128-Native (SAND-128)")
    sub=p.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("asm");a.add_argument("source");a.add_argument("-o","--output",required=True)
    d=sub.add_parser("dis");d.add_argument("image")
    r=sub.add_parser("run");r.add_argument("images",nargs="+");r.add_argument("--ram",type=positive_int,default=1<<20);r.add_argument("--max-steps",type=positive_int,default=5_000_000);r.add_argument("--trace")
    b=sub.add_parser("boot");b.add_argument("user",nargs="?",default="examples/factorial.s");b.add_argument("--kernel",default="kernel/kernelloom.s");b.add_argument("--ram",type=positive_int,default=1<<20);b.add_argument("--max-steps",type=positive_int,default=5_000_000);b.add_argument("--trace")
    i=sub.add_parser("info");i.add_argument("--ram",type=positive_int,default=1<<20);i.add_argument("--max-steps",type=positive_int,default=5_000_000);i.add_argument("--json",action="store_true")
    sub.add_parser("opcodes");args=p.parse_args(argv)
    try:
        if args.cmd=="asm":
            with open(args.source) as f:blob=asm.assemble(f.read())
            with open(args.output,"wb") as f:f.write(blob)
            print(f"[assembler] wrote {len(blob)} bytes to {args.output}",file=sys.stderr);return 0
        if args.cmd=="dis":
            with open(args.image,"rb") as f:sys.stdout.write(asm.disassemble_image(f.read()))
            return 0
        if args.cmd=="opcodes":sys.stdout.write(isa.table_json());return 0
        if args.cmd=="info":print_profile(args.ram,args.max_steps,args.json);return 0
        if args.cmd=="boot":
            with open(args.kernel) as k,open(args.user) as u:blobs=[asm.assemble(k.read()),asm.assemble(u.read())]
            return execute(blobs,args.ram,args.max_steps,args.trace,"boot:"+args.user)
        blobs=[]
        for name in args.images:
            with open(name,"rb") as f:blobs.append(f.read())
        return execute(blobs,args.ram,args.max_steps,args.trace,"run")
    except (asm.AsmError,image.ImageError,OSError,ValueError) as exc:
        print(f"veylith: {exc}",file=sys.stderr);return 2
def execute(blobs,ram,max_steps,trace_path,workload):
    print_profile(ram,max_steps)
    print(f"[workload] {workload}; image_count={len(blobs)}; trace={'enabled' if trace_path else 'disabled'}",file=sys.stderr)
    m=Machine(ram)
    if trace_path:m.trace=[]
    for i,blob in enumerate(blobs):m.load(blob,set_entry=(i==0))
    reason=m.run(max_steps);sys.stdout.write(m.console.decode("utf-8","replace"))
    if trace_path:
        with open(trace_path,"w") as f:
            for rec in m.trace:f.write(json.dumps(rec)+"\n")
        print(f"[tracebook] wrote {len(m.trace)} records to {trace_path}",file=sys.stderr)
    print(f"[machine] stopped: {reason}; exit code {m.exit_code}; {m.cycles} Glyphs retired; pc=0x{m.pc:032x}; privilege={m.priv}",file=sys.stderr)
    return 0 if m.exit_code==0 else 1
if __name__=="__main__":sys.exit(main())
