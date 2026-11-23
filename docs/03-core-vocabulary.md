# 03 — Core vocabulary

**Status:** Provisional terminology  
**Purpose:** Establish a consistent SAND-128 vocabulary without copying the names of another ISA's subsystems.

Names below are project-defined labels for this repository. They are not claims of worldwide uniqueness or trademark availability. Technical explanations remain authoritative; a name never substitutes for a precise definition.

| Term | Meaning | Status |
|---|---|---|
| **Veylith** | The proposed SAND-128 instruction-set and machine architecture | Provisional codename |
| **Veyl** | Proposed name for a 128-bit general-purpose scalar register | Proposed |
| **Veylset** | The complete architecturally visible scalar-register bank | Proposed |
| **Glyph** | A decoded instruction operation, independent of its eventual binary encoding | Proposed |
| **Glyphstream** | The ordered sequence of encoded instructions in a program | Proposed |
| **Kernelloom** | The proposed name for the privileged kernel execution environment | Proposed |
| **Aperture map** | The documented mapping and permission model for an address space | Descriptive term |
| **Tracebook** | A deterministic emulator trace containing state changes and events | Proposed |
| **Forgepath** | The toolchain pipeline from source or assembly to a loadable image | Proposed |

## Naming rules

1. Prefer short names with one stable meaning.
2. Do not reuse a term for both an instruction and a subsystem.
3. Keep standard terms such as *register*, *opcode*, *virtual address*, *page table*, *interrupt*, and *ABI* when they improve precision.
4. Do not rename standard computer-science concepts solely to appear different.
5. Record a term's definition and status here before using it as a formal architectural term.
6. If a term conflicts with an established project or becomes confusing, change it before the specification is frozen.

## Naming and originality

SAND-128 will define its own instruction semantics, encoding, register conventions, exception rules, and software interfaces. Originality is a matter of the actual specification and implementation, not merely unusual labels. Before a public stable release, names should be checked for collisions and legal concerns; this project does not claim exclusivity over coined words.
