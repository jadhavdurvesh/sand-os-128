# 09 — Kernel architecture

**Status:** Planned; no kernel implementation yet  
**Working term:** Kernelloom (provisional)

## 1. Purpose

The experimental kernel will test whether the architecture is capable of supporting a small protected operating system. It is downstream of the ISA and platform specifications; it must not define architectural behaviour accidentally through implementation quirks.

## 2. Kernel responsibilities

The initial kernel may eventually provide:
- Boot hand-off and machine initialisation.
- Exception and interrupt handling.
- Physical-memory inventory and allocation.
- Virtual-memory management.
- Basic task or process isolation.
- A minimal system-call interface.
- A simple console or serial-like output device in the emulator.

Scheduling, storage, networking, graphics, and a desktop environment are later concerns.

## 3. Boot contract

Before writing a bootloader, specify the platform's reset state and boot hand-off:
- Entry privilege and instruction location.
- Memory map and reserved regions.
- Available firmware or loader services.
- Device discovery mechanism.
- Kernel image format and relocation rules.
- How the kernel establishes its own memory-management state.

The emulator should provide a documented virtual platform so a kernel can be tested without physical hardware.

## 4. Isolation

The kernel must own privileged state and validate all user-to-kernel inputs. The memory architecture must support protection boundaries before meaningful process isolation can be claimed.

## 5. System-call interface

System calls are an ABI, not merely a special opcode. Define the entry mechanism, argument and return convention, error representation, register preservation, and versioning rules.

## 6. Porting boundary

The first kernel should be small and architecture-specific. Portable subsystems can be considered later, but the architecture-specific boundary must remain explicit.

## 7. Non-goals for the first kernel

No initial commitment to a GUI, application ecosystem, networking stack, USB support, SMP, or broad hardware compatibility. A tiny deterministic kernel is a better first proof of concept.
