"""
Deterministic layout engine with measured text for the Plant Pathway Atlas.

Labels drive geometry:
    text -> measure real glyph extents -> wrap -> size box -> place in lane grid

A node's bounding rectangle is derived from its wrapped text plus padding, ensuring
that labels cannot overflow boxes by construction. Boxes are placed in lanes with
enforced minimum horizontal and vertical gutters, preventing overlapping.
"""

from __future__ import annotations

import dataclasses
import functools
import math
from typing import Iterable, Sequence

from matplotlib.font_manager import FontProperties
from matplotlib.textpath import TextPath

FONT_FAMILY = "DejaVu Sans"
SVG_FONT_STACK = "'DejaVu Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif"

# Geometry constants (SVG px user units at 1:1)
PAD_X = 12.0
PAD_Y = 9.0
LINE_SPACING = 1.28
MIN_GUTTER_X = 32.0
MIN_GUTTER_Y = 28.0
COMPARTMENT_PAD = 26.0
CANVAS_MARGIN = 32.0

# Subunit / Chicklet 2.0 constants
SUBUNIT_HEIGHT = 16.0
SUBUNIT_PAD_X = 6.0
SUBUNIT_GUTTER = 4.0


@functools.lru_cache(maxsize=4096)
def measure(text: str, size: float, weight: str = "normal") -> tuple[float, float]:
    """Return (width, height) of a single text run in user units.

    Uses matplotlib TextPath to obtain true vector font outline extents.
    """
    if not text:
        return (0.0, size)
    try:
        fp = FontProperties(family=FONT_FAMILY, size=size, weight=weight)
        tp = TextPath((0, 0), text, prop=fp)
        bb = tp.get_extents()
        return (float(bb.width), float(size))
    except Exception:
        # Fallback character-width approximation if font engine is unavailable
        factor = 0.62 if weight == "bold" else 0.58
        return (len(text) * size * factor, float(size))


def wrap(text: str, size: float, max_width: float, weight: str = "normal") -> list[str]:
    """Greedy word wrap against measured width.

    A single word longer than max_width is never split — the box widens for it
    instead. Explicit newlines are honoured.
    """
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        current = words[0]
        for word in words[1:]:
            trial = f"{current} {word}"
            if measure(trial, size, weight)[0] <= max_width:
                current = trial
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines


def text_block(
    text: str, size: float, max_width: float, weight: str = "normal"
) -> tuple[list[str], float, float]:
    """Wrap `text` and return (lines, block_width, block_height)."""
    lines = wrap(text, size, max_width, weight)
    width = max((measure(ln, size, weight)[0] for ln in lines), default=0.0)
    height = len(lines) * size * LINE_SPACING
    return lines, width, height


@dataclasses.dataclass
class Box:
    """An axis-aligned rectangle in user units, origin top-left."""

    x: float
    y: float
    w: float
    h: float

    @property
    def x2(self) -> float:
        return self.x + self.w

    @property
    def y2(self) -> float:
        return self.y + self.h

    @property
    def cx(self) -> float:
        return self.x + self.w / 2.0

    @property
    def cy(self) -> float:
        return self.y + self.h / 2.0

    def overlaps(self, other: "Box", tol: float = 0.01) -> bool:
        """True if this box intersects other by more than tolerance."""
        return not (
            self.x2 <= other.x + tol
            or other.x2 <= self.x + tol
            or self.y2 <= other.y + tol
            or other.y2 <= self.y + tol
        )

    def contains(self, other: "Box", tol: float = 0.01) -> bool:
        """True if this box completely contains other."""
        return (
            self.x - tol <= other.x
            and self.y - tol <= other.y
            and other.x2 <= self.x2 + tol
            and other.y2 <= self.y2 + tol
        )

    def expanded(self, pad: float) -> "Box":
        return Box(self.x - pad, self.y - pad, self.w + 2 * pad, self.h + 2 * pad)


@dataclasses.dataclass
class LaidOutNode:
    """A pathway entity after measurement and placement."""

    id: str
    box: Box
    lines: list[str]
    font_size: float
    font_weight: str
    kind: str = "simple"  # simple, complex, family, metabolite, reaction
    sublines: list[str] = dataclasses.field(default_factory=list)
    sub_font_size: float = 0.0
    lane: str | None = None
    compartment: str | None = None
    row: int = 0
    col: int = 0
    subunits: list[dict] = dataclasses.field(default_factory=list)
    family_loci: list[str] = dataclasses.field(default_factory=list)
    payload: dict = dataclasses.field(default_factory=dict)
    reserve_bottom: float = 0.0

    def text_box(self) -> Box:
        """Bounding box of the laid-out text runs."""
        width = max(
            (measure(ln, self.font_size, self.font_weight)[0] for ln in self.lines),
            default=0.0,
        )
        height = len(self.lines) * self.font_size * LINE_SPACING
        if self.sublines:
            width = max(
                width, max(measure(s, self.sub_font_size)[0] for s in self.sublines)
            )
            height += len(self.sublines) * self.sub_font_size * LINE_SPACING
        return Box(self.box.cx - width / 2.0, self.box.cy - height / 2.0, width, height)


def size_node(
    label: str,
    font_size: float,
    *,
    kind: str = "simple",
    sublabel: str = "",
    sub_font_size: float = 0.0,
    preferred_width: float = 190.0,
    min_width: float = 96.0,
    weight: str = "normal",
    subunits: Sequence[dict] | None = None,
    n_family_loci: int = 0,
) -> tuple[Box, list[str], list[str]]:
    """Size a node box around its text and structured components.

    The box derives from the text and child elements, never the reverse.
    """
    lines, w, h = text_block(label, font_size, preferred_width, weight)
    sublines: list[str] = []
    if sublabel:
        sub_size = sub_font_size or font_size * 0.8
        sublines, sw, sh = text_block(sublabel, sub_size, preferred_width)
        w = max(w, sw)
        h += sh

    # Widen for any unbreakable token
    for token in label.replace("\n", " ").split() + (sublabel.split() if sublabel else []):
        w = max(w, measure(token, font_size, weight)[0])

    extra_h = 0.0
    # Additional height and width for multi-subunit complex pills ("Chicklets 2.0")
    if kind == "complex" and subunits:
        extra_h += SUBUNIT_HEIGHT + 6.0
        # Check if all subunit pills fit in w
        total_sub_w = sum(
            measure(sub.get("symbol", sub.get("id", "")), 9.0, "normal")[0] + SUBUNIT_PAD_X * 2
            for sub in subunits
        ) + SUBUNIT_GUTTER * max(0, len(subunits) - 1)
        w = max(w, total_sub_w)
    elif kind == "family" and n_family_loci > 0:
        # Micro-heatmap strip + distribution marker height
        extra_h += 18.0
        min_strip_w = min(240.0, max(120.0, n_family_loci * 8.0))
        w = max(w, min_strip_w)
    elif kind == "metabolite":
        min_width = max(70.0, min_width * 0.75)

    node_w = max(min_width, w + 2 * PAD_X)
    node_h = h + extra_h + 2 * PAD_Y

    return (Box(0.0, 0.0, node_w, node_h), lines, sublines)


def place_rows(
    rows: Sequence[Sequence[LaidOutNode]],
    *,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    gutter_x: float = MIN_GUTTER_X,
    gutter_y: float | Sequence[float] = MIN_GUTTER_Y,
    align: str = "center",
) -> Box:
    """Place pre-sized nodes as rows in user space, returning the bounding box.

    Gutters are guaranteed minimums so adjacent boxes cannot touch.
    """
    row_widths = [
        sum(n.box.w for n in row) + gutter_x * max(0, len(row) - 1) for row in rows
    ]
    total_width = max(row_widths, default=0.0)

    if isinstance(gutter_y, (int, float)):
        gutters = [float(gutter_y)] * max(0, len(rows) - 1)
    else:
        gutters = [float(g) for g in gutter_y]
        if len(gutters) != max(0, len(rows) - 1):
            raise ValueError(
                f"gutter_y has {len(gutters)} values but {len(rows)} rows need {max(0, len(rows) - 1)}"
            )

    y = origin_y
    for i, (row, row_width) in enumerate(zip(rows, row_widths)):
        if not row:
            continue
        if align == "center":
            x = origin_x + (total_width - row_width) / 2.0
        elif align == "left":
            x = origin_x
        elif align == "right":
            x = origin_x + (total_width - row_width)
        else:
            raise ValueError(f"unknown align mode: {align!r}")

        row_height = max(n.box.h for n in row)
        for node in row:
            node.box.x = x
            node.box.y = y + (row_height - node.box.h) / 2.0  # vertically centre
            x += node.box.w + gutter_x
        y += row_height
        if i < len(gutters):
            y += gutters[i]

    return Box(origin_x, origin_y, total_width, max(0.0, y - origin_y))


def bounding_box(nodes: Iterable[LaidOutNode], pad: float = CANVAS_MARGIN) -> Box:
    """Union bounding box of every node, padded so nothing clips."""
    boxes = [n.box for n in nodes]
    if not boxes:
        return Box(0.0, 0.0, pad * 2, pad * 2)
    x1 = min(b.x for b in boxes) - pad
    y1 = min(b.y for b in boxes) - pad
    x2 = max(b.x2 for b in boxes) + pad
    y2 = max(b.y2 for b in boxes) + pad
    return Box(x1, y1, x2 - x1, y2 - y1)


def resolve_collisions(
    nodes: Sequence[LaidOutNode], gutter: float = 8.0, max_passes: int = 64
) -> int:
    """Nudge overlapping boxes apart along the axis of least displacement."""
    moves = 0
    for _ in range(max_passes):
        collided = False
        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                if not a.box.overlaps(b.box, tol=-gutter):
                    continue
                collided = True
                moves += 1
                dx = (b.box.cx - a.box.cx) or 1e-6
                dy = (b.box.cy - a.box.cy) or 1e-6
                overlap_x = (a.box.w + b.box.w) / 2.0 + gutter - abs(dx)
                overlap_y = (a.box.h + b.box.h) / 2.0 + gutter - abs(dy)
                if overlap_x < overlap_y:
                    shift = math.copysign(overlap_x / 2.0, dx)
                    a.box.x -= shift
                    b.box.x += shift
                else:
                    shift = math.copysign(overlap_y / 2.0, dy)
                    a.box.y -= shift
                    b.box.y += shift
        if not collided:
            return moves
    raise RuntimeError(
        f"layout did not converge after {max_passes} passes ({moves} moves) — "
        "the map declares more nodes than its lanes can hold without overlap"
    )


def edge_anchors(a: Box, b: Box) -> tuple[tuple[float, float], tuple[float, float]]:
    """Calculate the perimeter intersection points for a directed edge from `a` to `b`."""
    dx = b.cx - a.cx
    dy = b.cy - a.cy
    if abs(dx) * a.h >= abs(dy) * a.w:  # horizontal departure
        sx = a.x2 if dx > 0 else a.x
        sy = a.cy + (dy / dx * (sx - a.cx) if dx else 0.0)
        ex = b.x if dx > 0 else b.x2
        ey = b.cy + (dy / dx * (ex - b.cx) if dx else 0.0)
    else:  # vertical departure
        sy = a.y2 if dy > 0 else a.y
        sx = a.cx + (dx / dy * (sy - a.cy) if dy else 0.0)
        ey = b.y if dy > 0 else b.y2
        ex = b.cx + (dx / dy * (ey - b.cy) if dy else 0.0)
    return (sx, sy), (ex, ey)
