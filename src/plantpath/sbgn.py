"""
SBGN-ML Process Description (libsbgn 0.3) emitter for Plant Pathway Atlas.

Emits standard-compliant SBGN-ML with a <ppa:annotation> extension containing
MapMan BINs, PlantCyc reaction IDs, EC numbers, and AGI loci.
"""

from __future__ import annotations

import pathlib
import xml.etree.ElementTree as ET
from typing import Sequence

from .layout import Box, LaidOutNode
from .maps import LaidOutMap

SBGN_NS = "http://sbgn.org/libsbgn/0.3"
PPA_NS = "https://dr-richard-barker.github.io/plant-pathway-atlas/ppa/1.0"

KIND_TO_GLYPH = {
    "simple": "macromolecule",
    "complex": "complex",
    "family": "macromolecule",
    "metabolite": "simple chemical",
    "reaction": "process",
}

EDGE_TO_ARC = {
    "flux": "consumption",
    "catalysis": "catalysis",
    "inhibition": "inhibition",
    "activation": "stimulation",
}


def _bbox(el: ET.Element, box: Box) -> None:
    ET.SubElement(
        el,
        "bbox",
        {"x": f"{box.x:.2f}", "y": f"{box.y:.2f}", "w": f"{box.w:.2f}", "h": f"{box.h:.2f}"},
    )


def _annotation(glyph: ET.Element, node: LaidOutNode) -> None:
    ext = ET.SubElement(glyph, "extension")
    ann = ET.SubElement(ext, f"{{{PPA_NS}}}annotation", {"xmlns:ppa": PPA_NS})
    ann.set("nodeId", node.id)
    if node.compartment:
        ann.set("compartment", node.compartment)
    if "mapman_bin" in node.payload:
        ann.set("mapmanBin", str(node.payload["mapman_bin"]))
    if "ec" in node.payload:
        ann.set("ecNumber", str(node.payload["ec"]))

    raw_loci = node.payload.get("loci", [])
    if not raw_loci and node.subunits:
        raw_loci = [s.get("locus", "") for s in node.subunits if s.get("locus")]
    for loc in raw_loci:
        if loc:
            ET.SubElement(ann, f"{{{PPA_NS}}}locus").text = loc


def export_sbgn(laid_out_map: LaidOutMap, out_path: pathlib.Path | None = None) -> str:
    """Generate SBGN-ML PD XML for a LaidOutMap."""
    sbgn = ET.Element("sbgn", {"xmlns": SBGN_NS})
    map_el = ET.SubElement(sbgn, "map", {"id": laid_out_map.id, "language": "process description"})

    _bbox(map_el, laid_out_map.canvas_box)

    # Compartments
    for comp in laid_out_map.compartments:
        cid = comp["id"]
        cbox = comp["box"]
        cglyph = ET.SubElement(map_el, "glyph", {"id": f"comp_{cid}", "class": "compartment"})
        c_label = ET.SubElement(cglyph, "label", {"text": cid.replace("_", " ").title()})
        _bbox(cglyph, cbox)

    # Nodes
    for node in laid_out_map.nodes:
        gclass = KIND_TO_GLYPH.get(node.kind, "unspecified entity")
        glyph = ET.SubElement(map_el, "glyph", {"id": node.id, "class": gclass})
        if node.compartment:
            glyph.set("compartmentRef", f"comp_{node.compartment}")

        label_text = " ".join(node.lines)
        lbl = ET.SubElement(glyph, "label", {"text": label_text})
        _bbox(glyph, node.box)
        _annotation(glyph, node)

    # Edges / Arcs
    for idx, e in enumerate(laid_out_map.edges):
        aclass = EDGE_TO_ARC.get(e.get("class", "flux"), "unknown influence")
        arc = ET.SubElement(
            map_el,
            "arc",
            {"id": f"arc_{idx}", "class": aclass, "source": e["from"], "target": e["to"]},
        )
        sx, sy = e["start"]
        ex, ey = e["end"]
        ET.SubElement(arc, "start", {"x": f"{sx:.2f}", "y": f"{sy:.2f}"})
        ET.SubElement(arc, "end", {"x": f"{ex:.2f}", "y": f"{ey:.2f}"})

    tree = ET.ElementTree(sbgn)
    ET.indent(tree, space="  ")
    xml_str = ET.tostring(sbgn, encoding="utf-8", xml_declaration=True).decode("utf-8")

    if out_path:
        out_path = pathlib.Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(xml_str, encoding="utf-8")

    return xml_str
