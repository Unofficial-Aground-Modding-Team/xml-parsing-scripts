import math
from pathlib import Path
from PIL import Image
import pydantic
from fanfish.utils.models import (
    AbstractAnimation,
    AnimationFrame,
    AnimationSequence,
    ImageFrame,
    Tile,
    TilePart,
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
        self.image = Image.new("RGB", (512, 512), (128, 128, 128))
        self.tilesheets = data.tilesheets
        self.tiles = data.tiles
        self.animations = data.animations

    def render(self, tile_id: str, animation_id: str, index: int):
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
                # assert sheet_image.index == combined_x
                # assert divmod(combined_x, cols) == (sheet_image.y, sheet_image.x)
                cropped = img_file.crop(
                    (
                        # left, upper, right, and lower
                        sheet_image.x,
                        sheet_image.y,
                        sheet_image.x + sheet_image.width,
                        sheet_image.y + sheet_image.height,
                    )
                )
                combined_offset_X = subtile.offsetX + frame.offsetX
                combined_offset_Y = subtile.offsetY + frame.offsetY
                self.image.paste(
                    cropped,
                    (
                        255 + int(combined_offset_X * sheet_image.width),
                        255 + int(combined_offset_Y * sheet_image.height),
                    ),
                )


if __name__ == "__main__":
    from lxml import etree

    def create_data():
        from fanfish.utils.images.parse_xml import (
            parse_source_sheet,
            load_tilesheet,
            load_tile,
            load_animation,
            xml_tile_sheets,
            xml_tiles,
            xml_animations,
        )
        from fanfish.utils.images.convert_internal import (
            convert_tilesheet,
            convert_tile,
            convert_animation,
            tilesheets,
            tiles,
            animations,
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
        with open("clean/parsed.json", 'w') as file:
            file.write(data.model_dump_json())

    def main():
        with open("clean/parsed.json", 'r') as file:
            data = DataContainer.model_validate_json(file.read())

        stage = Stage(data)
        stage.render("young_dragon", "young_dragon.fly", 0)
        stage.image.save("tmp.png")

    create_data()
    main()
