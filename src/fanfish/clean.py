"Uses a custom XML Parser to convert Aground XML data into a standard XML format, so that normal parsers can read it"

# import pathlib
from pathlib import Path
import re

from xmlparser import XmlNode, parse

data_folder = Path("data")
clean_folder = Path("clean")

replacements = {
    # '"': "&quot;",
    # "'": "&apos;",
    r"<": "&lt;",
    r">": "&gt;",
    r"&(?!(gt;|lt;|amp;))": "&amp;",
}

replacements = [(re.compile(pattern), replacement) for pattern, replacement in replacements.items()]

def escape(string: str) -> str:
    for pattern, replacement in replacements:
        string = re.sub(pattern, replacement, string)
    return string

data: dict[Path, XmlNode] = {}

for file in data_folder.rglob("*.xml"):
    node = parse(file.read_text('UTF-8'))
    data[file] = node
    cleaned_file = clean_folder / (file.relative_to(data_folder))
    cleaned_file.parent.mkdir(parents=True, exist_ok=True)

    for child in (node, *node.get_children(recursive=True)):
        child.text = escape(child.text)
        child.attributes = {key: escape(value) for key, value in child.attributes.items()}

    cleaned_file.write_text(node.to_string(), encoding="UTF-8")
