#!/usr/bin/env python3
"""Real allocation traces -> what do Sigil-style bounds cost?
Collects malloc/free traces of real programs with an LD_PRELOAD logger (tools/alloc/interpose.c), then measures
  (1) internal fragmentation if every object's bounds are rounded up to m mantissa bits (m=0 is Sigil's exponent-only power-of-two bounds),
  (2) peak footprint of a buddy allocator, which natural alignment of power-of-two regions forces, against peak live bytes.
Output: docs/paper/fragmentation.json. These are traces of THIS machine's programs, not a benchmark suite."""
import json, os, struct, subprocess, sys, tempfile, shutil
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GRAN = 16                                   # capability granule: smallest region 16 bytes
def collect(cmd, env_extra=None):
    d = tempfile.mkdtemp(); so = os.path.join(d, "i.so"); tr = os.path.join(d, "t.bin")
    subprocess.run(["gcc", "-O2", "-shared", "-fPIC", "-o", so, os.path.join(root, "tools/alloc/interpose.c"), "-ldl"], check=True)
    env = dict(os.environ, LD_PRELOAD=so, ALLOC_TRACE=tr, **(env_extra or {}))
    subprocess.run(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=root)
    data = open(tr, "rb").read() if os.path.exists(tr) else b""
    shutil.rmtree(d)
    return [struct.unpack_from("<cQQ", data, i) for i in range(0, len(data) - 16, 17)]
def round_m(s, m):
    s = max(s, GRAN)
    e = s.bit_length() - 1
    step = 1 << max(e - m, 4)               # alignment unit: 2^(e-m), never below the 16-byte granule
    return (s + step - 1) // step * step
class Buddy:
    def __init__(self): self.free = {}; self.top = 0; self.live = {}; self.cur = 0; self.peak_span = 0
    def alloc(self, size):
        k = max((size - 1).bit_length(), 4)
        j = k
        while j < 60 and not self.free.get(j): j += 1
        if j < 60 and self.free.get(j): a = self.free[j].pop()
        else:
            j = max(k, (self.top - 1).bit_length() if self.top else k); a = (self.top + (1 << k) - 1) // (1 << k) * (1 << k); self.top = a + (1 << k); j = k
            self.peak_span = max(self.peak_span, self.top); return a, k
        while j > k: j -= 1; self.free.setdefault(j, []).append(a + (1 << j))
        return a, k
    def release(self, a, k):
        while True:
            buddy = a ^ (1 << k)
            fl = self.free.get(k, [])
            if buddy in fl: fl.remove(buddy); a = min(a, buddy); k += 1
            else: self.free.setdefault(k, []).append(a); return
def analyse(events):
    sizes = [s for op, p, s in events if op == b"m" and s > 0]
    res = {"allocations": len(sizes), "bytes_requested": sum(sizes), "median_size": sorted(sizes)[len(sizes) // 2] if sizes else 0}
    res["internal_fragmentation_percent_by_mantissa_bits"] = {str(m): round(100 * (sum(round_m(s, m) for s in sizes) - sum(sizes)) / sum(sizes), 2) for m in (0, 1, 2, 4, 6, 8)}
    b = Buddy(); live = {}; cur = 0; peak_live = 0
    for op, p, s in events:
        if op == b"m" and s > 0:
            a, k = b.alloc(s); live[p] = (a, k, s); cur += s; peak_live = max(peak_live, cur)
        elif op == b"f" and p in live:
            a, k, s0 = live.pop(p); b.release(a, k); cur -= s0
    res["peak_live_bytes"] = peak_live; res["buddy_peak_span_bytes"] = b.peak_span
    res["buddy_peak_overhead_percent"] = round(100 * (b.peak_span - peak_live) / max(peak_live, 1), 1)
    return res
PROGRAMS = {
 "python_json_re_decimal": ([sys.executable, "-c", "import json,re,decimal,collections;d={str(i):[i]*5 for i in range(20000)};s=json.dumps(d);json.loads(s);[re.findall(r'\\d+',s) for _ in range(3)];sum(decimal.Decimal(i)/7 for i in range(2000))"], {"PYTHONMALLOC": "malloc"}),
 "gcc_compile_veylith_vm": (["gcc", "-O2", "-c", "-o", "/dev/null", "native/veylith-vm.c"], {}),
 "tar_gzip_repo": (["bash", "-c", "tar cf - . 2>/dev/null | gzip -9 > /dev/null"], {}),
 "sort_and_uniq": (["bash", "-c", "seq 1 200000 | awk '{print $1*7919%100003}' | sort | uniq -c | sort -rn > /dev/null"], {}),
 "git_log_and_diff": (["bash", "-c", "git log --stat -n 50 > /dev/null; git diff HEAD~3 > /dev/null"], {}),
}
def main():
    out = {}
    for name, (cmd, env) in PROGRAMS.items():
        ev = collect(cmd, env)
        if len(ev) < 100: print("skip", name, len(ev)); continue
        out[name] = analyse(ev); print(name, json.dumps(out[name]))
    json.dump(out, open(os.path.join(root, "docs/paper/fragmentation.json"), "w"), indent=1)
if __name__ == "__main__": main()
