#!/usr/bin/env python3
"""docs/paper/evidence.json -> docs/paper/numbers.tex (LaTeX macros), so the paper's numbers cannot drift from the measurements."""
import json, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ev = json.load(open(os.path.join(root, "docs/paper/evidence.json"))); b = ev["bench"]
wl = json.load(open(os.path.join(root, "docs/paper/workloads.json")))
M = {
 "UnitTests": ev["unit"]["tests"], "FuzzPrograms": ev["differential"]["programs"], "FuzzDivergences": ev["differential"]["divergences"],
 "FactNative": b["factorial_34"]["native128_glyphs"], "FactLimb": b["factorial_34"]["limb64_glyphs"], "FactRatio": b["factorial_34"]["ratio"],
 "SyscallCost": b["syscall_getpid"]["extra_glyphs_per_call"], "YieldCost": b["yield_context_switch"]["extra_glyphs_per_yield"],
 "FrameBytes": b["yield_context_switch"]["register_frame_bytes"], "TimerCost": b["preemption"]["kernel_glyphs_per_timer_trap"],
 "Quantum": b["preemption"]["quantum_glyphs"], "Overhead": round(100 * b["preemption"]["overhead_fraction"], 1),
 "SigilGuesses": b["sigil"]["random_guesses_tried"], "SigilAccepted": b["sigil"]["random_guesses_accepted"], "Avalanche": b["sigil"]["avalanche_mean_mac_bits_flipped"],
 "IsoWords": b["sigil_gate"]["isolated_call_register_quads_spilled_and_restored"], "GateCall": b["sigil_gate"]["glyphs_per_gate_call_counter_service"], "GateRatio": round(b["syscall_getpid"]["extra_glyphs_per_call"] / b["sigil_gate"]["glyphs_per_gate_call_counter_service"]),
 "SortFrac": wl["capability_access_fraction_of_sort"], "SortOne": wl["sensitivity_percent_slowdown_if_each_capability_access_costs_k_extra_cycles"]["1"], "SortFour": wl["sensitivity_percent_slowdown_if_each_capability_access_costs_k_extra_cycles"]["4"],
 "KernelBytes": b["images"]["kernel_image_bytes"], "Opcodes": b["images"]["veylith_opcodes"],
}
nice = {"python_json_re_decimal": "Python (json, re, decimal)", "gcc_compile_veylith_vm": "gcc compiling \\texttt{veylith-vm.c}", "tar_gzip_repo": "tar and gzip of the repository", "sort_and_uniq": "sort and uniq, 200k lines", "git_log_and_diff": "git log and diff"}
fr = json.load(open(os.path.join(root, "docs/paper/fragmentation.json")))
FRAGROWS = "\n".join(nice[k] + " & " + f'{v["allocations"]:,}'.replace(",", "\\,") + f' & {v["internal_fragmentation_percent_by_mantissa_bits"]["0"]} & {v["internal_fragmentation_percent_by_mantissa_bits"]["2"]} & {v["internal_fragmentation_percent_by_mantissa_bits"]["6"]} & {v["buddy_peak_overhead_percent"]}\\\\' for k, v in fr.items())
with open(os.path.join(root, "docs/paper/numbers.tex"), "w") as f:
    f.write("\\newcommand{\\FragRows}{" + FRAGROWS.replace("\n", " ") + "}\n")
    for k, v in M.items():
        f.write(f"\\newcommand{{\\{k}}}{{{v}}}\n")
print(open(os.path.join(root, "docs/paper/numbers.tex")).read())
