import pathlib
import xml.etree.ElementTree as ET
import pytest
from plantpath.maps import compile_map, load_map
from plantpath.sbgn import SBGN_NS, PPA_NS, export_sbgn

MAPS_DIR = pathlib.Path(__file__).resolve().parent.parent / "maps" / "src"


def test_export_sbgn_valid_xml():
    spec = load_map(MAPS_DIR / "PPA-01_central_metabolism.yaml")
    laid_out = compile_map(spec)

    xml_str = export_sbgn(laid_out)
    root = ET.fromstring(xml_str)

    assert root.tag == f"{{{SBGN_NS}}}sbgn"
    map_el = root.find(f"{{{SBGN_NS}}}map")
    assert map_el is not None
    assert map_el.get("id") == "PPA-01"

    # Verify glyphs and annotations exist
    glyphs = map_el.findall(f"{{{SBGN_NS}}}glyph")
    assert len(glyphs) > 0

    calvin_glyph = [g for g in glyphs if g.get("id") == "CALVIN_CYCLE"][0]
    ext = calvin_glyph.find(f"{{{SBGN_NS}}}extension")
    assert ext is not None
    ann = ext.find(f"{{{PPA_NS}}}annotation")
    assert ann is not None
    assert ann.get("mapmanBin") == "1.2"
