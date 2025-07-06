import marimo

__generated_with = "0.14.10"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    from fanfish.utils.images.render import (
        DataContainer,
        Stage,
    )
    return DataContainer, Stage


@app.cell
def _(mo):
    width_slider = mo.ui.slider(64, 1024, 16, value=256, show_value=True, include_input=True)
    height_slider = mo.ui.slider(64, 1024, 16, value=256, show_value=True, include_input=True)
    mo.vstack(
        [mo.hstack(["Width:", width_slider], justify="start"), mo.hstack(["Height:", height_slider], justify="start")]
    )
    return height_slider, width_slider


@app.cell
def _(height_slider, width_slider):
    WIDTH = width_slider.value
    HEIGHT = height_slider.value
    return HEIGHT, WIDTH


@app.cell
def _(HEIGHT, Image, WIDTH):
    background = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))
    return (background,)


@app.cell
def _(DataContainer, HEIGHT, Stage, WIDTH):
    with open("clean/parsed.json", "r") as _file:
        data = DataContainer.model_validate_json(_file.read())
    stage = Stage(width=WIDTH, height=HEIGHT, data=data)
    return data, stage


@app.cell
def _():
    from PIL import Image
    return (Image,)


@app.cell
def _(mo):
    search_box = mo.ui.text(placeholder="Search by an ID...")
    search_box
    return (search_box,)


@app.cell
def _(data, mo, search_box):
    _query = search_box.value.split()
    tile_choices = [tile for tile in data.tiles if all(part in tile for part in _query)]
    animation_choices = [anim for anim in data.animations if all(part in anim for part in _query)]

    tile_selection = mo.ui.dropdown(options=tile_choices, allow_select_none=True, value=None)
    animation_selection = mo.ui.dropdown(options=["single"] + animation_choices, value="single")
    mo.vstack(
        [
            tile_selection,
            animation_selection,
        ]
    )
    return animation_selection, tile_selection


@app.cell
def _(animation_selection, tile_selection):
    tile_id = tile_selection.value
    animation_id = animation_selection.value
    return animation_id, tile_id


@app.cell
def _(animation_id, background, data, mo, stage, tile_id):
    gif = []
    mo.stop(tile_id is None or animation_id is None)
    _anim = data.animations[animation_id]
    _anim_len = max(len(anim.frames) for anim in _anim.animations)  # TODO swap to least common multiple
    for _index in range(_anim_len):
        stage.image = background.copy()
        stage.render(tile_id, animation_id, index=_index)
        gif.append(stage.image)

    gif[0].save("tmp.gif", save_all=True, append_images=gif[1:], loop=0, duration=1000 / 15)
    mo.image(open("tmp.gif", "rb"))
    return


if __name__ == "__main__":
    app.run()
