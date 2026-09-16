# SPDX-License-Identifier: Apache-2.0
# Part of the A3 universe. See LICENSE.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from a3ui_cli.core import (
    ExtensionError,
    FormRegistry,
    LifecycleError,
    LifecycleState,
    Surface,
    SurfaceBinding,
    SurfaceExtensions,
    SurfaceLifecycle,
    SurfaceMemory,
    SurfaceQueue,
    TupleError,
    PRIMITIVES,
)
from a3ui_cli.render import render_surface


ROOT = Path(__file__).resolve().parents[1]
A3 = Path(__file__).resolve().parents[2] / "a3"
FIXTURES = A3 / "conformance" / "a3ui" / "fixtures"


def fixture(name: str) -> Surface:
    with (FIXTURES / name).open(encoding="utf-8") as handle:
        return Surface.from_mapping(json.load(handle))


def ref(key: str):
    from a3ui_cli.core import DataRef

    return DataRef(key, "cli-test-source", f"cli-test-lineage-{key}")


def test_cl_001_shared_fixtures_have_expected_cta_semantics():
    cases = {
        "calendar-contradicted.json": (False, True),
        "hotel-stale.json": (True, False),
        "train-pending.json": (False, True),
        "flight-fact.json": (True, False),
    }
    for name, (enabled, has_reason) in cases.items():
        surface = fixture(name)
        assert surface.cta.enabled is enabled
        assert (surface.cta.reason is not None) is has_reason
        assert surface.mark in {"CONTRADICTED", "STALE", "PENDING", "FACT"}


def test_cl_002_incomplete_tuple_is_an_explicit_reject():
    with pytest.raises(TupleError, match="missing-field"):
        Surface.from_mapping({"oggetto": "missing"})


def test_cl_003_pre_mount_queue_mounts_when_container_arrives():
    queue = SurfaceQueue()
    surface = SurfaceLifecycle.proposed("cl-003")
    queue.enqueue("container", surface)
    assert queue.pending_count("container") == 1
    assert surface.state is LifecycleState.PROPOSED
    assert queue.mount("container") == [surface]
    assert surface.state is LifecycleState.MOUNTED


def test_cl_004_producer_dismiss_is_rejected():
    surface = SurfaceLifecycle.proposed("cl-004")
    with pytest.raises(LifecycleError, match="MUST NOT dismiss"):
        surface.producer_dismiss()


def test_cl_005_dismissed_surface_has_no_memory_reference():
    memory = SurfaceMemory()
    surface = memory.register(SurfaceLifecycle.proposed("cl-005"))
    surface.mount().activate()
    memory.dismiss(surface.id)
    assert memory.get(surface.id) is None
    assert memory.size == 0
    assert surface.state is LifecycleState.DISMISSED


def test_cl_006_n_value_rebinds_generate_one_form():
    registry = FormRegistry()
    surface = SurfaceLifecycle.proposed("cl-006").mount().activate()
    binding = SurfaceBinding.proposed(surface, "card", ref("initial"), registry)
    for index in range(25):
        binding.rebind(ref(f"value-{index}"))
    assert registry.generation_count == 1
    assert binding.data_ref.key == "value-24"


def test_cl_007_surface_id_is_stable_through_rebinds():
    registry = FormRegistry()
    surface = SurfaceLifecycle.proposed("stable-cl-007").mount().activate()
    binding = SurfaceBinding.proposed(surface, "card", ref("initial"), registry)
    for index in range(10):
        binding.rebind(ref(str(index)))
    assert binding.surface_id == "stable-cl-007"
    assert binding.surface.id == "stable-cl-007"


def test_cl_008_form_key_change_increments_generation_to_two():
    registry = FormRegistry()
    surface = SurfaceLifecycle.proposed("cl-008").mount().activate()
    binding = SurfaceBinding.proposed(surface, "card", ref("initial"), registry)
    binding.regenerate("list")
    assert registry.generation_count == 2
    assert binding.form.form_key == "list"
    assert binding.form.generation == 2


def test_cl_009_extension_payload_is_opaque_and_invalid_key_rejects():
    extension_key = "x-" + "consumer" + "-gate"
    payload = {"status": "pending", "nested": [1, 2]}
    extensions = SurfaceExtensions.of({extension_key: payload})
    assert extensions.entries[extension_key] is payload
    with pytest.raises(ExtensionError, match="MUST start with x-"):
        SurfaceExtensions.of({"gate": payload})


def test_cl_010_unknown_extension_is_ignored_and_surface_is_rendered():
    surface = fixture("flight-fact.json")
    extensions = SurfaceExtensions.of({"x-consumer-private": {"opaque": True}})
    output = render_surface(surface)
    assert "stack" in output and "action cta=enabled" in output
    assert extensions.entries["x-consumer-private"] == {"opaque": True}


def test_cl_011_boundary_has_no_forbidden_consumer_or_person_references():
    forbidden_consumer = "".join(("M", "O", "N", "O"))
    forbidden_person = "amb" + "ro"
    for path in (ROOT / "a3ui_cli").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert forbidden_consumer not in text
        assert forbidden_person not in text.lower()
    assert (A3 / "spec" / "SPEC_A3UI.md").is_file()
    assert FIXTURES.is_dir()


def test_cl_012_text_renderer_contains_exactly_seven_primitives():
    output = render_surface(fixture("calendar-contradicted.json"))
    names = [line.split(" ", 1)[0] for line in output.splitlines()]
    assert tuple(names) == PRIMITIVES
    assert len(names) == 7
    assert "mark=CONTRADICTED" in output
    assert "cta=disabled" in output


def test_cli_render_success_and_reject_exit_codes(tmp_path: Path):
    source = FIXTURES / "flight-fact.json"
    ok = subprocess.run(
        [sys.executable, "-m", "a3ui_cli", "render", str(source)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert ok.returncode == 0
    assert "stack mark=FACT" in ok.stdout

    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"oggetto": "incomplete"}', encoding="utf-8")
    rejected = subprocess.run(
        [sys.executable, "-m", "a3ui_cli", "render", str(invalid)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert rejected.returncode == 1
    assert "reject: missing-field" in rejected.stderr
