# SPDX-License-Identifier: Apache-2.0
# Part of the A3 universe. See LICENSE.
"""Protocol-facing A3UI model primitives; no renderer or consumer policy lives here."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

PRIMITIVES = ("stack", "row", "list", "item", "action", "field", "text")
MARKS = ("UNKNOWN", "STALE", "HELD", "CONTRADICTED", "PENDING", "FACT")
REQUIRED_FIELDS = (
    "oggetto",
    "truth_class",
    "provenance",
    "age",
    "confidence",
    "actions_permitted",
    "actions_forbidden",
)
TRUTH_CLASSES = ("FACT", "OBSERVATION", "HYPOTHESIS", "UNKNOWN")
PROVENANCE = ("OBSERVED_SIGNED", "DERIVED_MODEL", "INFERRED", "HUMAN_ADMITTED")


class TupleError(ValueError):
    """A surface tuple is absent, malformed, or incomplete."""


class LifecycleError(ValueError):
    """A lifecycle transition violates the surface contract."""


class ExtensionError(ValueError):
    """An extension key violates the opaque namespace contract."""


class LifecycleState(str, Enum):
    PROPOSED = "PROPOSED"
    MOUNTED = "MOUNTED"
    ALIVE = "ALIVE"
    FROZEN = "FROZEN"
    DISMISSED = "DISMISSED"


@dataclass(frozen=True)
class CTA:
    enabled: bool
    reason: str | None = None
    warning: str | None = None
    reserved: bool = False


@dataclass(frozen=True)
class Surface:
    """The seven-field tuple plus renderer-neutral fixture metadata."""

    id: str
    oggetto: str
    truth_class: str
    provenance: str
    age: str
    confidence: float
    actions_permitted: tuple[str, ...]
    actions_forbidden: tuple[str, ...]
    mark: str
    extra: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "Surface":
        missing = [field for field in REQUIRED_FIELDS if field not in value]
        if missing:
            raise TupleError(f"missing-field: {', '.join(missing)}")
        truth_class = value["truth_class"]
        provenance = value["provenance"]
        if truth_class not in TRUTH_CLASSES:
            raise TupleError(f"invalid-truth-class: {truth_class}")
        if provenance not in PROVENANCE:
            raise TupleError(f"invalid-provenance: {provenance}")
        mark = str(value.get("mark", value.get("status", "UNKNOWN"))).upper()
        if mark not in MARKS:
            raise TupleError(f"invalid-mark: {mark}")
        if not isinstance(value["actions_permitted"], list) or not isinstance(value["actions_forbidden"], list):
            raise TupleError("invalid-actions: expected lists")
        if set(value["actions_permitted"]) & set(value["actions_forbidden"]):
            raise TupleError("invalid-actions: permitted and forbidden overlap")
        try:
            confidence = float(value["confidence"])
        except (TypeError, ValueError) as error:
            raise TupleError("invalid-confidence") from error
        if not 0 <= confidence <= 1:
            raise TupleError("invalid-confidence: expected [0, 1]")
        identifier = str(value.get("id", value.get("oggetto", "surface")))
        return cls(
            id=identifier,
            oggetto=str(value["oggetto"]),
            truth_class=str(truth_class),
            provenance=str(provenance),
            age=str(value["age"]),
            confidence=confidence,
            actions_permitted=tuple(str(item) for item in value["actions_permitted"]),
            actions_forbidden=tuple(str(item) for item in value["actions_forbidden"]),
            mark=mark,
            extra=MappingProxyType(dict(value)),
        )

    @property
    def cta(self) -> CTA:
        if self.mark == "CONTRADICTED":
            return CTA(False, reason=str(self.extra.get("reason", "contradicted: resolve conflict first")))
        if self.mark == "HELD":
            return CTA(False, reason="quarantine")
        if self.mark == "UNKNOWN":
            return CTA(False, reason="insufficient evidence")
        if self.mark == "STALE":
            return CTA(True, warning=f"stale {self.age}")
        if self.mark == "PENDING":
            return CTA(False, reason=str(self.extra.get("pending_label", "in verifica")), reserved=True)
        return CTA(True)


class SurfaceLifecycle:
    """Headless shell-owned state machine for one ephemeral surface."""

    def __init__(self, surface_id: str):
        if not surface_id.strip():
            raise LifecycleError("surfaceId is required")
        self.id = surface_id
        self.state = LifecycleState.PROPOSED
        self.snapshot: dict[str, Any] | None = None
        self.restoration: dict[str, Any] | None = None

    @classmethod
    def proposed(cls, surface_id: str) -> "SurfaceLifecycle":
        return cls(surface_id)

    @staticmethod
    def proposed_by_shell(surface_id: str) -> "SurfaceLifecycle":
        raise LifecycleError(f"shell MUST NOT create PROPOSED surface '{surface_id}'")

    def producer_dismiss(self) -> None:
        raise LifecycleError(f"producer MUST NOT dismiss surface '{self.id}'")

    def mount(self) -> "SurfaceLifecycle":
        self._transition(LifecycleState.PROPOSED, LifecycleState.MOUNTED)
        return self

    def activate(self) -> "SurfaceLifecycle":
        self._transition(LifecycleState.MOUNTED, LifecycleState.ALIVE)
        return self

    def freeze(self, preserved: Mapping[str, Any], discarded: set[str] | frozenset[str]) -> "SurfaceLifecycle":
        self._transition(LifecycleState.ALIVE, LifecycleState.FROZEN)
        self.snapshot = {"preserved": dict(preserved), "discarded": frozenset(discarded)}
        self.restoration = None
        return self

    def revive(self) -> Mapping[str, Any]:
        self._transition(LifecycleState.FROZEN, LifecycleState.ALIVE)
        if self.snapshot is None:
            raise LifecycleError("frozen surface lacks preservation declaration")
        self.restoration = {
            "restored": dict(self.snapshot["preserved"]),
            "discarded": self.snapshot["discarded"],
        }
        return self.restoration

    def dismiss(self) -> "SurfaceLifecycle":
        if self.state not in (LifecycleState.MOUNTED, LifecycleState.ALIVE, LifecycleState.FROZEN):
            raise LifecycleError(f"surface '{self.id}': {self.state.value} -> DISMISSED is illegal")
        self.state = LifecycleState.DISMISSED
        self.snapshot = None
        self.restoration = None
        return self

    def _transition(self, expected: LifecycleState, target: LifecycleState) -> None:
        if self.state != expected:
            raise LifecycleError(
                f"surface '{self.id}': {self.state.value} -> {target.value}; expected {expected.value}"
            )
        self.state = target


class SurfaceQueue:
    def __init__(self) -> None:
        self._pending: dict[str, dict[str, SurfaceLifecycle]] = {}

    def enqueue(self, container_id: str, surface: SurfaceLifecycle) -> None:
        if surface.state is not LifecycleState.PROPOSED:
            raise LifecycleError("only PROPOSED surfaces can be queued")
        self._pending.setdefault(container_id, {})[surface.id] = surface

    def mount(self, container_id: str) -> list[SurfaceLifecycle]:
        waiting = list(self._pending.pop(container_id, {}).values())
        for surface in waiting:
            surface.mount()
        return waiting

    def pending_count(self, container_id: str) -> int:
        return len(self._pending.get(container_id, {}))


class SurfaceMemory:
    def __init__(self) -> None:
        self._registry: dict[str, SurfaceLifecycle] = {}

    def register(self, surface: SurfaceLifecycle) -> SurfaceLifecycle:
        if surface.state is LifecycleState.DISMISSED:
            raise LifecycleError("dismissed surface cannot be registered")
        if surface.id in self._registry:
            raise LifecycleError(f"duplicate surface: {surface.id}")
        self._registry[surface.id] = surface
        return surface

    def dismiss(self, surface_id: str) -> None:
        surface = self._registry.pop(surface_id, None)
        if surface is not None:
            surface.dismiss()

    def get(self, surface_id: str) -> SurfaceLifecycle | None:
        return self._registry.get(surface_id)

    @property
    def size(self) -> int:
        return len(self._registry)


@dataclass(frozen=True)
class DataRef:
    key: str
    source: str
    lineage: str


@dataclass(frozen=True)
class Form:
    form_key: str
    schema_key: str
    generation: int


class FormRegistry:
    def __init__(self) -> None:
        self._forms: dict[str, Form] = {}
        self.generation_count = 0

    def get_or_create(self, form_key: str, schema_key: str | None = None) -> Form:
        schema = schema_key or form_key
        current = self._forms.get(form_key)
        if current is not None and current.schema_key == schema:
            return current
        self.generation_count += 1
        form = Form(form_key, schema, self.generation_count)
        self._forms[form_key] = form
        return form


class SurfaceBinding:
    def __init__(self, surface: SurfaceLifecycle, form: Form, data_ref: DataRef, registry: FormRegistry):
        self.surface = surface
        self.form = form
        self.data_ref = data_ref
        self.registry = registry
        self.surface_id = surface.id
        self._pending: DataRef | None = None

    @classmethod
    def proposed(
        cls, surface: SurfaceLifecycle, form_key: str, data_ref: DataRef, registry: FormRegistry
    ) -> "SurfaceBinding":
        if surface.state not in (LifecycleState.PROPOSED, LifecycleState.MOUNTED, LifecycleState.ALIVE, LifecycleState.FROZEN):
            raise LifecycleError("binding cannot start on DISMISSED surface")
        return cls(surface, registry.get_or_create(form_key), data_ref, registry)

    @property
    def has_pending_restore(self) -> bool:
        return self._pending is not None

    def rebind(self, data_ref: DataRef) -> "SurfaceBinding":
        self._reject_dismissed()
        if self.surface.state is LifecycleState.FROZEN:
            self._pending = data_ref
        else:
            self.data_ref = data_ref
        return self

    def regenerate(self, form_key: str, schema_key: str | None = None) -> "SurfaceBinding":
        self._reject_dismissed()
        self.form = self.registry.get_or_create(form_key, schema_key)
        return self

    def restore(self) -> DataRef:
        if self.surface.state is not LifecycleState.FROZEN:
            raise LifecycleError("binding restore requires FROZEN surface")
        self.surface.revive()
        if self._pending is not None:
            self.data_ref = self._pending
            self._pending = None
        return self.data_ref

    def _reject_dismissed(self) -> None:
        if self.surface.state is LifecycleState.DISMISSED:
            raise LifecycleError("cannot rebind DISMISSED surface")


class SurfaceExtensions:
    def __init__(self, entries: Mapping[str, Any]):
        self.entries = MappingProxyType(dict(entries))

    @classmethod
    def of(cls, entries: Mapping[str, Any]) -> "SurfaceExtensions":
        for key in entries:
            if not key.startswith("x-") or len(key) <= 2:
                raise ExtensionError(f"extension key '{key}' MUST start with x-")
        return cls(entries)

    @classmethod
    def empty(cls) -> "SurfaceExtensions":
        return cls({})
