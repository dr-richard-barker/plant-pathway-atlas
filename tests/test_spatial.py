import pytest
from plantpath.spatial import SpatialOrganMap, load_ggplant_organs


def test_spatial_organs_loading():
    organ_map = load_ggplant_organs()
    assert "rosette" in organ_map.available_organs
    assert "root_radial" in organ_map.available_organs

    rosette_polys = organ_map.get_organ_polygons("rosette")
    assert len(rosette_polys) == 15
    assert any(p["cellType"] == "Mesophyll" for p in rosette_polys)


def test_spatial_projection_and_svg():
    organ_map = load_ggplant_organs()
    cell_type_vals = {"Mesophyll": 2.5, "Epidermis": -1.2, "Vascular": 0.0}

    svg = organ_map.render_organ_svg("rosette", values=cell_type_vals)
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in svg
    assert 'class="plant-poly"' in svg
    assert 'data-cell-type="Mesophyll"' in svg
