; Kernelloom v1 syscall smoke test: getpid (3) and getcycles (4).
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   v1, 3
    sys  0
    li   v2, 1
    beq  v1, v2, pid_ok
    jmp  failed
pid_ok:
    li   v1, 1
    la   v2, pid_message
    li   v3, 16
    sys  0

    li   v1, 4
    sys  0
    bne  v1, v0, cycles_ok
    jmp  failed
cycles_ok:
    li   v1, 1
    la   v2, cycles_message
    li   v3, 25
    sys  0

    li   v1, 2
    li   v2, 0
    sys  0

failed:
    li   v1, 1
    la   v2, fail_message
    li   v3, 22
    sys  0
    li   v1, 2
    li   v2, 1
    sys  0

pid_message:     .ascii "PID syscall: OK\n"
cycles_message:  .ascii "Cycle counter syscall: OK\n"
fail_message:    .ascii "Kernel syscall FAIL\n"
