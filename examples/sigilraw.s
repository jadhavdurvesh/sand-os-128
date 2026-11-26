; Sigil negative test 2: a task in capability mode attempts a raw load. Raw memory access is forbidden there.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    li   v1, 11
    sys  0
    la   v5, data
    lq   v4, [v5 + 0]
    li   v2, 0
    li   v1, 2
    sys  0
.align 16
data: .space 16
