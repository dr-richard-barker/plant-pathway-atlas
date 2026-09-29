# Plant Pathway Atlas (PPA)

[![CI Test & ABAI QC](https://github.com/dr-richard-barker/plant-pathway-atlas/actions/workflows/ci.yml/badge.svg)](https://github.com/dr-richard-barker/plant-pathway-atlas/actions/workflows/ci.yml)
[![Pages Deployment](https://github.com/dr-richard-barker/plant-pathway-atlas/actions/workflows/deploy.yml/badge.svg)](https://dr-richard-barker.github.io/plant-pathway-atlas/)
[![ABAI QC Standard](https://img.shields.io/badge/ABAI%20QC-VERDICT%20CLEAR-059669.svg)](.abai/attest.json)
[![FAIR Data Compliance](https://img.shields.io/badge/FAIR-Level%205%20Compliant-3B6EA5.svg)](MANIFEST.tsv)
[![SBGN-ML Validated](https://img.shields.io/badge/SBGN--ML-LibSBGN%200.3-0284c7.svg)](maps/sbgn/)
[![License: MIT](https://img.shields.io/badge/Code%20License-MIT-blue.svg)](LICENSE)
[![License: CC BY 4.0](https://img.shields.io/badge/Data%20License-CC%20BY%204.0-lightgrey.svg)](LICENSE-DATA)

> **Modernizing MapMan, PlantCyc, and ggPlant for Systems Biology and Cross-Species Omics Projection**

The **Plant Pathway Atlas (PPA)** is a high-information-density visualization package, declarative pathway compiler, and omics projection framework. It modernizes classic **MapMan4/Mercator4 functional BIN hierarchies** and **PlantCyc metabolic reaction networks** by adopting the measured-text deterministic layout, publication vector rendering, and dual-backbone orthology connectivity developed in the **Quantum Biology Atlas**.

---

## The Problem PPA Solves

Classic **MapMan** ([bio.tools/mapman](https://bio.tools/mapman)) is one of the most foundational functional ontologies in plant biology. However, its visual representations are over two decades old:
1. **Low-Resolution Bitmap Chicklets**: Fixed-grid $3 \times 3$ pixel squares overlaid on static PNG rasters.
2. **Text Clipping & Collisions**: Labels hardcoded into background images that cannot adapt to font metrics or screen sizes.
3. **No Responsive Vector Scaling**: Lack of true vector SVGs with colorblind-safe palettes and light/dark mode support.
4. **Desktop Java Lock-In**: Requires standalone desktop JVM installations rather than instant client-side web exploration.
5. **Separation from Spatial Anatomy**: No bridge connecting cellular/tissue histology (ggPlant) to subcellular metabolic flux.

### The PPA Solution: "Chicklets 2.0" & Multi-Scale Spatial Integration
PPA replaces bitmap chicklets with adaptive, deterministic vector components:
- **Single-Gene Nodes**: Precise gene cards with symbol, AGI locus, name, and significance badge.
- **Structured Multi-Subunit Holoenzymes**: Stoichiometric subunit tags with individual expression fills and tooltips (e.g. Cytochrome b6f core subunits).
- **Large Multi-Gene Families (BIN Hubs)**: Micro-heatmap strips with distribution quartile markers (mean/median/extreme) and expandable drawers for large gene cohorts.
- **ggPlant Anatomical Integration**: Bridges tissue/cell-type expression (rosette, root radial cross-sections, root tip zones, floral organs) directly to metabolic pathways.

---

## Repository Architecture & FAIR Organization

This repository strictly adheres to **FAIR (Findable, Accessible, Interoperable, Reusable)** data principles:

```
├── .abai/                         # ABAI Quality Control audit certificate (attest.json)
├── .github/workflows/             # GitHub Actions CI & Pages automated deployment
│   ├── ci.yml                     # Continuous integration test suite & ABAI QC screen
│   └── deploy.yml                 # Automated deployment to GitHub Pages
├── catalog/                       # Published catalog & cross-species matrices
│   ├── manifest.json              # Central catalog registry with node & locus totals
│   ├── orthologs.json             # Precomputed cross-species orthology cache
│   └── sidecars/                  # Per-map locus & annotation sidecar JSONs
├── docs/                          # Self-contained GitHub Pages client-side web app
│   ├── index.html                 # Atlas map gallery with CoSE theme (no side rail)
│   ├── explore.html               # Interactive drag-and-drop omics projection GUI
│   ├── spatial.html               # ggPlant interactive histological tissue viewer
│   ├── .nojekyll                  # GitHub Pages Jekyll bypass
│   └── assets/                    # CoSE stylesheets and browser projection engine
├── maps/                          # Source and compiled pathway maps
│   ├── src/                       # Declarative YAML pathway sources (PPA-01, PPA-02, PPA-05)
│   ├── svg/                       # Standalone vector SVGs (light & dark mode)
│   └── sbgn/                      # Systems Biology Graphical Notation (SBGN-ML PD)
├── ontology/                      # Functional vocabularies and validation schemas
│   ├── mapman_bins.yaml           # MapMan4/Mercator4 functional BIN tree
│   └── schema/map.schema.json     # JSON Schema for declarative map validation
├── spatial/                       # ggPlant anatomical geometries
│   └── data/ggplant_organs.json   # Audited cell and organ polygons from Redox Decoder
├── src/plantpath/                 # Core Python library
│   ├── layout.py                  # Measured-text deterministic layout engine
│   ├── render.py                  # Publication SVG emitter with Okabe-Ito palettes
│   ├── sbgn.py                    # SBGN-ML PD (libsbgn 0.3) standard emitter
│   ├── maps.py                    # Map specification and layout compiler
│   ├── ortho.py                   # Dual-backbone cross-species orthology engine
│   ├── project.py                 # Multi-locus omics projection and provenance engine
│   ├── spatial.py                 # ggPlant anatomical polygon parser & projector
│   └── mapman.py                  # MapMan BIN ontology interface
├── tests/                         # Automated test suite (20 tests passed)
├── CHECKSUMS.sha256               # Cryptographic SHA256 integrity checksums
├── CITATION.cff                   # Citation File Format metadata
├── LICENSE                        # Open-source MIT license for software
├── LICENSE-DATA                   # CC-BY-4.0 license for data, maps, and ontologies
├── MANIFEST.tsv                   # Tabular manifest of all tracked files and checksums
└── .zenodo.json                   # Zenodo permanent archival metadata
```

---

## Flagship Modernized Pathway Maps

| Map ID | Pathway Title & Scope | Compartments | Nodes | Loci | Formats |
|---|---|---|---|---|---|
| **[PPA-01](maps/svg/PPA-01.svg)** | **Central Metabolism Overview**<br>Calvin-Benson cycle, starch turnover, sucrose partitioning, glycolysis, TCA cycle, mitochondrial ETC, and AOX | Chloroplast, Cytosol, Mitochondrion | 15 | 33 | SVG (Light/Dark), SBGN-ML, JSON |
| **[PPA-02](maps/svg/PPA-02.svg)** | **Photosynthesis & Bioenergetics**<br>Thylakoid Z-scheme: PSII core, OEC water splitting, PQ pool, Cytochrome b6f, Plastocyanin, PSI, FNR, CEF, and CF0-CF1 ATP synthase | Thylakoid Membrane, Lumen, Stroma | 12 | 34 | SVG (Light/Dark), SBGN-ML, JSON |
| **[PPA-05](maps/svg/PPA-05.svg)** | **ROS Dynamics & Redox Homeostasis**<br>Plasma membrane RBOH NADPH oxidases, SODs (CSD, FSD, MSD), Foyer-Halliwell-Asada cycle (APX, MDHAR, DHAR, GR), catalases, and thioredoxins | Plasma Membrane, Cytosol, Stroma, Peroxisome | 15 | 36 | SVG (Light/Dark), SBGN-ML, JSON |

---

## Cross-Species Orthology Connectivity

PPA anchors on *Arabidopsis thaliana* (TAIR10 AGI loci) and projects across plant crops and comparative animal/fungal models using dual backbones:
1. **Ensembl Compara `pan_homology`**: Live REST access spanning plant divisions and cross-kingdom comparisons.
2. **Precomputed Plant Orthology Matrix**: Offline, frozen, reproducible cache for air-gapped and fast browser projection.

Supported Target Species:
- **Crops & Model Plants**: Rice (*Oryza sativa*), Maize (*Zea mays*), Tomato (*Solanum lycopersicum*), Soybean (*Glycine max*), Moss (*Physcomitrium patens*), Algae (*Chlamydomonas reinhardtii*).
- **Comparative Models**: Yeast (*S. cerevisiae*), Human (*H. sapiens*), Mouse (*M. musculus*), Fly (*D. melanogaster*), Worm (*C. elegans*).

---

## Installation & Quickstart

```bash
# 1. Clone repository
git clone https://github.com/dr-richard-barker/plant-pathway-atlas.git
cd "plant-pathway-atlas"

# 2. Set up virtual environment and install dependencies
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 3. Run full test suite & ABAI QC screen
make test
make abai
```

---

## Web Application (CoSE Theme)

The interactive browser application is located in `docs/` and formatted with the official **CoSE (Council of Space Entomologists) Design System** (featuring brand header, horizontal tab navigation, and **no side rail**, per design specifications):

- **[docs/index.html](docs/index.html)**: Interactive map gallery with dark/light mode toggle.
- **[docs/explore.html](docs/explore.html)**: Client-side drag-and-drop omics data projector with automated column detection, significance thresholding, and live SVG colorization.
- **[docs/spatial.html](docs/spatial.html)**: Interactive ggPlant spatial anatomy viewer with real-time tissue expression sliders.

To preview locally:
```bash
make serve
# Open http://localhost:8080 in your browser
```

---

## ABAI Quality Control (QC) Standard

PPA implements the 5-point ABAI QC Verification Standard:
```bash
python scripts/run_abai_qc_screen.py
```
```
================================================================
       ABAI QUALITY CONTROL (QC) SCREEN REPORT         
================================================================
[CHECK 1/5] Unfiltered Blocklist Sweep...             ✅ PASS: 0 blocklisted strings found
[CHECK 2/5] Citations & Metadata Grounding...        ✅ PASS: CITATION.cff verified (ORCID: 0000-0001-5681-9857)
[CHECK 3/5] Numerical Traceability to Artefacts...   ✅ PASS: 42 nodes & 103 loci match sidecars exactly
[CHECK 4/5] File Paths & Format Integrity...         ✅ PASS: All SVGs (light/dark) and SBGNs exist
[CHECK 5/5] FAIR Synchronization & Checksums...       ✅ PASS: 42 checksums & manifest entries synchronized
================================================================
              ABAI QC SCREEN: VERDICT CLEAR            
================================================================
Issued ABAI Attestation -> .abai/attest.json
```

---

## Citing & License

- **Software License**: [MIT License](LICENSE)
- **Data & Maps License**: [Creative Commons Attribution 4.0 International (CC-BY-4.0)](LICENSE-DATA)
- **Citation**: Please cite using the metadata in [`CITATION.cff`](CITATION.cff).
