"""seed_generator.py — helpers for building Excalidraw seed files."""

import json
import random
import secrets
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Color constants  (Excalidraw palette — Open Color shades)
# ---------------------------------------------------------------------------

TRANSPARENT  = "transparent"
WHITE        = "#ffffff"
GRAY         = "#ced4da"      # oc-gray-4
RED          = "#ff6b6b"      # oc-red-5
GREEN        = "#b2f2bb"      # oc-green-2
YELLOW       = "#ffec99"      # oc-yellow-2
BLUE         = "#a5d8ff"      # oc-blue-2
ORANGE       = "#ffa94d"      # oc-orange-4
PINK         = "#fcc2d7"      # oc-pink-2
VIOLET       = "#d0bfff"      # oc-violet-2
CYAN         = "#99e9f2"      # oc-cyan-2
STROKE_RED   = "#e03131"
STROKE_BLUE  = "#1971c2"
STROKE_GREEN = "#2f9e44"
STROKE_ORANGE= "#e67700"
STROKE_BLACK = "#1e1e1e"

# ---------------------------------------------------------------------------
# Element factories
# ---------------------------------------------------------------------------


def _id() -> str:
    return secrets.token_urlsafe(16)


def _seed() -> int:
    """Random 32-bit positive int, same range Excalidraw uses."""
    return random.randint(1, 2**31 - 1)


def _base(x: float, y: float, width: float, height: float,
          background_color: str, stroke_color: str,
          fill_style: str, stroke_width: int, roughness: int,
          stroke_style: str = "solid") -> dict[str, Any]:
    return {
        "id": _id(),
        "x": x, "y": y, "width": width, "height": height,
        "angle": 0,
        "strokeColor": stroke_color,
        "backgroundColor": background_color,
        "fillStyle": fill_style,
        "strokeWidth": stroke_width,
        "strokeStyle": stroke_style,
        "roughness": roughness,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": None,
        "seed": _seed(),
        "version": 1,
        "versionNonce": _seed(),
        "isDeleted": False,
        "boundElements": [],
        "updated": int(time.time() * 1000),
        "link": None,
        "locked": False,
    }


def rectangle(
    x: float, y: float, width: float, height: float,
    background_color: str = TRANSPARENT,
    stroke_color: str = STROKE_BLACK,
    fill_style: str = "solid",
    stroke_width: int = 2,
    roughness: int = 0,
    stroke_style: str = "solid",
    rounded: bool = False,
) -> dict[str, Any]:
    el = {"type": "rectangle", **_base(x, y, width, height, background_color, stroke_color, fill_style, stroke_width, roughness, stroke_style)}
    if rounded:
        el["roundness"] = {"type": 3}
    return el


def ellipse(
    x: float, y: float, width: float, height: float,
    background_color: str = TRANSPARENT,
    stroke_color: str = STROKE_BLACK,
    fill_style: str = "solid",
    stroke_width: int = 2,
    roughness: int = 0,
    stroke_style: str = "solid",
) -> dict[str, Any]:
    return {"type": "ellipse", **_base(x, y, width, height, background_color, stroke_color, fill_style, stroke_width, roughness, stroke_style)}


def diamond(
    x: float, y: float, width: float, height: float,
    background_color: str = TRANSPARENT,
    stroke_color: str = STROKE_BLACK,
    fill_style: str = "solid",
    stroke_width: int = 2,
    roughness: int = 0,
    stroke_style: str = "solid",
) -> dict[str, Any]:
    return {"type": "diamond", **_base(x, y, width, height, background_color, stroke_color, fill_style, stroke_width, roughness, stroke_style)}


def _line_like(
    kind: str, x: float, y: float, points: list[list[float]],
    stroke_color: str, stroke_width: int, stroke_style: str,
    start_arrowhead: str | None, end_arrowhead: str | None,
) -> dict[str, Any]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    width = max(xs) - min(xs)
    height = max(ys) - min(ys)
    el = {"type": kind, **_base(x, y, width, height, TRANSPARENT, stroke_color, "solid", stroke_width, 0, stroke_style)}
    el["points"] = [list(p) for p in points]
    el["lastCommittedPoint"] = None
    el["startBinding"] = None
    el["endBinding"] = None
    el["startArrowhead"] = start_arrowhead
    el["endArrowhead"] = end_arrowhead
    return el


def line(
    x: float, y: float, points: list[list[float]],
    stroke_color: str = STROKE_BLACK, stroke_width: int = 2, stroke_style: str = "solid",
) -> dict[str, Any]:
    """A multi-point line. `points` are relative to (x, y); first is usually [0, 0]."""
    return _line_like("line", x, y, points, stroke_color, stroke_width, stroke_style, None, None)


def arrow(
    x: float, y: float, points: list[list[float]],
    stroke_color: str = STROKE_BLACK, stroke_width: int = 2, stroke_style: str = "solid",
    end_arrowhead: str | None = "arrow", start_arrowhead: str | None = None,
) -> dict[str, Any]:
    """An arrow. `points` are relative to (x, y); first is usually [0, 0]."""
    return _line_like("arrow", x, y, points, stroke_color, stroke_width, stroke_style, start_arrowhead, end_arrowhead)


def text(
    x: float, y: float,
    content: str,
    font_size: int = 20,
    stroke_color: str = STROKE_BLACK,
    font_family: int = 5,
) -> dict[str, Any]:
    width = len(content) * font_size * 0.55
    height = font_size * 1.25
    return {
        "type": "text",
        **_base(x, y, width, height, TRANSPARENT, stroke_color, "solid", 2, 0),
        "text": content,
        "originalText": content,
        "fontSize": font_size,
        "fontFamily": font_family,
        "textAlign": "left",
        "verticalAlign": "top",
        "containerId": None,
        "autoResize": True,
        "lineHeight": 1.25,
    }


def bound_text(
    container: dict[str, Any],
    content: str,
    font_size: int = 20,
    stroke_color: str = STROKE_BLACK,
    font_family: int = 5,
) -> dict[str, Any]:
    """Create a text element bound inside *container*.

    Sets up the bidirectional binding that Excalidraw requires:
      - text.containerId  → container id
      - container.boundElements includes {"type": "text", "id": text_id}
      - text is centered (textAlign=center, verticalAlign=middle)
      - text position is auto-calculated to the container center
    """
    text_width = len(content) * font_size * 0.55
    text_height = font_size * 1.25
    # Center text inside container
    tx = container["x"] + (container["width"] - text_width) / 2
    ty = container["y"] + (container["height"] - text_height) / 2
    el = {
        "type": "text",
        **_base(tx, ty, text_width, text_height, TRANSPARENT, stroke_color, "solid", 2, 0),
        "text": content,
        "originalText": content,
        "fontSize": font_size,
        "fontFamily": font_family,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": container["id"],
        "autoResize": True,
        "lineHeight": 1.25,
    }
    # Update container's boundElements with the text reference
    container["boundElements"] = [
        ref for ref in container.get("boundElements", [])
        if ref.get("type") != "text"
    ] + [{"type": "text", "id": el["id"]}]
    return el


# ---------------------------------------------------------------------------
# SeedBuilder
# ---------------------------------------------------------------------------


# Excalidraw fractional-indexing base-62 digit charset (sorts lexicographically).
_BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


class SeedBuilder:
    """Builds an Excalidraw seed JSON."""

    def __init__(self):
        self._elements: list[dict[str, Any]] = []

    @staticmethod
    def _fractional_index(n: int) -> str:
        """Return a valid Excalidraw fractional index key for position *n*.

        Uses the 'a' integer prefix plus base-62 fractional digits,
        matching the format Excalidraw generates (e.g. 'a0', 'a1', 'aV', 'az').
        """
        if n < 0:
            raise ValueError(f"Index must be non-negative, got {n}")
        digits = []
        val = n
        while True:
            digits.append(_BASE62[val % 62])
            val //= 62
            if val == 0:
                break
        return "a" + "".join(reversed(digits))

    def add(self, element: dict[str, Any]) -> "SeedBuilder":
        el = dict(element)
        el["index"] = self._fractional_index(len(self._elements))
        self._elements.append(el)
        return self

    def build(self) -> dict[str, Any]:
        return {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": self._elements,
            "appState": {
                "gridSize": 20,
                "gridStep": 5,
                "gridModeEnabled": False,
                "viewBackgroundColor": "#ffffff",
                "currentItemStrokeColor": STROKE_BLACK,
                "currentItemStrokeWidth": 2,
                "currentItemStrokeStyle": "solid",
                "currentItemRoughness": 0,
                "currentItemOpacity": 100,
                "currentItemFillStyle": "solid",
                "currentItemFontFamily": 5,
                "currentItemFontSize": 20,
                "currentItemRoundness": "sharp",
                "lockedMultiSelections": {},
                "fileHandle": None,
            },
            "files": {},
        }

    def save(self, path: str | Path) -> None:
        """Write seed.json to path."""
        Path(path).write_text(json.dumps(self.build(), indent=2))
        print(f"Written: {path}")
