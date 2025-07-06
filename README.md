# xml-parsing-scripts
A collection of scripts used to parse data from FancyFish games

Currently supports the following operations, intended for assisting in the creation of the Aground wiki:
- Cleaning into a format understood by standard parsers (clean.py)
- Aggregating into a single file (main.py)
- Parse items data, more specifically
- - items.py : The item's definition, while also 'joining' on some relations such as the recipes that mention the item
- - item_icons.py : The item's icon, also parsing all tiles and tilesheets

# General

Run `clean.py` to create the `/clean` folder
Run `main.py` to create the aggregated file
(parses and wraps files that are imported with includesRoot, and separates mod metadata from actual contents)

# Data types

Run `items.py`

# Notebook

```sh
# (install uv from https://docs.astral.sh/uv/)
uv sync --group notebook
# Copy the Aground/data folder from your Steam Library or Itch.io download over to this repository's folder
# (manually)
# Scripts to clean and prepare the data:
uv run src/fanfish/clean.py
uv run src/fanfish/main.py
uv run src/fanfish/utils/images/render.py
# Running the Notebook ('app mode', as in without showing the code):
uv run marimo run notebooks/interactive_render.py
# Editing the Notebook:
uv run marimo edit notebooks/interactive_render.py
```
