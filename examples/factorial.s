; User program: native 128-bit arithmetic.  Prints 34! (the largest factorial that fits in 128 bits)
; and 2^127, then exits with code 0.  Runs inside Kernelloom's user aperture.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    la   v2, hello
    li   v3, 21
    li   v1, 1
    sys  0

    li   v4, 1              ; acc
    li   v5, 1              ; i
    li   v6, 34
fact:
    mul  v4, v4, v5
    addi v5, v5, 1
    bge  v6, v5, fact
    mv   v7, v4
    call print_user

    li   v7, 1
    shli v7, v7, 127        ; 2^127
    call print_user

    li   v2, 0
    li   v1, 2
    sys  0

; print_user: v7 = value; writes decimal digits + newline via syscall 1
print_user:
    li   v10, 10
    la   v11, BUF + 48
    mv   v12, v11
    addi v12, v12, -1
    li   v13, 10
    sb   [v12 + 0], v13     ; trailing newline
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

hello:  .ascii "native 128-bit math:\n"
.align 16
BUF:    .space 48
