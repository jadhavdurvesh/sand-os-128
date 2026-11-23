; User program that reads kernel memory.  Kernelloom must catch the ACCESS fault and halt with 128+5.
.org 0x10000
_start:
    li   v1, 0x100
    lq   v2, [v1 + 0]
    li   v1, 2
    li   v2, 0
    sys  0
