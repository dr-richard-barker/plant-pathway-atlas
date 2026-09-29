#!/usr/bin/env python3
"""
Compile declarative YAML maps into vector SVGs (light & dark mode) and catalog sidecars.
"""

from __future__ import annotations

import json
import pathlib
import sys

# Ensure src/ is on python path
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from plantpath.maps import compile_map, load_map
from plantpath.render import render_svg
from plantpath.sbgn import export_sbgn


def main():
    src_dir = ROOT / "maps" / "src"
    svg_dir = ROOT / "maps" / "svg"
    sbgn_dir = ROOT / "maps" / "sbgn"
    sidecar_dir = ROOT / "catalog" / "sidecars"
    manifest_path = ROOT / "catalog" / "manifest.json"

    svg_dir.mkdir(parents=True, exist_ok=True)
    sbgn_dir.mkdir(parents=True, exist_ok=True)
    sidecar_dir.mkdir(parents=True, exist_ok=True)

    yaml_files = sorted(src_dir.glob("*.yaml"))
    if not yaml_files:
        print("No map YAML files found in maps/src/")
        return

    catalog_entries = []

    for yf in yaml_files:
        print(f"Compiling {yf.name}...")
        spec = load_map(yf)
        laid_out = compile_map(spec)

        # 1. Render light mode SVG
        svg_light = render_svg(laid_out, theme="light")
        light_out = svg_dir / f"{spec.id}.svg"
        light_out.write_text(svg_light, encoding="utf-8")

        # 2. Render dark mode SVG
        svg_dark = render_svg(laid_out, theme="dark")
        dark_out = svg_dir / f"{spec.id}_dark.svg"
        dark_out.write_text(svg_dark, encoding="utf-8")

        # 3. Export SBGN-ML PD standard
        sbgn_out = sbgn_dir / f"{spec.id}.sbgn"
        export_sbgn(laid_out, sbgn_out)

        # 4. Create per-map sidecar JSON
        node_records = []
        all_loci = set()
        for node in laid_out.nodes:
            raw_loci = node.payload.get("loci", [])
            if not raw_loci and node.subunits:
                raw_loci = [s.get("locus", "") for s in node.subunits if s.get("locus")]
            if not raw_loci and node.family_loci:
                raw_loci = node.family_loci

            cleaned_loci = [l.strip().upper() for l in raw_loci if l.strip()]
            all_loci.update(cleaned_loci)

            node_records.append(
                {
                    "id": node.id,
                    "label": " ".join(node.lines),
                    "kind": node.kind,
                    "compartment": node.compartment,
                    "mapman_bin": node.payload.get("mapman_bin", ""),
                    "loci": cleaned_loci,
                    "subunits": node.subunits,
                }
            )

        sidecar = {
            "id": spec.id,
            "title": spec.title,
            "subtitle": spec.subtitle,
            "caption": spec.caption,
            "species_anchor": spec.species_anchor,
            "nodes": node_records,
            "edges": laid_out.edges,
            "total_nodes": len(laid_out.nodes),
            "distinct_loci": len(all_loci),
            "loci_list": sorted(all_loci),
        }
        sidecar_out = sidecar_dir / f"{spec.id}.json"
        sidecar_out.write_text(json.dumps(sidecar, indent=2), encoding="utf-8")

        catalog_entries.append(
            {
                "id": spec.id,
                "title": spec.title,
                "subtitle": spec.subtitle,
                "svg_light": f"maps/svg/{spec.id}.svg",
                "svg_dark": f"maps/svg/{spec.id}_dark.svg",
                "sbgn": f"maps/sbgn/{spec.id}.sbgn",
                "sidecar": f"catalog/sidecars/{spec.id}.json",
                "total_nodes": len(laid_out.nodes),
                "distinct_loci": len(all_loci),
            }
        )

    # 4. Write manifest.json
    manifest = {
        "version": "0.1.0",
        "species_anchor": "arabidopsis_thaliana",
        "maps": catalog_entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Successfully compiled {len(catalog_entries)} maps to {svg_dir}")


if __name__ == "__main__":
    main()
