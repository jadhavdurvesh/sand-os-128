; Demonstrate a full-width 128-bit immediate and a 128-bit RAM transfer.
.equ USER_BASE, 0x10000
.equ SCRATCH,   0x18000
.org USER_BASE
_start:
    li   v1, 0xFEDCBA98765432100123456789ABCDEF
    li   v2, SCRATCH
    sq   [v2 + 0], v1
    lq   v3, [v2 + 0]
    beq  v1, v3, roundtrip_ok

    li   v1, 1
    la   v2, failed
    li   v3, 5
    sys  0
    jmp  finish

roundtrip_ok:
    li   v1, 1
    la   v2, message
    li   v3, 50
    sys  0

finish:
    li   v1, 2
    li   v2, 0
    sys  0

message:
    .ascii "Veylith 128-Native: 128-bit memory round-trip OK!\n"
failed:
    .ascii "FAILED"
