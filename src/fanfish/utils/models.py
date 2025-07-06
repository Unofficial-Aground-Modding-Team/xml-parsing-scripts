from pathlib import Path

import pydantic
from pydantic import BaseModel, Field

from fanfish.utils.common import Color


class TilePart(BaseModel):
    sheet_id: str
    x: int  # defaults to 0
    y: int  # defaults to 0
    offsetX: int  # defaults to 0
    offsetY: int  # defaults to 0


class Tile(BaseModel):
    id: str
    subtiles: list[TilePart]


class ImageFrame(BaseModel):
    index: int = Field(
        validation_alias=pydantic.AliasChoices("index", "frame")
    )  # <tilesheet <image frame=''
    x: int  # defaults to 0
    y: int  # defaults to 0
    width: int  # defaults to same as sheet
    height: int  # defaults to same as sheet
    offsetX: int  # defaults to 0
    offsetY: int  # defaults to 0


class TileSheet(BaseModel):
    id: str
    sheet_file: Path
    frames: list[ImageFrame]
    # TODO consider dx and dy? seem to be related to parallax


class AnimationFrame(BaseModel):
    visible: bool  # defaults to False, do not render during this frame
    x: int  # defaults to inherit
    y: int  # defaults to inherit
    offsetX: float  # defaults to 0
    offsetY: float  # defaults to 0
    color: Color
    glow: bool


class AbstractAnimation(BaseModel):
    overwrite_tile_id: str | None
    rotate: float  # degrees to rotate the tile (e.g. jumpship)
    repeat: int  #  defaults to 0, not sure what it is used for
    scale: int  # defaults to 1, makes it larger
    behind: bool
    flip: bool
    frames: list[AnimationFrame]


class AnimationSequence(BaseModel):
    id: str
    animations: list[AbstractAnimation]
    # TODO THINK ABOUT offset? (hair etc.)
