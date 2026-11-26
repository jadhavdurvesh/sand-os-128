; Gate calls survive context switches: the gate's return link is saved per task. Both tasks enter the same service, and the
; service yields to the other task in the MIDDLE of the call. Each task must still return to its own caller.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    la   v2, svc
    li   v3, 8
    li   v4, 7 | 8
    li   v1, 10
    sys  0                       ; capget
    cseal v30, v1
    li   v1, 11
    sys  0                       ; capability mode, inherited by the worker
    la   v2, worker
    li   v3, 0x1E000
    mv   v4, v30                 ; the gate token is the worker's argument
    li   v1, 6
    sys  0
    mv   v24, v1
    ccall v20, v30               ; yields inside the service, comes back here
    mv   v10, v1
    li   v1, 9                   ; recv the worker's result
    sys  0
    mv   v11, v1
    add  v12, v10, v11
    li   v6, 3
    bne  v12, v6, bad            ; the two results are 1 and 2 in some order
    beq  v10, v11, bad
    mv   v2, v24
    li   v1, 7
    sys  0                       ; join
    la   v2, msg_ok
    li   v3, 19
    li   v1, 1
    sys  0
    li   v2, 0
    li   v1, 2
    sys  0
bad:
    la   v2, msg_bad
    li   v3, 4
    li   v1, 1
    sys  0
    li   v2, 1
    li   v1, 2
    sys  0
worker:
    mv   v30, v1
    ccall v20, v30
    mv   v3, v1
    li   v2, 1
    li   v1, 8                   ; send the result to task 1; retry if its mailbox is full
retry:
    li   v1, 8
    sys  0
    li   v6, -2
    beq  v1, v6, again
    li   v2, 0
    li   v1, 2
    sys  0
again:
    li   v1, 5
    sys  0
    li   v2, 1
    jmp  retry
msg_ok:  .ascii "gate switching: ok\n"
msg_bad: .ascii "BAD\n"
.align 256
svc:
    clq  v6, [v20 + 128]
    addi v6, v6, 1
    csq  [v20 + 128], v6
    li   v1, 5                   ; yield in the middle of the call
    sys  0
    mv   v1, v6
    cretn
.space 144
