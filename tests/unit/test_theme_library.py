"""Tests for the public YAML-theme and chart interfaces."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import pytest

from wood_charts import Theme, ThemeConfigurationError, load_theme
from wood_charts.charts import (
    area_chart,
    bar_chart,
    combo_chart,
    donut_chart,
    gauge_chart,
    heatmap_chart,
    line_chart,
    range_bar_chart,
    stacked_bar_chart,
)
from wood_charts.colors import blend_color, color_with_alpha, hex_to_rgb


@pytest.mark.parametrize(
    ("name", "dimensions"),
    [
        ("powerpoint_2_1", (1600, 800)),
        ("powerpoint_16_9", (1600, 900)),
        ("latex_3_2", (1200, 800)),
        ("notebook", (960, 600)),
    ],
)
def test_bundled_themes_resolve_inherited_dimensions(
    name: str, dimensions: tuple[int, int]
) -> None:
    theme = load_theme(name)
    assert (theme.width, theme.height) == dimensions
    assert theme.colors.primary_area == "rgba(0, 47, 108, 0.2)"


def test_color_utilities_and_derived_palette() -> None:
    theme = load_theme("powerpoint_2_1")
    assert hex_to_rgb("#002F6C") == (0, 47, 108)
    assert color_with_alpha("#002F6C", 0.5) == "rgba(0, 47, 108, 0.5)"
    assert blend_color("#000000", "#FFFFFF", 0.5) == "#808080"
    assert theme.colors.sequential_scale[-1][1] == theme.colors.primary
    assert theme.colors.gauge_steps[0] != theme.colors.primary
    assert theme.colors.series_palette == (
        theme.colors.primary,
        theme.colors.secondary,
        theme.colors.neutral_strong,
        theme.colors.neutral,
    )


def test_powerpoint_2_1_reserves_header_space_for_titles() -> None:
    theme = load_theme("powerpoint_2_1")
    assert theme.margin.top == 197


def test_notebook_theme_uses_compact_tokens_for_interactive_output() -> None:
    notebook = load_theme("notebook")
    base = load_theme("powerpoint_2_1")
    assert (
        notebook.margin.left,
        notebook.margin.right,
        notebook.margin.top,
        notebook.margin.bottom,
    ) == (110, 60, 95, 80)
    assert notebook.typography.title_size < base.typography.title_size
    assert notebook.typography.tick_size < base.typography.tick_size
    assert notebook.line_width < base.line_width
    assert notebook.secondary_line_width < base.secondary_line_width
    assert notebook.marker_size < base.marker_size
    assert notebook.responsive is True
    assert notebook.show_title_accent is False


def test_notebook_theme_creates_responsive_figures() -> None:
    theme = load_theme("notebook")
    figure = line_chart(
        pd.DataFrame({"month": ["Jan"], "sessions": [4]}),
        "month",
        "sessions",
        theme,
    )
    assert figure.layout.width is None
    assert figure.layout.height == 600
    assert figure.layout.autosize is True


def test_line_chart_has_no_event_bands_by_default() -> None:
    figure = line_chart(
        pd.DataFrame({"day": [1, 2], "sessions": [4, 5]}),
        "day",
        "sessions",
        load_theme("notebook"),
    )
    assert not figure.layout.shapes
    assert not figure.layout.annotations


def test_line_chart_adds_a_labeled_event_band_using_theme_defaults() -> None:
    theme = load_theme("notebook")
    figure = line_chart(
        pd.DataFrame({"day": [1, 2], "sessions": [4, 5]}),
        "day",
        "sessions",
        theme,
        event_bands=[{"start": 1, "end": 1.5, "label": "Campaign"}],
    )
    band = figure.layout.shapes[0]
    annotation = figure.layout.annotations[0]
    assert (band.x0, band.x1) == (1, 1.5)
    assert band.fillcolor == theme.event_band.fill_color
    assert band.opacity == theme.event_band.opacity
    assert band.layer == "below"
    assert band.line.width == 0
    assert annotation.text == "Campaign"
    assert annotation.font.size == theme.event_band.annotation_size
    assert annotation.font.color == theme.event_band.annotation_color
    assert annotation.font.weight == theme.event_band.annotation_weight


def test_line_chart_adds_multiple_event_bands_with_overrides() -> None:
    theme = load_theme("notebook")
    figure = line_chart(
        pd.DataFrame({"day": [1, 2, 3], "sessions": [4, 5, 6]}),
        "day",
        "sessions",
        theme,
        event_bands=[
            {"start": 1, "end": 1.5, "label": "Launch"},
            {
                "start": 2,
                "end": 2.5,
                "label": "Sale",
                "opacity": 0.30,
                "annotation_position": "bottom right",
            },
        ],
    )
    assert len(figure.layout.shapes) == 2
    assert tuple(band.opacity for band in figure.layout.shapes) == (
        theme.event_band.opacity,
        0.30,
    )
    assert tuple(annotation.text for annotation in figure.layout.annotations) == (
        "Launch",
        "Sale",
    )
    assert figure.layout.annotations[1].xanchor == "right"
    assert figure.layout.annotations[1].yanchor == "bottom"


def test_notebook_theme_omits_the_title_accent() -> None:
    figure = line_chart(
        pd.DataFrame({"month": ["Jan"], "sessions": [4]}),
        "month",
        "sessions",
        load_theme("notebook"),
        title="Sessions",
    )
    assert not figure.layout.shapes


def test_notebook_theme_keeps_source_captions_inside_the_bottom_margin() -> None:
    figure = line_chart(
        pd.DataFrame({"month": ["Jan"], "sessions": [4]}),
        "month",
        "sessions",
        load_theme("notebook"),
        source="Analytics platform",
    )
    source = figure.layout.annotations[0]
    assert source.text == "Source: Analytics platform"
    assert source.y == -0.13


def test_notebook_theme_uses_auto_margin_for_axis_titles() -> None:
    figure = bar_chart(
        pd.DataFrame({"event_type": ["page_view"], "event_count": [1]}),
        "event_count",
        "event_type",
        load_theme("notebook"),
        orientation="horizontal",
        x_axis_title="Count",
        y_axis_title="Event Type",
    )
    assert figure.layout.xaxis.automargin is True
    assert figure.layout.yaxis.automargin is True
    assert figure.layout.yaxis.title.text == "Event Type"
    assert not any(
        annotation.text == "Event Type" for annotation in figure.layout.annotations
    )


def test_notebook_theme_enables_responsive_show_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def show_stub(*_args: object, **kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(pio, "show", show_stub)
    figure = line_chart(
        pd.DataFrame({"month": ["Jan"], "sessions": [4]}),
        "month",
        "sessions",
        load_theme("notebook"),
    )
    figure.show()
    assert captured["config"] == {"responsive": True}


def test_bar_chart_uses_primary_bars_and_can_focus_a_category() -> None:
    theme = load_theme("notebook")
    data = pd.DataFrame(
        {"event_type": ["page_view", "purchase"], "event_count": [10, 2]}
    )
    default = bar_chart(
        data, "event_count", "event_type", theme, orientation="horizontal"
    )
    focused = bar_chart(
        data,
        "event_count",
        "event_type",
        theme,
        orientation="horizontal",
        focus="purchase",
    )
    multiple_focused = bar_chart(
        data,
        "event_count",
        "event_type",
        theme,
        orientation="horizontal",
        focus=["page_view", "purchase"],
    )
    assert default.data[0].marker.color == (theme.colors.primary,) * 2
    assert focused.data[0].marker.color == (
        theme.colors.neutral_light,
        theme.colors.primary,
    )
    assert multiple_focused.data[0].marker.color == (theme.colors.primary,) * 2


def test_themes_reserve_horizontal_space_for_axis_titles() -> None:
    assert load_theme("powerpoint_2_1").margin.left == 190
    assert load_theme("powerpoint_16_9").margin.right == 190
    assert load_theme("latex_3_2").margin.left == 190
    assert load_theme("powerpoint_2_1").margin.bottom == 160
    assert load_theme("powerpoint_2_1").axis_title_gutter == 32


def test_invalid_theme_reports_clear_error(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("canvas: {width: 0}\n")
    with pytest.raises(ThemeConfigurationError, match=r"missing|required|positive"):
        load_theme(path)


def test_custom_theme_deep_merges_parent(tmp_path: Path) -> None:
    parent = tmp_path / "parent.yaml"
    parent.write_text(
        (Path(__file__).parents[2] / "src/wood_charts/themes/base.yaml").read_text()
    )
    child = tmp_path / "child.yaml"
    child.write_text("extends: parent.yaml\ncolors:\n  primary: '#009B4E'\n")
    theme = load_theme(child)
    assert theme.colors.primary == "#009B4E"
    assert theme.colors.secondary == "#4A90C2"
    assert theme.colors.primary_area == "rgba(0, 155, 78, 0.2)"


@pytest.mark.parametrize(
    ("factory", "trace_type"),
    [
        (
            lambda theme: line_chart(
                pd.DataFrame({"x": [1, 2], "y": [3, 4]}), "x", "y", theme
            ),
            "scatter",
        ),
        (
            lambda theme: bar_chart(
                pd.DataFrame({"x": ["A"], "y": [3]}), "x", "y", theme
            ),
            "bar",
        ),
        (
            lambda theme: area_chart(
                pd.DataFrame({"x": [1, 2], "y": [3, 4]}), "x", "y", theme
            ),
            "scatter",
        ),
        (
            lambda theme: heatmap_chart(
                pd.DataFrame({"hour": ["AM"], "Mon": [3]}), "hour", ["Mon"], theme
            ),
            "heatmap",
        ),
        (lambda theme: gauge_chart(82, 90, theme), "indicator"),
        (
            lambda theme: combo_chart(
                pd.DataFrame({"month": ["Jan"], "sessions": [3], "rate": [4]}),
                "month",
                "sessions",
                "rate",
                theme,
            ),
            "bar",
        ),
    ],
)
def test_chart_functions_return_styled_figures(
    factory: Callable[[Theme], go.Figure], trace_type: str
) -> None:
    theme = load_theme("powerpoint_16_9")
    figure = factory(theme)
    assert isinstance(figure, go.Figure)
    assert figure.data[0].type == trace_type
    assert (figure.layout.width, figure.layout.height) == (theme.width, theme.height)


def test_stacked_percent_range_and_area_fill() -> None:
    theme = load_theme("powerpoint_2_1")
    data = pd.DataFrame({"month": ["Jan"], "organic": [60], "direct": [40]})
    stacked = stacked_bar_chart(
        data, "month", ["organic", "direct"], theme, percent=True
    )
    area = area_chart(
        pd.DataFrame({"week": ["Jan"], "sessions": [4]}), "week", "sessions", theme
    )
    assert stacked.layout.yaxis.range == (0, 108)
    assert area.data[0].fillcolor == theme.colors.primary_area


def test_donut_total_and_range_bar_use_semantic_solid_colors() -> None:
    theme = load_theme("powerpoint_2_1")
    donut = donut_chart(
        pd.DataFrame({"channel": ["Organic", "Direct"], "sessions": [1240, 950]}),
        "channel",
        "sessions",
        theme,
    )
    range_chart = range_bar_chart(
        pd.DataFrame({"channel": ["Organic"], "low": [980], "high": [1280]}),
        "channel",
        "low",
        "high",
        theme,
    )
    assert any("2,190" in annotation.text for annotation in donut.layout.annotations)
    assert donut.data[0].hole == 0.5
    assert donut.data[0].insidetextorientation == "horizontal"
    assert range_chart.data[0].marker.color == theme.colors.primary


def test_donut_label_orientation_defaults_to_auto_outside_2_1() -> None:
    assert load_theme("powerpoint_16_9").donut_text_orientation == "auto"
    assert load_theme("latex_3_2").donut_text_orientation == "auto"


def test_axis_titles_are_optional_and_combo_values_use_one_decimal() -> None:
    theme = load_theme("powerpoint_2_1")
    line = line_chart(
        pd.DataFrame({"week": ["Jan"], "sessions": [4]}),
        "week",
        "sessions",
        theme,
        x_axis_title="Week",
        y_axis_title="Sessions",
    )
    combo = combo_chart(
        pd.DataFrame({"month": ["Jan"], "sessions": [4], "rate": [4.25]}),
        "month",
        "sessions",
        "rate",
        theme,
        secondary_y_axis_title="Conversion rate",
    )
    assert line.layout.xaxis.title.text == "Week"
    assert line.layout.yaxis.title.text is None
    assert any(annotation.text == "Sessions" for annotation in line.layout.annotations)
    assert combo.layout.yaxis2.tickformat == ".1f"
    assert combo.layout.yaxis2.title.text == "Conversion rate"


def test_fixed_theme_margins_are_preserved_with_axis_titles() -> None:
    theme = load_theme("powerpoint_2_1")
    figure = bar_chart(
        pd.DataFrame({"channel": ["Organic"], "sessions": [1240]}),
        "sessions",
        "channel",
        theme,
        orientation="horizontal",
        x_axis_title="Sessions",
        y_axis_title="Acquisition channel",
    )
    assert figure.layout.margin.l == theme.margin.left
    assert figure.layout.margin.r == theme.margin.right
    assert figure.layout.margin.b == theme.margin.bottom


def test_horizontal_charts_separate_category_labels_from_the_plot() -> None:
    theme = load_theme("powerpoint_2_1")
    figure = bar_chart(
        pd.DataFrame({"channel": ["Organic"], "sessions": [1240]}),
        "sessions",
        "channel",
        theme,
        orientation="horizontal",
    )
    assert figure.layout.yaxis.ticklabelstandoff == 20
