from __future__ import annotations

from collections import defaultdict

from .models import PointPrompt


class PointStore:
    """Undoable collection of positive and negative prompts."""

    def __init__(self) -> None:
        self._points: list[PointPrompt] = []
        self._redo: list[PointPrompt] = []

    def add(self, point: PointPrompt) -> None:
        self._points.append(point)
        self._redo.clear()

    def undo(self) -> PointPrompt | None:
        if not self._points:
            return None
        point = self._points.pop()
        self._redo.append(point)
        return point

    def redo(self) -> PointPrompt | None:
        if not self._redo:
            return None
        point = self._redo.pop()
        self._points.append(point)
        return point

    def clear_frame(self, frame: int) -> None:
        removed = [point for point in self._points if point.frame == frame]
        self._points = [point for point in self._points if point.frame != frame]
        self._redo.extend(reversed(removed))

    def clear(self) -> None:
        self._redo.extend(reversed(self._points))
        self._points.clear()

    def for_frame(self, frame: int) -> tuple[PointPrompt, ...]:
        return tuple(point for point in self._points if point.frame == frame)

    def by_frame(self) -> dict[int, tuple[PointPrompt, ...]]:
        grouped: dict[int, list[PointPrompt]] = defaultdict(list)
        for point in self._points:
            grouped[point.frame].append(point)
        return {frame: tuple(points) for frame, points in grouped.items()}

    def all(self) -> tuple[PointPrompt, ...]:
        return tuple(self._points)

    @property
    def can_undo(self) -> bool:
        return bool(self._points)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

