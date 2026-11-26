; Kernelloom v2 + timer interrupt: nobody ever yields. A worker spins incrementing a 128-bit counter, task 1 spins
; waiting for it to pass 5000. Only the timer interrupt (timecmp, cause 7) lets them take turns.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    la   v2, worker
    li   v3, 0x1E000
    li   v4, 0
    li   v1, 6
    sys  0
    mv   v20, v1
    la   v21, counter
    li   v22, 5000
wait:                        ; busy-wait: only a preemption can hand the CPU to the worker
    lq   v23, [v21 + 0]
    bltu v23, v22, wait
    la   v24, stop
    li   v25, 1
    sq   [v24 + 0], v25      ; ask the worker to finish
    mv   v2, v20
    li   v1, 7
    sys  0                   ; join
    la   v2, msg
    li   v3, 22
    li   v1, 1
    sys  0
    li   v2, 0
    li   v1, 2
    sys  0
worker:
    la   v21, counter
    la   v24, stop
wloop:
    lq   v23, [v21 + 0]
    addi v23, v23, 1
    sq   [v21 + 0], v23
    lq   v25, [v24 + 0]
    beq  v25, v0, wloop
    li   v1, 2
    li   v2, 0
    sys  0
msg:     .ascii "preemption works: ok\n\n"
.align 16
counter: .space 16
stop:    .space 16
