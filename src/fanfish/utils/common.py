from dataclasses import dataclass
from functools import cache


@dataclass
class Color:
    # colors are parsed into 0.0 ~ 1.0, but can go beyond that via colorScale
    red: float
    green: float
    blue: float

    @classmethod
    @cache
    def parse_color(cls, color_string: str, color_scale: float) -> "Color":
        # <TODO PARSE IT PROPERLY?>
        if color_string == "shirt":
            color_string = "cf2b2b"
        if color_string == "eyes":
            color_string = "5ab1ea"
        if color_string == "hair":
            color_string = "130e01"
        # </TODO>
        if color_string.startswith("#"):
            color_string = color_string.strip("#")
        if len(color_string) == 3:
            red, blue, green = (int(color_string[i], 16) * 17 for i in range(3))
        elif len(color_string) == 6:
            red, blue, green = (
                int(color_string[i : i + 2], 16) for i in range(0, 6, 2)
            )
        else:
            raise ValueError(f"Invalid length for {color_string=}")
        return Color(
            red / 0xFF * color_scale,
            green / 0xFF * color_scale,
            blue / 0xFF * color_scale,
        )


# DEFAULT_COLOR = Color(red=1.0, green=1.0, blue=1.0)
# DEFAULT_COLOR = Color.parse_color("#ffffff", 1.0)
DEFAULT_COLOR = Color.parse_color("fff", 1.0)
