; Kernelloom v2 -- the Veylith kernel (v2 adds cooperative threads, see the syscall list below).
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
.equ CURRENT,     0x7010          ; index of the running task slot (kernel data lives at 0x7000..0x7FFF, above the trap frame)
.equ LINKSAVE,    0x7000
.equ TASKS,       0x8000          ; task table: 8 slots, kept outside the user aperture
.equ TSTRIDE,     0x900
.equ NTASKS,      8
.equ T_STATE,     0               ; 0 free, 1 ready/running, 2 blocked in join, 3 blocked in recv
.equ T_RESULT,    16              ; value handed back in v1 when the task next runs
.equ T_TPC,       32
.equ T_AUX,       48              ; join: the tid awaited
.equ T_MBFULL,    64
.equ T_MBVAL,     80              ; one-deep 128-bit mailbox
.equ T_CMODE,     96              ; 1 = capability mode: raw loads/stores trap, only Sigil capabilities reach memory
.equ T_CLINK,     112             ; return link of an active gate call (CSR clink), saved per task
.equ CSTACK_BASE,  0x21000          ; ccalx spills v1..v128 here: 2048 bytes per task, above the 64 KiB user aperture
.equ CSTACK_STRIDE, 0x800
.equ T_FRAME,     128             ; saved copy of the 129-quad register frame
.equ FRAMEQ,      129
.equ CKEY_VALUE,   0x5349474C4B45592D56455945564559A  ; boot-time Sigil key: a constant so runs stay deterministic (a real machine needs an entropy source)
.equ QUANTUM,      3000            ; preemption slice, in retired Glyphs (timecmp = cycles + QUANTUM)
.equ GPU,       0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFE000

.org 0
_start:
    la   v1, trap_entry
    csrw tvec, v1
    li   v127, USER_BASE + USER_SIZE
    la   v1, banner
    call puts
    call desktop_init
    li   v1, CKEY_VALUE
    csrw ckey, v1
    li   v1, 1
    sq   [v0 + TASKS + T_STATE], v1      ; task 1 (slot 0) is the booting program
    csrr v1, cycles
    addi v1, v1, QUANTUM
    csrw timecmp, v1                 ; arm the first preemption deadline
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
    sq [v0 + LINKSAVE], v128       ; preserve caller link across nested gpu_rect calls
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
    li v1, 54
    li v2, 18
    la v3, text_brand
    li v4, 5
    li v5, 0xFFE8EEF6
    call gpu_text
    li v1, 24
    li v2, 95
    la v3, text_home
    li v4, 4
    li v5, 0xFFDDE8F5
    call gpu_text
    li v1, 24
    li v2, 160
    la v3, text_files
    li v4, 5
    li v5, 0xFFB9C9DA
    call gpu_text
    li v1, 24
    li v2, 225
    la v3, text_terminal
    li v4, 8
    li v5, 0xFFB9C9DA
    call gpu_text
    li v1, 24
    li v2, 290
    la v3, text_settings
    li v4, 8
    li v5, 0xFFB9C9DA
    call gpu_text
    li v1, 330
    li v2, 103
    la v3, text_workspace
    li v4, 9
    li v5, 0xFFEAF0F7
    call gpu_text
    li v1, 330
    li v2, 155
    la v3, text_welcome
    li v4, 12
    li v5, 0xFFEAF0F7
    call gpu_text
    li v1, 330
    li v2, 195
    la v3, text_ready
    li v4, 25
    li v5, 0xFFAFC1D5
    call gpu_text
    li v1, 340
    li v2, 285
    la v3, text_files_card
    li v4, 5
    li v5, 0xFFEAF0F7
    call gpu_text
    li v1, 340
    li v2, 320
    la v3, text_files_count
    li v4, 9
    li v5, 0xFFB9C9DA
    call gpu_text
    li v1, 630
    li v2, 285
    la v3, text_system_card
    li v4, 6
    li v5, 0xFFEAF0F7
    call gpu_text
    li v1, 630
    li v2, 320
    la v3, text_system_ok
    li v4, 10
    li v5, 0xFFB9C9DA
    call gpu_text
    li v1, 54
    li v2, 674
    la v3, text_launcher
    li v4, 5
    li v5, 0xFFEAF0F7
    call gpu_text
    li v1, 950
    li v2, 674
    la v3, text_clock
    li v4, 16
    li v5, 0xFFEAF0F7
    call gpu_text
    lq v128, [v0 + LINKSAVE]
    ret

gpu_text:
    li v6, GPU
    sq [v6 + 0], v1
    sq [v6 + 16], v2
    sq [v6 + 32], v3
    sq [v6 + 48], v4
    sq [v6 + 64], v5
    li v7, 2
    sq [v6 + 80], v7
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
    li   v17, 7
    beq  v16, v17, timer_preempt
    li   v17, 6
    bne  v16, v17, user_fault
    li   v17, 1
    beq  v1, v17, sys_write
    li   v17, 2
    beq  v1, v17, sys_exit_any
    li   v17, 3
    beq  v1, v17, sys_getpid
    li   v17, 4
    beq  v1, v17, sys_getcycles
    li   v17, 5
    beq  v1, v17, sys_yield
    li   v17, 6
    beq  v1, v17, sys_spawn
    li   v17, 7
    beq  v1, v17, sys_join
    li   v17, 8
    beq  v1, v17, sys_send
    li   v17, 9
    beq  v1, v17, sys_recv
    li   v17, 10
    beq  v1, v17, sys_capget
    li   v17, 11
    beq  v1, v17, sys_cmode
    li   v17, 12
    beq  v1, v17, sys_cwrite
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

; Return the current task identifier (1 = the booting program, 2.. = threads from spawn).
sys_getpid:
    lq   v16, [v0 + CURRENT]
    addi v16, v16, 1
    jmp  syscall_return

; Return the guest machine's retired Glyph counter at syscall entry.
sys_getcycles:
    csrr v16, cycles
    jmp  syscall_return

; ---- Sigil capabilities (docs/18) ----
;  10 capget(base, exp, perms)  -> a capability for [base, base + 2^exp) inside the aperture (perms: 1 READ, 2 WRITE, 4 NARROW), or -1
;  11 cmode()                   -> 0; the task (and the threads it spawns) can from now on reach memory only through capabilities
;  12 cwrite(cap, len)          -> like write(), but the buffer is named by a READ capability instead of a raw pointer
sys_capget:                         ; v2 = base, v3 = exp | lenm1 << 8, v4 = perms; region = (lenm1 + 1) << exp bytes
    shri v21, v3, 8                 ; length multiplier minus one
    andi v3, v3, 255                ; exponent
    li   v17, 16
    bltu v17, v3, task_bad          ; alignment unit larger than the 64 KiB aperture
    li   v17, 15
    bltu v17, v4, task_bad          ; perms must be within READ|WRITE|NARROW|GATE
    li   v17, USER_BASE
    bltu v2, v17, task_bad
    addi v18, v21, 1
    shl  v18, v18, v3               ; region size = (lenm1 + 1) << exp
    add  v19, v2, v18
    li   v17, USER_BASE + USER_SIZE
    bltu v17, v19, task_bad         ; region must lie inside the aperture
    li   v19, 1
    shl  v19, v19, v3
    addi v19, v19, -1
    and  v19, v2, v19
    bne  v19, v0, task_bad          ; and be aligned to 2^exp
    shli v20, v3, 8
    shli v22, v21, 16
    or   v20, v20, v22
    or   v20, v20, v4
    cmint v16, v2, v20
    jmp  syscall_return
sys_cmode:
    lq   v24, [v0 + CURRENT]
    li   v17, TSTRIDE
    mul  v25, v24, v17
    li   v17, TASKS
    add  v25, v25, v17
    li   v18, 1
    sq   [v25 + T_CMODE], v18
    li   v16, 0
    jmp  syscall_return
sys_cwrite:
    cinfo v17, v2                   ; never traps: 0 if the capability does not verify
    beq  v17, v0, task_bad
    shri v18, v17, 80
    andi v18, v18, 1
    beq  v18, v0, task_bad          ; needs READ
    shri v19, v17, 72
    andi v19, v19, 255              ; exp
    li   v20, 1
    shl  v20, v20, v19
    bltu v20, v3, task_bad          ; len beyond the region
    shli v2, v17, 56
    shri v2, v2, 56                 ; base = low 72 bits
    jmp  sys_write
syscall_return:
    lq   v17, [v0 + CURRENT]        ; install the returning task's capability mode
    li   v19, CSTACK_STRIDE         ; per-task register save area for isolated gate calls (outside the user aperture)
    mul  v19, v17, v19
    addi v19, v19, CSTACK_BASE
    csrw cstack, v19
    li   v18, TSTRIDE
    mul  v18, v17, v18
    lq   v17, [v18 + TASKS + T_CMODE]
    csrw cmode, v17
    lq   v17, [v18 + TASKS + T_CLINK]
    csrw clink, v17
    csrr v17, cycles                ; every return to user mode re-arms the one-shot timer
    addi v17, v17, QUANTUM
    csrw timecmp, v17
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

; ---- Kernelloom v2: cooperative threads sharing the user aperture ----
;   5 yield()                      -> 0
;   6 spawn(entry, stack_top, arg) -> tid, or -1 (bad entry/stack, table full); the new task starts with v1 = arg, sp = stack_top
;   7 join(tid)                    -> 0 once that task has ended (-1: bad tid or joining yourself)
;   8 send(tid, value)             -> 0, -1 (no such task) or -2 (its mailbox is full); value is a full 128 bits
;   9 recv()                       -> the next 128-bit message (blocks while the mailbox is empty)
; exit() in task 1 ends the machine as before; exit() in a thread ends only that thread.
; Each task keeps its 129-quad register frame in the table; a switch copies frames in and out of FRAME (unrolled: a copy loop
; cost ~1900 Glyphs per switch, see docs/paper).
sys_exit_any:
    lq   v17, [v0 + CURRENT]
    beq  v17, v0, sys_exit
    ; a thread ends: free its slot, wake whoever is joining it, never come back
    li   v18, TSTRIDE
    mul  v25, v17, v18
    li   v18, TASKS
    add  v25, v25, v18
    sq   [v25 + T_STATE], v0
    addi v29, v17, 1                ; tid that just ended
    li   v20, 0                     ; slot index
    li   v21, TASKS
wake_loop:
    lq   v22, [v21 + T_STATE]
    li   v23, 2
    bne  v22, v23, wake_next
    lq   v22, [v21 + T_AUX]
    bne  v22, v29, wake_next
    li   v23, 1
    sq   [v21 + T_STATE], v23
wake_next:
    addi v21, v21, TSTRIDE
    addi v20, v20, 1
    li   v23, NTASKS
    bne  v20, v23, wake_loop
    li   v26, 1                     ; exited: nothing to save
    jmp  schedule

; Timer interrupt (cause 7): the user task is preempted between two Glyphs. Its v1 is kept as its pending result.
timer_preempt:
    lq   v16, [v0 + FRAME + 16]
    li   v26, 0
    jmp  schedule

sys_yield:
    li   v16, 0
    li   v26, 0
    jmp  schedule

sys_join:
    li   v17, 1
    bltu v2, v17, task_bad
    li   v17, NTASKS + 1
    bgeu v2, v17, task_bad
    addi v28, v2, -1
    lq   v24, [v0 + CURRENT]
    beq  v28, v24, task_bad         ; cannot join yourself
    li   v17, TSTRIDE
    mul  v25, v28, v17
    li   v17, TASKS
    add  v25, v25, v17
    lq   v18, [v25 + T_STATE]
    li   v16, 0
    beq  v18, v0, syscall_return    ; already ended
    li   v17, TSTRIDE
    mul  v25, v24, v17
    li   v17, TASKS
    add  v25, v25, v17
    li   v18, 2
    sq   [v25 + T_STATE], v18
    sq   [v25 + T_AUX], v2
    li   v16, 0
    li   v26, 0
    jmp  schedule
task_bad:
    li   v16, -1
    jmp  syscall_return

sys_spawn:
    li   v17, USER_BASE
    bltu v2, v17, task_bad          ; entry below the aperture
    li   v17, USER_BASE + USER_SIZE
    bgeu v2, v17, task_bad          ; entry beyond it
    andi v18, v2, 15
    bne  v18, v0, task_bad          ; Glyphs are 16-byte aligned
    li   v17, USER_BASE
    bgeu v17, v3, task_bad          ; stack top must be above the aperture base
    li   v17, USER_BASE + USER_SIZE
    bltu v17, v3, task_bad
    li   v28, 0
spawn_scan:
    li   v17, TSTRIDE
    mul  v25, v28, v17
    li   v17, TASKS
    add  v25, v25, v17
    lq   v18, [v25 + T_STATE]
    beq  v18, v0, spawn_found
    addi v28, v28, 1
    li   v17, NTASKS
    bne  v28, v17, spawn_scan
    jmp  task_bad                   ; table full
spawn_found:
    lq   v19, [v0 + CURRENT]        ; the child inherits the spawner's capability mode
    li   v17, TSTRIDE
    mul  v19, v19, v17
    lq   v19, [v19 + TASKS + T_CMODE]
    sq   [v25 + T_CMODE], v19
    sq   [v25 + T_CLINK], v0
    li   v18, 1
    sq   [v25 + T_STATE], v18
    sq   [v25 + T_RESULT], v4       ; the first v1 is the argument
    sq   [v25 + T_TPC], v2
    sq   [v25 + T_AUX], v0
    sq   [v25 + T_MBFULL], v0
    sq   [v25 + T_MBVAL], v0
    addi v20, v25, T_FRAME
    li   v22, FRAMEQ
spawn_zero:
    sq   [v20 + 0], v0
    addi v20, v20, 16
    addi v22, v22, -1
    bne  v22, v0, spawn_zero
    sq   [v25 + T_FRAME + 2032], v3 ; v127 = sp
    addi v16, v28, 1
    jmp  syscall_return

sys_send:
    li   v17, 1
    bltu v2, v17, task_bad
    li   v17, NTASKS + 1
    bgeu v2, v17, task_bad
    addi v28, v2, -1
    li   v17, TSTRIDE
    mul  v25, v28, v17
    li   v17, TASKS
    add  v25, v25, v17
    lq   v18, [v25 + T_STATE]
    beq  v18, v0, task_bad          ; no such task
    li   v19, 3
    bne  v18, v19, send_store
    sq   [v25 + T_RESULT], v3       ; it is waiting in recv: hand the message over and wake it
    li   v19, 1
    sq   [v25 + T_STATE], v19
    li   v16, 0
    jmp  syscall_return
send_store:
    lq   v19, [v25 + T_MBFULL]
    li   v16, -2
    bne  v19, v0, syscall_return    ; mailbox already holds a message
    sq   [v25 + T_MBVAL], v3
    li   v19, 1
    sq   [v25 + T_MBFULL], v19
    li   v16, 0
    jmp  syscall_return

sys_recv:
    lq   v24, [v0 + CURRENT]
    li   v17, TSTRIDE
    mul  v25, v24, v17
    li   v17, TASKS
    add  v25, v25, v17
    lq   v19, [v25 + T_MBFULL]
    beq  v19, v0, recv_block
    lq   v16, [v25 + T_MBVAL]
    sq   [v25 + T_MBFULL], v0
    jmp  syscall_return
recv_block:
    li   v18, 3
    sq   [v25 + T_STATE], v18
    li   v16, 0
    li   v26, 0
    jmp  schedule

; schedule: v16 = result for the current task, v26 = 1 when the current task has ended.
; Saves the current task (unless ended), picks the next READY task round-robin, loads it and returns to user mode.
schedule:
    lq   v24, [v0 + CURRENT]
    li   v17, TSTRIDE
    mul  v25, v24, v17
    li   v17, TASKS
    add  v25, v25, v17
    bne  v26, v0, sched_pick
    sq   [v25 + T_RESULT], v16
    csrr v17, tpc
    sq   [v25 + T_TPC], v17
    csrr v17, clink
    sq   [v25 + T_CLINK], v17
    li   v20, FRAME
    addi v21, v25, T_FRAME
    lq   v23, [v20 + 0]
    sq   [v21 + 0], v23
    lq   v23, [v20 + 16]
    sq   [v21 + 16], v23
    lq   v23, [v20 + 32]
    sq   [v21 + 32], v23
    lq   v23, [v20 + 48]
    sq   [v21 + 48], v23
    lq   v23, [v20 + 64]
    sq   [v21 + 64], v23
    lq   v23, [v20 + 80]
    sq   [v21 + 80], v23
    lq   v23, [v20 + 96]
    sq   [v21 + 96], v23
    lq   v23, [v20 + 112]
    sq   [v21 + 112], v23
    lq   v23, [v20 + 128]
    sq   [v21 + 128], v23
    lq   v23, [v20 + 144]
    sq   [v21 + 144], v23
    lq   v23, [v20 + 160]
    sq   [v21 + 160], v23
    lq   v23, [v20 + 176]
    sq   [v21 + 176], v23
    lq   v23, [v20 + 192]
    sq   [v21 + 192], v23
    lq   v23, [v20 + 208]
    sq   [v21 + 208], v23
    lq   v23, [v20 + 224]
    sq   [v21 + 224], v23
    lq   v23, [v20 + 240]
    sq   [v21 + 240], v23
    lq   v23, [v20 + 256]
    sq   [v21 + 256], v23
    lq   v23, [v20 + 272]
    sq   [v21 + 272], v23
    lq   v23, [v20 + 288]
    sq   [v21 + 288], v23
    lq   v23, [v20 + 304]
    sq   [v21 + 304], v23
    lq   v23, [v20 + 320]
    sq   [v21 + 320], v23
    lq   v23, [v20 + 336]
    sq   [v21 + 336], v23
    lq   v23, [v20 + 352]
    sq   [v21 + 352], v23
    lq   v23, [v20 + 368]
    sq   [v21 + 368], v23
    lq   v23, [v20 + 384]
    sq   [v21 + 384], v23
    lq   v23, [v20 + 400]
    sq   [v21 + 400], v23
    lq   v23, [v20 + 416]
    sq   [v21 + 416], v23
    lq   v23, [v20 + 432]
    sq   [v21 + 432], v23
    lq   v23, [v20 + 448]
    sq   [v21 + 448], v23
    lq   v23, [v20 + 464]
    sq   [v21 + 464], v23
    lq   v23, [v20 + 480]
    sq   [v21 + 480], v23
    lq   v23, [v20 + 496]
    sq   [v21 + 496], v23
    lq   v23, [v20 + 512]
    sq   [v21 + 512], v23
    lq   v23, [v20 + 528]
    sq   [v21 + 528], v23
    lq   v23, [v20 + 544]
    sq   [v21 + 544], v23
    lq   v23, [v20 + 560]
    sq   [v21 + 560], v23
    lq   v23, [v20 + 576]
    sq   [v21 + 576], v23
    lq   v23, [v20 + 592]
    sq   [v21 + 592], v23
    lq   v23, [v20 + 608]
    sq   [v21 + 608], v23
    lq   v23, [v20 + 624]
    sq   [v21 + 624], v23
    lq   v23, [v20 + 640]
    sq   [v21 + 640], v23
    lq   v23, [v20 + 656]
    sq   [v21 + 656], v23
    lq   v23, [v20 + 672]
    sq   [v21 + 672], v23
    lq   v23, [v20 + 688]
    sq   [v21 + 688], v23
    lq   v23, [v20 + 704]
    sq   [v21 + 704], v23
    lq   v23, [v20 + 720]
    sq   [v21 + 720], v23
    lq   v23, [v20 + 736]
    sq   [v21 + 736], v23
    lq   v23, [v20 + 752]
    sq   [v21 + 752], v23
    lq   v23, [v20 + 768]
    sq   [v21 + 768], v23
    lq   v23, [v20 + 784]
    sq   [v21 + 784], v23
    lq   v23, [v20 + 800]
    sq   [v21 + 800], v23
    lq   v23, [v20 + 816]
    sq   [v21 + 816], v23
    lq   v23, [v20 + 832]
    sq   [v21 + 832], v23
    lq   v23, [v20 + 848]
    sq   [v21 + 848], v23
    lq   v23, [v20 + 864]
    sq   [v21 + 864], v23
    lq   v23, [v20 + 880]
    sq   [v21 + 880], v23
    lq   v23, [v20 + 896]
    sq   [v21 + 896], v23
    lq   v23, [v20 + 912]
    sq   [v21 + 912], v23
    lq   v23, [v20 + 928]
    sq   [v21 + 928], v23
    lq   v23, [v20 + 944]
    sq   [v21 + 944], v23
    lq   v23, [v20 + 960]
    sq   [v21 + 960], v23
    lq   v23, [v20 + 976]
    sq   [v21 + 976], v23
    lq   v23, [v20 + 992]
    sq   [v21 + 992], v23
    lq   v23, [v20 + 1008]
    sq   [v21 + 1008], v23
    lq   v23, [v20 + 1024]
    sq   [v21 + 1024], v23
    lq   v23, [v20 + 1040]
    sq   [v21 + 1040], v23
    lq   v23, [v20 + 1056]
    sq   [v21 + 1056], v23
    lq   v23, [v20 + 1072]
    sq   [v21 + 1072], v23
    lq   v23, [v20 + 1088]
    sq   [v21 + 1088], v23
    lq   v23, [v20 + 1104]
    sq   [v21 + 1104], v23
    lq   v23, [v20 + 1120]
    sq   [v21 + 1120], v23
    lq   v23, [v20 + 1136]
    sq   [v21 + 1136], v23
    lq   v23, [v20 + 1152]
    sq   [v21 + 1152], v23
    lq   v23, [v20 + 1168]
    sq   [v21 + 1168], v23
    lq   v23, [v20 + 1184]
    sq   [v21 + 1184], v23
    lq   v23, [v20 + 1200]
    sq   [v21 + 1200], v23
    lq   v23, [v20 + 1216]
    sq   [v21 + 1216], v23
    lq   v23, [v20 + 1232]
    sq   [v21 + 1232], v23
    lq   v23, [v20 + 1248]
    sq   [v21 + 1248], v23
    lq   v23, [v20 + 1264]
    sq   [v21 + 1264], v23
    lq   v23, [v20 + 1280]
    sq   [v21 + 1280], v23
    lq   v23, [v20 + 1296]
    sq   [v21 + 1296], v23
    lq   v23, [v20 + 1312]
    sq   [v21 + 1312], v23
    lq   v23, [v20 + 1328]
    sq   [v21 + 1328], v23
    lq   v23, [v20 + 1344]
    sq   [v21 + 1344], v23
    lq   v23, [v20 + 1360]
    sq   [v21 + 1360], v23
    lq   v23, [v20 + 1376]
    sq   [v21 + 1376], v23
    lq   v23, [v20 + 1392]
    sq   [v21 + 1392], v23
    lq   v23, [v20 + 1408]
    sq   [v21 + 1408], v23
    lq   v23, [v20 + 1424]
    sq   [v21 + 1424], v23
    lq   v23, [v20 + 1440]
    sq   [v21 + 1440], v23
    lq   v23, [v20 + 1456]
    sq   [v21 + 1456], v23
    lq   v23, [v20 + 1472]
    sq   [v21 + 1472], v23
    lq   v23, [v20 + 1488]
    sq   [v21 + 1488], v23
    lq   v23, [v20 + 1504]
    sq   [v21 + 1504], v23
    lq   v23, [v20 + 1520]
    sq   [v21 + 1520], v23
    lq   v23, [v20 + 1536]
    sq   [v21 + 1536], v23
    lq   v23, [v20 + 1552]
    sq   [v21 + 1552], v23
    lq   v23, [v20 + 1568]
    sq   [v21 + 1568], v23
    lq   v23, [v20 + 1584]
    sq   [v21 + 1584], v23
    lq   v23, [v20 + 1600]
    sq   [v21 + 1600], v23
    lq   v23, [v20 + 1616]
    sq   [v21 + 1616], v23
    lq   v23, [v20 + 1632]
    sq   [v21 + 1632], v23
    lq   v23, [v20 + 1648]
    sq   [v21 + 1648], v23
    lq   v23, [v20 + 1664]
    sq   [v21 + 1664], v23
    lq   v23, [v20 + 1680]
    sq   [v21 + 1680], v23
    lq   v23, [v20 + 1696]
    sq   [v21 + 1696], v23
    lq   v23, [v20 + 1712]
    sq   [v21 + 1712], v23
    lq   v23, [v20 + 1728]
    sq   [v21 + 1728], v23
    lq   v23, [v20 + 1744]
    sq   [v21 + 1744], v23
    lq   v23, [v20 + 1760]
    sq   [v21 + 1760], v23
    lq   v23, [v20 + 1776]
    sq   [v21 + 1776], v23
    lq   v23, [v20 + 1792]
    sq   [v21 + 1792], v23
    lq   v23, [v20 + 1808]
    sq   [v21 + 1808], v23
    lq   v23, [v20 + 1824]
    sq   [v21 + 1824], v23
    lq   v23, [v20 + 1840]
    sq   [v21 + 1840], v23
    lq   v23, [v20 + 1856]
    sq   [v21 + 1856], v23
    lq   v23, [v20 + 1872]
    sq   [v21 + 1872], v23
    lq   v23, [v20 + 1888]
    sq   [v21 + 1888], v23
    lq   v23, [v20 + 1904]
    sq   [v21 + 1904], v23
    lq   v23, [v20 + 1920]
    sq   [v21 + 1920], v23
    lq   v23, [v20 + 1936]
    sq   [v21 + 1936], v23
    lq   v23, [v20 + 1952]
    sq   [v21 + 1952], v23
    lq   v23, [v20 + 1968]
    sq   [v21 + 1968], v23
    lq   v23, [v20 + 1984]
    sq   [v21 + 1984], v23
    lq   v23, [v20 + 2000]
    sq   [v21 + 2000], v23
    lq   v23, [v20 + 2016]
    sq   [v21 + 2016], v23
    lq   v23, [v20 + 2032]
    sq   [v21 + 2032], v23
    lq   v23, [v20 + 2048]
    sq   [v21 + 2048], v23
sched_pick:
    li   v27, NTASKS
    mv   v28, v24
sched_next:
    addi v28, v28, 1
    li   v17, NTASKS
    bltu v28, v17, sched_slot
    li   v28, 0
sched_slot:
    li   v17, TSTRIDE
    mul  v25, v28, v17
    li   v17, TASKS
    add  v25, v25, v17
    lq   v17, [v25 + T_STATE]
    li   v18, 1
    beq  v17, v18, sched_run
    addi v27, v27, -1
    bne  v27, v0, sched_next
    la   v1, msg_deadlock           ; nothing can run: every task is blocked
    call puts
    li   v1, 200
    halt
sched_run:
    sq   [v0 + CURRENT], v28
    addi v20, v25, T_FRAME
    li   v21, FRAME
    lq   v23, [v20 + 0]
    sq   [v21 + 0], v23
    lq   v23, [v20 + 16]
    sq   [v21 + 16], v23
    lq   v23, [v20 + 32]
    sq   [v21 + 32], v23
    lq   v23, [v20 + 48]
    sq   [v21 + 48], v23
    lq   v23, [v20 + 64]
    sq   [v21 + 64], v23
    lq   v23, [v20 + 80]
    sq   [v21 + 80], v23
    lq   v23, [v20 + 96]
    sq   [v21 + 96], v23
    lq   v23, [v20 + 112]
    sq   [v21 + 112], v23
    lq   v23, [v20 + 128]
    sq   [v21 + 128], v23
    lq   v23, [v20 + 144]
    sq   [v21 + 144], v23
    lq   v23, [v20 + 160]
    sq   [v21 + 160], v23
    lq   v23, [v20 + 176]
    sq   [v21 + 176], v23
    lq   v23, [v20 + 192]
    sq   [v21 + 192], v23
    lq   v23, [v20 + 208]
    sq   [v21 + 208], v23
    lq   v23, [v20 + 224]
    sq   [v21 + 224], v23
    lq   v23, [v20 + 240]
    sq   [v21 + 240], v23
    lq   v23, [v20 + 256]
    sq   [v21 + 256], v23
    lq   v23, [v20 + 272]
    sq   [v21 + 272], v23
    lq   v23, [v20 + 288]
    sq   [v21 + 288], v23
    lq   v23, [v20 + 304]
    sq   [v21 + 304], v23
    lq   v23, [v20 + 320]
    sq   [v21 + 320], v23
    lq   v23, [v20 + 336]
    sq   [v21 + 336], v23
    lq   v23, [v20 + 352]
    sq   [v21 + 352], v23
    lq   v23, [v20 + 368]
    sq   [v21 + 368], v23
    lq   v23, [v20 + 384]
    sq   [v21 + 384], v23
    lq   v23, [v20 + 400]
    sq   [v21 + 400], v23
    lq   v23, [v20 + 416]
    sq   [v21 + 416], v23
    lq   v23, [v20 + 432]
    sq   [v21 + 432], v23
    lq   v23, [v20 + 448]
    sq   [v21 + 448], v23
    lq   v23, [v20 + 464]
    sq   [v21 + 464], v23
    lq   v23, [v20 + 480]
    sq   [v21 + 480], v23
    lq   v23, [v20 + 496]
    sq   [v21 + 496], v23
    lq   v23, [v20 + 512]
    sq   [v21 + 512], v23
    lq   v23, [v20 + 528]
    sq   [v21 + 528], v23
    lq   v23, [v20 + 544]
    sq   [v21 + 544], v23
    lq   v23, [v20 + 560]
    sq   [v21 + 560], v23
    lq   v23, [v20 + 576]
    sq   [v21 + 576], v23
    lq   v23, [v20 + 592]
    sq   [v21 + 592], v23
    lq   v23, [v20 + 608]
    sq   [v21 + 608], v23
    lq   v23, [v20 + 624]
    sq   [v21 + 624], v23
    lq   v23, [v20 + 640]
    sq   [v21 + 640], v23
    lq   v23, [v20 + 656]
    sq   [v21 + 656], v23
    lq   v23, [v20 + 672]
    sq   [v21 + 672], v23
    lq   v23, [v20 + 688]
    sq   [v21 + 688], v23
    lq   v23, [v20 + 704]
    sq   [v21 + 704], v23
    lq   v23, [v20 + 720]
    sq   [v21 + 720], v23
    lq   v23, [v20 + 736]
    sq   [v21 + 736], v23
    lq   v23, [v20 + 752]
    sq   [v21 + 752], v23
    lq   v23, [v20 + 768]
    sq   [v21 + 768], v23
    lq   v23, [v20 + 784]
    sq   [v21 + 784], v23
    lq   v23, [v20 + 800]
    sq   [v21 + 800], v23
    lq   v23, [v20 + 816]
    sq   [v21 + 816], v23
    lq   v23, [v20 + 832]
    sq   [v21 + 832], v23
    lq   v23, [v20 + 848]
    sq   [v21 + 848], v23
    lq   v23, [v20 + 864]
    sq   [v21 + 864], v23
    lq   v23, [v20 + 880]
    sq   [v21 + 880], v23
    lq   v23, [v20 + 896]
    sq   [v21 + 896], v23
    lq   v23, [v20 + 912]
    sq   [v21 + 912], v23
    lq   v23, [v20 + 928]
    sq   [v21 + 928], v23
    lq   v23, [v20 + 944]
    sq   [v21 + 944], v23
    lq   v23, [v20 + 960]
    sq   [v21 + 960], v23
    lq   v23, [v20 + 976]
    sq   [v21 + 976], v23
    lq   v23, [v20 + 992]
    sq   [v21 + 992], v23
    lq   v23, [v20 + 1008]
    sq   [v21 + 1008], v23
    lq   v23, [v20 + 1024]
    sq   [v21 + 1024], v23
    lq   v23, [v20 + 1040]
    sq   [v21 + 1040], v23
    lq   v23, [v20 + 1056]
    sq   [v21 + 1056], v23
    lq   v23, [v20 + 1072]
    sq   [v21 + 1072], v23
    lq   v23, [v20 + 1088]
    sq   [v21 + 1088], v23
    lq   v23, [v20 + 1104]
    sq   [v21 + 1104], v23
    lq   v23, [v20 + 1120]
    sq   [v21 + 1120], v23
    lq   v23, [v20 + 1136]
    sq   [v21 + 1136], v23
    lq   v23, [v20 + 1152]
    sq   [v21 + 1152], v23
    lq   v23, [v20 + 1168]
    sq   [v21 + 1168], v23
    lq   v23, [v20 + 1184]
    sq   [v21 + 1184], v23
    lq   v23, [v20 + 1200]
    sq   [v21 + 1200], v23
    lq   v23, [v20 + 1216]
    sq   [v21 + 1216], v23
    lq   v23, [v20 + 1232]
    sq   [v21 + 1232], v23
    lq   v23, [v20 + 1248]
    sq   [v21 + 1248], v23
    lq   v23, [v20 + 1264]
    sq   [v21 + 1264], v23
    lq   v23, [v20 + 1280]
    sq   [v21 + 1280], v23
    lq   v23, [v20 + 1296]
    sq   [v21 + 1296], v23
    lq   v23, [v20 + 1312]
    sq   [v21 + 1312], v23
    lq   v23, [v20 + 1328]
    sq   [v21 + 1328], v23
    lq   v23, [v20 + 1344]
    sq   [v21 + 1344], v23
    lq   v23, [v20 + 1360]
    sq   [v21 + 1360], v23
    lq   v23, [v20 + 1376]
    sq   [v21 + 1376], v23
    lq   v23, [v20 + 1392]
    sq   [v21 + 1392], v23
    lq   v23, [v20 + 1408]
    sq   [v21 + 1408], v23
    lq   v23, [v20 + 1424]
    sq   [v21 + 1424], v23
    lq   v23, [v20 + 1440]
    sq   [v21 + 1440], v23
    lq   v23, [v20 + 1456]
    sq   [v21 + 1456], v23
    lq   v23, [v20 + 1472]
    sq   [v21 + 1472], v23
    lq   v23, [v20 + 1488]
    sq   [v21 + 1488], v23
    lq   v23, [v20 + 1504]
    sq   [v21 + 1504], v23
    lq   v23, [v20 + 1520]
    sq   [v21 + 1520], v23
    lq   v23, [v20 + 1536]
    sq   [v21 + 1536], v23
    lq   v23, [v20 + 1552]
    sq   [v21 + 1552], v23
    lq   v23, [v20 + 1568]
    sq   [v21 + 1568], v23
    lq   v23, [v20 + 1584]
    sq   [v21 + 1584], v23
    lq   v23, [v20 + 1600]
    sq   [v21 + 1600], v23
    lq   v23, [v20 + 1616]
    sq   [v21 + 1616], v23
    lq   v23, [v20 + 1632]
    sq   [v21 + 1632], v23
    lq   v23, [v20 + 1648]
    sq   [v21 + 1648], v23
    lq   v23, [v20 + 1664]
    sq   [v21 + 1664], v23
    lq   v23, [v20 + 1680]
    sq   [v21 + 1680], v23
    lq   v23, [v20 + 1696]
    sq   [v21 + 1696], v23
    lq   v23, [v20 + 1712]
    sq   [v21 + 1712], v23
    lq   v23, [v20 + 1728]
    sq   [v21 + 1728], v23
    lq   v23, [v20 + 1744]
    sq   [v21 + 1744], v23
    lq   v23, [v20 + 1760]
    sq   [v21 + 1760], v23
    lq   v23, [v20 + 1776]
    sq   [v21 + 1776], v23
    lq   v23, [v20 + 1792]
    sq   [v21 + 1792], v23
    lq   v23, [v20 + 1808]
    sq   [v21 + 1808], v23
    lq   v23, [v20 + 1824]
    sq   [v21 + 1824], v23
    lq   v23, [v20 + 1840]
    sq   [v21 + 1840], v23
    lq   v23, [v20 + 1856]
    sq   [v21 + 1856], v23
    lq   v23, [v20 + 1872]
    sq   [v21 + 1872], v23
    lq   v23, [v20 + 1888]
    sq   [v21 + 1888], v23
    lq   v23, [v20 + 1904]
    sq   [v21 + 1904], v23
    lq   v23, [v20 + 1920]
    sq   [v21 + 1920], v23
    lq   v23, [v20 + 1936]
    sq   [v21 + 1936], v23
    lq   v23, [v20 + 1952]
    sq   [v21 + 1952], v23
    lq   v23, [v20 + 1968]
    sq   [v21 + 1968], v23
    lq   v23, [v20 + 1984]
    sq   [v21 + 1984], v23
    lq   v23, [v20 + 2000]
    sq   [v21 + 2000], v23
    lq   v23, [v20 + 2016]
    sq   [v21 + 2016], v23
    lq   v23, [v20 + 2032]
    sq   [v21 + 2032], v23
    lq   v23, [v20 + 2048]
    sq   [v21 + 2048], v23
    lq   v17, [v25 + T_TPC]
    csrw tpc, v17
    lq   v16, [v25 + T_RESULT]
    jmp  syscall_return

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
msg_deadlock: .asciz "[kernelloom] deadlock: every task is blocked\n"

; SAND Desktop UI labels rendered by the guest graphics device.
text_brand:       .ascii "SAND "
text_home:        .ascii "HOME"
text_files:       .ascii "FILES"
text_terminal:    .ascii "TERMINAL"
text_settings:    .ascii "SETTINGS"
text_workspace:   .ascii "WORKSPACE"
text_welcome:     .ascii "WELCOME BACK"
text_ready:       .ascii "YOUR SYSTEM IS READY TO USE"
text_files_card:  .ascii "FILES"
text_files_count: .ascii "12 ITEMS"
text_system_card: .ascii "SYSTEM"
text_system_ok:   .ascii "ALL SYSTEMS"
text_launcher:    .ascii "START"
text_clock:       .ascii "23 NOV 2026 19"
