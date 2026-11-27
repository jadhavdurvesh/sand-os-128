; Isolated gate call (ccalx / cretx): the callee sees none of the caller's registers and cannot corrupt them.
; The caller fills several registers (including sp) with secrets, calls the service with two arguments (v1, v2), and checks that
;   - the service saw zero in every non-argument register it probed (it reports what it saw),
;   - the service's own clobbering of those registers is invisible after the return,
;   - the arguments arrived and the result came back in v1.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    la   v2, svc
    li   v3, 8
    li   v4, 15                  ; READ | WRITE | NARROW | GATE
    li   v1, 10
    sys  0                       ; capget
    cseal v30, v1
    li   v1, 11
    sys  0                       ; capability mode
    li   v10, 0x1111
    li   v11, 0x2222
    li   v50, 0x5050
    li   v100, 0x100100
    li   v1, 7                   ; argument 1
    li   v2, 5                   ; argument 2
    ccalx v20, v30
    li   v6, 12
    bne  v1, v6, bad             ; 7 + 5, and nothing the service saw was non-zero
    li   v6, 0
    bne  v2, v6, bad             ; v2 carries the service's second result: the count of secrets it saw (must be 0)
    li   v6, 0x1111
    bne  v10, v6, bad
    li   v6, 0x2222
    bne  v11, v6, bad
    li   v6, 0x5050
    bne  v50, v6, bad
    li   v6, 0x100100
    bne  v100, v6, bad
    li   v6, 0x1F000
    bne  sp, v6, bad             ; sp came back untouched even though the service trashed it
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
msg_ok:  .ascii "gate isolation: ok\n"
msg_bad: .ascii "BAD\n"
.align 256
svc:                             ; v1, v2 = arguments; v20 = data capability; everything else is zero
    add  v8, v1, v2              ; the real work
    li   v9, 0                   ; count the caller secrets that leaked in
    beq  v10, v0, s1
    addi v9, v9, 1
s1: beq  v11, v0, s2
    addi v9, v9, 1
s2: beq  v50, v0, s3
    addi v9, v9, 1
s3: beq  v100, v0, s4
    addi v9, v9, 1
s4: beq  sp, v0, s5
    addi v9, v9, 1
s5: li   v10, 0xBAD              ; now trash them: none of this may survive the return
    li   v11, 0xBAD
    li   v50, 0xBAD
    li   v100, 0xBAD
    li   sp, 0xBAD
    mv   v1, v8
    mv   v2, v9
    cretx
