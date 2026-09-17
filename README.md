# a3ui-cli — textual A3UI renderer

![a3ui-cli cover](docs/assets/cover.png)

A deterministic Python standard-library CLI that renders A3UI surfaces as text.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/valeriobitzone-png/a3/blob/main/LICENSE) [![Latest tag](https://img.shields.io/github/v/tag/valeriobitzone-png/a3ui-cli?sort=semver)](https://github.com/valeriobitzone-png/a3ui-cli/tags) [![CI](https://github.com/valeriobitzone-png/a3ui-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/valeriobitzone-png/a3ui-cli/actions/workflows/ci.yml)

## What it is

A Python 3.11+ protocol-honesty bench. It validates the seven-field surface tuple, lifecycle, DataRef re-binding, opaque `x-*` extensions, marks, provenance, age, and CTA state.

## What it is NOT

It is not a product UI, not a graphical renderer, and not a copy of another A3UI implementation.

## Status

- **VERIFIED:** CL-001..CL-012, 13 pytest tests, CLI smoke behavior, seven-primitive closure, and shared fixture semantics.
- **UNVERIFIED:** downstream adoption and terminal presentation outside the deterministic text format.

## Quickstart

### Get it

```bash
git clone https://github.com/valeriobitzone-png/a3ui-cli.git
cd a3ui-cli
# Requirements: Python 3.11+ and pytest for the test gate.
git clone https://github.com/valeriobitzone-png/a3.git ../a3
git -C ../a3 checkout closeout-v1.0
```

### Prove it

```bash
python3 -m pytest -q
python3 -m a3ui_cli render ../a3/conformance/a3ui/fixtures/calendar-contradicted.json
```

### Integrate it

Run `python3 -m a3ui_cli render <surface.json>` as a textual bench for your own surfaces. Read `../a3/spec/SPEC_A3UI.md`, preserve provenance and UNKNOWN-first semantics, and keep the seven primitive catalog closed.

## Architecture

`a3ui_cli/core.py` validates protocol semantics; `a3ui_cli/render.py` emits deterministic text; `tests/` covers the shared surface behavior. Runtime dependencies are standard library only.

## Testing & conformance

CI runs pytest. The CLI exits 0 for valid input and exits 1 with `reject:` for invalid input; fixture semantics are compared with the family implementations.

## Family

- [a3](https://github.com/valeriobitzone-png/a3) — normative specs and Kotlin implementation
- [a3-ts](https://github.com/valeriobitzone-png/a3-ts) — TypeScript reference implementation
- [a3-go](https://github.com/valeriobitzone-png/a3-go) — Go reference implementation
- [a3ui-web](https://github.com/valeriobitzone-png/a3ui-web) — Web Components renderer
- [a3ui-graphics](https://github.com/valeriobitzone-png/a3ui-graphics) — renderer-neutral graphics tokens

## Contributing

Keep text output deterministic, preserve provenance, and add tests for protocol behavior before changing the renderer.

## License

Implementation code is Apache-2.0. The consumed A3UI specification and schemas are CC BY 4.0 in the A3 repository.

## Provenance

Measured: pytest results, CLI exit codes, primitive inventory, and path-based fixture reads. Textual layout is a renderer decision, not evidence about the underlying world.
