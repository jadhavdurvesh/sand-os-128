# 06 — Memory architecture

**Accepted Veylith 128-Native v1 address model**

- Pointer width: 128 bits.
- Virtual address width: 128 bits.
- Program counter and trap addresses: 128 bits.
- Effective-address arithmetic: modulo 2^128, followed by range and access checks.
- Physical RAM: bounded platform/emulator capacity, default 1 MiB.
- Initial mapping: flat RAM plus explicitly defined high-address console MMIO; paging is not yet implemented.

The virtual address domain is the full unsigned 128-bit range. This does not mean the emulator allocates 2^128 bytes or that a physical machine has that amount of RAM. The implementation stores only configured physical RAM. Unmapped addresses trap ACCESS.

Console output is a byte-store MMIO register at 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFF0000. Accesses are little-endian and naturally aligned. The kernel/user aperture and privilege checks remain mandatory. Physical address width and actual memory capacity are platform parameters and are not inferred from the 128-bit virtual address width.

Paging, translation caches, page tables, address-space identifiers, and multicore memory ordering remain future work.
