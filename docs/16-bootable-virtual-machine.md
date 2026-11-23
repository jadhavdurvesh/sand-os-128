# Veylith virtual-machine disk and boot contract

## Scope
The first independently launchable SAND-128 target is a hosted Veylith virtual machine. A compiled C host machine runs Veylith 128-Native v1; that same C source is compiled to WebAssembly for the browser. Python remains the reference emulator and build-time assembler.

## Disk format: SAND128D v1
- 512-byte sectors.
- Sector 0 contains magic \`SAND128D\`, u32 version 1, u32 sector size 512, u64 payload offset 512, u64 payload length and u64 FNV-1a-64 checksum.
- Payload is a VYLI v2 image containing Kernelloom and the selected user program.
- Remaining bytes are zero padding; default image size is 2 MiB.
- Firmware verifies the header/checksum, parses VYLI, loads segments into bounded 1 MiB guest RAM and sets the reset PC to the VYLI entry.

## Boot sequence
1. Host opens the raw \`.img\`.
2. Veylith firmware validates the SAND128D header/checksum.
3. Bootloader parses VYLI v2 and loads kernel/user segments.
4. Guest resets in kernel privilege at the image entry.
5. Kernelloom configures traps and user aperture, then enters the user program.
6. The user program writes to the virtual console and exits through the kernel syscall ABI.

## Build and run
\`\`\`bash
python -m veylith disk --output build/SAND-128-Veylith.img
gcc -std=c11 -O2 -o veylith-vm native/veylith-vm.c
./veylith-vm build/SAND-128-Veylith.img
\`\`\`

GitHub Actions verifies the disk in the native machine, compiles the same C machine to WebAssembly, publishes the browser emulator, and uploads the image as an artifact.

## Compatibility
This is not an x86 machine. The image is not directly bootable by PC BIOS/UEFI or a generic x86 QEMU machine. It boots in the Veylith hosted VM and WebAssembly Web Machine. A future FPGA implementation needs its own reset/boot ROM and platform loader.


## Kernelloom v1 syscall additions

Kernelloom v1 retains the original write and exit ABI and adds:
- `3 getpid()`: returns task identifier 1. The kernel is still single-task; this is an identity syscall, not evidence of a scheduler.
- `4 getcycles()`: returns the guest machine's retired Glyph counter at syscall entry.

Run the syscall smoke test with:

```bash
python -m veylith boot examples/process_info.s
```

The test checks both return values from user mode. Multi-task scheduling, task creation, and context switching remain future work.


## SAND Desktop framebuffer

The hosted Veylith machine exposes a 1280×720, 32-bit RGBA framebuffer through a kernel-only memory-mapped graphics command block at `0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFE000`. Six 128-bit registers specify X, Y, width, height, color, and command (1 = fill rectangle). Kernelloom draws the initial desktop surfaces from guest assembly; the browser presents the framebuffer returned by the WebAssembly machine. This is a static guest-rendered desktop scene, not yet an interactive desktop: window management, mouse/keyboard input, text rendering, and applications remain future work.


## SAND Desktop typography

The Veylith graphics MMIO device supports command 2 for guest-memory text rendering. Kernelloom supplies guest RAM string pointers and text positions; the device rasterizes a built-in 5×7 uppercase bitmap font at 2× scale into the RGBA framebuffer. The first labelled shell includes navigation labels, a workspace welcome area, status cards, and a taskbar label. This remains a static desktop shell; input, interactive window management, and persistent applications are not yet implemented.


## Interactive browser desktop shell

The WebAssembly boot page adds a browser-hosted desktop layer after a successful guest boot. It provides window focus, dragging, minimize/maximize/close controls, a launcher, taskbar, desktop shortcuts, and demo Files, Terminal, Settings, and About applications. The terminal accepts a small set of built-in demonstration commands. This is intentionally distinguished from guest-kernel functionality: pointer/keyboard events and application state currently live in the browser host, not in Veylith guest RAM. A later input-device ABI and guest-side window server will move these responsibilities into the operating system.
