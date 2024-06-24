"Utility classes for parsing tile animations"
from lxml import etree
from pathlib import Path
from dataclasses import dataclass
from PIL import Image

@dataclass
class Frame:
    frame: int
    x: int
    y: int
    width: int | None
    height: int | None
    offsetX: int | None
    offsetY: int | None

@dataclass
class Tilesheet:
    id: str
    source_file: Path
    width: int
    height: int
    offsetX: int
    offsetY: int
    frames: list[Frame]

@dataclass
class Tile:
    id: str
    source_file: Path
    sheet: Tilesheet
    x: int
    y: int

@dataclass
class Animation:
    id: str
    count: int
    x: int | None
    y: int | None
    offsetX: int | None
    offsetY: int | None


def _get_default(frames, frame_index, field, default):
    'Find the `equals=` frame and grab its field, or return a default value'
    return next((getattr(frame, field) for frame in frames if frame.frame == frame_index), default)

_frame_defaults = {
    "frame": 0,
    "x": 0,
    "y": 0,
    "width": None,  # "Inherited" from the <sheet>
    "height": None,
    "offsetX": None,
    "offsetY": None,    
}

class TileManager:
    def __init__(self, data_folder: Path):
        self.data_folder = data_folder
        self.tilesheets: dict[Path, Tilesheet] = {}
        self.tiles: dict[str, Tile] = {}
        self.animations: dict[str, Animation] = {}

    # Part 1 - Load data
    def load_tilesheet(self, sheet_id: Path, sheet: etree._Element | None) -> Tilesheet:
        "Parses a <sheet> element, or a reference to a tilesheet which does not have an explicitly <sheet> tag (using default values)"
        if sheet is None:  # Default settings with no explicit <sheet>
            tilesheet = Tilesheet(
                id=sheet_id.name,
                source_file=sheet_id,
                width=16,
                height=16,
                offsetX=0,
                offsetY=0,
                frames=[],
            )
        else:  # Custom <sheet> definition
            # If it has a `sheet` tag, use that for the actual image instead of the `id`
            sheet_image_path = sheet_id.parent / (sheet.get("sheet", sheet.get("id", None)))
            tilesheet = Tilesheet(
                id=sheet.get("id", None),
                source_file=sheet_image_path,
                width=int(sheet.get("width", 16)),
                height=int(sheet.get("height", 16)),
                offsetX=int(sheet.get("offsetX", 0)),
                offsetY=int(sheet.get("offsetY", 0)),
                frames=self.parse_frames(sheet),
            )
            for frame in tilesheet.frames:
                for field in ('width', 'height', 'offsetX', 'offsetY'):
                    if getattr(frame, field) is None:  # Set defaults for all Frames
                        setattr(frame, field, getattr(tilesheet, field))
        self.tilesheets[sheet_id] = tilesheet
        return tilesheet

    def load_tile(self, source_file: Path, tile: etree._Element) -> Tile:
        "Parses a <tile> element"
        sheet_id = self.parse_source_sheet(source_file, tile.get("sheet", None))
        if sheet_id not in self.tilesheets:
            assert self.tilesheets, "You must load all Tilesheets before loading any tiles"
            sheet = self.load_tilesheet(sheet_id, None)
        else:
            sheet = self.tilesheets[sheet_id]

        result = Tile(
            id=tile.get("id", None),
            source_file=source_file,
            sheet=sheet,
            x=int(tile.get("x", 0)),
            y=int(tile.get("y", 0)),
        )
        self.tiles[result.id] = result
        return result

    def load_animation(self, animation: etree._Element) -> Animation:
        def _load(field: str):
            result = animation.get(field, None)
            if result is not None:
                return int(float(result))
        anim = Animation(
            id=animation.get("id", None),
            count=int(animation.get("count", 1)),
            x=_load("x"),
            y=_load("y"),
            offsetX=_load("offsetX"),
            offsetY=_load("offsetY"),
        )
        self.animations[anim.id] = anim
        return anim

    # Helpers for Part 1
    @staticmethod
    def parse_frames(sheet: etree._Element) -> list[Frame]:
        "Parse <image> tags inside of a <sheet>. Returns an empty list if it has none."
        frames = []
        frame: etree._Element
        for frame in sheet.findall("image", None):
            fields = {}
            equals = frame.get("equals", None)
            for field, default in _frame_defaults.items():
                if equals is not None:
                    default = _get_default(frames, int(equals), field, default)
                result = frame.get(field, default)
                fields[field] = int(result) if result is not None else None

            frames.append(Frame(**fields))
        frames.sort(key = lambda frame: frame.frame)
        return frames

    @staticmethod
    def parse_source_sheet(source_file: Path, sheet_id: str) -> Path:
        "Resolve the path to a Tilesheet"
        if '{' in sheet_id:
            return Path(sheet_id.replace('{', '').replace('}', ''))
        else:
            return Path(source_file).parent / sheet_id

    # Part 2 - Load the Images
    def get_tile_animation(self, tile_id: str, animation_id: str) -> tuple[list[Image.Image], list[tuple[int, int]]]:
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
        base_position = ((animation.x or 0) + tile.x) + (((animation.y or 0) + tile.y) * n_cols)
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
                frame = next((frame for frame in sheet.frames if frame.frame == position))
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

            img_frame = image.crop((
                new_x, new_y,
                new_x + width, new_y + height,
            ))
            frames.append(img_frame)
            offsets.append((offsetX, offsetY))
        return frames, offsets

    @staticmethod
    def format_animation(frames: list[Image.Image], offsets: list[tuple[int, int]]) -> list[Image.Image]:
        "Pads and offsets all frames to fit in an animation sequence"
        max_width = max(frame.width + abs(offset[0]) for frame, offset in zip(frames, offsets))
        max_height = max(frame.height + abs(offset[1]) for frame, offset in zip(frames, offsets))
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

    # Part 3 - Utils
    @staticmethod
    def iterate_elements(aggregated_xml: etree._ElementTree, element_name: str) -> list[tuple[Path, etree._Element]]:
        result = []
        for source in aggregated_xml.findall("./", None):
            source_file = Path(source.get("source", None))
            for element in source.findall(element_name, None):
                result.append((source_file, element))
        return result


    @classmethod
    def from_aggregated_xml(cls, data_folder: Path, aggregated_xml: etree._ElementTree) -> 'TileManager':
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
            if source_tile == 'empty':
                continue
            manager.tiles[equal_tile] = manager.tiles[source_tile]

        del equal_tiles

        for source, animation in manager.iterate_elements(aggregated_xml, "animation"):
            manager.load_animation(animation)

        return manager
