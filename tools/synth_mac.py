#!/usr/bin/env python3
"""Synthesise rtl/sipmac.v with Yosys (pip package yowasp-yosys) to a generic gate library and report logic depth and size.
Technology-independent: depth is in levels of 2-input gates (AND/NAND/OR/NOR/XOR/XNOR/ANDNOT/ORNOT) and MUX cells; it is NOT a
timing result for any process. Also checks the RTL against the Python MAC on random vectors (Yosys `eval`).
Output: docs/paper/synth.json."""
import json, os, random, re, subprocess, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, root)
from veylith.machine import sigil_mac
YOSYS = "yowasp-yosys"
RTL = os.path.join(root, "rtl", "sipmac.v")
GATES = "AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX"


def yosys(cmd):
    r = subprocess.run([YOSYS, "-p", cmd], capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout[-800:] + r.stderr[-800:])
    return r.stdout


def verify(n=8, seed=1):
    rng = random.Random(seed)
    for _ in range(n):
        key, body = rng.getrandbits(128), rng.getrandbits(88)
        out = yosys(f"read_verilog {RTL}; hierarchy -top sipmac; proc; flatten; opt; eval -set key 128'h{key:x} -set body 88'h{body:x} -show mac")
        bits = re.search(r"mac = 40'([01]{40})", out).group(1)
        assert int(bits, 2) == sigil_mac(key, body), "RTL differs from the Python MAC"
    return n


def synth(top):
    # ABC does not run in the WebAssembly build of Yosys, so there is no logic optimisation here: proc/flatten/opt, then
    # techmap to 2-input AND/OR/XOR gates (Yosys's own adder mapping), then topological longest path.
    out = yosys(f"read_verilog {RTL}; hierarchy -top {top}; proc; flatten; opt; techmap; opt -fast; opt_clean; ltp -noff; stat")
    depth = int(re.search(r"length=(\d+)", out).group(1))
    cells = {m.group(2): int(m.group(1)) for m in re.finditer(r"^\s+(\d+)\s+(\$_\w+_)\s*$", out, re.M)}
    total = sum(cells.values())
    return {"depth_levels": depth, "cells": total, "by_type": cells}


def main():
    res = {"rtl_vectors_verified": verify(), "sipround": synth("sipround"), "sipmac_unrolled": synth("sipmac")}
    res["rounds"] = 8
    d1, du = res["sipround"]["depth_levels"], res["sipmac_unrolled"]["depth_levels"]
    ceil = lambda a, b: -(-a // b)
    res["cycles_by_gate_levels_per_cycle"] = {str(D): {"unrolled": ceil(du, D), "iterative_8_rounds": 8 * ceil(d1 + 3, D)} for D in (8, 12, 16, 24, 32)}
    json.dump(res, open(os.path.join(root, "docs/paper/synth.json"), "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
