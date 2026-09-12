"""Chart constructors shared by the gallery notebooks and package consumers."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from math import isfinite
from numbers import Real
from typing import Any, NotRequired, TypedDict

import plotly.graph_objects as go

from ..colors import color_with_alpha
from ..figure import ResponsiveFigure
from ..layout import apply_default_design, apply_overrides
from ..theme import Theme

Data = Any


class EventBandDefinition(TypedDict):
    """A vertical time or category range highlighted behind a line chart."""

    start: Any
    end: Any
    label: NotRequired[str]
    opacity: NotRequired[float]
    annotation_position: NotRequired[str]


class AxisBreakDefinition(TypedDict):
    """A numeric y-axis interval to omit while visibly marking the break."""

    start: float
    end: float


def _series_columns(y: str | Sequence[str]) -> list[str]:
    return [y] if isinstance(y, str) else list(y)


def _series_name(column: str, index: int, names: Sequence[str] | None) -> str:
    return names[index] if names else column.replace("_", " ").title()


def _finish(
    fig: go.Figure,
    theme: Theme,
    title: str | None,
    subtitle: str | None,
    source: str | None,
    show_legend: bool = True,
    layout_overrides: dict[str, Any] | None = None,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
) -> go.Figure:
    if theme.responsive:
        fig = ResponsiveFigure(fig)
    return apply_overrides(
        apply_default_design(
            fig,
            theme,
            title=title,
            subtitle=subtitle,
            source=source,
            show_legend=show_legend,
            x_axis_title=x_axis_title,
            y_axis_title=y_axis_title,
        ),
        layout_overrides,
    )


def line_chart(
    data: Data,
    x: str,
    y: str | Sequence[str],
    theme: Theme,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    names: Sequence[str] | None = None,
    event_bands: Sequence[EventBandDefinition] | None = None,
    axis_break: AxisBreakDefinition | None = None,
    layout_overrides: dict[str, Any] | None = None,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
) -> go.Figure:
    """Create one or more line-and-marker series."""
    columns = _series_columns(y)
    fig = go.Figure()
    for index, column in enumerate(columns):
        color = theme.colors.series_palette[index % len(theme.colors.series_palette)]
        fig.add_trace(
            go.Scatter(
                x=data[x],
                y=data[column],
                mode="lines+markers",
                name=_series_name(column, index, names),
                line={"color": color, "width": theme.line_width},
                marker={"color": color, "size": theme.marker_size},
            )
        )
    _add_event_bands(fig, event_bands, theme)
    return _add_y_axis_break(
        _finish(
            fig,
            theme,
            title,
            subtitle,
            source,
            len(columns) > 1,
            layout_overrides,
            x_axis_title,
            y_axis_title,
        ),
        axis_break,
        theme,
        auto=True,
    )


def _add_event_bands(
    figure: go.Figure,
    event_bands: Sequence[EventBandDefinition] | None,
    theme: Theme,
) -> None:
    """Add below-data vertical event bands using the active theme defaults."""
    if event_bands is None:
        return
    for band in event_bands:
        label = band.get("label")
        options: dict[str, Any] = {
            "x0": band["start"],
            "x1": band["end"],
            "fillcolor": theme.event_band.fill_color,
            "opacity": band.get("opacity", theme.event_band.opacity),
            "layer": "below",
            "line_width": 0,
        }
        if label is not None:
            options.update(
                annotation_text=label,
                annotation_position=band.get(
                    "annotation_position", theme.event_band.annotation_position
                ),
                annotation_font_size=theme.event_band.annotation_size,
                annotation_font_color=theme.event_band.annotation_color,
                annotation_font_weight=theme.event_band.annotation_weight,
            )
        figure.add_vrect(**options)


def _add_y_axis_break(
    figure: go.Figure,
    axis_break: AxisBreakDefinition | None,
    theme: Theme,
    *,
    auto: bool = False,
) -> go.Figure:
    """Truncate a numeric y-axis and mark the omission with a Z-shaped path."""
    if axis_break is None and auto:
        axis_break = _automatic_y_axis_break(figure)
    if axis_break is None:
        return figure
    start, end = axis_break["start"], axis_break["end"]
    if start >= end:
        msg = "axis_break.start must be less than axis_break.end."
        raise ValueError(msg)
    figure.update_yaxes(
        range=[end, _axis_break_upper_bound(figure, end)], autorange=False
    )
    figure.add_shape(
        type="path",
        path="M -0.008,0.035 L 0.008,0.027 L -0.008,0.019 L 0.008,0.011",
        xref="paper",
        yref="paper",
        layer="above",
        line={
            "color": theme.colors.text_secondary,
            "width": min(theme.secondary_line_width, 2),
        },
    )
    return figure


def _automatic_y_axis_break(figure: go.Figure) -> AxisBreakDefinition | None:
    """Return a break when Plotly's natural numeric range materially omits zero."""
    values = _numeric_trace_values(figure)
    if not values:
        return None
    minimum, maximum = min(values), max(values)
    span = maximum - minimum
    if minimum <= 0 or span <= 0 or minimum <= max(span * 0.25, 1.0):
        return None
    return {"start": 0, "end": minimum - max(span * 0.06, 1.0)}


def _axis_break_upper_bound(figure: go.Figure, lower_bound: float) -> float:
    """Calculate a stable padded upper y-axis bound from figure traces."""
    candidates = [lower_bound]
    stacked_totals: dict[str, list[float]] = {}
    for trace in figure.data:
        trace_values = trace.y if trace.y is not None else ()
        values = _numeric_values(trace_values)
        stackgroup = getattr(trace, "stackgroup", None)
        if stackgroup:
            totals = stacked_totals.setdefault(stackgroup, [0.0] * len(values))
            for index, value in enumerate(values):
                totals[index] += value
        else:
            candidates.extend(values)
    candidates.extend(value for totals in stacked_totals.values() for value in totals)
    maximum = max(candidates)
    padding = max((maximum - lower_bound) * 0.06, 1.0)
    return maximum + padding


def _numeric_trace_values(figure: go.Figure) -> list[float]:
    """Return finite numeric y-values from all traces in a figure."""
    return [
        value
        for trace in figure.data
        for value in _numeric_values(trace.y if trace.y is not None else ())
    ]


def _numeric_values(values: Sequence[Any]) -> list[float]:
    """Filter a sequence down to finite real numbers."""
    return [
        float(value)
        for value in values
        if isinstance(value, Real) and not isinstance(value, bool) and isfinite(value)
    ]


def bar_chart(
    data: Data,
    x: str,
    y: str,
    theme: Theme,
    *,
    orientation: str = "vertical",
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    sort: bool = False,
    show_values: bool = False,
    focus: str | Collection[str] | None = None,
    layout_overrides: dict[str, Any] | None = None,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
) -> go.Figure:
    """Create a single-series bar chart, optionally emphasizing categories."""
    values = data.sort_values(x if orientation == "horizontal" else y) if sort else data
    horizontal = orientation == "horizontal"
    category, measure = (y, x) if horizontal else (x, y)
    colors = [theme.colors.primary] * len(values)
    if focus is not None:
        focused_categories = {focus} if isinstance(focus, str) else set(focus)
        colors = [
            (
                theme.colors.primary
                if value in focused_categories
                else theme.colors.neutral_light
            )
            for value in values[category]
        ]
    fig = go.Figure(
        go.Bar(
            x=values[measure] if horizontal else values[category],
            y=values[category] if horizontal else values[measure],
            orientation="h" if horizontal else "v",
            marker={"color": colors},
            text=values[measure] if show_values else None,
            textposition="outside" if show_values else None,
            cliponaxis=not show_values,
        )
    )
    if horizontal:
        fig.update_yaxes(ticklabelstandoff=20)
    return _finish(
        fig,
        theme,
        title,
        subtitle,
        source,
        False,
        layout_overrides,
        x_axis_title,
        y_axis_title,
    )


def grouped_bar_chart(
    data: Data, x: str, series: Sequence[str], theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create grouped bars for named value columns."""
    fig = _bar_series(data, x, series, theme)
    fig.update_layout(barmode="group", bargap=0.22, bargroupgap=0.08)
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        True,
        kwargs.get("layout_overrides"),
        kwargs.get("x_axis_title"),
        kwargs.get("y_axis_title"),
    )


def stacked_bar_chart(
    data: Data,
    x: str,
    series: Sequence[str],
    theme: Theme,
    *,
    percent: bool = False,
    y_headroom: float = 108,
    **kwargs: Any,
) -> go.Figure:
    """Create a stacked bar chart, optionally with percentage labels and headroom."""
    fig = _bar_series(data, x, series, theme, labels=percent)
    fig.update_layout(barmode="stack", bargap=0.30)
    if percent:
        fig.update_yaxes(
            range=[0, y_headroom], ticksuffix="%", tickvals=[0, 20, 40, 60, 80, 100]
        )
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        True,
        kwargs.get("layout_overrides"),
        kwargs.get("x_axis_title"),
        kwargs.get("y_axis_title"),
    )


def _bar_series(
    data: Data, x: str, series: Sequence[str], theme: Theme, labels: bool = False
) -> go.Figure:
    fig = go.Figure()
    for index, column in enumerate(series):
        color = theme.colors.series_palette[index % 4]
        fig.add_trace(
            go.Bar(
                x=data[x],
                y=data[column],
                name=column.replace("_", " ").title(),
                marker={"color": color},
                text=data[column] if labels else None,
                texttemplate="%{text:.0f}%" if labels else None,
                textposition="inside" if labels else None,
                textfont={
                    "family": theme.typography.family,
                    "size": theme.typography.annotation_size,
                    "weight": theme.typography.annotation_weight,
                    "color": theme.colors.white,
                },
            )
        )
    return fig


def area_chart(
    data: Data,
    x: str,
    y: str | Sequence[str],
    theme: Theme,
    *,
    names: Sequence[str] | None = None,
    event_bands: Sequence[EventBandDefinition] | None = None,
    axis_break: AxisBreakDefinition | None = None,
    **kwargs: Any,
) -> go.Figure:
    """Create a filled single-series or stacked multi-series area chart."""
    columns = _series_columns(y)
    fig = go.Figure()
    for index, column in enumerate(columns):
        color = theme.colors.series_palette[index % len(theme.colors.series_palette)]
        trace_options: dict[str, Any] = {
            "x": data[x],
            "y": data[column],
            "mode": "lines",
            "name": _series_name(column, index, names),
            "line": {"color": color, "width": theme.line_width},
            "fillcolor": color_with_alpha(color, theme.colors.area_alpha),
        }
        if len(columns) == 1:
            trace_options["fill"] = "tozeroy"
        else:
            trace_options["stackgroup"] = "area"
        fig.add_trace(go.Scatter(**trace_options))
    fig.update_yaxes(rangemode="tozero")
    _add_event_bands(fig, event_bands, theme)
    return _add_y_axis_break(
        _finish(
            fig,
            theme,
            kwargs.get("title"),
            kwargs.get("subtitle"),
            kwargs.get("source"),
            len(columns) > 1,
            kwargs.get("layout_overrides"),
            kwargs.get("x_axis_title"),
            kwargs.get("y_axis_title"),
        ),
        axis_break,
        theme,
    )


def scatter_chart(data: Data, x: str, y: str, theme: Theme, **kwargs: Any) -> go.Figure:
    """Create a primary-color scatter plot."""
    fig = go.Figure(
        go.Scatter(
            x=data[x],
            y=data[y],
            mode="markers",
            marker={
                "size": theme.marker_size + 4,
                "color": theme.colors.primary,
                "opacity": 0.85,
            },
        )
    )
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )


def dot_chart(data: Data, x: str, y: str, theme: Theme, **kwargs: Any) -> go.Figure:
    """Create a categorical dot plot with outside numeric labels."""
    ordered = data.sort_values(x) if kwargs.get("sort", True) else data
    colors = [
        theme.colors.series_palette[index % len(theme.colors.series_palette)]
        for index in range(len(ordered))
    ]
    fig = go.Figure(
        go.Scatter(
            x=ordered[x],
            y=ordered[y],
            mode="markers+text",
            marker={"size": theme.marker_size + 8, "color": colors},
            text=ordered[x],
            texttemplate="%{text:,}",
            textposition="middle right",
            cliponaxis=False,
        )
    )
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )


def donut_chart(
    data: Data, labels: str, values: str, theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create a labeled donut with an optional centre total."""
    fig = go.Figure(
        go.Pie(
            labels=data[labels],
            values=data[values],
            hole=theme.donut_hole,
            sort=False,
            direction="clockwise",
            marker={"colors": theme.colors.series_palette, "line": {"width": 0}},
            textinfo="percent",
            textposition="inside",
            insidetextorientation=theme.donut_text_orientation,
        )
    )
    fig.update_traces(domain={"x": [0.08, 0.68], "y": [0.05, 0.95]})
    fig = _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        True,
        kwargs.get("layout_overrides"),
    )
    fig.update_layout(
        legend={
            "orientation": "v",
            "x": 0.78,
            "xanchor": "left",
            "y": 0.5,
            "yanchor": "middle",
            "font": {
                "family": theme.typography.family,
                "size": theme.typography.legend_size,
                "weight": theme.typography.legend_weight,
                "color": theme.colors.text_primary,
            },
        }
    )
    total = data[values].sum()
    fig.add_annotation(
        text=f"<b>{total:,.0f}</b><br><b>Sessions</b>",
        x=0.38,
        y=0.50,
        xref="paper",
        yref="paper",
        showarrow=False,
        align="center",
        font={
            "family": theme.typography.family,
            "size": theme.typography.title_size,
            "weight": theme.typography.title_weight,
            "color": theme.colors.text_primary,
        },
    )
    return fig


def histogram_chart(data: Data, x: str, theme: Theme, **kwargs: Any) -> go.Figure:
    """Create a primary-color histogram."""
    fig = go.Figure(
        go.Histogram(
            x=data[x],
            nbinsx=kwargs.get("bins", 12),
            marker={"color": theme.colors.primary},
            opacity=0.9,
        )
    )
    fig.update_layout(bargap=0.06)
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )


def box_chart(
    data: Data, category: str, value: str, theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create one styled box trace per category."""
    fig = go.Figure()
    for index, item in enumerate(data[category].unique()):
        color = theme.colors.series_palette[index % 4]
        fig.add_trace(
            go.Box(
                y=data.loc[data[category] == item, value],
                name=item,
                marker={"color": color},
                line={"color": color, "width": 2},
                fillcolor=color,
                opacity=0.75,
                boxpoints="outliers",
            )
        )
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )


def heatmap_chart(
    data: Data,
    x: str,
    y_columns: Sequence[str],
    theme: Theme,
    *,
    title: str | None = None,
    subtitle: str | None = None,
    source: str | None = None,
    mask_zero: bool = False,
    annotate: bool = False,
    value_format: str | None = None,
    contrast_aware: bool = True,
    annotation_contrast_threshold: float | None = None,
    format_labels: bool = False,
    zmin: float | None = None,
    zmax: float | None = None,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
    colorbar_title: str | None = None,
    layout_overrides: dict[str, Any] | None = None,
    **_: Any,
) -> go.Figure:
    """Create a background-to-primary sequential heatmap.

    The dataframe order supplies the x-axis order, while ``y_columns`` supplies
    the y-axis order.  Zero masking and annotations are opt-in so ordinary
    heatmaps retain their existing appearance.
    """
    columns = list(y_columns)
    values = [list(row) for row in data[columns].T.values]
    z_values = (
        [[None if _is_zero_value(value) else value for value in row] for row in values]
        if mask_zero
        else values
    )
    trace_options: dict[str, Any] = {
        "z": z_values,
        "x": _heatmap_labels(data[x], format_labels),
        "y": _heatmap_labels(columns, format_labels),
        "colorscale": theme.colors.sequential_scale,
        "showscale": True,
    }
    if zmin is not None:
        trace_options["zmin"] = zmin
    if zmax is not None:
        trace_options["zmax"] = zmax
    if annotate:
        annotation_text = _heatmap_annotation_text(values, value_format)
        trace_options.update(
            text=annotation_text,
            texttemplate=None if contrast_aware else "%{text}",
            textfont={
                "family": theme.typography.family,
                "size": theme.typography.annotation_size,
                "color": theme.colors.text_primary,
            },
        )
    if colorbar_title is not None or value_format is not None:
        colorbar: dict[str, Any] = {}
        if colorbar_title is not None:
            colorbar["title"] = {
                "text": colorbar_title,
                "font": {
                    "family": theme.typography.family,
                    "size": theme.typography.axis_title_size,
                    "color": theme.colors.text_primary,
                },
            }
        if value_format is not None:
            colorbar["tickformat"] = value_format
        trace_options["colorbar"] = colorbar
    fig = go.Figure(go.Heatmap(**trace_options))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    figure = _finish(
        fig,
        theme,
        title,
        subtitle,
        source,
        False,
        layout_overrides,
        x_axis_title,
        y_axis_title,
    )
    figure.update_yaxes(showgrid=False)
    _separate_heatmap_footer(figure, theme, source, x_axis_title)
    if annotate and contrast_aware:
        _add_heatmap_annotations(
            figure,
            x_values=trace_options["x"],
            y_values=trace_options["y"],
            values=values,
            text=annotation_text,
            theme=theme,
            zmin=zmin,
            zmax=zmax,
            threshold=(
                theme.colors.heatmap_annotation_threshold
                if annotation_contrast_threshold is None
                else annotation_contrast_threshold
            ),
        )
    return figure


def _is_zero_value(value: Any) -> bool:
    """Return whether a heatmap value represents an exact numeric zero."""
    return isinstance(value, Real) and not isinstance(value, bool) and value == 0


def _heatmap_labels(values: Sequence[Any], format_labels: bool) -> list[Any]:
    """Optionally turn source-friendly string categories into display labels."""
    if not format_labels:
        return list(values)
    return [
        value.replace("_", " ").title() if isinstance(value, str) else value
        for value in values
    ]


def _format_heatmap_value(value: Any, value_format: str | None) -> str:
    """Format a numeric heatmap value for a cell annotation."""
    if value_format is None:
        return str(value)
    return format(value, value_format)


def _separate_heatmap_footer(
    figure: go.Figure,
    theme: Theme,
    source: str | None,
    x_axis_title: str | None,
) -> None:
    """Keep a heatmap's source clear of its category labels and x-axis title."""
    if source is None or x_axis_title is None:
        return
    footer_margin = max(
        theme.margin.bottom,
        theme.typography.tick_size * 9
        + theme.typography.axis_title_size
        + theme.typography.source_size,
    )
    figure.update_layout(margin={"b": footer_margin})
    figure.update_xaxes(title_standoff=24)
    source_text = f"Source: {source}"
    for annotation in figure.layout.annotations:
        if annotation.text == source_text:
            annotation.y = -0.45
            break


def _heatmap_annotation_text(
    values: Sequence[Sequence[Any]], value_format: str | None
) -> list[list[str]]:
    """Precompute display text while retaining numeric z-values for hover."""
    return [
        [
            "" if _is_zero_value(value) else _format_heatmap_value(value, value_format)
            for value in row
        ]
        for row in values
    ]


def _add_heatmap_annotations(
    figure: go.Figure,
    *,
    x_values: Sequence[Any],
    y_values: Sequence[Any],
    values: Sequence[Sequence[Any]],
    text: Sequence[Sequence[str]],
    theme: Theme,
    zmin: float | None,
    zmax: float | None,
    threshold: float,
) -> None:
    """Add per-cell annotation colors based on normalized heatmap intensity."""
    if not 0 <= threshold <= 1:
        msg = "annotation_contrast_threshold must be between 0 and 1."
        raise ValueError(msg)
    numeric_values = [value for row in values for value in _numeric_values(row)]
    if not numeric_values:
        return
    lower_bound = min(numeric_values) if zmin is None else zmin
    upper_bound = max(numeric_values) if zmax is None else zmax
    scale_span = upper_bound - lower_bound
    for y_value, row, text_row in zip(y_values, values, text, strict=True):
        for x_value, value, label in zip(x_values, row, text_row, strict=True):
            if not label or not isinstance(value, Real) or isinstance(value, bool):
                continue
            intensity = (
                0 if scale_span <= 0 else (float(value) - lower_bound) / scale_span
            )
            color = (
                theme.colors.heatmap_annotation_dark
                if intensity >= threshold
                else theme.colors.heatmap_annotation_light
            )
            figure.add_annotation(
                x=x_value,
                y=y_value,
                text=label,
                showarrow=False,
                font={
                    "family": theme.typography.family,
                    "size": theme.typography.annotation_size,
                    "color": color,
                },
            )


def waterfall_chart(
    data: Data, x: str, y: str, measure: str, theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create a waterfall using semantic positive, negative, and total colors."""
    fig = go.Figure(
        go.Waterfall(
            x=data[x],
            y=data[y],
            measure=data[measure],
            increasing={"marker": {"color": theme.colors.primary}},
            decreasing={"marker": {"color": theme.colors.neutral}},
            totals={"marker": {"color": theme.colors.neutral_strong}},
            connector={"line": {"color": theme.colors.grid}},
        )
    )
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )


def gauge_chart(value: float, target: float, theme: Theme, **kwargs: Any) -> go.Figure:
    """Create a bullet gauge with derived primary-color qualitative bands."""
    light, medium = theme.colors.gauge_steps
    fig = go.Figure(
        go.Indicator(
            mode="number+gauge",
            value=value,
            number={"suffix": "%"},
            gauge={
                "shape": "bullet",
                "axis": {"range": [0, 100], "ticksuffix": "%"},
                "bar": {"color": theme.colors.primary},
                "steps": [
                    {"range": [0, 60], "color": theme.colors.neutral_light},
                    {"range": [60, 80], "color": light},
                    {"range": [80, 100], "color": medium},
                ],
                "threshold": {
                    "line": {
                        "color": theme.colors.neutral_strong,
                        "width": theme.line_width,
                    },
                    "value": target,
                },
            },
        )
    )
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )


def slope_chart(
    data: Data, start: str, end: str, category: str, theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create a category-to-category slope chart."""
    fig = go.Figure()
    for index, (_, row) in enumerate(data.iterrows()):
        color = theme.colors.series_palette[index % 4]
        fig.add_trace(
            go.Scatter(
                x=[start.title(), end.title()],
                y=[row[start], row[end]],
                mode="lines+markers",
                line={"color": color, "width": theme.line_width},
                marker={"color": color, "size": theme.marker_size + 2},
                name=row[category],
                showlegend=False,
            )
        )
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )


def dumbbell_chart(
    data: Data, category: str, start: str, end: str, theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create paired markers joined by neutral connector lines."""
    fig = go.Figure()
    for _, row in data.iterrows():
        fig.add_trace(
            go.Scatter(
                x=[row[start], row[end]],
                y=[row[category], row[category]],
                mode="lines",
                line={
                    "color": theme.colors.neutral_light,
                    "width": theme.secondary_line_width,
                },
                showlegend=False,
            )
        )
    for column, color in ((start, theme.colors.neutral), (end, theme.colors.primary)):
        fig.add_trace(
            go.Scatter(
                x=data[column],
                y=data[category],
                mode="markers",
                name=column.title(),
                marker={"size": theme.marker_size + 5, "color": color},
            )
        )
    fig.update_yaxes(ticklabelstandoff=20)
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        True,
        kwargs.get("layout_overrides"),
    )


def range_bar_chart(
    data: Data, category: str, low: str, high: str, theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create horizontal forecast ranges from low to high values."""
    ordered = data.sort_values(high)
    fig = go.Figure(
        go.Bar(
            x=ordered[high] - ordered[low],
            y=ordered[category],
            orientation="h",
            base=ordered[low],
            marker={"color": theme.colors.primary},
            showlegend=False,
        )
    )
    fig.update_yaxes(ticklabelstandoff=20)
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )


def combo_chart(
    data: Data, x: str, bar: str, line: str, theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create a bar and secondary-axis line combination chart."""
    fig = go.Figure(
        go.Bar(
            x=data[x],
            y=data[bar],
            name=bar.replace("_", " ").title(),
            marker={"color": theme.colors.primary},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data[x],
            y=data[line],
            name=line.replace("_", " ").title(),
            yaxis="y2",
            mode="lines+markers",
            line={"color": theme.colors.secondary, "width": theme.line_width},
        )
    )
    figure = _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        True,
        kwargs.get("layout_overrides"),
        kwargs.get("x_axis_title"),
        kwargs.get("y_axis_title"),
    )
    figure.update_layout(
        yaxis2={
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
            "tickformat": ".1f",
            "title_text": kwargs.get("secondary_y_axis_title"),
            "title_font": {
                "family": theme.typography.family,
                "size": theme.typography.axis_title_size,
                "weight": theme.typography.axis_title_weight,
                "color": theme.colors.text_primary,
            },
            "tickfont": {
                "family": theme.typography.family,
                "size": theme.typography.tick_size,
                "weight": theme.typography.tick_weight,
                "color": theme.colors.text_secondary,
            },
            "automargin": kwargs.get("secondary_y_axis_title") is not None,
        }
    )
    return figure


def kpi_cards(
    metrics: Sequence[dict[str, Any]], theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create the notebook's two-row, four-column KPI card arrangement."""
    fig = _finish(
        go.Figure(),
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
    )
    for index, metric in enumerate(metrics):
        x, y = (0.02 + (index % 4) * 0.25, 0.72 - (index // 4) * 0.44)
        change = (metric["value"] - metric["previous"]) / metric["previous"]
        for text, offset, size, color in (
            (
                metric["label"],
                0.16,
                theme.typography.subtitle_size,
                theme.colors.text_secondary,
            ),
            (
                f"<b>{metric['format'].format(metric['value'])}</b>",
                0,
                theme.typography.title_size,
                theme.colors.text_primary,
            ),
            (
                f"<b>{change:+.1%}</b> vs. prior week",
                -0.17,
                theme.typography.annotation_size,
                theme.colors.primary if change >= 0 else theme.colors.neutral,
            ),
        ):
            fig.add_annotation(
                x=x,
                y=y + offset,
                xref="paper",
                yref="paper",
                text=text,
                xanchor="left",
                showarrow=False,
                font={"family": theme.typography.family, "size": size, "color": color},
            )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig
