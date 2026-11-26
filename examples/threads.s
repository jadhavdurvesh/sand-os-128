; Kernelloom v2 threads: three workers each compute a 128-bit factorial and send it to task 1.
; Task 1 receives the three 128-bit messages, joins the workers and prints the results and their sum.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    li   v20, 0              ; running sum (full 128 bits)
    li   v21, 3              ; messages still expected
    la   v2, worker
    li   v3, 0x1E000
    li   v4, 20              ; 20!
    li   v1, 6
    sys  0
    la   v2, worker
    li   v3, 0x1D000
    li   v4, 30              ; 30!
    li   v1, 6
    sys  0
    la   v2, worker
    li   v3, 0x1C000
    li   v4, 34              ; 34! (the largest that fits in 128 bits)
    li   v1, 6
    sys  0
collect:
    li   v1, 9               ; recv: blocks until a worker sends
    sys  0
    add  v20, v20, v1
    mv   v7, v1
    la   v2, msg_result
    li   v3, 15
    li   v1, 1
    sys  0
    call print_user
    addi v21, v21, -1
    bne  v21, v0, collect
    li   v22, 2              ; join tids 2..4
joins:
    mv   v2, v22
    li   v1, 7
    sys  0
    addi v22, v22, 1
    li   v23, 5
    bne  v22, v23, joins
    la   v2, msg_sum
    li   v3, 5
    li   v1, 1
    sys  0
    mv   v7, v20
    call print_user
    li   v2, 0
    li   v1, 2
    sys  0

; worker: v1 = n; sends n! to task 1, then exits
worker:
    li   v4, 1
    li   v5, 1
wloop:
    mul  v4, v4, v5
    addi v5, v5, 1
    bge  v1, v5, wloop
wsend:
    li   v1, 8               ; send(tid 1, value); -2 means its mailbox is full, so yield and retry
    li   v2, 1
    mv   v3, v4
    sys  0
    li   v6, -2
    bne  v1, v6, wdone
    li   v1, 5
    sys  0
    jmp  wsend
wdone:
    li   v1, 2
    li   v2, 0
    sys  0

print_user:
    li   v10, 10
    la   v11, BUF + 48
    mv   v12, v11
    addi v12, v12, -1
    li   v13, 10
    sb   [v12 + 0], v13
conv:
    urem v8, v7, v10
    udiv v7, v7, v10
    addi v8, v8, 48
    addi v12, v12, -1
    sb   [v12 + 0], v8
    bne  v7, v0, conv
    sub  v3, v11, v12
    mv   v2, v12
    li   v1, 1
    sys  0
    ret

msg_result: .ascii "worker result:\n"
msg_sum:    .ascii "sum:\n"
.align 16
BUF:        .space 48
