"""Merges all game XML files into one single aggregated XML file,
adding the source path into the XML and wrapping around files that are included by root."""

import pathlib
from lxml import etree

folder = pathlib.Path("clean")
mods_cache_file = folder / "mods.xml"
data_cache_file = folder / "aggregated.xml"

mods_cache_file.unlink(missing_ok=True)
data_cache_file.unlink(missing_ok=True)

# Load data
parser = etree.XMLParser(
    encoding="UTF-8",
    recover=False,
    remove_blank_text=True,
    remove_comments=True,
    remove_pis=False,
    strip_cdata=False,
)
mod_meta: dict [pathlib.Path, etree._Element]= {}
data: dict[pathlib.Path, etree._Element] = {}

for file in folder.rglob("*.xml"):
    tree: etree._ElementTree = etree.parse(file, parser)
    root: etree._Element = tree.getroot()
    if file.name == 'mod.xml':
        init = root.find("init", None)
        root.remove(init)
        mod_meta[file] = root
        data[file] = init
    else:
        data[file] = root


# Identify which files have no proper 'root'
requires_wrapper: set[pathlib.Path] = set()

for file, root in data.items():
    include: etree._Element
    for include in root.findall("include", None):
        if include.get("includeRoot", "false") == "true":
            included_file = file.parent / include.get("id", None)
            requires_wrapper.add(included_file)


requires_wrapper.difference_update({path for path in requires_wrapper if path.name == "music.xml"})

assert requires_wrapper.issubset(data.keys())

for path in requires_wrapper:
    wrapper: etree._Element = etree.Element("data", None, None)
    wrapper.append(data[path])
    data[path] = wrapper

# ---

aggregated_mods: etree._Element = etree.Element("xml", None, None)
for path, root in mod_meta.items():
    root.set("source", path.relative_to(folder).as_posix())
    aggregated_mods.append(root)

aggregated_data: etree._Element = etree.Element("xml", None, None)
for path, root in data.items():
    root.set("source", path.relative_to(folder).as_posix())
    aggregated_data.append(root)

final_tree_mods: etree._ElementTree = aggregated_mods.getroottree()
final_tree_mods.write(mods_cache_file)

final_tree_data: etree._ElementTree = aggregated_data.getroottree()
final_tree_data.write(data_cache_file)
