; Minimal user-mode application for the Veylith v0 Kernelloom environment.
; Demonstrates the write and exit system calls.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   v1, 1
    la   v2, message
    li   v3, 23
    sys  0

    li   v1, 2
    li   v2, 0
    sys  0

message:
    .ascii "Hello from Veylith v0!\n"
