import copy
import math
from pathlib import Path
from PIL import Image
from fanfish.utils.models import (
    AbstractAnimation,
    AnimationFrame,
    AnimationSequence,
    ImageFrame,
    Tile,
    TilePart,
    TileSheet,
)
from fanfish.utils.xml_models import (
    XmlAnimation,
    XmlAnimationFrame,
    XmlAppendedAnimation,
    XmlSheetImage,
    XmlSubTile,
    XmlTile,
    XmlTileSheet,
)

DATA_FOLDER = Path("data")

tilesheets: dict[str, TileSheet] = {}
tiles: dict[str, Tile] = {}
animations: dict[str, AnimationSequence] = {}

def convert_tilesheet(tilesheet: XmlTileSheet) -> TileSheet:
    path = Path(tilesheet.sheet)
    frames = []
    if tilesheet.images:
        for frame in tilesheet.images:
            frames.append(ImageFrame.model_validate(frame.model_dump()))
            # TODO DOUBLE CHECK IF I MUST OFFSET BY THE TILESHEET'S OFFSETS
    else:
        im = Image.open(DATA_FOLDER / path)
        full_width, full_height = im.size
        # TODO DOUBLE CHECK THIS DIVISION
        rows = math.ceil(full_height / tilesheet.height)
        cols = math.ceil(full_width / tilesheet.width)
        for y in range(rows):
            for x in range(cols):
                index = y * cols + x
                img_frame = ImageFrame(
                    index=index,
                    x=x,
                    y=y,
                    width=tilesheet.width,
                    height=tilesheet.height,
                    offsetX=tilesheet.offsetX,
                    offsetY=tilesheet.offsetY,
                )
                frames.append(img_frame)
    return TileSheet(id=tilesheet.id, sheet_file=path, frames=frames)
    

def convert_tile(tile: XmlTile) -> Tile:
    parts = []
    parts.append(TilePart(sheet_id=tile.sheet.id, x=tile.x, y=tile.y, offsetX=tile.offsetX, offsetY=tile.offsetY))
    for subtile in tile.subtiles:
        parts.append(TilePart(
            sheet_id=subtile.sheet.id,
            x=subtile.x, y=subtile.y, offsetX=subtile.offsetX, offsetY=subtile.offsetY,
        ))
    return Tile(id=tile.id, subtiles=parts)

def convert_animation(animation: XmlAnimation) -> AnimationSequence:
    abs_animations: list[AbstractAnimation] = []
    main_frames: list[AnimationFrame] = []
    for count in range(animation.count):
        for _ in range(animation.length):
            frame = AnimationFrame(
                visible=True,
                x=animation.x + count,
                y=animation.y,
                offsetX=animation.offsetX,
                offsetY=animation.offsetY,
                color=animation.color,
                glow=animation.glow,
            )
            main_frames.append(frame)
            del frame
        del count

    for _ in range(animation.shift):
        for _ in range(animation.length):
            main_frames.append(main_frames.pop(0))
    # TODO FIGURE OUT HOW repeat WORKS

    for base_frame in animation.frames:
        extra = []
        # TODO ADD parentX AND parentY?
        for count in range(base_frame.count):
            for _ in range(base_frame.length):
                frame = AnimationFrame(
                    visible=True,
                    x=base_frame.x + count,
                    y=base_frame.y,
                    # TODO TEST WHICH OFFSET CALCULATION IS RIGHT
                    # offsetX=base_frame.offsetX + animation.offsetX,
                    # offsetY=base_frame.offsetY + animation.offsetY,
                    offsetX=base_frame.offsetX,
                    offsetY=base_frame.offsetY,
                    color=animation.color,
                    glow=base_frame.glow,
                )
                extra.append(frame)
                del frame
            del count
        if base_frame.reverse:
            extra.reverse()
        main_frames.extend(extra)
        del base_frame
        del extra

    if animation.reverse:
        main_frames.reverse()
    main_sequence = AbstractAnimation(
        overwrite_tile_id=animation.tile,
        rotate=animation.rotate,
        repeat=animation.repeat,
        scale=animation.scale,
        behind=False,
        flip=False,
        frames=main_frames,
    )
    abs_animations.append(main_sequence)

    # ---
    for appended in animation.appends:
        source = animations[appended.animation]
        for abs in source.animations:
            sequence = AbstractAnimation(
                overwrite_tile_id=appended.tile,
                rotate=abs.rotate,
                repeat=abs.repeat,
                scale=abs.scale,
                behind=appended.behind,
                flip=appended.flip,
                frames=copy.deepcopy(abs.frames),
            )
            if appended.color:
                for frame in sequence.frames:
                    frame.color *= appended.color
            abs_animations.append(sequence)
    # ---
    return AnimationSequence(id=animation.id, animations=abs_animations)

if __name__ == "__main__":
    from lxml import etree
    from fanfish.utils.images.parse_xml import (
        parse_source_sheet,
        load_tilesheet,
        load_tile,
        load_animation,
        xml_tile_sheets,
        xml_tiles,
        xml_animations,
    )

    def prepare():
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


    def main():
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
                if any((an := dependency.animation) is not None and an not in _solved for dependency in animation.appends):
                    continue

                converted = convert_animation(animation)
                animations[converted.id] = converted
                _solved.add(animation_id)
            _missing -= _solved
        if _missing:
            raise RuntimeError("Could not resolve animations equals=")

        print("tilesheets", len(tilesheets))
        print("tilesheets.frames", sum(len(sheet.frames) for sheet in tilesheets.values()))

        print("tiles", len(tiles))
        print("tiles.subtiles", sum(len(tile.subtiles) for tile in tiles.values()))

        print("animations", len(animations))
        print("animations.animations", sum(len(animation.animations) for animation in animations.values()))
        print("animations.animations.frames", sum((len(abs.frames) for animation in animations.values() for abs in animation.animations)))

    prepare()
    main()
