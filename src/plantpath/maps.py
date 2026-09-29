"""
Declarative map specification, validation, and layout compilation.

Maps are authored without coordinates: lanes, compartments, and biological groupings
are declared; box sizes and canvas geometries are derived deterministically.
"""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Sequence

import yaml

from .layout import (
    CANVAS_MARGIN,
    COMPARTMENT_PAD,
    MIN_GUTTER_X,
    MIN_GUTTER_Y,
    Box,
    LaidOutNode,
    bounding_box,
    edge_anchors,
    place_rows,
    resolve_collisions,
    size_node,
)


class MapError(Exception):
    """Raised when a declarative map specification is invalid or uncompilable."""


@dataclasses.dataclass
class MapSpec:
    id: str
    title: str
    subtitle: str
    caption: str
    derived_from: str
    species_anchor: str
    lanes: list[dict]
    nodes: dict[str, dict]
    edges: list[dict]
    source_path: pathlib.Path | None = None

    @property
    def node_ids(self) -> list[str]:
        return [nid for lane in self.lanes for nid in lane.get("nodes", [])]


@dataclasses.dataclass
class LaidOutMap:
    id: str
    title: str
    subtitle: str
    caption: str
    canvas_box: Box
    nodes: list[LaidOutNode]
    edges: list[dict]
    compartments: list[dict]
    margin_x: float = 36.0
    margin_bottom: float = 48.0

    def node_by_id(self, nid: str) -> LaidOutNode | None:
        for n in self.nodes:
            if n.id == nid:
                return n
        return None


def load_map(path: str | pathlib.Path) -> MapSpec:
    """Load and validate a declarative map YAML specification."""
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Map specification not found: {p}")

    doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    for req in ("id", "title", "lanes"):
        if req not in doc:
            raise MapError(f"{p.name}: map missing required field {req!r}")

    nodes = {n["id"]: n for n in (doc.get("nodes") or [])}
    edges = []
    for e in doc.get("edges") or []:
        if isinstance(e, dict):
            edges.append(
                {
                    "from": e["from"],
                    "to": e["to"],
                    "class": e.get("class", "flux"),
                    "label": e.get("label", ""),
                }
            )
        elif isinstance(e, (list, tuple)) and len(e) >= 2:
            edges.append(
                {
                    "from": e[0],
                    "to": e[1],
                    "class": e[2] if len(e) > 2 else "flux",
                    "label": e[3] if len(e) > 3 else "",
                }
            )

    return MapSpec(
        id=doc["id"],
        title=doc["title"],
        subtitle=doc.get("subtitle", ""),
        caption=doc.get("caption", ""),
        derived_from=doc.get("derived_from", ""),
        species_anchor=doc.get("species_anchor", "arabidopsis_thaliana"),
        lanes=doc["lanes"],
        nodes=nodes,
        edges=edges,
        source_path=p,
    )


def compile_map(spec: MapSpec) -> LaidOutMap:
    """Compile a MapSpec into a concrete LaidOutMap with all geometries placed."""
    node_instances: dict[str, LaidOutNode] = {}
    rows_by_lane: list[list[LaidOutNode]] = []
    lane_compartments: list[str] = []

    # 1. Size all nodes
    for lane_idx, lane in enumerate(spec.lanes):
        lane_id = lane.get("id", f"lane_{lane_idx}")
        lane_comp = lane.get("compartment", "general")
        lane_compartments.append(lane_comp)
        lane_pref_width = float(lane.get("node_width", 180.0))

        current_row: list[LaidOutNode] = []
        for nid in lane.get("nodes", []):
            if nid not in spec.nodes:
                # Stub node if declared in lane but not in nodes dict
                ndata = {"id": nid, "label": nid.replace("_", " ").title()}
            else:
                ndata = spec.nodes[nid]

            label = ndata.get("label", nid.replace("_", " ").title())
            sublabel = ndata.get("sublabel", "")
            if not sublabel and "mapman_bin" in ndata:
                sublabel = f"BIN {ndata['mapman_bin']}"
            elif not sublabel and "ec" in ndata:
                sublabel = f"EC {ndata['ec']}"

            kind = ndata.get("kind", "simple")
            subunits = ndata.get("subunits", [])
            family_loci = ndata.get("family_loci", ndata.get("loci", []))

            box, lines, sublines = size_node(
                label,
                font_size=12.0,
                kind=kind,
                sublabel=sublabel,
                preferred_width=lane_pref_width,
                subunits=subunits,
                n_family_loci=len(family_loci) if kind == "family" else 0,
            )

            lnode = LaidOutNode(
                id=nid,
                box=box,
                lines=lines,
                font_size=12.0,
                font_weight="bold",
                kind=kind,
                sublines=sublines,
                sub_font_size=9.5,
                lane=lane_id,
                compartment=lane_comp,
                subunits=subunits,
                family_loci=family_loci,
                payload=ndata,
            )
            node_instances[nid] = lnode
            current_row.append(lnode)

        rows_by_lane.append(current_row)

    # 2. Place rows in vertical progression
    top_offset = 72.0  # Room for title and subtitle
    grid_box = place_rows(
        rows_by_lane,
        origin_x=40.0,
        origin_y=top_offset + 30.0,
        gutter_x=MIN_GUTTER_X,
        gutter_y=MIN_GUTTER_Y + 16.0,
        align="center",
    )

    # 3. Compute compartment bands
    compartments: list[dict] = []
    comp_node_map: dict[str, list[LaidOutNode]] = {}
    for n in node_instances.values():
        cid = n.compartment or "general"
        comp_node_map.setdefault(cid, []).append(n)

    for cid, cnodes in comp_node_map.items():
        if not cnodes:
            continue
        c_box = bounding_box(cnodes, pad=COMPARTMENT_PAD)
        # Give space for the compartment header text
        c_box.y -= 14.0
        c_box.h += 14.0
        compartments.append({"id": cid, "box": c_box})

    # 4. Route edges
    laid_out_edges: list[dict] = []
    for edge in spec.edges:
        fnid = edge["from"]
        tnid = edge["to"]
        if fnid not in node_instances or tnid not in node_instances:
            continue
        from_node = node_instances[fnid]
        to_node = node_instances[tnid]
        start_pt, end_pt = edge_anchors(from_node.box, to_node.box)
        laid_out_edges.append(
            {
                "from": fnid,
                "to": tnid,
                "start": start_pt,
                "end": end_pt,
                "class": edge.get("class", "flux"),
                "label": edge.get("label", ""),
            }
        )

    # 5. Calculate overall canvas dimensions
    all_boxes = [n.box for n in node_instances.values()] + [c["box"] for c in compartments]
    min_x = min((b.x for b in all_boxes), default=0.0) - CANVAS_MARGIN
    min_y = 0.0
    max_x = max((b.x2 for b in all_boxes), default=800.0) + CANVAS_MARGIN
    max_y = max((b.y2 for b in all_boxes), default=600.0) + 70.0  # Caption buffer

    canvas = Box(min_x, min_y, max(920.0, max_x - min_x), max(680.0, max_y - min_y))

    return LaidOutMap(
        id=spec.id,
        title=spec.title,
        subtitle=spec.subtitle,
        caption=spec.caption,
        canvas_box=canvas,
        nodes=list(node_instances.values()),
        edges=laid_out_edges,
        compartments=compartments,
        margin_x=40.0,
        margin_bottom=48.0,
    )
