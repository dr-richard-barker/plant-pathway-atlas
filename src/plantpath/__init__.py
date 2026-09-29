"""
Plant Pathway Atlas (plantpath)

A modern, high-information-density pathway visualization package and omics projection
framework for plant systems biology — uniting MapMan BIN hierarchies, PlantCyc metabolic
reactions, and ggPlant anatomical geometries.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Richard Barker"

from .layout import Box, LaidOutNode, place_rows, size_node, bounding_box
from .render import render_svg, OKABE_ITO
from .maps import MapSpec, LaidOutMap, load_map, compile_map
from .project import project_expression, Projection, NodeValue
from .ortho import project_orthologs, Coverage, Ortholog, OrthologyError
from .spatial import SpatialOrganMap, load_ggplant_organs
from .mapman import MapManBin, MapManOntology

__all__ = [
    "Box",
    "LaidOutNode",
    "place_rows",
    "size_node",
    "bounding_box",
    "render_svg",
    "OKABE_ITO",
    "MapSpec",
    "LaidOutMap",
    "load_map",
    "compile_map",
    "project_expression",
    "Projection",
    "NodeValue",
    "project_orthologs",
    "Coverage",
    "Ortholog",
    "OrthologyError",
    "SpatialOrganMap",
    "load_ggplant_organs",
    "MapManBin",
    "MapManOntology",
]
