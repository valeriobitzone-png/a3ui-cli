# SPDX-License-Identifier: Apache-2.0
# Part of the A3 universe. See LICENSE.
"""Text renderer: deliberately small, deterministic, and independent of chrome."""

from __future__ import annotations

import json
from typing import Any

from .core import PRIMITIVES, Surface


def render_surface(surface: Surface) -> str:
    cta = surface.cta
    reason = cta.reason or "-"
    warning = cta.warning or "-"
    cta_state = "enabled" if cta.enabled else "disabled"
    lines = [
        f"stack mark={surface.mark} surfaceId={surface.id}",
        f"row object={surface.oggetto} age={surface.age}",
        f"list truth_class={surface.truth_class} provenance={surface.provenance}",
        f"item confidence={surface.confidence:g}",
        f"action cta={cta_state} reason={reason} warning={warning}",
        f"field permitted={','.join(surface.actions_permitted) or '-'} forbidden={','.join(surface.actions_forbidden) or '-'}",
        f"text status={surface.mark} reserved={'yes' if cta.reserved else 'no'}",
    ]
    return "\n".join(lines)


def render_json(value: dict[str, Any]) -> str:
    return render_surface(Surface.from_mapping(value))


def primitive_names() -> tuple[str, ...]:
    return PRIMITIVES


def load_and_render(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("surface JSON must be an object")
    return render_json(value)
