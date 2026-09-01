"""Color parsing and derivation utilities."""

from __future__ import annotations


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convert a six-digit hex color to RGB."""
    value = color.removeprefix("#")
    if len(value) != 6 or any(
        character not in "0123456789abcdefABCDEF" for character in value
    ):
        msg = f"Expected a six-digit hex color, received {color!r}."
        raise ValueError(msg)
    return tuple(int(value[index : index + 2], 16) for index in range(0, 6, 2))  # type: ignore[return-value]


def color_with_alpha(color: str, alpha: float) -> str:
    """Return a CSS rgba color using ``color`` and opacity ``alpha``."""
    if not 0 <= alpha <= 1:
        msg = "Alpha must be between 0 and 1."
        raise ValueError(msg)
    red, green, blue = hex_to_rgb(color)
    return f"rgba({red}, {green}, {blue}, {alpha})"


def blend_color(foreground: str, background: str, weight: float) -> str:
    """Blend ``foreground`` over ``background`` using ``weight``."""
    if not 0 <= weight <= 1:
        msg = "Blend weight must be between 0 and 1."
        raise ValueError(msg)
    foreground_rgb = hex_to_rgb(foreground)
    background_rgb = hex_to_rgb(background)
    channels = [
        round(foreground_channel * weight + background_channel * (1 - weight))
        for foreground_channel, background_channel in zip(
            foreground_rgb, background_rgb, strict=True
        )
    ]
    return "#" + "".join(f"{channel:02X}" for channel in channels)
