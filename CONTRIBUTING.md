# Contributing to SAND-128

SAND-128 is an experimental architecture research project. Contributions should strengthen the specification before expanding the implementation.

## Design-first workflow

1. Read the project charter and the relevant architecture documents.
2. Search the decision register for an existing decision or unresolved question.
3. For a new architectural choice, add a decision record explaining the context, alternatives, trade-offs, and consequences.
4. Update the specification before relying on the behaviour in code.
5. Add conformance tests for every accepted behavioural rule.
6. Keep documentation explicit about whether a feature is proposed, accepted, implemented, or verified.

## Original architecture requirement

Do not copy another ISA's instruction encodings, register conventions, ABI, exception model, or platform contract and merely rename them. Existing architectures may be studied as references, but any borrowed idea must be acknowledged and independently evaluated. The resulting Veylith specification must define its own rules precisely.

## Naming

Use the project vocabulary in [the core vocabulary](docs/03-core-vocabulary.md). Add new terms there before treating them as formal architecture terminology. Prefer meaningful technical definitions over decorative renaming.

## Code quality

- Keep emulator behaviour deterministic.
- Do not depend on host integer overflow or undefined behaviour.
- Add boundary and negative tests, not only happy-path tests.
- Reject malformed instructions and images predictably.
- Keep architectural semantics separate from emulator implementation details.
- Avoid claiming support for features that are not implemented and tested.

## Scope

This repository is independent of SAND OS 64. Changes must not assume that the experimental architecture is compatible with the primary SAND OS architecture.
