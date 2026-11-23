; Kernelloom v0 -- the first Veylith kernel experiment.
; Runs in kernel privilege, boots one user program inside an aperture (abase/alim),
; and serves two system calls.  Syscall ABI: number in v1, arguments in v2..v3, result in v1.
;   1 write(ptr=v2, len=v3)  -> bytes written, or -1 if the buffer is not inside the user aperture
;   2 exit(code=v2)          -> prints the code and halts the machine
;   3 getpid()                -> current task identifier (1; single-task kernel)
;   4 getcycles()             -> retired Glyph count at syscall entry
; Any other call returns -1.  Any user fault is reported and halts the machine with 128+cause.
; Kernel scratch registers: v16..v29.  User registers are saved in a fixed frame (single core, not re-entrant).

.equ CONSOLE,   0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF0000
.equ USER_BASE, 0x10000
.equ USER_SIZE, 0x10000
.equ FRAME,     0x6000
.equ DIGITS,    0x7F00          ; 40-byte scratch for decimal conversion (end of buffer)
.equ GPU,       0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFE000

.org 0
_start:
    la   v1, trap_entry
    csrw tvec, v1
    li   v127, USER_BASE + USER_SIZE
    la   v1, banner
    call puts
    call desktop_init
    li   v1, USER_BASE
    csrw abase, v1
    csrw tpc, v1
    li   v1, USER_SIZE
    csrw alim, v1
    li   v1, 1
    csrw tpriv, v1
    tret


; SAND Desktop 128 initial guest-rendered framebuffer scene, 1280x720.
; gpu_rect: v1=x, v2=y, v3=width, v4=height, v5=RGBA word.
desktop_init:
    li v1, 0
    li v2, 0
    li v3, 1280
    li v4, 720
    li v5, 0xFF291B11
    call gpu_rect
    li v1, 0
    li v2, 0
    li v3, 1280
    li v4, 42
    li v5, 0xFF362517
    call gpu_rect
    li v1, 0
    li v2, 652
    li v3, 1280
    li v4, 68
    li v5, 0xFF4D3624
    call gpu_rect
    li v1, 24
    li v2, 76
    li v3, 244
    li v4, 548
    li v5, 0xFF3A2B20
    call gpu_rect
    li v1, 292
    li v2, 76
    li v3, 964
    li v4, 548
    li v5, 0xFF34271D
    call gpu_rect
    li v1, 292
    li v2, 76
    li v3, 964
    li v4, 44
    li v5, 0xFF594333
    call gpu_rect
    li v1, 316
    li v2, 148
    li v3, 916
    li v4, 448
    li v5, 0xFF403126
    call gpu_rect
    li v1, 340
    li v2, 172
    li v3, 868
    li v4, 72
    li v5, 0xFF594333
    call gpu_rect
    li v1, 340
    li v2, 270
    li v3, 260
    li v4, 190
    li v5, 0xFF604B39
    call gpu_rect
    li v1, 620
    li v2, 270
    li v3, 588
    li v4, 190
    li v5, 0xFF49382B
    call gpu_rect
    ret

gpu_rect:
    li v6, GPU
    sq [v6 + 0], v1
    sq [v6 + 16], v2
    sq [v6 + 32], v3
    sq [v6 + 48], v4
    sq [v6 + 64], v5
    li v7, 1
    sq [v6 + 80], v7
    ret

trap_entry:
    sq   [v0 + FRAME + 16], v1
    sq   [v0 + FRAME + 32], v2
    sq   [v0 + FRAME + 48], v3
    sq   [v0 + FRAME + 64], v4
    sq   [v0 + FRAME + 80], v5
    sq   [v0 + FRAME + 96], v6
    sq   [v0 + FRAME + 112], v7
    sq   [v0 + FRAME + 128], v8
    sq   [v0 + FRAME + 144], v9
    sq   [v0 + FRAME + 160], v10
    sq   [v0 + FRAME + 176], v11
    sq   [v0 + FRAME + 192], v12
    sq   [v0 + FRAME + 208], v13
    sq   [v0 + FRAME + 224], v14
    sq   [v0 + FRAME + 240], v15
    sq   [v0 + FRAME + 256], v16
    sq   [v0 + FRAME + 272], v17
    sq   [v0 + FRAME + 288], v18
    sq   [v0 + FRAME + 304], v19
    sq   [v0 + FRAME + 320], v20
    sq   [v0 + FRAME + 336], v21
    sq   [v0 + FRAME + 352], v22
    sq   [v0 + FRAME + 368], v23
    sq   [v0 + FRAME + 384], v24
    sq   [v0 + FRAME + 400], v25
    sq   [v0 + FRAME + 416], v26
    sq   [v0 + FRAME + 432], v27
    sq   [v0 + FRAME + 448], v28
    sq   [v0 + FRAME + 464], v29
    sq   [v0 + FRAME + 480], v30
    sq   [v0 + FRAME + 496], v31
    sq   [v0 + FRAME + 512], v32
    sq   [v0 + FRAME + 528], v33
    sq   [v0 + FRAME + 544], v34
    sq   [v0 + FRAME + 560], v35
    sq   [v0 + FRAME + 576], v36
    sq   [v0 + FRAME + 592], v37
    sq   [v0 + FRAME + 608], v38
    sq   [v0 + FRAME + 624], v39
    sq   [v0 + FRAME + 640], v40
    sq   [v0 + FRAME + 656], v41
    sq   [v0 + FRAME + 672], v42
    sq   [v0 + FRAME + 688], v43
    sq   [v0 + FRAME + 704], v44
    sq   [v0 + FRAME + 720], v45
    sq   [v0 + FRAME + 736], v46
    sq   [v0 + FRAME + 752], v47
    sq   [v0 + FRAME + 768], v48
    sq   [v0 + FRAME + 784], v49
    sq   [v0 + FRAME + 800], v50
    sq   [v0 + FRAME + 816], v51
    sq   [v0 + FRAME + 832], v52
    sq   [v0 + FRAME + 848], v53
    sq   [v0 + FRAME + 864], v54
    sq   [v0 + FRAME + 880], v55
    sq   [v0 + FRAME + 896], v56
    sq   [v0 + FRAME + 912], v57
    sq   [v0 + FRAME + 928], v58
    sq   [v0 + FRAME + 944], v59
    sq   [v0 + FRAME + 960], v60
    sq   [v0 + FRAME + 976], v61
    sq   [v0 + FRAME + 992], v62
    sq   [v0 + FRAME + 1008], v63
    sq   [v0 + FRAME + 1024], v64
    sq   [v0 + FRAME + 1040], v65
    sq   [v0 + FRAME + 1056], v66
    sq   [v0 + FRAME + 1072], v67
    sq   [v0 + FRAME + 1088], v68
    sq   [v0 + FRAME + 1104], v69
    sq   [v0 + FRAME + 1120], v70
    sq   [v0 + FRAME + 1136], v71
    sq   [v0 + FRAME + 1152], v72
    sq   [v0 + FRAME + 1168], v73
    sq   [v0 + FRAME + 1184], v74
    sq   [v0 + FRAME + 1200], v75
    sq   [v0 + FRAME + 1216], v76
    sq   [v0 + FRAME + 1232], v77
    sq   [v0 + FRAME + 1248], v78
    sq   [v0 + FRAME + 1264], v79
    sq   [v0 + FRAME + 1280], v80
    sq   [v0 + FRAME + 1296], v81
    sq   [v0 + FRAME + 1312], v82
    sq   [v0 + FRAME + 1328], v83
    sq   [v0 + FRAME + 1344], v84
    sq   [v0 + FRAME + 1360], v85
    sq   [v0 + FRAME + 1376], v86
    sq   [v0 + FRAME + 1392], v87
    sq   [v0 + FRAME + 1408], v88
    sq   [v0 + FRAME + 1424], v89
    sq   [v0 + FRAME + 1440], v90
    sq   [v0 + FRAME + 1456], v91
    sq   [v0 + FRAME + 1472], v92
    sq   [v0 + FRAME + 1488], v93
    sq   [v0 + FRAME + 1504], v94
    sq   [v0 + FRAME + 1520], v95
    sq   [v0 + FRAME + 1536], v96
    sq   [v0 + FRAME + 1552], v97
    sq   [v0 + FRAME + 1568], v98
    sq   [v0 + FRAME + 1584], v99
    sq   [v0 + FRAME + 1600], v100
    sq   [v0 + FRAME + 1616], v101
    sq   [v0 + FRAME + 1632], v102
    sq   [v0 + FRAME + 1648], v103
    sq   [v0 + FRAME + 1664], v104
    sq   [v0 + FRAME + 1680], v105
    sq   [v0 + FRAME + 1696], v106
    sq   [v0 + FRAME + 1712], v107
    sq   [v0 + FRAME + 1728], v108
    sq   [v0 + FRAME + 1744], v109
    sq   [v0 + FRAME + 1760], v110
    sq   [v0 + FRAME + 1776], v111
    sq   [v0 + FRAME + 1792], v112
    sq   [v0 + FRAME + 1808], v113
    sq   [v0 + FRAME + 1824], v114
    sq   [v0 + FRAME + 1840], v115
    sq   [v0 + FRAME + 1856], v116
    sq   [v0 + FRAME + 1872], v117
    sq   [v0 + FRAME + 1888], v118
    sq   [v0 + FRAME + 1904], v119
    sq   [v0 + FRAME + 1920], v120
    sq   [v0 + FRAME + 1936], v121
    sq   [v0 + FRAME + 1952], v122
    sq   [v0 + FRAME + 1968], v123
    sq   [v0 + FRAME + 1984], v124
    sq   [v0 + FRAME + 2000], v125
    sq   [v0 + FRAME + 2016], v126
    sq   [v0 + FRAME + 2032], v127
    sq   [v0 + FRAME + 2048], v128
    li   v127, 0x6000
    csrr v16, tcause
    li   v17, 6
    bne  v16, v17, user_fault
    li   v17, 1
    beq  v1, v17, sys_write
    li   v17, 2
    beq  v1, v17, sys_exit
    li   v17, 3
    beq  v1, v17, sys_getpid
    li   v17, 4
    beq  v1, v17, sys_getcycles
    li   v16, -1
    jmp  syscall_return

sys_write:
    li   v17, USER_SIZE
    bltu v17, v3, bad_buffer        ; len > aperture size
    li   v17, USER_BASE
    bltu v2, v17, bad_buffer        ; ptr below the aperture
    add  v18, v2, v3
    li   v17, USER_BASE + USER_SIZE
    bltu v17, v18, bad_buffer       ; ptr + len beyond the aperture
    li   v19, CONSOLE
    mv   v20, v2
    mv   v16, v3
write_loop:
    beq  v3, v0, syscall_return
    lb   v21, [v20 + 0]
    sb   [v19 + 0], v21
    addi v20, v20, 1
    addi v3, v3, -1
    jmp  write_loop
bad_buffer:
    li   v16, -1
    jmp  syscall_return

; Return the current task identifier. Kernelloom v1 is single-task, so PID 1 is the only task.
sys_getpid:
    li   v16, 1
    jmp  syscall_return

; Return the guest machine's retired Glyph counter at syscall entry.
sys_getcycles:
    csrr v16, cycles
    jmp  syscall_return

syscall_return:
    sq   [v0 + FRAME + 16], v16     ; result goes back in the saved v1
    lq   v1, [v0 + FRAME + 16]
    lq   v2, [v0 + FRAME + 32]
    lq   v3, [v0 + FRAME + 48]
    lq   v4, [v0 + FRAME + 64]
    lq   v5, [v0 + FRAME + 80]
    lq   v6, [v0 + FRAME + 96]
    lq   v7, [v0 + FRAME + 112]
    lq   v8, [v0 + FRAME + 128]
    lq   v9, [v0 + FRAME + 144]
    lq   v10, [v0 + FRAME + 160]
    lq   v11, [v0 + FRAME + 176]
    lq   v12, [v0 + FRAME + 192]
    lq   v13, [v0 + FRAME + 208]
    lq   v14, [v0 + FRAME + 224]
    lq   v15, [v0 + FRAME + 240]
    lq   v16, [v0 + FRAME + 256]
    lq   v17, [v0 + FRAME + 272]
    lq   v18, [v0 + FRAME + 288]
    lq   v19, [v0 + FRAME + 304]
    lq   v20, [v0 + FRAME + 320]
    lq   v21, [v0 + FRAME + 336]
    lq   v22, [v0 + FRAME + 352]
    lq   v23, [v0 + FRAME + 368]
    lq   v24, [v0 + FRAME + 384]
    lq   v25, [v0 + FRAME + 400]
    lq   v26, [v0 + FRAME + 416]
    lq   v27, [v0 + FRAME + 432]
    lq   v28, [v0 + FRAME + 448]
    lq   v29, [v0 + FRAME + 464]
    lq   v30, [v0 + FRAME + 480]
    lq   v31, [v0 + FRAME + 496]
    lq   v32, [v0 + FRAME + 512]
    lq   v33, [v0 + FRAME + 528]
    lq   v34, [v0 + FRAME + 544]
    lq   v35, [v0 + FRAME + 560]
    lq   v36, [v0 + FRAME + 576]
    lq   v37, [v0 + FRAME + 592]
    lq   v38, [v0 + FRAME + 608]
    lq   v39, [v0 + FRAME + 624]
    lq   v40, [v0 + FRAME + 640]
    lq   v41, [v0 + FRAME + 656]
    lq   v42, [v0 + FRAME + 672]
    lq   v43, [v0 + FRAME + 688]
    lq   v44, [v0 + FRAME + 704]
    lq   v45, [v0 + FRAME + 720]
    lq   v46, [v0 + FRAME + 736]
    lq   v47, [v0 + FRAME + 752]
    lq   v48, [v0 + FRAME + 768]
    lq   v49, [v0 + FRAME + 784]
    lq   v50, [v0 + FRAME + 800]
    lq   v51, [v0 + FRAME + 816]
    lq   v52, [v0 + FRAME + 832]
    lq   v53, [v0 + FRAME + 848]
    lq   v54, [v0 + FRAME + 864]
    lq   v55, [v0 + FRAME + 880]
    lq   v56, [v0 + FRAME + 896]
    lq   v57, [v0 + FRAME + 912]
    lq   v58, [v0 + FRAME + 928]
    lq   v59, [v0 + FRAME + 944]
    lq   v60, [v0 + FRAME + 960]
    lq   v61, [v0 + FRAME + 976]
    lq   v62, [v0 + FRAME + 992]
    lq   v63, [v0 + FRAME + 1008]
    lq   v64, [v0 + FRAME + 1024]
    lq   v65, [v0 + FRAME + 1040]
    lq   v66, [v0 + FRAME + 1056]
    lq   v67, [v0 + FRAME + 1072]
    lq   v68, [v0 + FRAME + 1088]
    lq   v69, [v0 + FRAME + 1104]
    lq   v70, [v0 + FRAME + 1120]
    lq   v71, [v0 + FRAME + 1136]
    lq   v72, [v0 + FRAME + 1152]
    lq   v73, [v0 + FRAME + 1168]
    lq   v74, [v0 + FRAME + 1184]
    lq   v75, [v0 + FRAME + 1200]
    lq   v76, [v0 + FRAME + 1216]
    lq   v77, [v0 + FRAME + 1232]
    lq   v78, [v0 + FRAME + 1248]
    lq   v79, [v0 + FRAME + 1264]
    lq   v80, [v0 + FRAME + 1280]
    lq   v81, [v0 + FRAME + 1296]
    lq   v82, [v0 + FRAME + 1312]
    lq   v83, [v0 + FRAME + 1328]
    lq   v84, [v0 + FRAME + 1344]
    lq   v85, [v0 + FRAME + 1360]
    lq   v86, [v0 + FRAME + 1376]
    lq   v87, [v0 + FRAME + 1392]
    lq   v88, [v0 + FRAME + 1408]
    lq   v89, [v0 + FRAME + 1424]
    lq   v90, [v0 + FRAME + 1440]
    lq   v91, [v0 + FRAME + 1456]
    lq   v92, [v0 + FRAME + 1472]
    lq   v93, [v0 + FRAME + 1488]
    lq   v94, [v0 + FRAME + 1504]
    lq   v95, [v0 + FRAME + 1520]
    lq   v96, [v0 + FRAME + 1536]
    lq   v97, [v0 + FRAME + 1552]
    lq   v98, [v0 + FRAME + 1568]
    lq   v99, [v0 + FRAME + 1584]
    lq   v100, [v0 + FRAME + 1600]
    lq   v101, [v0 + FRAME + 1616]
    lq   v102, [v0 + FRAME + 1632]
    lq   v103, [v0 + FRAME + 1648]
    lq   v104, [v0 + FRAME + 1664]
    lq   v105, [v0 + FRAME + 1680]
    lq   v106, [v0 + FRAME + 1696]
    lq   v107, [v0 + FRAME + 1712]
    lq   v108, [v0 + FRAME + 1728]
    lq   v109, [v0 + FRAME + 1744]
    lq   v110, [v0 + FRAME + 1760]
    lq   v111, [v0 + FRAME + 1776]
    lq   v112, [v0 + FRAME + 1792]
    lq   v113, [v0 + FRAME + 1808]
    lq   v114, [v0 + FRAME + 1824]
    lq   v115, [v0 + FRAME + 1840]
    lq   v116, [v0 + FRAME + 1856]
    lq   v117, [v0 + FRAME + 1872]
    lq   v118, [v0 + FRAME + 1888]
    lq   v119, [v0 + FRAME + 1904]
    lq   v120, [v0 + FRAME + 1920]
    lq   v121, [v0 + FRAME + 1936]
    lq   v122, [v0 + FRAME + 1952]
    lq   v123, [v0 + FRAME + 1968]
    lq   v124, [v0 + FRAME + 1984]
    lq   v125, [v0 + FRAME + 2000]
    lq   v126, [v0 + FRAME + 2016]
    lq   v127, [v0 + FRAME + 2032]
    lq   v128, [v0 + FRAME + 2048]
    tret

sys_exit:
    mv   v22, v2
    la   v1, msg_exit
    call puts
    mv   v1, v22
    call print_dec
    call newline
    mv   v1, v22
    halt

user_fault:
    la   v1, msg_fault
    call puts
    csrr v1, tcause
    call print_dec
    la   v1, msg_addr
    call puts
    csrr v1, tval
    call print_dec
    call newline
    csrr v1, tcause
    addi v1, v1, 128
    halt

; puts: v1 = address of NUL-terminated string
puts:
    li   v18, CONSOLE
puts_loop:
    lb   v16, [v1 + 0]
    beq  v16, v0, puts_done
    sb   [v18 + 0], v16
    addi v1, v1, 1
    jmp  puts_loop
puts_done:
    ret

newline:
    li   v18, CONSOLE
    li   v16, 10
    sb   [v18 + 0], v16
    ret

; print_dec: v1 = unsigned 128-bit value, printed in decimal (uses native udiv/urem)
print_dec:
    li   v17, 10
    li   v19, DIGITS
    li   v18, CONSOLE
dec_loop:
    urem v20, v1, v17
    udiv v1, v1, v17
    addi v20, v20, 48
    addi v19, v19, -1
    sb   [v19 + 0], v20
    bne  v1, v0, dec_loop
    li   v21, DIGITS
dec_out:
    lb   v20, [v19 + 0]
    sb   [v18 + 0], v20
    addi v19, v19, 1
    bne  v19, v21, dec_out
    ret

banner:    .asciz "[kernelloom] Veylith 128-Native v1 booting user program\n"
msg_exit:  .asciz "[kernelloom] user exit "
msg_fault: .asciz "[kernelloom] user fault cause="
msg_addr:  .asciz " tval="
