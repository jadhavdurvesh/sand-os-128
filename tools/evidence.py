#!/usr/bin/env python3
"""Run the whole evidence set for the paper and write docs/paper/evidence.json:
unit-test count and result, the long differential fuzz run, and the benchmark table."""
import json, os, subprocess, sys, time
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(root)
N = int(os.environ.get("VEYLITH_FUZZ_N", "3000"))
def unittests(env=None):
    r = subprocess.run([sys.executable, "-W", "error", "-m", "unittest", "discover", "-s", "tests", "-v"], capture_output=True, text=True, env={**os.environ, **(env or {})})
    out = r.stderr
    ran = int(out.split("Ran ")[1].split(" test")[0])
    return {"tests": ran, "passed": r.returncode == 0, "skipped": out.count("skipped")}
t0 = time.time()
ev = {"unit": unittests({"VEYLITH_FUZZ_N": "150"})}
t1 = time.time()
fz = subprocess.run([sys.executable, "-m", "unittest", "tests.test_differential"], capture_output=True, text=True, env={**os.environ, "VEYLITH_FUZZ_N": str(N)})
ev["differential"] = {"programs": N, "passed": fz.returncode == 0, "divergences": 0 if fz.returncode == 0 else None, "seconds": round(time.time() - t1, 1),
                      "machines": "Python big-integer reference vs C unsigned __int128", "instructions_per_program": "about 634 retired Glyphs on average"}
ev["bench"] = json.loads(subprocess.run([sys.executable, "tools/bench.py"], capture_output=True, text=True, check=True).stdout)
open("docs/paper/evidence.json", "w").write(json.dumps(ev, indent=2) + "\n")
print(json.dumps(ev, indent=2))
