"""Shared Plotly layout construction."""
# ruff: noqa: PLR0913, PLR0917

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from .theme import Theme


def apply_default_design(
    figure: go.Figure,
    theme: Theme,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    show_legend: bool = True,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
) -> go.Figure:
    """Apply shared canvas, axes, annotations, and legend design."""
    typography = theme.typography
    colors = theme.colors
    figure.update_layout(
        width=None if theme.responsive else theme.width,
        height=theme.height,
        autosize=theme.responsive,
        paper_bgcolor=colors.background,
        plot_bgcolor=colors.plot_background,
        margin={
            "l": theme.margin.left,
            "r": theme.margin.right,
            "t": theme.margin.top,
            "b": theme.margin.bottom,
        },
        font={
            "family": typography.family,
            "size": typography.tick_size,
            "weight": typography.tick_weight,
            "color": colors.text_primary,
        },
        showlegend=show_legend,
        hovermode=theme.hover_mode,
        bargap=theme.bar_gap,
        legend={
            "orientation": "h",
            "x": 0,
            "xanchor": "left",
            "y": theme.legend_y,
            "yanchor": "bottom" if theme.responsive else "top",
            "maxheight": 0.12 if theme.responsive else None,
            "font": {
                "family": typography.family,
                "size": typography.legend_size,
                "weight": typography.legend_weight,
                "color": colors.text_primary,
            },
        },
    )
    figure.update_xaxes(
        showgrid=False,
        showline=False,
        zeroline=False,
        ticks="",
        title_font={
            "family": typography.family,
            "size": typography.axis_title_size,
            "weight": typography.axis_title_weight,
            "color": colors.text_primary,
        },
        tickfont={
            "family": typography.family,
            "size": typography.tick_size,
            "weight": typography.tick_weight,
            "color": colors.text_secondary,
        },
        automargin=theme.responsive,
    )
    figure.update_yaxes(
        showgrid=True,
        gridcolor=colors.grid,
        gridwidth=1,
        showline=False,
        zeroline=False,
        zerolinecolor=colors.zero_line,
        ticks="",
        title_font={
            "family": typography.family,
            "size": typography.axis_title_size,
            "weight": typography.axis_title_weight,
            "color": colors.text_primary,
        },
        tickfont={
            "family": typography.family,
            "size": typography.tick_size,
            "weight": typography.tick_weight,
            "color": colors.text_secondary,
        },
        automargin=theme.responsive,
    )
    apply_axis_titles(
        figure, theme, x_axis_title=x_axis_title, y_axis_title=y_axis_title
    )
    if title:
        if theme.show_title_accent:
            figure.add_shape(
                type="rect",
                xref="paper",
                yref="paper",
                x0=0,
                x1=theme.accent_x_end,
                y0=theme.accent_y_start,
                y1=theme.accent_y_end,
                line={"width": 0},
                fillcolor=colors.primary,
            )
        _annotation(
            figure,
            title,
            0,
            theme.title_y,
            theme,
            typography.title_size,
            typography.title_weight,
            colors.text_primary,
        )
    if subtitle:
        _annotation(
            figure,
            subtitle,
            0,
            theme.subtitle_y,
            theme,
            typography.subtitle_size,
            typography.subtitle_weight,
            colors.text_secondary,
        )
    if source:
        _annotation(
            figure,
            f"Source: {source}",
            0,
            theme.source_y,
            theme,
            typography.source_size,
            typography.source_weight,
            colors.text_muted,
        )
    return figure


def apply_axis_titles(
    figure: go.Figure,
    theme: Theme,
    *,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
    secondary_y_axis_title: str | None = None,
) -> go.Figure:
    """Add optional axis titles using responsive or fixed-gutter positioning."""
    if x_axis_title is not None:
        figure.update_xaxes(title_text=x_axis_title)
    if y_axis_title is not None:
        if theme.responsive:
            figure.update_yaxes(title_text=y_axis_title, automargin=True)
            return figure
        figure.update_yaxes(title_text=None)
        if not any(
            annotation.text == y_axis_title and annotation.textangle == -90
            for annotation in figure.layout.annotations
        ):
            plot_width = theme.width - theme.margin.left - theme.margin.right
            title_x = (theme.axis_title_gutter - theme.margin.left) / plot_width
            figure.add_annotation(
                text=y_axis_title,
                x=title_x,
                y=0.5,
                xref="paper",
                yref="paper",
                xanchor="center",
                yanchor="middle",
                textangle=-90,
                showarrow=False,
                font={
                    "family": theme.typography.family,
                    "size": theme.typography.axis_title_size,
                    "weight": theme.typography.axis_title_weight,
                    "color": theme.colors.text_primary,
                },
            )
    if secondary_y_axis_title is not None:
        figure.update_layout(yaxis2={"title_text": secondary_y_axis_title})
    return figure


def _annotation(
    figure: go.Figure,
    text: str,
    x: float,
    y: float,
    theme: Theme,
    size: int,
    weight: int,
    color: str,
) -> None:
    figure.add_annotation(
        text=text,
        x=x,
        y=y,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        showarrow=False,
        align="left",
        font={
            "family": theme.typography.family,
            "size": size,
            "weight": weight,
            "color": color,
        },
    )


def apply_overrides(
    figure: go.Figure, layout_overrides: dict[str, Any] | None
) -> go.Figure:
    """Apply optional advanced layout overrides after the theme."""
    if layout_overrides:
        figure.update_layout(**layout_overrides)
    return figure
