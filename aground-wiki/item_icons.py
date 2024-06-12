"Parses all Tiles and their Tilesheets, then find all icons used by items and extract them individually"

from lxml import etree
from pathlib import Path
from dataclasses import dataclass
from PIL import Image

DATA_FOLDER = Path("data")

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


cached = Path("clean/aggregated.xml")
output_folder = Path("output/items")

output_folder.mkdir(parents=True, exist_ok=True)

tree: etree._ElementTree = etree.parse(cached, None)

def show(element):
    'utils function for debugging'
    print(etree.tostring(element, pretty_print=True).decode())  # type: ignore

# Each element in the data list corresponds to one file's root <data> or equivalent
data: list[etree._Element] = tree.findall('./', None)

# NOTE: THE OUTPUT DOES NOT INCLUDES ANYTHING INHERITED FROM EXTENDING

items: list[etree._Element] = [item for root in data for item in root.findall("item", None)]


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


def create_tilesheet(path: Path, sheet: etree._Element | None) -> Tilesheet:
    "Parses a <sheet> element, or a reference to a tilesheet which does not have an explicitly <sheet> tag (using default values)"
    if sheet is None:
        return Tilesheet(
            id=path.name,
            source_file=path,
            width=16,
            height=16,
            offsetX=0,
            offsetY=0,
            frames=[],
        )
    else:
        tilesheet = Tilesheet(
            id=sheet.get("id", None),
            source_file=path,
            width=int(sheet.get("width", 16)),
            height=int(sheet.get("height", 16)),
            offsetX=int(sheet.get("offsetX", 0)),
            offsetY=int(sheet.get("offsetY", 0)),
            frames=parse_frames(sheet),
        )
        for frame in tilesheet.frames:
            for field in ('width', 'height', 'offsetX', 'offsetY'):
                if getattr(frame, field) is None:  # Set defaults for all Frames
                    setattr(frame, field, getattr(tilesheet, field))
        return tilesheet


tilesheets: dict[Path, Tilesheet] = {}

for source in data:
    sheet: etree._Element
    # Register all Tilesheets with an explicit definition (with non-default settings such as setting its width, height or frames)
    for sheet in source.findall("tilesheet", None):
        sheet_long_id = Path(source.get("source", None)).parent / sheet.get("id", None)
        # In some cases, the ID may differ from the actual file path, if `sheet='*.png'` is present
        sheet_path = Path(source.get("source", None)).parent / sheet.get("sheet", sheet.get("id", None))
        tilesheets[sheet_long_id] = create_tilesheet(sheet_path, sheet)

# ----------------

def parse_source_sheet(source_path: Path, sheet_id: str) -> Path:
    "Resolve the path to a Tilesheet"
    if '{' in sheet_id:
        return Path(sheet_id.replace('{', '').replace('}', ''))
    else:
        return Path(source_path).parent / source_sheet


def create_tile(sheet: Tilesheet, tile: etree._Element) -> Tile:
    "Parses a <tile> element"
    return Tile(
        id=tile.get("id", None),
        source_file=source_file,
        sheet=sheet,
        x=int(tile.get("x", 0)),
        y=int(tile.get("y", 0)),
    )

tiles: dict[str, Tile] = {}
_equal_tiles: dict[str, str] = {}

for source in data:
    tile: etree._Element
    source_file = Path(source.get("source", None))
    # Load all tiles
    for tile in source.findall("tile", None):
        if (eq := tile.get("equals", None)) is not None:
            _equal_tiles[tile.get("id", None)] = eq
            continue  # Handled later
        if (source_sheet := tile.get("sheet", None)) is None:
            print("Ignoring tile as it has no sheet", end='')
            show(tile)
            continue  # Ignored
        # Load the full path, then create with default settings if it's not registered
        sheet_path = parse_source_sheet(source_file, source_sheet)
        if sheet_path not in tilesheets:
            print(f"Creating sheet with default settings: {sheet_path}")
            tilesheets[sheet_path] = create_tilesheet(sheet_path, None)
        # Parse the tile from the tilesheet
        tiles[tile.get("id", None)] = create_tile(tilesheets[sheet_path], tile)


for equal_tile, source_tile in _equal_tiles.items():
    if source_tile == 'empty':
        continue
    tiles[equal_tile] = tiles[source_tile]

del _equal_tiles



def load_tile_image(tile: Tile) -> Image.Image:
    # TODO SUPPORT OFFSET
    # TODO CREATE GIF?
    tilesheet = tile.sheet
    # TODO Might want to 'cache' the image?
    image = Image.open(DATA_FOLDER / tilesheet.source_file)

    n_cols = image.width // tilesheet.width
    # n_rows = image.height // tilesheet.height
    if tilesheet.frames:
        position = tile.x + tile.y * n_cols
        frame = next((frame for frame in tilesheet.frames if frame.frame == position))
        new_y, new_x = divmod(frame.x + frame.y * n_cols, n_cols)
    else:
        new_y, new_x = divmod(tile.x + tile.y * n_cols, n_cols)

    return image.crop((
        new_x * tilesheet.width,
        new_y * tilesheet.height,
        (new_x + 1) * tilesheet.width,
        (new_y + 1) * tilesheet.height,
    ))


for source_data in data:
    item: etree._Element
    for item in source_data.findall("./item", None):
        # show(item)
        # print(tiles[item_icon])
        item_id = item.get("id", None)
        item_icon = item.get("icon", None)
        # TODO SUPPORT OTHER PROPERTIES (COLOR, COLORSCALE, EXTENDS, etc)
        if item_icon is None:
            continue
        icon = load_tile_image(tiles[item_icon])
        out_file = output_folder / (item_id + '.png')
        icon.save(out_file)
