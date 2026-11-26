; Sigil call gate: a protected counter service reached by a 2-Glyph call, with no kernel involvement per call.
; The service owns a 256-byte region: its code is at the region base (the ONLY entry point a gate allows) and its counter
; lives inside the region. The client seals the region capability into a gate, enters capability mode, and can then reach the
; service only through ccall: it cannot read or write the counter, and cannot jump anywhere else in the service.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    la   v2, svc
    li   v3, 8                   ; 2^8 = 256 bytes, naturally aligned (see .align below)
    li   v4, 7 | 8               ; READ | WRITE | NARROW | GATE
    li   v1, 10
    sys  0                       ; capget
    cseal v30, v1                ; the gate: an opaque token; its base is the one entry point
    li   v1, 11
    sys  0                       ; capability mode: raw loads and stores now trap
    ccall v20, v30               ; v1 = 1
    mv   v10, v1
    ccall v20, v30               ; v1 = 2
    mv   v11, v1
    ccall v20, v30               ; v1 = 3
    mv   v12, v1
    li   v6, 1
    bne  v10, v6, bad
    li   v6, 2
    bne  v11, v6, bad
    li   v6, 3
    bne  v12, v6, bad
    la   v2, msg_ok
    li   v3, 9
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
msg_ok:  .ascii "gate: ok\n"
msg_bad: .ascii "BAD\n"
.align 256
svc:                             ; entry: v20 = the service's own data authority, delivered by ccall
    clq  v6, [v20 + 128]
    addi v6, v6, 1
    csq  [v20 + 128], v6
    mv   v1, v6
    cretn
.space 160
