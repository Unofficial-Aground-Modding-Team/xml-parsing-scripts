from collections import defaultdict

from lxml import etree

input_file = "clean/aggregated.xml"
output_file = "clean/structure_overview.xml"

attributes = defaultdict(set)
children = {}

tree = etree.parse(input_file)
root = tree.getroot()


def _register_path(tag_path: str) -> dict:
    child = children
    for part in tag_path.split("."):
        child = child.setdefault(part, {})
    return child


# Iterate though Root, extract all Children and Attributes
def walk(elem, parent_path=""):
    tag_path = f"{parent_path}.{elem.tag}" if parent_path else elem.tag
    _register_path(tag_path)
    # Collect attributes
    for attr in elem.attrib:
        attributes[tag_path].add(attr)
    # Collect children
    for child in elem:
        walk(child, tag_path)


walk(root)


# (2) Build the structure tree back from children and attributes
def build_structure(tag, parent_path=""):
    tag_path = f"{parent_path}.{tag}" if parent_path else tag
    elem = etree.Element(tag)
    # Add attributes as <attr name="..."/>
    for attr in sorted(attributes.get(tag_path, [])):
        elem.set(attr, "")
    # Add children recursively
    child = _register_path(tag_path)
    for child_tag in sorted(child):
        elem.append(build_structure(child_tag, tag_path))
    return elem


rebuilt = build_structure(root.tag)

with open(output_file, "wb") as f:
    f.write(
        etree.tostring(
            rebuilt, pretty_print=True, xml_declaration=True, encoding="UTF-8"
        )
    )
