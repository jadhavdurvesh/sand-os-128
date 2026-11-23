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
