"""Command line: python3 -m veylith {asm,dis,run,boot,opcodes}"""
import argparse
import json
import sys

from . import asm, image
from .machine import Machine


def main(argv=None):
    p = argparse.ArgumentParser(prog="veylith", description="Veylith (SAND-128) tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("asm", help="assemble a source file into a VYLI image")
    a.add_argument("source"); a.add_argument("-o", "--output", required=True)
    d = sub.add_parser("dis", help="disassemble a VYLI image")
    d.add_argument("image")
    r = sub.add_parser("run", help="load one or more images (first one sets the entry) and run")
    r.add_argument("images", nargs="+")
    r.add_argument("--ram", type=int, default=1 << 20)
    r.add_argument("--max-steps", type=int, default=5_000_000)
    r.add_argument("--trace", metavar="FILE", help="write a Tracebook (JSON lines)")
    b = sub.add_parser("boot", help="assemble Kernelloom + a user source and run them")
    b.add_argument("user", nargs="?", default="examples/factorial.s")
    b.add_argument("--kernel", default="kernel/kernelloom.s")
    sub.add_parser("opcodes", help="print the machine-readable glyph table")
    args = p.parse_args(argv)

    try:
        if args.cmd == "asm":
            with open(args.output, "wb") as f:
                f.write(asm.assemble(open(args.source).read()))
            return 0
        if args.cmd == "dis":
            sys.stdout.write(asm.disassemble_image(open(args.image, "rb").read()))
            return 0
        if args.cmd == "opcodes":
            from . import isa
            sys.stdout.write(isa.table_json())
            return 0
        if args.cmd == "boot":
            blobs = [asm.assemble(open(args.kernel).read()), asm.assemble(open(args.user).read())]
            return _run(blobs, 1 << 20, 5_000_000, None)
        return _run([open(f, "rb").read() for f in args.images], args.ram, args.max_steps, args.trace)
    except (asm.AsmError, image.ImageError, OSError) as e:
        print(f"veylith: {e}", file=sys.stderr)
        return 2


def _run(blobs, ram, max_steps, trace_path):
    m = Machine(ram)
    if trace_path:
        m.trace = []
    for i, blob in enumerate(blobs):
        m.load(blob, set_entry=(i == 0))
    reason = m.run(max_steps)
    sys.stdout.write(m.console.decode("utf-8", "replace"))
    if trace_path:
        with open(trace_path, "w") as f:
            for rec in m.trace:
                f.write(json.dumps(rec) + "\n")
    print(f"[machine] stopped: {reason}; exit code {m.exit_code}; {m.cycles} glyphs retired", file=sys.stderr)
    return 0 if m.exit_code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
