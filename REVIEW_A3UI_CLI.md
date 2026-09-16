# REVIEW_A3UI_CLI

The `a3ui-cli` repository is a third, dependency-free A3UI renderer. It reads the normative contract from `../a3/spec/SPEC_A3UI.md` and reads the shared fixtures from `../a3/conformance/a3ui/fixtures/` by path. Fixture bytes are not copied into this repository.

The implementation is intentionally small: Python 3.11 standard library only, headless protocol model in `a3ui_cli/core.py`, and deterministic seven-primitive text output in `a3ui_cli/render.py`.

## Audit table

| ID | Requirement | Result | Evidence |
|---|---|---|---|
| CL-001 | Four shared fixtures produce the required CTA semantics | PASS | `tests/test_cli.py` |
| CL-002 | Missing tuple field is an explicit reject | PASS | `TupleError` and test |
| CL-003 | Pre-mount proposal queues and mounts with its container | PASS | `SurfaceQueue` and test |
| CL-004 | Producer dismissal is rejected | PASS | `SurfaceLifecycle.producer_dismiss` |
| CL-005 | Dismissal removes the memory reference | PASS | `SurfaceMemory` and test |
| CL-006 | 25 value re-binds produce one form generation | PASS | `FormRegistry.generation_count == 1` |
| CL-007 | Surface identity remains stable through re-bindings | PASS | `SurfaceBinding.surface_id` |
| CL-008 | Form-key change produces generation two | PASS | explicit `regenerate` test |
| CL-009 | Opaque `x-*` payload crosses unchanged; invalid key rejects | PASS | `SurfaceExtensions` and test |
| CL-010 | Unknown extension does not prevent text rendering | PASS | renderer test |
| CL-011 | Boundary has no forbidden consumer/person references or imports | PASS | source scan and path-only spec/fixture assertions |
| CL-012 | Exactly seven primitives are rendered | PASS | `PRIMITIVES` equality test |

The CLI also has a smoke test proving `python3 -m a3ui_cli render <surface.json>` exits `0` for valid input and `1` with an explicit reject message for incomplete input.

## Shared fixture comparison

All three implementations consume the same four fixture files. The comparison is semantic, not pixel-based.

| Fixture | Mark | Compose conformance | Web conformance | CLI | Shared meaning |
|---|---|---|---|---|---|
| `calendar-contradicted.json` | CONTRADICTED | CTA disabled; reason visible | CTA disabled; reason visible | `cta=disabled`; reason emitted | Confirmation is forbidden because evidence conflicts |
| `hotel-stale.json` | STALE | CTA enabled; age/warning visible | CTA enabled; age/warning visible | `cta=enabled`; warning emitted | The value may be acted on, but its age is visible |
| `train-pending.json` | PENDING | CTA disabled; reserved slot | CTA disabled; reserved slot | `cta=disabled`; `reserved=yes` | Verification is ongoing; it is not completion |
| `flight-fact.json` | FACT | CTA enabled; baseline chrome | CTA enabled; baseline chrome | `cta=enabled`; baseline row | Normal authorization path, with no extra mark |

The CLI does not promote a receipt, model output, or sandbox result into a fact. It consumes the declared fixture tuple and preserves its mark, provenance, age, confidence, and action lists.

## Lifecycle, binding, and extension notes

- Lifecycle ownership is explicit: producers propose; the shell mounts, activates, freezes, restores, and dismisses.
- Frozen state carries declared preserved and discarded fields; restore reports both sets.
- `DataRef` retains source and lineage. Value re-binding does not regenerate a form; form-key regeneration is explicit and counted.
- Extension values are retained as opaque object references. The CLI validates only the `x-*` key shape and never interprets consumer payload contents.
- Text rendering uses exactly `stack`, `row`, `list`, `item`, `action`, `field`, and `text`; no consumer-specific primitive is introduced.

## Gate evidence

- `pytest`: PASS, 13 tests.
- CLI smoke test: PASS within the pytest suite.
- Standard-library implementation: PASS; no runtime dependencies or package manager manifest.
- Shared fixture access: PASS by relative path; no fixture copies added.
- Commit and local tag are created only after the green gate. No push is performed by this slice.
