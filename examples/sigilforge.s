; Sigil negative test 1: a task in capability mode tries to use a forged capability (a made-up 128-bit value).
; The hardware raises a CAPABILITY trap and Kernelloom reports it as a user fault.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    li   v1, 11
    sys  0
    li   v3, 0x7F0000000000000000000000000000AA       ; a plausible-looking but forged capability
    clq  v4, [v3 + 0]
    li   v2, 0
    li   v1, 2
    sys  0
