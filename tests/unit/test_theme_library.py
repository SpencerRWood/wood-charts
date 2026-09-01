"""Tests for the public YAML-theme and chart interfaces."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
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
