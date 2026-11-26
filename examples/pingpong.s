; Kernelloom v2 round-robin: task 1 prints "A" and a spawned task prints "B", each yielding after every letter.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    la   v2, other
    li   v3, 0x1E000
    li   v4, 0
    li   v1, 6
    sys  0
    mv   v20, v1             ; the new tid
    li   v21, 4
aloop:
    li   v1, 1
    la   v2, ch_a
    li   v3, 1
    sys  0
    li   v1, 5               ; yield
    sys  0
    addi v21, v21, -1
    bne  v21, v0, aloop
    mv   v2, v20
    li   v1, 7               ; join: wait for the other task to finish
    sys  0
    li   v1, 1
    la   v2, ch_nl
    li   v3, 1
    sys  0
    li   v2, 0
    li   v1, 2
    sys  0
other:
    li   v21, 4
bloop:
    li   v1, 1
    la   v2, ch_b
    li   v3, 1
    sys  0
    li   v1, 5
    sys  0
    addi v21, v21, -1
    bne  v21, v0, bloop
    li   v1, 2
    li   v2, 0
    sys  0
ch_a:  .ascii "A"
ch_b:  .ascii "B"
ch_nl: .ascii "\n"
