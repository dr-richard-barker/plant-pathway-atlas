"""
Vector SVG rendering engine for the Plant Pathway Atlas.

Visual Principles:
1. High-Information-Density with Legibility: Measured typography ensures zero overflow.
2. Colorblind-Safe by Default: Okabe-Ito diverging palette (Vermillion for up, Blue for down).
3. "Chicklets 2.0": Structured representation of multi-subunit complexes and multi-gene families.
4. Native Dual-Theme: Clean light mode for print; high-contrast dark mode for screens.
5. Interactive Metadata: Emits DOM data attributes (data-node-id, data-loci, data-bin).
"""

from __future__ import annotations

import html
import textwrap
from typing import Sequence

from .layout import (
    LINE_SPACING,
    SVG_FONT_STACK,
    Box,
    LaidOutNode,
    edge_anchors,
    measure,
    text_block,
)

# Okabe-Ito palette
OKABE_ITO = {
    "orange": "#E69F00",
    "sky": "#56B4E9",
    "green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "purple": "#CC79A7",
    "black": "#000000",
    "neutral": "#64748B",
    "light_neutral": "#E2E8F0",
}

# Subcellular compartment themes
COMPARTMENT_THEMES = {
    "chloroplast_stroma": ("#065F46", "Chloroplast Stroma"),
    "thylakoid_membrane": ("#047857", "Thylakoid Membrane"),
    "thylakoid_lumen": ("#059669", "Thylakoid Lumen"),
    "chloroplast": ("#065F46", "Chloroplast"),
    "mitochondrial_matrix": ("#92400E", "Mitochondrial Matrix"),
    "mitochondrial_inner_membrane": ("#B45309", "Inner Mitochondrial Membrane"),
    "mitochondrion": ("#92400E", "Mitochondrion"),
    "peroxisome": ("#854D0E", "Peroxisome"),
    "vacuole": ("#1E40AF", "Vacuole"),
    "cytosol": ("#1E293B", "Cytosol"),
    "nucleus": ("#581C87", "Nucleus"),
    "endoplasmic_reticulum": ("#374151", "Endoplasmic Reticulum"),
    "plasma_membrane": ("#334155", "Plasma Membrane"),
    "apoplast": ("#475569", "Apoplast / Cell Wall"),
    "cell_wall": ("#475569", "Cell Wall"),
    "general": ("#334155", "Cellular Subsystem"),
}

TITLE_SIZE = 20.0
SUBTITLE_SIZE = 12.0
NODE_SIZE = 12.0
SUB_SIZE = 9.5
CAPTION_SIZE = 11.0


def esc(s: str | None) -> str:
    return html.escape(str(s or ""), quote=True)


def _color_for_value(val: float | None, max_fc: float = 3.0) -> str:
    """Map log2FC value to an Okabe-Ito diverging color hex string."""
    if val is None:
        return "var(--ppa-node-fill)"
    # Clamp -max_fc to +max_fc
    clamped = max(-max_fc, min(max_fc, float(val)))
    ratio = abs(clamped) / max_fc
    if clamped > 0:
        # Vermillion interpolate: #ffffff -> #D55E00 (213, 94, 0)
        r = int(255 - ratio * (255 - 213))
        g = int(255 - ratio * (255 - 94))
        b = int(255 - ratio * (255 - 0))
    elif clamped < 0:
        # Blue interpolate: #ffffff -> #0072B2 (0, 114, 178)
        r = int(255 - ratio * (255 - 0))
        g = int(255 - ratio * (255 - 114))
        b = int(255 - ratio * (255 - 178))
    else:
        return "var(--ppa-node-fill)"
    return f"#{r:02x}{g:02x}{b:02x}"


def _stylesheet() -> str:
    """CSS variables for light/dark themes and typography."""
    return textwrap.dedent(
        f"""
        :root {{
          --ppa-bg: #ffffff;
          --ppa-ink: #0f172a;
          --ppa-ink-soft: #475569;
          --ppa-node-fill: #f8fafc;
          --ppa-node-stroke: #1e293b;
          --ppa-hairline: #cbd5e1;
          --ppa-edge: #475569;
          --ppa-compartment-fill: rgba(15, 23, 42, 0.035);
          --ppa-compartment-stroke: rgba(15, 23, 42, 0.22);
          --ppa-accent: #0284c7;
          --ppa-up: #D55E00;
          --ppa-down: #0072B2;
        }}
        :root[data-theme="dark"] {{
          --ppa-bg: #0b0f17;
          --ppa-ink: #f1f5f9;
          --ppa-ink-soft: #94a3b8;
          --ppa-node-fill: #151c28;
          --ppa-node-stroke: #cbd5e1;
          --ppa-hairline: #334155;
          --ppa-edge: #94a3b8;
          --ppa-compartment-fill: rgba(255, 255, 255, 0.04);
          --ppa-compartment-stroke: rgba(255, 255, 255, 0.25);
          --ppa-accent: #38bdf8;
          --ppa-up: #ea580c;
          --ppa-down: #38bdf8;
        }}

        .ppa-canvas {{ fill: var(--ppa-bg, #ffffff); }}
        text {{ font-family: {SVG_FONT_STACK}; fill: var(--ppa-ink); }}
        .ppa-title {{ font-size: {TITLE_SIZE}px; font-weight: 700; fill: var(--ppa-ink); }}
        .ppa-subtitle {{ font-size: {SUBTITLE_SIZE}px; fill: var(--ppa-ink-soft); }}
        .ppa-caption {{ font-size: {CAPTION_SIZE}px; fill: var(--ppa-ink-soft); line-height: 1.4; }}
        .ppa-label {{ font-size: {NODE_SIZE}px; font-weight: 600; text-anchor: middle; }}
        .ppa-sub {{ font-size: {SUB_SIZE}px; fill: var(--ppa-ink-soft); font-weight: 400; text-anchor: middle; }}
        .ppa-subunit-text {{ font-size: 8.5px; font-weight: 600; fill: var(--ppa-ink); text-anchor: middle; }}
        .ppa-edge-label {{
          font-size: 9.5px;
          fill: var(--ppa-ink-soft);
          font-weight: 500;
          text-anchor: middle;
          paint-order: stroke fill;
          stroke: var(--ppa-bg, #ffffff);
          stroke-width: 3px;
          stroke-linejoin: round;
        }}

        .ppa-compartment-band {{
          fill: var(--ppa-compartment-fill);
          stroke: var(--ppa-compartment-stroke);
          stroke-width: 1.5px;
          stroke-dasharray: 6 3;
          rx: 10px;
        }}
        .ppa-compartment-title {{
          font-size: 11px;
          font-weight: 700;
          letter-spacing: 0.05em;
          text-transform: uppercase;
          fill: var(--ppa-ink-soft);
        }}

        .ppa-node {{
          cursor: pointer;
          transition: transform 0.15s ease, filter 0.15s ease;
        }}
        .ppa-node:hover {{
          filter: drop-shadow(0 4px 6px rgba(0, 0, 0, 0.15));
        }}
        .ppa-node rect, .ppa-node circle, .ppa-node path {{
          stroke: var(--ppa-node-stroke);
          stroke-width: 1.5px;
          transition: fill 0.25s ease, stroke 0.25s ease;
        }}
        .ppa-node.significant rect {{
          stroke-width: 2.5px;
          stroke: var(--ppa-ink);
        }}
        .ppa-node.non-significant rect {{
          stroke-width: 1.0px;
          stroke-dasharray: 3 2;
          stroke: var(--ppa-hairline);
        }}
        """
    )


def render_svg(
    laid_out_map,
    *,
    projection=None,
    theme: str = "light",
    show_provenance: bool = True,
) -> str:
    """Render a LaidOutMap object to a publication-ready vector SVG."""
    canvas = laid_out_map.canvas_box
    nodes = laid_out_map.nodes
    edges = laid_out_map.edges
    compartments = laid_out_map.compartments

    w = int(canvas.w)
    h = int(canvas.h)

    proj_values = projection.values if projection else {}

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'data-theme="{esc(theme)}" data-map-id="{esc(laid_out_map.id)}">'
        f"<defs><style>{_stylesheet()}</style>",
        # Arrowhead markers
        '<marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 1 L 10 5 L 0 9 z" fill="var(--ppa-edge)" />'
        "</marker>",
        '<marker id="inhibit" viewBox="0 0 10 10" refX="5" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto">'
        '<line x1="5" y1="1" x2="5" y2="9" stroke="var(--ppa-edge)" stroke-width="2" />'
        "</marker>",
        "</defs>",
        f'<rect class="ppa-canvas" width="{w}" height="{h}" />',
    ]

    # Header: Title & Subtitle
    y_cursor = 36.0
    parts.append(
        f'<text class="ppa-title" x="{laid_out_map.margin_x}" y="{y_cursor}">{esc(laid_out_map.title)}</text>'
    )
    if laid_out_map.subtitle:
        y_cursor += 20.0
        parts.append(
            f'<text class="ppa-subtitle" x="{laid_out_map.margin_x}" y="{y_cursor}">{esc(laid_out_map.subtitle)}</text>'
        )

    # Compartment Background Bands
    for comp in compartments:
        cb = comp["box"]
        cid = comp["id"]
        ctheme = COMPARTMENT_THEMES.get(cid, ("#475569", cid.replace("_", " ").title()))
        parts.append(
            f'<rect class="ppa-compartment-band" x="{cb.x:.1f}" y="{cb.y:.1f}" '
            f'width="{cb.w:.1f}" height="{cb.h:.1f}" />'
        )
        parts.append(
            f'<text class="ppa-compartment-title" x="{cb.x + 14:.1f}" y="{cb.y + 18:.1f}">'
            f"{esc(ctheme[1])}</text>"
        )

    # Directed Edges
    for e in edges:
        fn = laid_out_map.node_by_id(e["from"])
        tn = laid_out_map.node_by_id(e["to"])
        e_class = e.get("class", "flux")
        marker = 'marker-end="url(#inhibit)"' if e_class == "inhibition" else 'marker-end="url(#arrow)"'
        dash = 'stroke-dasharray="4 3"' if e_class == "catalysis" else ""

        path_d = ""
        mx, my = 0.0, 0.0

        if fn and tn:
            fa, ta = fn.box, tn.box
            dx = ta.cx - fa.cx
            dy = ta.cy - fa.cy

            # Same lane non-adjacent arch
            if fn.lane == tn.lane and abs(fa.cy - ta.cy) < 22.0 and abs(dx) > 1.25 * fa.w:
                arc_y = min(fa.y, ta.y) - 24.0
                path_d = f"M {fa.cx:.1f} {fa.y:.1f} C {fa.cx:.1f} {arc_y:.1f}, {ta.cx:.1f} {arc_y:.1f}, {ta.cx:.1f} {ta.y:.1f}"
                mx, my = (fa.cx + ta.cx) / 2.0, arc_y - 4.0

            # Upward flow / feedback loop
            elif ta.cy < fa.cy - 35.0:
                left_space = min(fa.x, ta.x)
                right_space = canvas.w - max(fa.x2, ta.x2)
                if left_space <= right_space:
                    loop_x = min(fa.x, ta.x) - 40.0
                    path_d = f"M {fa.x:.1f} {fa.cy:.1f} C {loop_x:.1f} {fa.cy:.1f}, {loop_x:.1f} {ta.cy:.1f}, {ta.x:.1f} {ta.cy:.1f}"
                    mx, my = loop_x - 4.0, (fa.cy + ta.cy) / 2.0
                else:
                    loop_x = max(fa.x2, ta.x2) + 40.0
                    path_d = f"M {fa.x2:.1f} {fa.cy:.1f} C {loop_x:.1f} {fa.cy:.1f}, {loop_x:.1f} {ta.cy:.1f}, {ta.x2:.1f} {ta.cy:.1f}"
                    mx, my = loop_x + 4.0, (fa.cy + ta.cy) / 2.0

        if not path_d:
            sx, sy = e["start"]
            ex, ey = e["end"]
            path_d = f"M {sx:.1f} {sy:.1f} L {ex:.1f} {ey:.1f}"
            mx, my = (sx + ex) / 2.0, (sy + ey) / 2.0 - 4.0

        parts.append(
            f'<path d="{path_d}" '
            f'stroke="var(--ppa-edge)" stroke-width="1.6" fill="none" '
            f"{marker} {dash} />"
        )
        if e.get("label"):
            parts.append(f'<text class="ppa-edge-label" x="{mx:.1f}" y="{my:.1f}">{esc(e["label"])}</text>')

    # Nodes
    for n in nodes:
        b = n.box
        val_obj = proj_values.get(n.id)
        val = val_obj.value if val_obj else None
        fill_color = _color_for_value(val)
        sig_class = ""
        if val_obj:
            sig_class = "significant" if val_obj.significant else "non-significant"

        loci_attr = ",".join(n.payload.get("loci", []))
        bin_attr = n.payload.get("mapman_bin", "")

        parts.append(
            f'<g class="ppa-node {esc(n.kind)} {sig_class}" '
            f'id="node-{esc(n.id)}" data-node-id="{esc(n.id)}" '
            f'data-loci="{esc(loci_attr)}" data-bin="{esc(bin_attr)}">'
        )

        # Shape based on kind
        if n.kind == "metabolite":
            parts.append(
                f'<rect x="{b.x:.1f}" y="{b.y:.1f}" width="{b.w:.1f}" height="{b.h:.1f}" '
                f'rx="16" ry="16" fill="{fill_color}" />'
            )
        else:
            parts.append(
                f'<rect x="{b.x:.1f}" y="{b.y:.1f}" width="{b.w:.1f}" height="{b.h:.1f}" '
                f'rx="8" ry="8" fill="{fill_color}" />'
            )

        # Label text lines
        text_y = b.y + 18.0
        for line in n.lines:
            parts.append(
                f'<text class="ppa-label" x="{b.cx:.1f}" y="{text_y:.1f}">{esc(line)}</text>'
            )
            text_y += n.font_size * LINE_SPACING

        for sline in n.sublines:
            parts.append(
                f'<text class="ppa-sub" x="{b.cx:.1f}" y="{text_y:.1f}">{esc(sline)}</text>'
            )
            text_y += (n.sub_font_size or 9.5) * LINE_SPACING

        # "Chicklets 2.0": Multi-subunit complex components
        if n.kind == "complex" and n.subunits:
            sub_y = b.y2 - 20.0
            total_sub_w = sum(len(s.get("symbol", "")) * 6.5 + 10.0 for s in n.subunits) + 4.0 * (len(n.subunits) - 1)
            sub_x = b.cx - total_sub_w / 2.0
            for sub in n.subunits:
                sym = sub.get("symbol", sub.get("id", ""))
                sw = len(sym) * 6.5 + 10.0
                parts.append(
                    f'<g class="ppa-subunit" data-locus="{esc(sub.get("locus", ""))}">'
                    f'<rect x="{sub_x:.1f}" y="{sub_y:.1f}" width="{sw:.1f}" height="14" rx="4" '
                    f'fill="rgba(0,0,0,0.06)" stroke="var(--ppa-hairline)" stroke-width="0.8" />'
                    f'<text class="ppa-subunit-text" x="{sub_x + sw / 2.0:.1f}" y="{sub_y + 10.5:.1f}">{esc(sym)}</text>'
                    f"</g>"
                )
                sub_x += sw + 4.0

        # "Chicklets 2.0": Large gene family micro-strip
        elif n.kind == "family" and n.family_loci:
            strip_y = b.y2 - 16.0
            n_tiles = min(16, len(n.family_loci))
            tile_w = min(12.0, (b.w - 24.0) / n_tiles)
            strip_x = b.cx - (n_tiles * tile_w) / 2.0
            for idx in range(n_tiles):
                parts.append(
                    f'<rect class="ppa-family-tile" x="{strip_x + idx * tile_w:.1f}" y="{strip_y:.1f}" '
                    f'width="{tile_w - 1.5:.1f}" height="9" rx="1.5" '
                    f'fill="rgba(0,0,0,0.12)" stroke="var(--ppa-hairline)" stroke-width="0.5" />'
                )

        parts.append("</g>")

    # Caption & Provenance footer
    if laid_out_map.caption or (projection and show_provenance):
        cap_y = canvas.h - laid_out_map.margin_bottom + 22.0
        cap_text = laid_out_map.caption
        if projection and show_provenance:
            cap_text = f"{cap_text} | {projection.provenance()}" if cap_text else projection.provenance()
        wrapped_caption = textwrap.wrap(cap_text, width=130)
        for cline in wrapped_caption:
            parts.append(
                f'<text class="ppa-caption" x="{laid_out_map.margin_x}" y="{cap_y:.1f}">{esc(cline)}</text>'
            )
            cap_y += CAPTION_SIZE * 1.35

    parts.append("</svg>")
    return "\n".join(parts)
