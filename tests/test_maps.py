import pathlib
import pytest
from plantpath.maps import compile_map, load_map

MAPS_DIR = pathlib.Path(__file__).resolve().parent.parent / "maps" / "src"


def test_load_and_compile_ppa01():
    spec = load_map(MAPS_DIR / "PPA-01_central_metabolism.yaml")
    assert spec.id == "PPA-01"
    assert len(spec.lanes) == 5

    laid_out = compile_map(spec)
    assert len(laid_out.nodes) == 15
    assert len(laid_out.compartments) >= 3
    assert laid_out.canvas_box.w >= 800.0
    assert laid_out.canvas_box.h >= 600.0


def test_load_and_compile_ppa02():
    spec = load_map(MAPS_DIR / "PPA-02_photosynthesis.yaml")
    assert spec.id == "PPA-02"
    laid_out = compile_map(spec)
    assert len(laid_out.nodes) == 12
    assert any(n.id == "CYTOCHROME_B6F" for n in laid_out.nodes)


def test_load_and_compile_ppa05():
    spec = load_map(MAPS_DIR / "PPA-05_ros_redox.yaml")
    assert spec.id == "PPA-05"
    laid_out = compile_map(spec)
    assert len(laid_out.nodes) == 15
    assert any(n.id == "ASCORBATE_PEROXIDASE" for n in laid_out.nodes)


def test_load_and_compile_all_maps():
    yaml_files = sorted(MAPS_DIR.glob("*.yaml"))
    assert len(yaml_files) == 16
    for yf in yaml_files:
        spec = load_map(yf)
        laid_out = compile_map(spec)
        assert len(laid_out.nodes) >= 10
        assert laid_out.canvas_box.w > 400
        assert laid_out.canvas_box.h > 300
