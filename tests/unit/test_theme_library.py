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
    box_chart,
    combo_chart,
    donut_chart,
    dot_chart,
    dumbbell_chart,
    gauge_chart,
    grouped_bar_chart,
    heatmap_chart,
    histogram_chart,
    kpi_cards,
    line_chart,
    range_bar_chart,
    scatter_chart,
    slope_chart,
    stacked_bar_chart,
    waterfall_chart,
)
from wood_charts.colors import blend_color, color_with_alpha, hex_to_rgb
from wood_charts.export import export_chart


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
    assert theme.colors.heatmap_annotation_light == theme.colors.text_primary
    assert theme.colors.heatmap_annotation_dark == theme.colors.white
    assert theme.colors.heatmap_annotation_threshold == 0.60


@pytest.mark.parametrize(
    ("function", "arguments", "message"),
    [
        (hex_to_rgb, ("#123",), "six-digit"),
        (color_with_alpha, ("#002F6C", 1.1), "Alpha"),
        (blend_color, ("#000000", "#FFFFFF", -0.1), "weight"),
    ],
)
def test_color_utilities_reject_invalid_values(
    function: Callable[..., object], arguments: tuple[object, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        function(*arguments)


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
    ) == (110, 60, 170, 80)
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
        pd.DataFrame({"day": [1, 2], "sessions": [0, 5]}),
        "day",
        "sessions",
        load_theme("notebook"),
    )
    assert not figure.layout.shapes
    assert not figure.layout.annotations


def test_line_chart_marks_an_automatically_truncated_positive_y_axis() -> None:
    figure = line_chart(
        pd.DataFrame({"day": [1, 2, 3], "sessions": [380, 450, 520]}),
        "day",
        "sessions",
        load_theme("notebook"),
    )
    assert figure.layout.yaxis.range[0] < 380
    assert figure.layout.yaxis.range[0] > 0
    assert figure.layout.yaxis.autorange is False
    assert figure.layout.shapes[0].type == "path"


def test_line_chart_keeps_zero_in_range_without_an_automatic_axis_break() -> None:
    figure = line_chart(
        pd.DataFrame({"day": [1, 2, 3], "sessions": [0, 50, 100]}),
        "day",
        "sessions",
        load_theme("notebook"),
    )
    assert figure.layout.yaxis.range is None
    assert not figure.layout.shapes


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
    event_band_shapes = [
        shape for shape in figure.layout.shapes if shape.type == "rect"
    ]
    assert len(event_band_shapes) == 2
    assert tuple(band.opacity for band in event_band_shapes) == (
        theme.event_band.opacity,
        0.30,
    )
    assert tuple(annotation.text for annotation in figure.layout.annotations) == (
        "Launch",
        "Sale",
    )
    assert figure.layout.annotations[1].xanchor == "right"
    assert figure.layout.annotations[1].yanchor == "bottom"


def test_notebook_legends_reserve_space_above_event_bands() -> None:
    figure = line_chart(
        pd.DataFrame({"day": [1, 2], "organic": [4, 5], "paid": [2, 3]}),
        "day",
        ["organic", "paid"],
        load_theme("notebook"),
        event_bands=[{"start": 1, "end": 1.5, "label": "Campaign"}],
    )
    assert figure.layout.legend.yanchor == "bottom"
    assert figure.layout.legend.maxheight == 0.12


def test_line_chart_supports_a_labeled_numeric_y_axis_break() -> None:
    figure = line_chart(
        pd.DataFrame({"day": [1, 2], "sessions": [2600, 2800]}),
        "day",
        "sessions",
        load_theme("notebook"),
        axis_break={"start": 0, "end": 2500},
    )
    assert figure.layout.yaxis.range[0] == 2500
    assert figure.layout.yaxis.range[1] > 2800
    assert figure.layout.yaxis.autorange is False
    assert len(figure.layout.shapes) == 1
    marker = figure.layout.shapes[0]
    assert marker.type == "path"
    assert marker.layer == "above"
    assert marker.path.startswith("M -0.008,0.035")
    assert marker.line.color == load_theme("notebook").colors.text_secondary
    assert marker.line.width == 2
    assert not figure.layout.annotations


def test_area_chart_supports_y_axis_breaks_and_rejects_invalid_ranges() -> None:
    data = pd.DataFrame({"day": [1, 2], "sessions": [2600, 2800]})
    figure = area_chart(
        data,
        "day",
        "sessions",
        load_theme("notebook"),
        axis_break={"start": 0, "end": 2500},
    )
    assert figure.layout.yaxis.range[0] == 2500
    assert figure.layout.yaxis.range[1] > 2800
    assert figure.layout.yaxis.autorange is False
    with pytest.raises(ValueError, match="start must be less"):
        area_chart(
            data,
            "day",
            "sessions",
            load_theme("notebook"),
            axis_break={"start": 2500, "end": 0},
        )


def test_stacked_area_chart_supports_event_bands_and_axis_breaks() -> None:
    figure = area_chart(
        pd.DataFrame({"day": [1, 2], "organic": [2600, 2800], "paid": [200, 300]}),
        "day",
        ["organic", "paid"],
        load_theme("notebook"),
        event_bands=[{"start": 1, "end": 1.5, "label": "Campaign"}],
        axis_break={"start": 0, "end": 2500},
    )
    assert tuple(trace.stackgroup for trace in figure.data) == ("area", "area")
    assert tuple(shape.type for shape in figure.layout.shapes) == ("rect", "path")
    assert figure.layout.shapes[1].layer == "above"
    assert tuple(annotation.text for annotation in figure.layout.annotations) == (
        "Campaign",
    )


def test_area_chart_preserves_single_series_behavior() -> None:
    theme = load_theme("notebook")
    figure = area_chart(
        pd.DataFrame({"day": [1, 2], "sessions": [4, 5]}),
        "day",
        "sessions",
        theme,
    )
    trace = figure.data[0]
    assert len(figure.data) == 1
    assert trace.fill == "tozeroy"
    assert trace.stackgroup is None
    assert trace.fillcolor == theme.colors.primary_area
    assert not figure.layout.shapes


def test_area_chart_stacks_multiple_series_in_supplied_order() -> None:
    theme = load_theme("notebook")
    figure = area_chart(
        pd.DataFrame({"day": [1, 2], "organic": [4, 5], "paid": [2, 3]}),
        "day",
        ["organic", "paid"],
        theme,
        names=["Organic", "Paid"],
    )
    assert tuple(trace.name for trace in figure.data) == ("Organic", "Paid")
    assert tuple(trace.stackgroup for trace in figure.data) == ("area", "area")
    assert tuple(tuple(trace.y) for trace in figure.data) == ((4, 5), (2, 3))
    assert figure.layout.showlegend is True


def test_area_chart_adds_one_event_band() -> None:
    figure = area_chart(
        pd.DataFrame({"day": [1, 2], "sessions": [4, 5]}),
        "day",
        "sessions",
        load_theme("notebook"),
        event_bands=[{"start": 1, "end": 1.5, "label": "Campaign"}],
    )
    assert len(figure.layout.shapes) == 1
    assert figure.layout.shapes[0].layer == "below"
    assert figure.layout.annotations[0].text == "Campaign"


def test_area_chart_adds_multiple_event_bands_with_multiple_series() -> None:
    figure = area_chart(
        pd.DataFrame({"day": [1, 2, 3], "organic": [4, 5, 6], "paid": [2, 3, 4]}),
        "day",
        ["organic", "paid"],
        load_theme("notebook"),
        event_bands=[
            {"start": 1, "end": 1.5, "label": "Launch"},
            {"start": 2, "end": 2.5, "label": "Sale", "opacity": 0.30},
        ],
    )
    assert len(figure.data) == 2
    assert len(figure.layout.shapes) == 2
    assert tuple(band.opacity for band in figure.layout.shapes) == (0.14, 0.30)
    assert tuple(annotation.text for annotation in figure.layout.annotations) == (
        "Launch",
        "Sale",
    )


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


def test_heatmap_chart_preserves_default_matrix_order_and_scale() -> None:
    theme = load_theme("notebook")
    figure = heatmap_chart(
        pd.DataFrame(
            {
                "to_page": ["product_page", "checkout"],
                "from_home": [0.6, 0.2],
                "from_cart": [0.1, 0.8],
            }
        ),
        "to_page",
        ["from_cart", "from_home"],
        theme,
    )
    trace = figure.data[0]
    assert tuple(trace.x) == ("product_page", "checkout")
    assert tuple(trace.y) == ("from_cart", "from_home")
    assert tuple(tuple(row) for row in trace.z) == ((0.1, 0.8), (0.6, 0.2))
    assert trace.zmin is None
    assert trace.zmax is None
    assert trace.texttemplate is None
    assert figure.layout.yaxis.showgrid is False


def test_heatmap_chart_can_mask_zero_cells() -> None:
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["home", "checkout"], "from_home": [0, 0.4]}),
        "to_page",
        ["from_home"],
        load_theme("notebook"),
        mask_zero=True,
    )
    assert tuple(figure.data[0].z[0]) == (None, 0.4)


def test_heatmap_chart_annotates_only_nonzero_values_as_percentages() -> None:
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["home", "checkout"], "from_home": [0, 0.42]}),
        "to_page",
        ["from_home"],
        load_theme("notebook"),
        annotate=True,
        value_format=".0%",
    )
    trace = figure.data[0]
    assert tuple(trace.z[0]) == (0, 0.42)
    assert tuple(trace.text[0]) == ("", "42%")
    assert trace.texttemplate is None
    assert tuple(annotation.text for annotation in figure.layout.annotations) == (
        "42%",
    )
    assert all("%{" not in value for row in trace.text for value in row)


def test_heatmap_chart_omits_masked_zero_annotations() -> None:
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["home", "checkout"], "from_home": [0, 0.42]}),
        "to_page",
        ["from_home"],
        load_theme("notebook"),
        mask_zero=True,
        annotate=True,
        value_format=".0%",
    )
    trace = figure.data[0]
    assert tuple(trace.z[0]) == (None, 0.42)
    assert tuple(trace.text[0]) == ("", "42%")
    assert tuple(annotation.text for annotation in figure.layout.annotations) == (
        "42%",
    )


def test_heatmap_chart_formats_nonpercentage_annotations() -> None:
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["checkout"], "from_home": [0.426]}),
        "to_page",
        ["from_home"],
        load_theme("notebook"),
        annotate=True,
        value_format=".2f",
    )
    assert tuple(figure.data[0].text[0]) == ("0.43",)


def test_heatmap_chart_uses_contrast_aware_annotation_colors() -> None:
    theme = load_theme("notebook")
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["home", "checkout"], "from_home": [0.2, 0.8]}),
        "to_page",
        ["from_home"],
        theme,
        annotate=True,
        value_format=".0%",
        zmin=0,
        zmax=1,
    )
    annotations = figure.layout.annotations
    assert tuple(annotation.text for annotation in annotations) == ("20%", "80%")
    assert annotations[0].font.color == theme.colors.heatmap_annotation_light
    assert annotations[1].font.color == theme.colors.heatmap_annotation_dark


def test_heatmap_chart_can_disable_contrast_aware_annotations() -> None:
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["checkout"], "from_home": [0.42]}),
        "to_page",
        ["from_home"],
        load_theme("notebook"),
        annotate=True,
        contrast_aware=False,
    )
    assert figure.data[0].texttemplate == "%{text}"
    assert not figure.layout.annotations


def test_heatmap_chart_formats_percentage_colorbar_ticks() -> None:
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["checkout"], "from_home": [0.42]}),
        "to_page",
        ["from_home"],
        load_theme("notebook"),
        value_format=".0%",
    )
    assert figure.data[0].colorbar.tickformat == ".0%"


def test_heatmap_chart_formats_snake_case_display_labels() -> None:
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["product_page"], "from_home_page": [0.42]}),
        "to_page",
        ["from_home_page"],
        load_theme("notebook"),
        format_labels=True,
    )
    assert tuple(figure.data[0].x) == ("Product Page",)
    assert tuple(figure.data[0].y) == ("From Home Page",)


def test_heatmap_chart_supports_fixed_color_scale_and_titles() -> None:
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["checkout"], "from_home": [0.42]}),
        "to_page",
        ["from_home"],
        load_theme("notebook"),
        zmin=0,
        zmax=1,
        x_axis_title="To Page",
        y_axis_title="From Page",
        colorbar_title="Transition Probability",
    )
    trace = figure.data[0]
    assert (trace.zmin, trace.zmax) == (0, 1)
    assert figure.layout.xaxis.title.text == "To Page"
    assert figure.layout.yaxis.title.text == "From Page"
    assert trace.colorbar.title.text == "Transition Probability"


def test_heatmap_chart_separates_source_from_x_axis_title() -> None:
    theme = load_theme("notebook")
    source = "Synthetic Website Data"
    figure = heatmap_chart(
        pd.DataFrame({"to_page": ["checkout"], "from_home": [0.42]}),
        "to_page",
        ["from_home"],
        theme,
        source=source,
        x_axis_title="To Page",
    )
    source_annotation = next(
        annotation
        for annotation in figure.layout.annotations
        if annotation.text == f"Source: {source}"
    )
    assert figure.layout.yaxis.showgrid is False
    assert figure.layout.margin.b == 154
    assert figure.layout.xaxis.title.standoff == 24
    assert source_annotation.y == -0.45


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


def test_remaining_chart_constructors_apply_semantic_defaults() -> None:
    theme = load_theme("powerpoint_2_1")
    values = pd.DataFrame(
        {
            "category": ["A", "B"],
            "value": [3, 4],
            "other": [2, 5],
            "start": [1, 2],
            "end": [4, 5],
            "measure": ["relative", "total"],
        }
    )
    grouped = grouped_bar_chart(values, "category", ["value", "other"], theme)
    scatter = scatter_chart(values, "value", "other", theme)
    dots = dot_chart(values, "value", "category", theme, sort=False)
    histogram = histogram_chart(values, "value", theme, bins=4)
    box = box_chart(values, "category", "value", theme)
    waterfall = waterfall_chart(values, "category", "value", "measure", theme)
    slope = slope_chart(values, "start", "end", "category", theme)
    dumbbell = dumbbell_chart(values, "category", "start", "end", theme)
    cards = kpi_cards(
        [
            {"label": "Sessions", "value": 120, "previous": 100, "format": ","},
            {"label": "Orders", "value": 8, "previous": 10, "format": ","},
        ],
        theme,
    )
    assert grouped.layout.barmode == "group"
    assert scatter.data[0].marker.size == theme.marker_size + 4
    assert dots.data[0].mode == "markers+text"
    assert histogram.data[0].nbinsx == 4
    assert len(box.data) == 2
    assert waterfall.data[0].type == "waterfall"
    assert len(slope.data) == 2
    assert len(dumbbell.data) == 4
    assert len(cards.layout.annotations) == 6


def test_export_chart_applies_theme_dimensions_and_svg_transparency(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls: list[tuple[go.Figure, str, dict[str, object]]] = []

    def write_image_stub(figure: go.Figure, path: str, **kwargs: object) -> None:
        calls.append((figure, path, kwargs))

    monkeypatch.setattr(go.Figure, "write_image", write_image_stub)
    theme = load_theme("notebook")
    figure = go.Figure()
    export_chart(figure, tmp_path / "chart.svg", theme=theme)
    export_chart(figure, tmp_path / "chart.png")
    svg_figure, _, svg_options = calls[0]
    assert svg_options == {"width": 960, "height": 600}
    assert svg_figure.layout.paper_bgcolor == "rgba(0,0,0,0)"
    assert svg_figure.layout.plot_bgcolor == "rgba(0,0,0,0)"
    assert calls[1][2] == {}


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
