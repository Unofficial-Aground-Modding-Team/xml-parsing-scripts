from pathlib import Path
from lxml import etree

from utils.images import TileManager

DATA_FOLDER = Path("data")

output_folder = Path("output/item_animations")
output_folder.mkdir(parents=True, exist_ok=True)
for file in output_folder.iterdir():
    file.unlink()

aggergated_file = Path("clean/aggregated.xml")
aggregated_xml: etree._ElementTree = etree.parse(aggergated_file, None)

manager = TileManager.from_aggregated_xml(DATA_FOLDER, aggregated_xml)

for source, item in manager.iterate_elements(aggregated_xml, "item"):
    animation = item.get("animation", "single")
    icon = item.get("icon", None)
    if icon is None:
        print(f"skipping {item.get("id", None)}")
        continue
    frames, offsets = manager.get_tile_animation(icon, animation)
    formatted = manager.format_animation(frames, offsets)
    
    for i, frame in enumerate(formatted):
        file = output_folder / f'{item.get("id", None)}_{i}.png'
        frame.save(file)
