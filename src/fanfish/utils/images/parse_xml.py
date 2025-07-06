"Utility classes for parsing tile animations"

from pathlib import Path

from lxml import etree

from fanfish.utils.common import DEFAULT_COLOR, Color
from fanfish.utils.xml_models import (
    XmlAnimation,
    XmlAnimationFrame,
    XmlAppendedAnimation,
    XmlSheetImage,
    XmlSubTile,
    XmlTile,
    XmlTileSheet,
)

DEFAULT_XML_TILE_SHEET = XmlTileSheet(
    id="",
    sheet="",
    name=None,
    extends=None,
    width=16,
    height=16,
    offsetX=0,
    offsetY=0,
    images=[],
)

DEFAULT_XML_SUB_TILE = XmlSubTile(
    sheet=DEFAULT_XML_TILE_SHEET,
    x=0,
    y=0,
    offsetX=0,
    offsetY=0,
)

DEFAULT_XML_TILE = XmlTile(
    id="",
    sheet=DEFAULT_XML_TILE_SHEET,
    equals=None,
    x=0,
    y=0,
    offsetX=0,
    offsetY=0,
    subtiles=[],
)

DEFAULT_XML_SHEET_IMAGE = XmlSheetImage(
    frame=0,
    equals=None,
    x=0,
    y=0,
    width=-1,
    height=-1,
    offsetX=0,
    offsetY=0,
)

DEFAULT_XML_ANIMATION_FRAME = XmlAnimationFrame(
    count=1,
    length=1,
    x=0,
    y=0,
    visible=True,
    glow=False,
    repeat=0,
    reverse=False,
    offsetX=0,
    offsetY=0,
    parentX=0,
    parentY=0,
)

DEFAULT_XML_APPENDED_ANIMATION = XmlAppendedAnimation(
    tile="",
    animation="",
    color=DEFAULT_COLOR,
    x=0,
    y=0,
    offsetX=0,
    offsetY=0,
    behind=False,
    flip=False,
)


DEFAULT_XML_ANIMATION = XmlAnimation(
    id="",
    x=0,
    y=0,
    tile="",
    equals="",
    count=0,
    length=1,
    shift=0,
    glow=False,
    repeat=0,
    reverse=False,
    raw_color="fff",
    raw_color_scale=1.0,
    color=DEFAULT_COLOR,
    scale=1,
    offsetX=0,
    offsetY=0,
    rotate=0,
    appends=[],
    frames=[],
)

xml_tiles: dict[str, XmlTile] = {}
xml_tile_sheets: dict[str, XmlTileSheet] = {}
xml_animations: dict[str, XmlAnimation] = {}


def parse_source_sheet(source_file: Path, sheet_id: str) -> Path:
    "Resolve the path to a Tilesheet"
    if "{" in sheet_id:
        sheet_id = sheet_id.replace("{", "").replace("}", "")
        if sheet_id.startswith("mod:"):
            return Path("mods") / sheet_id.removeprefix("mod:").replace(
                "full_version", "full"
            )
        else:
            return Path(sheet_id)
    else:
        return Path(source_file).parent / sheet_id


def parse_sheet_image_frames(
    tilesheet: XmlTileSheet, sheet: etree._Element
) -> list[XmlSheetImage]:
    "Parse <image> tags inside of a <sheet>. Returns an empty list if it has none."
    frames: list[XmlSheetImage] = []
    frame: etree._Element

    for frame in sheet.findall("image", None):
        values = {}
        values["frame"] = frame.get("frame")
        values["equals"] = frame.get("equals")
        base_frame = next(
            (
                existing
                for existing in frames
                if existing.frame == int(frame.get("equals", -1))
            ),
            DEFAULT_XML_SHEET_IMAGE,
        )
        values["width"] = frame.get(
            "width", base_frame.width if base_frame.width != -1 else tilesheet.width
        )
        values["height"] = frame.get(
            "height", base_frame.height if base_frame.height != -1 else tilesheet.height
        )
        simple_fields = ("x", "y", "offsetX", "offsetY")
        for field in simple_fields:
            value = frame.get(field, getattr(base_frame, field))
            values[field] = value

        frames.append(XmlSheetImage.model_validate(values))
    frames.sort(key=lambda frame: frame.frame)
    return frames


def load_tilesheet(sheet_id: Path, sheet: etree._Element | None) -> XmlTileSheet:
    "Parses a <sheet> element, or a reference to a tilesheet which does not have an explicitly <sheet> tag (using default values)"
    if sheet is None:  # Default settings with no explicit <sheet>
        tilesheet = XmlTileSheet(
            id=str(sheet_id),
            name=sheet_id.stem,
            extends=None,
            sheet=str(sheet_id),
            width=16,
            height=16,
            offsetX=0,
            offsetY=0,
            images=[],
        )
    else:  # Custom <sheet> definition
        # If it has a `sheet` tag, use that for the actual image instead of the `id`
        if (image_file := sheet.get("sheet")) is not None:
            path = sheet_id.with_name(image_file)
        else:
            path = sheet_id

        tilesheet = XmlTileSheet(
            id=str(sheet_id),
            name=sheet.get("name", None),
            extends=sheet.get("extends", None),
            sheet=str(path),
            width=int(sheet.get("width", 16)),
            height=int(sheet.get("height", 16)),
            offsetX=int(sheet.get("offsetX", 0)),
            offsetY=int(sheet.get("offsetY", 0)),
            images=[],
        )
        tilesheet.images = parse_sheet_image_frames(tilesheet, sheet)
    xml_tile_sheets[str(sheet_id)] = tilesheet
    return tilesheet


def parse_sub_tiles(source_file: Path, root: etree._Element) -> list[XmlSubTile]:
    "Parse sub<tile> tags inside of a <tile>. Returns an empty list if it has none."
    subtiles: list[XmlSubTile] = []
    subtile: etree._Element

    for subtile in root.findall("tile", None):
        values = {}

        _sheet = subtile.get("sheet")
        assert _sheet is not None
        sheet_id = parse_source_sheet(source_file, _sheet)
        if str(sheet_id) in xml_tile_sheets:
            sheet = xml_tile_sheets[str(sheet_id)]
        else:
            assert xml_tile_sheets, (
                "You must load all Tilesheets before loading any tiles"
            )
            sheet = load_tilesheet(sheet_id, None)

        values["sheet"] = sheet
        simple_fields = ("x", "y", "offsetX", "offsetY")
        for field in simple_fields:
            value = subtile.get(field, getattr(DEFAULT_XML_SUB_TILE, field))
            values[field] = value

        subtiles.append(XmlSubTile.model_validate(values))
    return subtiles


def load_tile(source_file: Path, tile: etree._Element) -> XmlTile:
    "Parses a <tile> element"
    _id = tile.get("id")
    base_tile = xml_tiles.get(tile.get("equals", ""), DEFAULT_XML_TILE)
    _sheet = tile.get("sheet", None)
    assert _id is not None and (
        _sheet is not None or base_tile.sheet != DEFAULT_XML_TILE
    )
    if _sheet is None:
        sheet = base_tile.sheet
    elif str(sheet_id := parse_source_sheet(source_file, _sheet)) in xml_tile_sheets:
        sheet = xml_tile_sheets[str(sheet_id)]
    else:
        assert xml_tile_sheets, "You must load all Tilesheets before loading any tiles"
        sheet = load_tilesheet(sheet_id, None)

    values = {}
    values["id"] = _id
    values["sheet"] = sheet
    values["equals"] = tile.get("equals")
    simple_fields = ("x", "y", "offsetX", "offsetY")
    for field in simple_fields:
        value = tile.get(field, getattr(base_tile, field))
        values[field] = value

    result = XmlTile.model_validate(values | {"subtiles": []})
    result.subtiles = parse_sub_tiles(source_file, tile)
    xml_tiles[result.id] = result
    return result


def parse_animation_frames(
    animation: XmlAnimation, anim: etree._Element
) -> list[XmlAnimationFrame]:
    "Parse <frame> tags inside of a <animation>. Returns an empty list if it has none."
    frames: list[XmlAnimationFrame] = []
    frame: etree._Element

    for frame in anim.findall("frame", None):
        values = {}
        # TODO DOUBLE CHECK X/Y
        values["x"] = frame.get("x", animation.x)
        values["y"] = frame.get("y", animation.y)
        values["glow"] = frame.get("glow", animation.glow)
        simple_fields = (
            "count",
            "length",
            "visible",
            "repeat",
            "reverse",
            "offsetX",
            "offsetY",
            "parentX",
            "parentY",
        )
        for field in simple_fields:
            value = frame.get(field, getattr(DEFAULT_XML_ANIMATION_FRAME, field))
            values[field] = value

        frames.append(XmlAnimationFrame.model_validate(values))
    return frames


def parse_appended_animation(
    animation: XmlAnimation, anim: etree._Element
) -> list[XmlAppendedAnimation]:
    "Parse <append> tags inside of a <animation>. Returns an empty list if it has none."
    frames: list[XmlAppendedAnimation] = []
    appended: etree._Element

    for appended in anim.findall("append", None):
        values = {}
        values["tile"] = appended.get("tile")
        values["animation"] = appended.get("animation", "single")
        values["color"] = Color.parse_color(
            appended.get("color", "fff"),
            float(appended.get("colorScale", "1.0")),
        )
        simple_fields = (
            "x",
            "y",
            "offsetX",
            "offsetY",
            "behind",
            "flip",
        )
        for field in simple_fields:
            value = appended.get(field, getattr(DEFAULT_XML_APPENDED_ANIMATION, field))
            values[field] = value

        frames.append(XmlAppendedAnimation.model_validate(values))
    return frames


def load_animation(anim: etree._Element) -> XmlAnimation:
    values = {}
    values["id"] = anim.get("id")
    values["equals"] = anim.get("equals")
    base_animation = xml_animations.get(anim.get("equals", ""), DEFAULT_XML_ANIMATION)
    values["tile"] = anim.get("tile", base_animation.tile)

    values["raw_color"] = anim.get("color", base_animation.raw_color)
    values["raw_color_scale"] = anim.get("color_scale", base_animation.raw_color_scale)
    values["color"] = Color.parse_color(
        anim.get("color", base_animation.raw_color),
        float(anim.get("colorScale", base_animation.raw_color_scale)),
    )
    simple_fields = (
        "x",
        "y",
        "count",
        "count",
        "length",
        "shift",
        "glow",
        "repeat",
        "reverse",
        "scale",
        "offsetX",
        "offsetY",
        "rotate",
    )
    for field in simple_fields:
        value = anim.get(field, getattr(base_animation, field))
        values[field] = value

    animation = XmlAnimation.model_validate(values | {"appends": [], "frames": []})
    xml_animations[animation.id] = animation
    animation.appends = parse_appended_animation(animation, anim)
    animation.frames = parse_animation_frames(animation, anim)
    return animation


"""
TODO......

    # Part 2 - Load the Images
    def get_tile_animation(
        self, tile_id: str, animation_id: str
    ) -> tuple[list[Image.Image], list[tuple[int, int]]]:
        # use the `single` animation if you want to load only a single frame
        # Returns:
        # - list of frames
        # - list of (offsetX, offsetY) tuples
        tile = self.tiles[tile_id]
        animation = self.animations[animation_id]
        sheet = tile.sheet
        image = Image.open(self.data_folder / sheet.source_file)

        n_cols = image.width // sheet.width
        # n_rows = image.height // sheet.height
        base_position = ((animation.x or 0) + tile.x) + (
            ((animation.y or 0) + tile.y) * n_cols
        )
        # base_position = (
        #     (animation.x if animation.x is not None else tile.x)
        #     + ((animation.y if animation.y is not None else tile.y) * n_cols)
        # )

        frames = []
        offsets = []
        for count in range(animation.count):
            position = base_position + count
            if sheet.frames:
                position = position % len(sheet.frames)
                frame = next(
                    (frame for frame in sheet.frames if frame.frame == position)
                )
                new_x, new_y = frame.x, frame.y
                width, height = frame.width or sheet.width, frame.height or sheet.height
                offsetX = (frame.offsetX or 0) + (animation.offsetX or 0)
                offsetY = (frame.offsetY or 0) + (animation.offsetY or 0)
            else:
                width, height = sheet.width, sheet.height
                offsetX = sheet.offsetX + (animation.offsetX or 0)
                offsetY = sheet.offsetY + (animation.offsetY or 0)
                new_y, new_x = divmod(position, n_cols)
                new_y, new_x = new_y * height, new_x * width

            img_frame = image.crop(
                (
                    new_x,
                    new_y,
                    new_x + width,
                    new_y + height,
                )
            )
            frames.append(img_frame)
            offsets.append((offsetX, offsetY))
        return frames, offsets

    @staticmethod
    def format_animation(
        frames: list[Image.Image], offsets: list[tuple[int, int]]
    ) -> list[Image.Image]:
        "Pads and offsets all frames to fit in an animation sequence"
        max_width = max(
            frame.width + abs(offset[0]) for frame, offset in zip(frames, offsets)
        )
        max_height = max(
            frame.height + abs(offset[1]) for frame, offset in zip(frames, offsets)
        )
        # Make sure that they are divisible by 2 (required for some programs)
        if max_width % 2:
            max_width += 1
        if max_height % 2:
            max_height += 1
        output = [Image.new(frame.mode, (max_width, max_height), 0) for frame in frames]
        for template, frame, offset in zip(output, frames, offsets):
            # anchor = (max_width - frame.width, max_height - frame.height)
            anchor = (0, 0)
            template.paste(frame, (anchor[0] + offset[0], anchor[1] + offset[1]))
        return output

    @classmethod
    def from_aggregated_xml(
        cls, data_folder: Path, aggregated_xml: etree._ElementTree
    ) -> "TileManager":
        manager = TileManager(data_folder)

        # Part 1) Tilesheets
        # Register all Tilesheets with an explicit definition
        # (with non-default settings such as setting its width, height or frames)
        for source, sheet in manager.iterate_elements(aggregated_xml, "tilesheet"):
            sheet_id = source.parent / sheet.get("id", None)
            manager.load_tilesheet(sheet_id, sheet)

        # Part 2) Tiles
        equal_tiles: dict[str, str] = {}
        for source, tile in manager.iterate_elements(aggregated_xml, "tile"):
            if (eq := tile.get("equals", None)) is not None:
                equal_tiles[tile.get("id", None)] = eq
                continue  # Handled later
            if tile.get("sheet", None) is None:
                continue  # Ignored
            manager.load_tile(source, tile)

        for equal_tile, source_tile in equal_tiles.items():
            if source_tile == "empty":
                continue
            manager.tiles[equal_tile] = manager.tiles[source_tile]

        del equal_tiles

        for source, animation in manager.iterate_elements(aggregated_xml, "animation"):
            manager.load_animation(animation)

        return manager

        """

if __name__ == "__main__":

    def main():
        input_file = "clean/aggregated.xml"
        # data_folder = Path("data")

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

        print("xml_tile_sheets", len(xml_tile_sheets))
        print(
            "sheet.images", sum(len(sheet.images) for sheet in xml_tile_sheets.values())
        )

        print("xml_tiles", len(xml_tiles))
        print("tile.subtiles", sum(len(tile.subtiles) for tile in xml_tiles.values()))

        print("xml_animations", len(xml_animations))
        print(
            "animation.appends",
            sum(len(animation.appends) for animation in xml_animations.values()),
        )
        print(
            "animation.frames",
            sum(len(animation.frames) for animation in xml_animations.values()),
        )
        # breakpoint()

    main()
