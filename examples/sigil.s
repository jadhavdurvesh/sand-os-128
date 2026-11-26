; Sigil capabilities in Kernelloom: a worker that can reach memory ONLY through a capability it was handed.
; Task 1 mints a 64-byte region (capget), narrows it, and passes the narrowed 128-bit capability to a worker as its spawn
; argument. The worker enters capability mode, writes through the capability, and prints through it with cwrite.
.equ USER_BASE, 0x10000
.org USER_BASE
_start:
    li   sp, 0x1F000
    la   v2, region
    li   v3, 6                   ; 2^6 = 64 bytes, naturally aligned
    li   v4, 7                   ; READ | WRITE | NARROW
    li   v1, 10
    sys  0                       ; capget
    mv   v20, v1                 ; the full-region capability
    li   v21, 1 | 5 << 8 | 32 << 16
    cnarrow v22, v20, v21        ; READ-only window on the upper half (kept to show derivation; not handed out)
    li   v21, 3 | 5 << 8
    cnarrow v23, v20, v21        ; READ|WRITE, lower 32 bytes; narrowed capabilities lose NARROW, so they cannot be widened
    la   v2, worker
    li   v3, 0x1E000
    mv   v4, v23                 ; the capability itself is the argument: all 128 bits travel in one register
    li   v1, 6
    sys  0
    mv   v24, v1
    li   v1, 9                   ; recv: the worker reports when it is done
    sys  0
    mv   v2, v24
    li   v1, 7
    sys  0                       ; join
    la   v5, region
    lq   v6, [v5 + 16]           ; plain load by task 1: the worker's 128-bit write is there
    li   v7, 0x5349474C5F4F4B21F00DFACE0000BEEF
    bne  v6, v7, bad
    la   v2, msg_ok
    li   v3, 23
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

worker:                          ; v1 = capability to region[0..32), READ|WRITE
    mv   v20, v1
    li   v1, 11
    sys  0                       ; cmode: from here on raw loads and stores trap
    li   v6, 0x5349474C5F4F4B21F00DFACE0000BEEF
    csq  [v20 + 16], v6          ; 128-bit store through the capability
    li   v8, 0x48                ; "Hi\n" at +0
    csb  [v20 + 0], v8
    li   v8, 0x69
    csb  [v20 + 1], v8
    li   v8, 0x0A
    csb  [v20 + 2], v8
    mv   v2, v20                 ; cwrite: the console buffer is named by the capability, not by a raw pointer
    li   v3, 3
    li   v1, 12
    sys  0
    li   v1, 8                   ; send "done" to task 1
    li   v2, 1
    li   v3, 1
    sys  0
    li   v1, 2
    li   v2, 0
    sys  0
.align 64
region: .space 64
msg_ok:  .ascii "sigil capabilities: ok\n"
msg_bad: .ascii "BAD\n"
