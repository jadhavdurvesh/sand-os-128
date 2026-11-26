#!/usr/bin/env python3
"""docs/paper/evidence.json -> docs/paper/numbers.tex (LaTeX macros), so the paper's numbers cannot drift from the measurements."""
import json, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ev = json.load(open(os.path.join(root, "docs/paper/evidence.json"))); b = ev["bench"]
M = {
 "UnitTests": ev["unit"]["tests"], "FuzzPrograms": ev["differential"]["programs"], "FuzzDivergences": ev["differential"]["divergences"],
 "FactNative": b["factorial_34"]["native128_glyphs"], "FactLimb": b["factorial_34"]["limb64_glyphs"], "FactRatio": b["factorial_34"]["ratio"],
 "SyscallCost": b["syscall_getpid"]["extra_glyphs_per_call"], "YieldCost": b["yield_context_switch"]["extra_glyphs_per_yield"],
 "FrameBytes": b["yield_context_switch"]["register_frame_bytes"], "TimerCost": b["preemption"]["kernel_glyphs_per_timer_trap"],
 "Quantum": b["preemption"]["quantum_glyphs"], "Overhead": round(100 * b["preemption"]["overhead_fraction"], 1),
 "SigilGuesses": b["sigil"]["random_guesses_tried"], "SigilAccepted": b["sigil"]["random_guesses_accepted"], "Avalanche": b["sigil"]["avalanche_mean_mac_bits_flipped"],
 "KernelBytes": b["images"]["kernel_image_bytes"], "Opcodes": b["images"]["veylith_opcodes"],
}
with open(os.path.join(root, "docs/paper/numbers.tex"), "w") as f:
    for k, v in M.items():
        f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
print(open(os.path.join(root, "docs/paper/numbers.tex")).read())
