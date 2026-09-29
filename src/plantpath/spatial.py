"""
Spatial anatomy and ggPlant polygon integration for the Plant Pathway Atlas.

Provides anatomical organ-level maps (rosette, root cross-section, root tip, leaf cross-section,
inflorescence) and bridges tissue/cell-type expression to subcellular metabolic pathways.
"""

from __future__ import annotations

import html
import json
import pathlib
from typing import Sequence

DEFAULT_DATA_PATH = pathlib.Path(__file__).resolve().parents[2] / "spatial" / "data" / "ggplant_organs.json"


def esc(s: str | None) -> str:
    return html.escape(str(s or ""), quote=True)


class SpatialOrganMap:
    """Manages anatomical cell and tissue polygons and projects spatial omics."""

    def __init__(self, data_path: pathlib.Path | None = None):
        self.path = pathlib.Path(data_path or DEFAULT_DATA_PATH)
        self.organs: dict[str, list[dict]] = {}
        if self.path.exists():
            self.organs = json.loads(self.path.read_text(encoding="utf-8"))

    @property
    def available_organs(self) -> list[str]:
        return list(self.organs.keys())

    def get_organ_polygons(self, organ: str) -> list[dict]:
        return self.organs.get(organ.lower(), [])

    def project_cell_type_data(
        self, organ: str, cell_type_values: dict[str, float]
    ) -> dict[str, float]:
        """Project expression values onto individual polygon IDs based on their cellType."""
        polys = self.get_organ_polygons(organ)
        cell_values: dict[str, float] = {}
        for p in polys:
            ctype = p.get("cellType", "")
            pid = p.get("id", "")
            if ctype in cell_type_values:
                cell_values[pid] = cell_type_values[ctype]
        return cell_values

    def render_organ_svg(
        self,
        organ: str,
        *,
        values: dict[str, float] | None = None,
        theme: str = "light",
        width: int = 500,
        height: int = 500,
    ) -> str:
        """Render an anatomical organ into a standalone vector SVG."""
        polys = self.get_organ_polygons(organ)
        if not polys:
            raise ValueError(f"Unknown organ {organ!r}. Available: {self.available_organs}")

        val_map = values or {}

        # Compute bounding box from polygon points
        all_pts: list[tuple[float, float]] = []
        for p in polys:
            pts_str = p.get("points", "")
            for pair in pts_str.split():
                if "," in pair:
                    try:
                        px, py = pair.split(",")
                        all_pts.append((float(px), float(py)))
                    except ValueError:
                        pass

        if all_pts:
            min_x = min(pt[0] for pt in all_pts) - 10.0
            min_y = min(pt[1] for pt in all_pts) - 10.0
            max_x = max(pt[0] for pt in all_pts) + 10.0
            max_y = max(pt[1] for pt in all_pts) + 10.0
            vb_w = max_x - min_x
            vb_h = max_y - min_y
        else:
            min_x, min_y, vb_w, vb_h = 0.0, 0.0, float(width), float(height)

        parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{min_x:.1f} {min_y:.1f} {vb_w:.1f} {vb_h:.1f}" '
            f'width="{width}" height="{height}" data-theme="{esc(theme)}" data-organ="{esc(organ)}">',
            "<defs><style>",
            """
            .plant-poly {
              stroke: #0f172a;
              stroke-width: 1.2px;
              stroke-linejoin: round;
              transition: fill 0.25s ease, stroke-width 0.15s ease, stroke 0.15s ease;
              cursor: pointer;
            }
            .plant-poly:hover {
              stroke: #D55E00 !important;
              stroke-width: 2.8px !important;
              filter: drop-shadow(0 0 5px rgba(213, 94, 0, 0.6));
            }
            """,
            "</defs>",
        ]

        for p in polys:
            pid = p.get("id", "")
            pts = p.get("points", "")
            ctype = p.get("cellType", "")
            cname = p.get("name", pid)
            default_fill = p.get("defaultFill", "#e2e8f0")

            # Determine fill color if value is provided
            fill = default_fill
            if pid in val_map:
                v = val_map[pid]
                from .render import _color_for_value

                fill = _color_for_value(v)
            elif ctype in val_map:
                v = val_map[ctype]
                from .render import _color_for_value

                fill = _color_for_value(v)

            parts.append(
                f'<polygon class="plant-poly" id="{esc(pid)}" '
                f'points="{esc(pts)}" fill="{esc(fill)}" '
                f'data-id="{esc(pid)}" data-cell-type="{esc(ctype)}" '
                f'data-name="{esc(cname)}">'
                f"<title>{esc(cname)} ({esc(ctype)})</title>"
                f"</polygon>"
            )

        parts.append("</svg>")
        return "\n".join(parts)


def load_ggplant_organs(data_path: pathlib.Path | None = None) -> SpatialOrganMap:
    """Convenience helper to initialize SpatialOrganMap."""
    return SpatialOrganMap(data_path)
