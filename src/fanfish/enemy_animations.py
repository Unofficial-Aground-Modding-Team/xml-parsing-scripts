from pathlib import Path
from lxml import etree

from utils.images import TileManager

DATA_FOLDER = Path("data")

output_folder = Path("output/enemy")
output_folder.mkdir(parents=True, exist_ok=True)

aggergated_file = Path("clean/aggregated.xml")
aggregated_xml: etree._ElementTree = etree.parse(aggergated_file, None)

manager = TileManager.from_aggregated_xml(DATA_FOLDER, aggregated_xml)

_animations = list(manager.animations.values())
anims: dict[str, list[tuple[str, str]]] = {}
for animation_id in (anim.id for anim in _animations if '.' in anim.id):
    base_object, animation_name = animation_id.rsplit('.', 1)
    anims.setdefault(base_object, []).append((animation_id, animation_name))


for source, enemy in manager.iterate_elements(aggregated_xml, "enemy"):
    for animation_id, animation_name in anims.get(enemy.get("tile", None), []):        
        frames, offsets = manager.get_tile_animation(enemy.get("tile", None), animation_id)
        formatted = manager.format_animation(frames, offsets)
        
        folder: Path = output_folder / enemy.get("id", None)            
        folder.mkdir(parents=True, exist_ok=True)
        for i, frame in enumerate(formatted):
            file = folder / f'{animation_id.replace('.', '_')}_{i}.png'
            frame.save(file)
