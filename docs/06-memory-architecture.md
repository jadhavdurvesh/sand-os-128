# 06 — Memory architecture

**Status:** Research draft

## 1. Separate the address concepts

A 128-bit register model does not require a 128-bit pointer or a 128-bit implemented address space.

SAND-128 will specify these independently:

- **Pointer representation:** how software represents references.
- **Virtual address width:** how many address bits the active translation model implements.
- **Physical address width:** how many physical address bits a platform implements.
- **Register width:** the width of scalar registers.
- **Access width:** the number of bits transferred by a load or store.

A 128-bit value may be used in arithmetic and still be rejected as an invalid address.

## 2. Address-space model

The architecture must define:
- Address-space identifiers and switching rules.
- Canonical or valid address ranges.
- Translation and page-table format.
- Page sizes and alignment.
- Read, write, execute, and user/supervisor permissions.
- Accessed and dirty tracking, if any.
- Translation-cache invalidation rules.
- Fault causes and fault-address reporting.

The initial implementation may use a simple software-defined translation model. That model must still specify all observable behaviour.

## 3. Memory protection

The kernel must be able to isolate address spaces and prevent user programs from modifying privileged memory. The architecture should specify permission checks for instruction fetch, data reads, and data writes separately.

## 4. Alignment and access rules

The ISA must state which load/store widths are supported and whether misaligned accesses are accepted, emulated, or faulted. Atomic operations require stricter, explicit rules and are not implied by ordinary loads or stores.

## 5. Memory ordering

A multicore system needs a defined memory consistency model. The first emulator can be single-core, but the architecture should avoid leaving memory ordering permanently ambiguous. A sequentially consistent baseline is easy to reason about but can constrain implementations; weaker models require formal rules and tests.

## 6. Physical limits

A theoretical address width describes a mathematical range, not an amount of installed memory or an implementable chip design. Real systems are constrained by physical address pins or interconnects, memory devices, translation structures, platform design, and cost.

## 7. Open decisions

Address widths, page-table structure, page size, endianness, memory ordering, atomic primitives, and I/O mapping remain open. See the decision register before treating any of these as fixed.
