#!/usr/bin/env python3
"""web/sigil-lab.src.html + web/sigil-lab-data.json -> web/sigil-lab.html (one self-contained page). Run tools/lab_data.py first."""
import json, os
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src = open(os.path.join(root, "web/sigil-lab.src.html")).read()
data = json.dumps(json.load(open(os.path.join(root, "web/sigil-lab-data.json"))), separators=(",", ":")).replace("</", "<\\/")
assert "/*DATA*/null" in src
page = src.replace("/*DATA*/null", data)
head = '<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>\n'
open(os.path.join(root, "web/sigil-lab.html"), "w").write(head + page + "\n</body></html>\n")   # standalone file
import sys
if len(sys.argv) > 1: open(sys.argv[1], "w").write(page)                                          # fragment for hosts that add their own skeleton
print("wrote web/sigil-lab.html", os.path.getsize(os.path.join(root, "web/sigil-lab.html")), "bytes")
