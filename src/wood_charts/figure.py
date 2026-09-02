"""Figure specializations used by theme-aware chart constructors."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go


class ResponsiveFigure(go.Figure):  # type: ignore[misc]
    """A Plotly figure that enables browser resize handling when shown."""

    def show(self, *args: Any, **kwargs: Any) -> Any:
        config = kwargs.pop("config", {}) or {}
        return super().show(*args, config={"responsive": True, **config}, **kwargs)
