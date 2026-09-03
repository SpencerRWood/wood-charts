# wood-charts

`wood-charts` is a typed Python library of theme-driven Plotly chart
constructors. Use it in any project that needs consistent, presentation-ready
charts without recreating visual defaults for every figure.

The package supplies four built-in canvas themes:

| Theme | Canvas |
| --- | --- |
| `powerpoint_2_1` | 1600 x 800 (2:1) |
| `powerpoint_16_9` | 1600 x 900 (16:9) |
| `latex_3_2` | 1200 x 800 (3:2) |
| `notebook` | 960 x 600 (interactive notebook) |

## Installation

After publishing this repository to GitHub, install it directly from a tag or
branch:

```sh
python -m pip install "wood-charts @ git+https://github.com/<owner>/<repository>.git@v0.0.1"
```

With `uv`:

```sh
uv add "wood-charts @ git+https://github.com/<owner>/<repository>.git@v0.0.1"
```

Replace `<owner>/<repository>` with the GitHub repository path. Pinning a
release tag provides reproducible installs; use `@main` only when intentionally
tracking unreleased changes.

## Quick start

```python
import pandas as pd

from wood_charts import load_theme
from wood_charts.charts import line_chart
from wood_charts.export import export_chart

data = pd.DataFrame(
    {
        "month": ["Jan", "Feb", "Mar", "Apr"],
        "sessions": [3650, 4120, 4380, 4720],
    }
)

theme = load_theme("powerpoint_16_9")
figure = line_chart(
    data,
    x="month",
    y="sessions",
    theme=theme,
    title="Sessions increased",
    subtitle="Monthly website sessions",
    source="Analytics platform",
    x_axis_title="Month",
    y_axis_title="Sessions",
)
export_chart(figure, "sessions.svg", theme=theme)
```

The figure is an ordinary `plotly.graph_objects.Figure`, so callers can apply
project-specific Plotly updates after construction when needed.

For responsive Jupyter output, use the compact `notebook` theme. It leaves the
figure width unset, enables Plotly autosizing, and configures `.show()` to
respond to notebook viewport changes. Axis titles and tick labels use Plotly's
automatic margins, so they retain space as the viewport changes:

```python
theme = load_theme("notebook")
figure = line_chart(data, x="month", y="sessions", theme=theme)
figure.show()
```

## Available charts

Import chart constructors from `wood_charts.charts`:

```python
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
```

For numeric y-axis values with a large omitted baseline, `line_chart()` and
`area_chart()` can display an explicit break marker and start the visible axis
at the end of that interval:

```python
figure = line_chart(
    data,
    "date",
    "sessions",
    theme,
    axis_break={"start": 0, "end": 2500},
)
```

`line_chart()` also applies this marker automatically when its positive data
range materially omits zero. Area charts keep a zero baseline by default, so
use `axis_break` when deliberately truncating a filled area.

All constructors accept a loaded `Theme` plus title, subtitle, source, and
advanced layout overrides as appropriate to the chart type. Cartesian charts
also support optional `x_axis_title` and `y_axis_title`; `combo_chart` supports
`secondary_y_axis_title`.

Single-series `bar_chart()` uses the theme primary color by default. To focus
one category or a collection of categories, pass their category value(s); all
remaining bars use the theme's neutral light gray:

```python
figure = bar_chart(data, "event_count", "event_type", theme, focus="purchase")
weekly = bar_chart(data, "count", "day", theme, focus=["Monday", "Tuesday"])
```

Use `event_bands` with `line_chart()` to shade one or more event windows behind
the data. Each band requires `start` and `end`; `label`, `opacity`, and
`annotation_position` are optional.

```python
figure = line_chart(
    data,
    "date",
    "sessions",
    theme,
    event_bands=[
        {"start": "2026-01-10", "end": "2026-01-17", "label": "Campaign"},
        {"start": "2026-02-01", "end": "2026-02-03", "opacity": 0.25},
    ],
)
```

## Themes and exports

`load_theme()` resolves the built-in YAML theme files bundled with the package.
For a project-specific theme, pass the path to a YAML file that extends one of
the bundled themes:

```yaml
extends: base.yaml
colors:
  primary: "#009B4E"
```

Use `export_chart()` to write PNG, SVG, or another Kaleido-supported format.
SVG exports use transparent paper and plot backgrounds; other formats retain
the theme background. Install IBM Plex Sans in the rendering environment to
use the configured font stack for static exports.

To validate a checkout:

```sh
uv sync --frozen --group dev
uv run ruff check src tests
uv run mypy
uv run pytest
uv build
```
