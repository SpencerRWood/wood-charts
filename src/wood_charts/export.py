"""Static figure export helpers."""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from .theme import Theme


def export_chart(
    figure: go.Figure, path: str | Path, *, theme: Theme | None = None
) -> None:
    """Export a figure using theme dimensions and transparent SVG backgrounds."""
    options = {} if theme is None else {"width": theme.width, "height": theme.height}
    destination = Path(path)
    if destination.suffix.lower() == ".svg":
        svg_figure = go.Figure(figure)
        svg_figure.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
        )
        svg_figure.write_image(str(destination), **options)
        return
    figure.write_image(str(destination), **options)
