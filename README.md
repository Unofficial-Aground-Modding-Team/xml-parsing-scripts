# xml-parsing-scripts
A collection of scripts used to parse data from FancyFish games

Currently supports the following operations, intended for assisting in the creation of the Aground wiki:
- Cleaning into a format understood by standard parsers (clean.py)
- Aggregating into a single file (main.py)
- Parse items data, more specifically
- - items.py : The item's definition, while also 'joining' on some relations such as the recipes that mention the item
- - item_icons.py : The item's icon, also parsing all tiles and tilesheets
