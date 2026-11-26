; Kernelloom v2: a single task that waits in recv with nobody left to send. The kernel reports the deadlock.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    li   v1, 9
    sys  0
    li   v1, 2
    li   v2, 0
    sys  0
