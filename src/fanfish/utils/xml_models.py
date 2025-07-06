from pydantic import BaseModel

from fanfish.utils.common import Color

"""
Original XML tags and attributes:
<tile animateSub="" autotile="" equals="" id="" offsetX="" offsetY="" sheet="" stride="" strideWidth="" x="" y="">
    <tile autotile="" offsetX="" offsetY="" p="" sheet="" x="" y="">
    <neighbor id=""/>
    </tile>
</tile>
<tilesheet dx="" dy="" extends="" height="" id="" name="" offsetX="" offsetY="" sheet="" width="">
    <image equals="" frame="" height="" offsetX="" offsetY="" width="" x="" y=""/>
</tilesheet>
<animation color="" colorScale="" count="" equals="" glow="" id="" length="" offset="" offsetX="" offsetY="" repeat="" reverse="" rotate="" scale="" shift="" tile="" x="" y="">
    <append animation="" behind="" color="" colorScale="" flip="" offsetX="" offsetY="" tile="" x="" y=""/>
    <frame count="" glow="" length="" offsetX="" offsetY="" parentX="" parentY="" repeat="" reverse="" visible="" x="" y=""/>
</animation>
"""


class XmlSubTile(BaseModel):
    # sheet: str
    sheet: "XmlTileSheet"
    # TODO consider if I care about autotile, p and neighbor
    x: int  # defaults to 0
    y: int  # defaults to 0
    offsetX: int  # defaults to 0
    offsetY: int  # defaults to 0


class XmlTile(BaseModel):
    id: str
    # sheet: str
    sheet: "XmlTileSheet"
    equals: str | None
    x: int  # defaults to 0
    y: int  # defaults to 0
    offsetX: int  # defaults to 0
    offsetY: int  # defaults to 0
    subtiles: list[XmlSubTile]


class XmlSheetImage(BaseModel):
    frame: int
    equals: int | None
    x: int  # defaults to 0
    y: int  # defaults to 0
    width: int  # defaults to same as sheet
    height: int  # defaults to same as sheet
    offsetX: int  # defaults to 0
    offsetY: int  # defaults to 0


class XmlTileSheet(BaseModel):
    id: str
    sheet: str
    name: str | None  # alias optionally used for extends
    extends: str | None
    width: int  # defaults to 16
    height: int  # defaults to 16
    offsetX: int  # defaults to 0
    offsetY: int  # defaults to 0
    images: list[XmlSheetImage]
    # TODO consider dx and dy? seem to be related to parallax


class XmlAnimationFrame(BaseModel):
    count: int  # defaults to 1
    length: int  # defaults to 1
    x: int  # defaults to inherit
    y: int  # defaults to inherit
    visible: bool  # defaults to False, do not render during this frame
    glow: bool  # defaults to inherit, ignores lightning in-game
    repeat: int  #  defaults to 0, not sure what it is used for
    reverse: bool  # pretty much ::-1, defaults to False
    offsetX: float  # defaults to 0
    offsetY: float  # defaults to 0
    parentX: (
        int  # defaults to 0 (offsets the player when they are using this equipment)
    )
    parentY: (
        int  # defaults to 0 (offsets the player when they are using this equipment)
    )


class XmlAppendedAnimation(BaseModel):
    tile: str
    x: int  # offset in the parent?...
    y: int  # offset in the parent?...
    animation: str
    color: Color
    offsetX: float  # offset in the children?..
    offsetY: float  # offset in the children?..
    behind: bool
    flip: bool


class XmlAnimation(BaseModel):
    id: str
    x: int  # defaults to 0
    y: int  # defaults to 0
    tile: str | None  # overwrites the tile being rendered
    equals: str | None
    count: int
    length: int
    shift: int  #  change the order of the frames, e.g. ABCD -> BCDA
    glow: bool  # defaults to False
    repeat: int  #  defaults to 0, not sure what it is used for
    reverse: bool  # pretty much ::-1, defaults to False
    raw_color: str  # defaults to fff
    raw_color_scale: float  # defaults to 1
    color: Color  # Parse color + colorScale.
    scale: int  # defaults to 1, makes it larger
    offsetX: float  # defaults to 0
    offsetY: float  # defaults to 0
    rotate: float  # degrees to rotate the tile (e.g. jumpship)
    appends: list[XmlAppendedAnimation]
    frames: list[XmlAnimationFrame]
    # TODO THINK ABOUT offset? (hair etc.)
