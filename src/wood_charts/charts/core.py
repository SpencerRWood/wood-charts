"""Chart constructors shared by the gallery notebooks and package consumers."""

from __future__ import annotations

from collections.abc import Collection, Sequence
from typing import Any, NotRequired, TypedDict

import plotly.graph_objects as go

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
    layout_overrides: dict[str, Any] | None = None,
    x_axis_title: str | None = None,
    y_axis_title: str | None = None,
) -> go.Figure:
    """Create one or more line-and-marker series."""
    columns = [y] if isinstance(y, str) else list(y)
    fig = go.Figure()
    for index, column in enumerate(columns):
        color = theme.colors.series_palette[index % len(theme.colors.series_palette)]
        fig.add_trace(
            go.Scatter(
                x=data[x],
                y=data[column],
                mode="lines+markers",
                name=(names[index] if names else str(column).replace("_", " ").title()),
                line={"color": color, "width": theme.line_width},
                marker={"color": color, "size": theme.marker_size},
            )
        )
    _add_event_bands(fig, event_bands, theme)
    return _finish(
        fig,
        theme,
        title,
        subtitle,
        source,
        len(columns) > 1,
        layout_overrides,
        x_axis_title,
        y_axis_title,
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


def area_chart(data: Data, x: str, y: str, theme: Theme, **kwargs: Any) -> go.Figure:
    """Create a filled primary-series area chart."""
    fig = go.Figure(
        go.Scatter(
            x=data[x],
            y=data[y],
            mode="lines",
            name=y.replace("_", " ").title(),
            line={"color": theme.colors.primary, "width": theme.line_width},
            fill="tozeroy",
            fillcolor=theme.colors.primary_area,
        )
    )
    fig.update_yaxes(rangemode="tozero")
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
        kwargs.get("x_axis_title"),
        kwargs.get("y_axis_title"),
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
    data: Data, x: str, y_columns: Sequence[str], theme: Theme, **kwargs: Any
) -> go.Figure:
    """Create a background-to-primary sequential heatmap."""
    fig = go.Figure(
        go.Heatmap(
            z=data[list(y_columns)].T.values,
            x=data[x],
            y=list(y_columns),
            colorscale=theme.colors.sequential_scale,
            showscale=True,
        )
    )
    fig.update_yaxes(autorange="reversed", showgrid=False)
    return _finish(
        fig,
        theme,
        kwargs.get("title"),
        kwargs.get("subtitle"),
        kwargs.get("source"),
        False,
        kwargs.get("layout_overrides"),
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
