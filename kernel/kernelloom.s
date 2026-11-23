; Kernelloom v0 -- the first Veylith kernel experiment.
; Runs in kernel privilege, boots one user program inside an aperture (abase/alim),
; and serves two system calls.  Syscall ABI: number in v1, arguments in v2..v3, result in v1.
;   1 write(ptr=v2, len=v3)  -> bytes written, or -1 if the buffer is not inside the user aperture
;   2 exit(code=v2)          -> prints the code and halts the machine
; Any other call returns -1.  Any user fault is reported and halts the machine with 128+cause.
; Kernel scratch registers: v16..v29.  User registers are saved in a fixed frame (single core, not re-entrant).

.equ CONSOLE,   0xF0000000
.equ USER_BASE, 0x10000
.equ USER_SIZE, 0x10000
.equ FRAME,     0x7000
.equ DIGITS,    0x7F00          ; 40-byte scratch for decimal conversion (end of buffer)

.org 0
_start:
    la   v1, trap_entry
    csrw tvec, v1
    li   v30, 0x6000
    la   v1, banner
    call puts
    li   v1, USER_BASE
    csrw abase, v1
    csrw tpc, v1
    li   v1, USER_SIZE
    csrw alim, v1
    li   v1, 1
    csrw tpriv, v1
    tret

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
    li   v30, 0x6000
    csrr v16, tcause
    li   v17, 6
    bne  v16, v17, user_fault
    li   v17, 1
    beq  v1, v17, sys_write
    li   v17, 2
    beq  v1, v17, sys_exit
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

banner:    .asciz "[kernelloom] Veylith v0 booting user program\n"
msg_exit:  .asciz "[kernelloom] user exit "
msg_fault: .asciz "[kernelloom] user fault cause="
msg_addr:  .asciz " tval="
