"""Typed loading, inheritance, and validation for bundled chart themes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .colors import blend_color, color_with_alpha, hex_to_rgb


class ThemeConfigurationError(ValueError):
    """Raised when a theme file cannot be resolved or validated."""


@dataclass(frozen=True)
class Margin:
    left: int
    right: int
    top: int
    bottom: int


@dataclass(frozen=True)
class Typography:
    family: str
    title_size: int
    subtitle_size: int
    axis_title_size: int
    tick_size: int
    legend_size: int
    annotation_size: int
    source_size: int
    title_weight: int = 700
    subtitle_weight: int = 400
    axis_title_weight: int = 500
    tick_weight: int = 400
    legend_weight: int = 400
    annotation_weight: int = 500
    source_weight: int = 400


@dataclass(frozen=True)
class Colors:
    primary: str
    secondary: str
    neutral_strong: str
    neutral: str
    neutral_light: str
    text_primary: str
    text_secondary: str
    text_muted: str
    grid: str
    zero_line: str
    background: str
    plot_background: str
    white: str
    area_alpha: float
    heatmap_weights: tuple[float, ...]
    heatmap_annotation_light: str
    heatmap_annotation_dark: str
    heatmap_annotation_threshold: float
    gauge_weights: tuple[float, float]

    @property
    def series_palette(self) -> tuple[str, str, str, str]:
        return (self.primary, self.secondary, self.neutral_strong, self.neutral)

    @property
    def primary_area(self) -> str:
        return color_with_alpha(self.primary, self.area_alpha)

    @property
    def sequential_scale(self) -> list[list[float | str]]:
        denominator = max(len(self.heatmap_weights) - 1, 1)
        return [
            [index / denominator, blend_color(self.primary, self.background, weight)]
            for index, weight in enumerate(self.heatmap_weights)
        ]

    @property
    def gauge_steps(self) -> tuple[str, str]:
        return tuple(
            blend_color(self.primary, self.background, weight)
            for weight in self.gauge_weights
        )  # type: ignore[return-value]


@dataclass(frozen=True)
class EventBand:
    fill_color: str
    opacity: float
    annotation_size: int
    annotation_color: str
    annotation_weight: int
    annotation_position: str


@dataclass(frozen=True)
class Theme:
    """Fully resolved design tokens consumed by chart constructors."""

    name: str
    width: int
    height: int
    margin: Margin
    typography: Typography
    colors: Colors
    event_band: EventBand
    line_width: int
    secondary_line_width: int
    marker_size: int
    bar_gap: float
    donut_hole: float
    donut_text_orientation: str
    accent_x_end: float
    accent_y_start: float
    accent_y_end: float
    title_y: float
    subtitle_y: float
    legend_y: float
    source_y: float
    axis_title_gutter: int
    hover_mode: str
    responsive: bool = False
    show_title_accent: bool = True


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = base.copy()
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_yaml(path: Path, ancestry: tuple[Path, ...] = ()) -> dict[str, Any]:
    resolved = path.resolve()
    if resolved in ancestry:
        msg = f"Circular theme inheritance detected at {path}."
        raise ThemeConfigurationError(msg)
    try:
        contents = yaml.safe_load(path.read_text())
    except FileNotFoundError as error:
        msg = f"Theme file does not exist: {path}."
        raise ThemeConfigurationError(msg) from error
    except yaml.YAMLError as error:
        msg = f"Malformed YAML in theme {path}: {error}."
        raise ThemeConfigurationError(msg) from error
    if not isinstance(contents, dict):
        msg = f"Theme {path} must contain a mapping."
        raise ThemeConfigurationError(msg)
    parent = contents.pop("extends", None)
    if parent is None:
        return contents
    if not isinstance(parent, str):
        msg = f"Theme {path} has a non-string extends value."
        raise ThemeConfigurationError(msg)
    return _deep_merge(
        _load_yaml(path.parent / parent, (*ancestry, resolved)), contents
    )


def _required(mapping: dict[str, Any], key: str, context: str) -> Any:
    try:
        return mapping[key]
    except KeyError as error:
        msg = f"Theme is missing required field {context}.{key}."
        raise ThemeConfigurationError(msg) from error


def _positive_int(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        msg = f"{name} must be a positive integer."
        raise ThemeConfigurationError(msg)
    return value


def _weight(value: Any, name: str) -> int:
    parsed = _positive_int(value, name)
    if not 100 <= parsed <= 1000:
        msg = f"{name} must be between 100 and 1000."
        raise ThemeConfigurationError(msg)
    return parsed


def _unit_interval(value: Any, name: str) -> float:
    parsed = float(value)
    if not 0 < parsed < 1:
        msg = f"{name} must be between 0 and 1, exclusive."
        raise ThemeConfigurationError(msg)
    return parsed


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        msg = f"{name} must be a boolean."
        raise ThemeConfigurationError(msg)
    return value


def _theme_from_mapping(name: str, config: dict[str, Any]) -> Theme:
    try:
        canvas = _required(config, "canvas", "root")
        margins = _required(config, "margin", "root")
        type_config = _required(config, "typography", "root")
        color_config = _required(config, "colors", "root")
        derived = _required(color_config, "derived", "colors")
        positions = _required(config, "positions", "root")
        marks = _required(config, "marks", "root")
        event_band_config = _required(config, "event_band", "root")
        for color_name, value in color_config.items():
            if color_name != "derived":
                hex_to_rgb(value)
        weights = tuple(
            float(item)
            for item in _required(derived, "heatmap_weights", "colors.derived")
        )
        if len(weights) < 2 or any(not 0 <= weight <= 1 for weight in weights):
            msg = (
                "colors.derived.heatmap_weights must contain at least two values "
                "between 0 and 1."
            )
            raise ThemeConfigurationError(msg)
        gauge_weights = tuple(
            float(item)
            for item in _required(derived, "gauge_weights", "colors.derived")
        )
        if len(gauge_weights) != 2 or any(
            not 0 <= weight <= 1 for weight in gauge_weights
        ):
            msg = (
                "colors.derived.gauge_weights must contain exactly two values "
                "between 0 and 1."
            )
            raise ThemeConfigurationError(msg)
        area_alpha = float(_required(derived, "area_alpha", "colors.derived"))
        if not 0 <= area_alpha <= 1:
            msg = "colors.derived.area_alpha must be between 0 and 1."
            raise ThemeConfigurationError(msg)
        heatmap_annotation_threshold = float(
            _required(derived, "heatmap_annotation_threshold", "colors.derived")
        )
        if not 0 <= heatmap_annotation_threshold <= 1:
            msg = "colors.derived.heatmap_annotation_threshold must be between 0 and 1."
            raise ThemeConfigurationError(msg)
        heatmap_annotation_light = str(
            _required(derived, "heatmap_annotation_light", "colors.derived")
        )
        heatmap_annotation_dark = str(
            _required(derived, "heatmap_annotation_dark", "colors.derived")
        )
        hex_to_rgb(heatmap_annotation_light)
        hex_to_rgb(heatmap_annotation_dark)
        typography = Typography(
            family=str(_required(type_config, "family", "typography")),
            **{
                key: _positive_int(
                    _required(type_config, key, "typography"), f"typography.{key}"
                )
                for key in (
                    "title_size",
                    "subtitle_size",
                    "axis_title_size",
                    "tick_size",
                    "legend_size",
                    "annotation_size",
                    "source_size",
                )
            },
            **{
                key: _weight(
                    _required(type_config, key, "typography"), f"typography.{key}"
                )
                for key in (
                    "title_weight",
                    "subtitle_weight",
                    "axis_title_weight",
                    "tick_weight",
                    "legend_weight",
                    "annotation_weight",
                    "source_weight",
                )
            },
        )
        event_band = EventBand(
            fill_color=str(_required(event_band_config, "fill_color", "event_band")),
            opacity=_unit_interval(
                _required(event_band_config, "opacity", "event_band"),
                "event_band.opacity",
            ),
            annotation_size=_positive_int(
                _required(event_band_config, "annotation_size", "event_band"),
                "event_band.annotation_size",
            ),
            annotation_color=str(
                _required(event_band_config, "annotation_color", "event_band")
            ),
            annotation_weight=_weight(
                _required(event_band_config, "annotation_weight", "event_band"),
                "event_band.annotation_weight",
            ),
            annotation_position=str(
                _required(event_band_config, "annotation_position", "event_band")
            ),
        )
        hex_to_rgb(event_band.fill_color)
        hex_to_rgb(event_band.annotation_color)
        return Theme(
            name=name,
            width=_positive_int(_required(canvas, "width", "canvas"), "canvas.width"),
            height=_positive_int(
                _required(canvas, "height", "canvas"), "canvas.height"
            ),
            margin=Margin(
                **{
                    key: _positive_int(
                        _required(margins, key, "margin"), f"margin.{key}"
                    )
                    for key in ("left", "right", "top", "bottom")
                }
            ),
            typography=typography,
            colors=Colors(
                **{
                    key: str(_required(color_config, key, "colors"))
                    for key in (
                        "primary",
                        "secondary",
                        "neutral_strong",
                        "neutral",
                        "neutral_light",
                        "text_primary",
                        "text_secondary",
                        "text_muted",
                        "grid",
                        "zero_line",
                        "background",
                        "plot_background",
                        "white",
                    )
                },
                area_alpha=area_alpha,
                heatmap_weights=weights,
                heatmap_annotation_light=heatmap_annotation_light,
                heatmap_annotation_dark=heatmap_annotation_dark,
                heatmap_annotation_threshold=heatmap_annotation_threshold,
                gauge_weights=(gauge_weights[0], gauge_weights[1]),
            ),
            event_band=event_band,
            line_width=_positive_int(
                _required(marks, "line_width", "marks"), "marks.line_width"
            ),
            secondary_line_width=_positive_int(
                _required(marks, "secondary_line_width", "marks"),
                "marks.secondary_line_width",
            ),
            marker_size=_positive_int(
                _required(marks, "marker_size", "marks"), "marks.marker_size"
            ),
            bar_gap=float(_required(marks, "bar_gap", "marks")),
            donut_hole=_unit_interval(
                _required(marks, "donut_hole", "marks"), "marks.donut_hole"
            ),
            donut_text_orientation=str(
                _required(marks, "donut_text_orientation", "marks")
            ),
            accent_x_end=float(_required(positions, "accent_x_end", "positions")),
            accent_y_start=float(_required(positions, "accent_y_start", "positions")),
            accent_y_end=float(_required(positions, "accent_y_end", "positions")),
            title_y=float(_required(positions, "title_y", "positions")),
            subtitle_y=float(_required(positions, "subtitle_y", "positions")),
            legend_y=float(_required(positions, "legend_y", "positions")),
            source_y=float(_required(positions, "source_y", "positions")),
            axis_title_gutter=_positive_int(
                _required(positions, "axis_title_gutter", "positions"),
                "positions.axis_title_gutter",
            ),
            hover_mode=str(_required(config, "hover_mode", "root")),
            responsive=_boolean(config.get("responsive", False), "responsive"),
            show_title_accent=_boolean(
                config.get("show_title_accent", True), "show_title_accent"
            ),
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, ThemeConfigurationError):
            raise
        msg = f"Invalid theme {name}: {error}"
        raise ThemeConfigurationError(msg) from error


def load_theme(theme: str | Path) -> Theme:
    """Load a named bundled theme or a theme YAML file."""
    path = Path(theme)
    if not path.suffix:
        path = Path(__file__).parent / "themes" / f"{theme}.yaml"
    return _theme_from_mapping(path.stem, _load_yaml(path))
