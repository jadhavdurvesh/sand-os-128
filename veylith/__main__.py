"""Command line: python3 -m veylith {asm,dis,run,boot,opcodes,info}"""
import argparse
import json
import sys

from . import asm, image, isa
from . import VERSION
from .machine import Machine, CONSOLE_ADDR


def _positive_int(value):
    try:
        number = int(value, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer (decimal or 0x-prefixed)") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return number


def _machine_profile(ram, max_steps):
    return {
        "architecture": "SAND-128 / Veylith",
        "profile": "v0",
        "emulator_version": VERSION,
        "register_width_bits": isa.WIDTH,
        "register_count": isa.NUM_VEYLS,
        "register_file_bits": isa.WIDTH * isa.NUM_VEYLS,
        "instruction_glyph_width_bits": isa.GLYPH_BYTES * 8,
        "instruction_glyph_bytes": isa.GLYPH_BYTES,
        "virtual_address_bits": isa.VA_BITS,
        "program_counter_width_bits": isa.WIDTH,
        "endianness": "little",
        "ram_bytes": ram,
        "ram_mib": round(ram / (1024 * 1024), 3),
        "console_mmio_address": f"0x{CONSOLE_ADDR:08X}",
        "default_max_steps": max_steps,
        "execution_model": "deterministic, sequential, single-core",
    }


def _print_profile(ram, max_steps, as_json=False):
    profile = _machine_profile(ram, max_steps)
    if as_json:
        print(json.dumps(profile, indent=2))
        return
    print("[Veylith machine configuration]", file=sys.stderr)
    for key, value in profile.items():
        print(f"  {key}: {value}", file=sys.stderr)


def main(argv=None):
    p = argparse.ArgumentParser(prog="veylith", description="Veylith (SAND-128) tools")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("asm", help="assemble a source file into a VYLI image")
    a.add_argument("source")
    a.add_argument("-o", "--output", required=True)
    d = sub.add_parser("dis", help="disassemble a VYLI image")
    d.add_argument("image")
    r = sub.add_parser("run", help="load one or more images (first one sets the entry) and run")
    r.add_argument("images", nargs="+")
    r.add_argument("--ram", type=_positive_int, default=1 << 20, help="RAM size in bytes (positive multiple of 8)")
    r.add_argument("--max-steps", type=_positive_int, default=5_000_000, help="maximum executed glyphs")
    r.add_argument("--trace", metavar="FILE", help="write a Tracebook (JSON lines)")
    b = sub.add_parser("boot", help="assemble Kernelloom + a user source and run them")
    b.add_argument("user", nargs="?", default="examples/factorial.s", help="user program source (default: factorial demo)")
    b.add_argument("--kernel", default="kernel/kernelloom.s", help="kernel assembly source")
    b.add_argument("--ram", type=_positive_int, default=1 << 20, help="RAM size in bytes (positive multiple of 8)")
    b.add_argument("--max-steps", type=_positive_int, default=5_000_000, help="maximum executed glyphs")
    b.add_argument("--trace", metavar="FILE", help="write a Tracebook (JSON lines)")
    info = sub.add_parser("info", help="print the complete Veylith machine configuration")
    info.add_argument("--ram", type=_positive_int, default=1 << 20, help="RAM size in bytes")
    info.add_argument("--max-steps", type=_positive_int, default=5_000_000, help="configured execution step limit")
    info.add_argument("--json", action="store_true", help="emit machine configuration as JSON")
    sub.add_parser("opcodes", help="print the machine-readable glyph table")
    args = p.parse_args(argv)

    try:
        if args.cmd == "asm":
            with open(args.source) as source:
                blob = asm.assemble(source.read())
            with open(args.output, "wb") as output:
                output.write(blob)
            print(f"[assembler] wrote {len(blob)} bytes to {args.output}", file=sys.stderr)
            return 0
        if args.cmd == "dis":
            with open(args.image, "rb") as source:
                sys.stdout.write(asm.disassemble_image(source.read()))
            return 0
        if args.cmd == "opcodes":
            sys.stdout.write(isa.table_json())
            return 0
        if args.cmd == "info":
            _print_profile(args.ram, args.max_steps, args.json)
            return 0
        if args.cmd == "boot":
            with open(args.kernel) as kernel_file, open(args.user) as user_file:
                blobs = [asm.assemble(kernel_file.read()), asm.assemble(user_file.read())]
            return _run(blobs, args.ram, args.max_steps, args.trace, f"boot:{args.user}")
        with_images = []
        for filename in args.images:
            with open(filename, "rb") as image_file:
                with_images.append(image_file.read())
        return _run(with_images, args.ram, args.max_steps, args.trace, "run")
    except (asm.AsmError, image.ImageError, OSError, ValueError) as exc:
        print(f"veylith: {exc}", file=sys.stderr)
        return 2


def _run(blobs, ram, max_steps, trace_path, workload):
    _print_profile(ram, max_steps)
    print(f"[workload] {workload}; image_count={len(blobs)}; trace={'enabled' if trace_path else 'disabled'}", file=sys.stderr)
    machine = Machine(ram)
    if trace_path:
        machine.trace = []
    for index, blob in enumerate(blobs):
        machine.load(blob, set_entry=(index == 0))
    reason = machine.run(max_steps)
    sys.stdout.write(machine.console.decode("utf-8", "replace"))
    if trace_path:
        with open(trace_path, "w") as trace_file:
            for record in machine.trace:
                trace_file.write(json.dumps(record) + "\n")
        print(f"[tracebook] wrote {len(machine.trace)} records to {trace_path}", file=sys.stderr)
    print(
        f"[machine] stopped: {reason}; exit code {machine.exit_code}; "
        f"{machine.cycles} glyphs retired; pc=0x{machine.pc:x}; privilege={machine.priv}",
        file=sys.stderr,
    )
    return 0 if machine.exit_code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
