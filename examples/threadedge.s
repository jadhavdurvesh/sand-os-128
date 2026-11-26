; Kernelloom v2 edge cases: bad spawn arguments, bad tids, a full mailbox, and a 128-bit message.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    li   v1, 6
    li   v2, 0x100            ; entry below the aperture
    li   v3, 0x1E000
    li   v4, 0
    sys  0
    mv   v20, v1              ; expect -1
    li   v1, 6
    la   v2, idle + 4         ; misaligned entry
    li   v3, 0x1E000
    li   v4, 0
    sys  0
    mv   v21, v1              ; expect -1
    li   v1, 7
    li   v2, 1                ; joining yourself
    sys  0
    mv   v22, v1              ; expect -1
    li   v1, 8
    li   v2, 9                ; no such task
    li   v3, 5
    sys  0
    mv   v23, v1              ; expect -1
    li   v1, 8
    li   v2, 1                ; to myself: stored in my mailbox
    li   v3, 0x123456789ABCDEF0123456789ABCDEF
    sys  0
    mv   v24, v1              ; expect 0
    li   v1, 8
    li   v2, 1                ; mailbox now full
    li   v3, 7
    sys  0
    mv   v25, v1              ; expect -2
    li   v1, 9                ; recv returns the stored 128-bit value
    sys  0
    mv   v26, v1
    li   v1, 3
    sys  0
    mv   v27, v1              ; getpid == 1
    li   v9, -1
    bne  v20, v9, fail
    bne  v21, v9, fail
    bne  v22, v9, fail
    bne  v23, v9, fail
    bne  v24, v0, fail
    li   v9, -2
    bne  v25, v9, fail
    li   v9, 0x123456789ABCDEF0123456789ABCDEF
    bne  v26, v9, fail
    li   v9, 1
    bne  v27, v9, fail
    la   v2, ok_msg
    li   v3, 3
    li   v1, 1
    sys  0
    li   v2, 0
    li   v1, 2
    sys  0
fail:
    la   v2, fail_msg
    li   v3, 5
    li   v1, 1
    sys  0
    li   v1, 2
    li   v2, 1
    sys  0
idle:
    li   v1, 2
    li   v2, 0
    sys  0
ok_msg: .ascii "ok\n"
fail_msg: .ascii "FAIL\n"
