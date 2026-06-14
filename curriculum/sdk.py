"""sdk.py — Excalidraw grading helpers."""

from __future__ import annotations

from typing import Any


class ExcalidrawElement:
    """Wrapper around an Excalidraw element."""

    def __init__(self, data: dict[str, Any]):
        self._data = data

    @property
    def type(self) -> str:
        return self._data.get("type", "")

    @property
    def id(self) -> str:
        return self._data.get("id", "")

    @property
    def x(self) -> float:
        return self._data.get("x", 0)

    @property
    def y(self) -> float:
        return self._data.get("y", 0)

    @property
    def width(self) -> float:
        return self._data.get("width", 0)

    @property
    def height(self) -> float:
        return self._data.get("height", 0)

    @property
    def background_color(self) -> str:
        return self._data.get("backgroundColor", "")

    @property
    def stroke_color(self) -> str:
        return self._data.get("strokeColor", "")

    @property
    def fill_style(self) -> str:
        return self._data.get("fillStyle", "")

    @property
    def stroke_width(self) -> float:
        return self._data.get("strokeWidth", 0)

    @property
    def stroke_style(self) -> str:
        return self._data.get("strokeStyle", "")

    @property
    def opacity(self) -> float:
        return self._data.get("opacity", 100)

    @property
    def text(self) -> str:
        return self._data.get("text", "")

    @property
    def angle(self) -> float:
        return self._data.get("angle", 0)

    @property
    def group_ids(self) -> list[str]:
        return self._data.get("groupIds", []) or []

    @property
    def frame_id(self) -> str | None:
        return self._data.get("frameId")

    @property
    def container_id(self) -> str | None:
        return self._data.get("containerId")

    @property
    def bound_elements(self) -> list[dict[str, Any]]:
        return self._data.get("boundElements", []) or []

    @property
    def start_binding(self) -> dict[str, Any] | None:
        return self._data.get("startBinding")

    @property
    def end_binding(self) -> dict[str, Any] | None:
        return self._data.get("endBinding")

    @property
    def points(self) -> list[list[float]]:
        return self._data.get("points", []) or []

    @property
    def index(self) -> str:
        """Excalidraw fractional index — sorts lexicographically by stacking order
        (lowest = back, highest = front)."""
        return self._data.get("index", "")

    @property
    def center_x(self) -> float:
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2

    def is_rectangle(self) -> bool:
        return self.type == "rectangle"

    def is_ellipse(self) -> bool:
        return self.type == "ellipse"

    def is_diamond(self) -> bool:
        return self.type == "diamond"

    def is_arrow(self) -> bool:
        return self.type == "arrow"

    def is_line(self) -> bool:
        return self.type == "line"

    def is_text(self) -> bool:
        return self.type == "text"

    def has_background_color(self, hex_color: str) -> bool:
        return self.background_color.lower() == hex_color.lower()

    def has_stroke_color(self, hex_color: str) -> bool:
        return self.stroke_color.lower() == hex_color.lower()

    def is_within(self, other: "ExcalidrawElement") -> bool:
        """Return True if this element is fully contained within other."""
        return (
            self.x >= other.x
            and self.y >= other.y
            and self.x + self.width <= other.x + other.width
            and self.y + self.height <= other.y + other.height
        )

    def overlaps(self, other: "ExcalidrawElement") -> bool:
        """Return True if this element's bounding box intersects other's.

        Edge-touching (shared boundary, zero-area overlap) is NOT counted as
        overlap, so two rectangles placed exactly side by side are allowed.
        """
        return (
            self.x < other.x + other.width
            and self.x + self.width > other.x
            and self.y < other.y + other.height
            and self.y + self.height > other.y
        )

    def distance_to(self, other: "ExcalidrawElement") -> float:
        """Euclidean distance between the two elements' centers."""
        dx = self.center_x - other.center_x
        dy = self.center_y - other.center_y
        return (dx * dx + dy * dy) ** 0.5


class ExcalidrawProject:
    """Wrapper for an Excalidraw project snapshot."""

    def __init__(self, data: dict[str, Any]):
        self._elements = [
            ExcalidrawElement(el)
            for el in data.get("elements", [])
            if not el.get("isDeleted", False)
        ]

    def get_rectangles(self) -> list[ExcalidrawElement]:
        return [el for el in self._elements if el.is_rectangle()]

    def get_ellipses(self) -> list[ExcalidrawElement]:
        return [el for el in self._elements if el.is_ellipse()]

    def get_diamonds(self) -> list[ExcalidrawElement]:
        return [el for el in self._elements if el.is_diamond()]

    def get_arrows(self) -> list[ExcalidrawElement]:
        return [el for el in self._elements if el.is_arrow()]

    def get_lines(self) -> list[ExcalidrawElement]:
        return [el for el in self._elements if el.is_line()]

    def get_texts(self) -> list[ExcalidrawElement]:
        return [el for el in self._elements if el.is_text()]

    def all_elements(self) -> list[ExcalidrawElement]:
        return list(self._elements)

    def get_by_id(self, element_id: str) -> ExcalidrawElement | None:
        for el in self._elements:
            if el.id == element_id:
                return el
        return None
