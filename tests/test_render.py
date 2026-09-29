import pathlib
import pytest
from plantpath.maps import compile_map, load_map
from plantpath.render import render_svg

MAPS_DIR = pathlib.Path(__file__).resolve().parent.parent / "maps" / "src"


def test_render_svg_light_and_dark():
    spec = load_map(MAPS_DIR / "PPA-01_central_metabolism.yaml")
    laid_out = compile_map(spec)

    svg_light = render_svg(laid_out, theme="light")
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in svg_light
    assert 'data-theme="light"' in svg_light
    assert 'class="ppa-canvas"' in svg_light
    assert 'id="node-CALVIN_CYCLE"' in svg_light

    svg_dark = render_svg(laid_out, theme="dark")
    assert 'data-theme="dark"' in svg_dark


def test_render_svg_data_attributes():
    spec = load_map(MAPS_DIR / "PPA-05_ros_redox.yaml")
    laid_out = compile_map(spec)
    svg = render_svg(laid_out)

    assert 'data-node-id="RBOH_BURST"' in svg
    assert 'data-bin="21.4"' in svg
    assert 'data-loci="AT5G47910,AT1G64060"' in svg
