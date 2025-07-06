import math
from pathlib import Path

import numpy as np
import pydantic
from PIL import Image

from fanfish.utils.common import DEFAULT_COLOR, Color
from fanfish.utils.models import (
    AnimationSequence,
    Tile,
    TileSheet,
)

DATA_FOLDER = Path("data")


class DataContainer(pydantic.BaseModel):
    tilesheets: dict[str, TileSheet]
    tiles: dict[str, Tile]
    animations: dict[str, AnimationSequence]


class Stage:
    def __init__(
        self,
        data: DataContainer,
    ):
        self.image = Image.new("RGBA", (512, 512), (255, 255, 255, 0))
        self.tilesheets = data.tilesheets
        self.tiles = data.tiles
        self.animations = data.animations

    def render(self, tile_id: str, animation_id: str, index: int, extra_offset_x: int = 0, extra_offset_y: int = 0, extra_color: Color = DEFAULT_COLOR):
        animation = self.animations[animation_id]
        for anim in animation.animations:
            frame = anim.frames[index]
            if not frame.visible:
                continue
            tile = self.tiles[anim.overwrite_tile_id or tile_id]
            for subtile in tile.subtiles:
                sheet = self.tilesheets[subtile.sheet_id]
                img_file = Image.open(DATA_FOLDER / sheet.sheet_file)
                cols = math.ceil(img_file.width / sheet.frames[0].width)
                combined_x = subtile.x + frame.x + cols * (subtile.y + frame.y)
                sheet_image = sheet.frames[combined_x]

                cropped = img_file.crop(
                    (
                        # left, upper, right, and lower
                        sheet_image.x,
                        sheet_image.y,
                        sheet_image.x + sheet_image.width,
                        sheet_image.y + sheet_image.height,
                    )
                )
                if (tint := (frame.color * extra_color)) != DEFAULT_COLOR:
                    _arr = np.array(cropped).astype(np.float64)
                    # _arr[:, :, 0] *= tint.red
                    # _arr[:, :, 1] *= tint.green
                    # _arr[:, :, 2] *= tint.blue
                    # <CUSTOM LOGIC>
                    # Modify the Luminance, unlike how color multipliers work in Aground, 
                    # to make everything have more or less the same brightness
                    L = _arr[:, :, :3] @ [0.2126, 0.7152, 0.0722]  # luminance
                    L *= 100 / L.mean()
                    _arr[:, :, 0] = L * tint.red
                    _arr[:, :, 1] = L * tint.green
                    _arr[:, :, 2] = L * tint.blue
                    # </CUSTOM LOGIC>
                    _arr = np.round(np.minimum(_arr, 255)).astype(np.uint8)
                    cropped = Image.fromarray(_arr)

                combined_offset_X = subtile.offsetX + frame.offsetX
                combined_offset_Y = subtile.offsetY + frame.offsetY
                self.image.paste(
                    cropped,
                    (
                        255 + int(combined_offset_X * sheet_image.width) + extra_offset_x,
                        255 + int(combined_offset_Y * sheet_image.height) + extra_offset_y,
                    ),
                )


if __name__ == "__main__":
    from lxml import etree

    def create_data():
        from fanfish.utils.images.convert_internal import (
            animations,
            convert_animation,
            convert_tile,
            convert_tilesheet,
            tiles,
            tilesheets,
        )
        from fanfish.utils.images.parse_xml import (
            load_animation,
            load_tile,
            load_tilesheet,
            parse_source_sheet,
            xml_animations,
            xml_tile_sheets,
            xml_tiles,
        )

        input_file = "clean/aggregated.xml"

        aggregated_xml = etree.parse(input_file).getroot()

        _agg_tilesheets: list[tuple[Path, etree._Element]] = []
        _agg_tiles: list[tuple[Path, etree._Element]] = []
        _agg_animations: list[tuple[Path, etree._Element]] = []

        for xmlfile in aggregated_xml.findall("./", None):
            _file = xmlfile.get("source", None)
            assert _file is not None
            source_file = Path(_file)
            for group, collection in [
                ("tilesheet", _agg_tilesheets),
                ("tile", _agg_tiles),
                ("animation", _agg_animations),
            ]:
                for element in xmlfile.findall(group, None):
                    collection.append((source_file, element))

        # Push elements with "equals" to the end
        # _agg_tilesheets.sort(key=lambda t: t[1].get("equals", None) is not None)
        # _agg_tiles.sort(key=lambda t: t[1].get("equals", None) is not None)
        # _agg_animations.sort(key=lambda t: t[1].get("equals", None) is not None)

        for source_file, element in _agg_tilesheets:
            _raw_id = element.get("id")
            assert _raw_id is not None
            adjusted_id = parse_source_sheet(source_file, _raw_id)
            load_tilesheet(adjusted_id, element)

        for source_file, element in _agg_tiles:
            load_tile(source_file, element)

        for source_file, element in _agg_animations:
            load_animation(element)

        for tilesheet in xml_tile_sheets.values():
            converted = convert_tilesheet(tilesheet)
            tilesheets[converted.id] = converted

        for tile in xml_tiles.values():
            converted = convert_tile(tile)
            tiles[converted.id] = converted

        _missing: set[str] = set(xml_animations.keys())
        _solved: set[str] = set()

        for i in range(10):
            for animation_id in _missing:
                animation = xml_animations[animation_id]
                if (eq := animation.equals) is not None and eq not in _solved:
                    continue
                if any(
                    (an := dependency.animation) is not None and an not in _solved
                    for dependency in animation.appends
                ):
                    continue

                converted = convert_animation(animation)
                animations[converted.id] = converted
                _solved.add(animation_id)
            _missing -= _solved
        if _missing:
            raise RuntimeError("Could not resolve animations equals=")
        data = DataContainer(tilesheets=tilesheets, tiles=tiles, animations=animations)
        with open("clean/parsed.json", "w") as file:
            file.write(data.model_dump_json())

    def main():
        with open("clean/parsed.json", "r") as file:
            data = DataContainer.model_validate_json(file.read())

        stage = Stage(data)
        colors = [
            Color.parse_color("#E40303", 1.0),
            Color.parse_color("#FF8C00", 1.0),
            Color.parse_color("#FFED00", 1.0),
            Color.parse_color("#008026", 1.0),
            Color.parse_color("#004CFF", 1.0),
            Color.parse_color("#732982", 1.0),
        ]
        for i, color in enumerate(colors, -3):
            for j in range(-5, 5):
                extra_color_scale = 0.75 + (((i + j) % 5) / 10) # 0.75 ~ 1.25
                stage.render("young_dragon", "young_dragon.fly", index=j, extra_offset_x=i*48, extra_offset_y=j*48, extra_color=color * extra_color_scale)
        stage.image.save("tmp.png")

    # create_data()
    main()
