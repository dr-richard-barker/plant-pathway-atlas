# Plant Pathway Atlas (PPA)

**High-information-density pathway maps, modern vector visualization, and cross-species omics projection for plant biology.**

The Plant Pathway Atlas (PPA) modernizes classic **MapMan** functional BIN hierarchies and **PlantCyc** metabolic reaction networks using the deterministic layout engine, publication-grade vector rendering, and dual-backbone orthology connectivity developed in the **Quantum Biology Atlas**.

---

## Key Features

- **Measured-Text Deterministic Layout**:
  Labels determine box sizes, never the reverse. Text outlines are measured with true vector font glyph extents, guaranteeing zero text overflow or clipping.
- **"Chicklets 2.0"**:
  Replaces 1990s fixed-grid pixel dots with structured vector glyphs: single-gene cards, multi-subunit stoichiometric complexes, and micro-heatmaps with distribution curves for large gene families.
- **Cross-Species Orthology Engine**:
  Anchors on *Arabidopsis thaliana* (TAIR10 AGI loci) and projects onto major crops (Rice, Maize, Tomato, Soybean) and comparative model organisms (Yeast, Fly, Worm, Mouse, Human) using Ensembl Compara `pan_homology` and precomputed OrthoDB matrices.
- **Multi-Scale Spatial Anatomy (ggPlant)**:
  Directly integrates anatomical cell and tissue polygons (rosette, root radial cross-sections, root tip zones, flower organs), bridging spatial transcriptomics to subcellular metabolic flux.
- **Strict Scientific Refusals**:
  Refuses to draw empty maps masquerading as results. Low coverage (<25%) triggers explicit warnings, and provenance statements are automatically embedded in exported figures.
- **Zero-Install Web Explorer**:
  Drag-and-drop tabular omics projection running 100% client-side in the browser.

---

## Directory Structure

```
├── catalog/                # Published catalog, manifest, and orthology cache
├── docs/                   # Interactive client-side web application
├── maps/
│   ├── src/                # Declarative YAML pathway maps (PPA-01, PPA-02, PPA-05)
│   └── svg/                # Compiled light and dark mode vector SVGs
├── ontology/               # MapMan4 BIN definitions and schemas
├── spatial/                # ggPlant anatomical cell and organ polygons
├── src/plantpath/          # Core Python package
└── tests/                  # Test suite
```

---

## Installation & Quickstart

```bash
# Clone the repository
git clone https://github.com/dr-richard-barker/plant-pathway-atlas.git
cd "plant-pathway-atlas"

# Set up virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e .

# Run test suite
pytest
```

---

## Python API Usage

```python
from plantpath.maps import load_map, compile_map
from plantpath.render import render_svg
from plantpath.project import parse_expression_table, project_expression

# Load and compile declarative map
spec = load_map("maps/src/PPA-01_central_metabolism.yaml")
laid_out = compile_map(spec)

# Project transcriptomics or proteomics data
data = parse_expression_table("experiment_de_genes.tsv")
projection = project_expression(laid_out, data, aggregator="mean")

# Render publication-ready vector SVG
svg_text = render_svg(laid_out, projection=projection, theme="light")
with open("my_metabolism_overlay.svg", "w") as f:
    f.write(svg_text)
```
