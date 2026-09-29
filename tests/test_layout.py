import pytest
from plantpath.layout import (
    Box,
    LaidOutNode,
    bounding_box,
    measure,
    place_rows,
    resolve_collisions,
    size_node,
    text_block,
    wrap,
)


def test_box_properties():
    b = Box(10.0, 20.0, 100.0, 50.0)
    assert b.x2 == 110.0
    assert b.y2 == 70.0
    assert b.cx == 60.0
    assert b.cy == 45.0


def test_box_overlaps_and_contains():
    b1 = Box(0, 0, 50, 50)
    b2 = Box(25, 25, 50, 50)
    b3 = Box(100, 100, 20, 20)
    assert b1.overlaps(b2)
    assert not b1.overlaps(b3)

    container = Box(0, 0, 100, 100)
    inside = Box(10, 10, 20, 20)
    assert container.contains(inside)
    assert not inside.contains(container)


def test_measure_and_wrap():
    w, h = measure("Photosystem II", 12.0, "normal")
    assert w > 0.0
    assert h == 12.0

    lines = wrap("Mitochondrial electron transport and oxidative phosphorylation", 12.0, 150.0)
    assert len(lines) > 1
    # Check that wrapping did not drop words
    words_original = "Mitochondrial electron transport and oxidative phosphorylation".split()
    words_wrapped = [w for ln in lines for w in ln.split()]
    assert words_original == words_wrapped


def test_size_node_simple():
    box, lines, sublines = size_node("AOX1A", 12.0, sublabel="Alternative Oxidase")
    assert box.w >= 96.0
    assert box.h > 20.0
    assert len(lines) == 1
    assert len(sublines) == 1


def test_size_node_complex():
    subunits = [{"symbol": "PsbA"}, {"symbol": "PsbD"}, {"symbol": "PsbB"}]
    box, lines, sublines = size_node(
        "Photosystem II Core", 12.0, kind="complex", subunits=subunits
    )
    assert box.w > 100.0
    assert box.h > 40.0


def test_place_rows_gutters():
    n1 = LaidOutNode(id="n1", box=Box(0, 0, 100, 40), lines=["N1"], font_size=12.0, font_weight="bold")
    n2 = LaidOutNode(id="n2", box=Box(0, 0, 100, 40), lines=["N2"], font_size=12.0, font_weight="bold")
    n3 = LaidOutNode(id="n3", box=Box(0, 0, 100, 40), lines=["N3"], font_size=12.0, font_weight="bold")

    bbox = place_rows([[n1, n2], [n3]], gutter_x=30.0, gutter_y=25.0)

    # In row 0, n2.box.x should equal n1.box.x2 + 30.0
    assert pytest.approx(n2.box.x) == n1.box.x2 + 30.0
    # Row 1 should be below row 0 by at least row height + gutter_y
    assert n3.box.y >= max(n1.box.y2, n2.box.y2) + 25.0
