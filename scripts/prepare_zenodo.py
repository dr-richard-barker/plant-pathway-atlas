#!/usr/bin/env python3
"""
FAIR compliance script: Compute SHA256 checksums, generate MANIFEST.tsv and CHECKSUMS.sha256.
"""

from __future__ import annotations

import hashlib
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent

DESCRIPTIONS = {
    "CITATION.cff": "FAIR Citation File Format metadata",
    ".zenodo.json": "Zenodo deposit metadata",
    "LICENSE": "MIT Open Source Software License",
    "LICENSE-DATA": "Creative Commons Attribution 4.0 International Data License",
    "README.md": "Repository documentation and quickstart guide",
    "Makefile": "Build automation rules",
    "pyproject.toml": "Python package build specification (PEP 621)",
    "catalog/manifest.json": "Complete catalog of pathway maps and node statistics",
    "catalog/orthologs.json": "Precomputed cross-species orthology connectivity matrix",
    "ontology/mapman_bins.yaml": "Curated MapMan4/Mercator4 functional BIN ontology",
    "ontology/schema/map.schema.json": "JSON Schema for declarative pathway map specifications",
    "spatial/data/ggplant_organs.json": "Audited ggPlant anatomical cell and organ polygons",
}


def get_file_list() -> list[pathlib.Path]:
    res = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip():
        files = [ROOT / f for f in res.stdout.split() if (ROOT / f).is_file()]
    else:
        files = [
            p
            for p in ROOT.rglob("*")
            if p.is_file() and ".venv" not in p.parts and ".git" not in p.parts and ".pytest_cache" not in p.parts
        ]
    return sorted(files)


def compute_sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def main():
    files = get_file_list()
    checksum_lines = []
    manifest_rows = [("path", "sha256", "size_bytes", "description")]

    for f in files:
        rel_path = f.relative_to(ROOT).as_posix()
        if rel_path in ("CHECKSUMS.sha256", "MANIFEST.tsv"):
            continue

        sha = compute_sha256(f)
        size = f.stat().st_size
        checksum_lines.append(f"{sha}  {rel_path}")

        desc = DESCRIPTIONS.get(rel_path, "")
        if not desc:
            if rel_path.startswith("maps/src/"):
                desc = "Declarative pathway YAML source"
            elif rel_path.startswith("maps/svg/"):
                desc = "Compiled publication-grade vector SVG"
            elif rel_path.startswith("maps/sbgn/"):
                desc = "Compiled SBGN-ML Process Description"
            elif rel_path.startswith("catalog/sidecars/"):
                desc = "Per-map annotation and locus sidecar JSON"
            elif rel_path.startswith("src/plantpath/"):
                desc = "Core Python library module"
            elif rel_path.startswith("tests/"):
                desc = "Automated test module"
            elif rel_path.startswith("docs/"):
                desc = "Interactive web application asset"
            else:
                desc = "Repository file"

        manifest_rows.append((rel_path, sha, str(size), desc))

    # Write CHECKSUMS.sha256
    checksums_file = ROOT / "CHECKSUMS.sha256"
    checksums_file.write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(checksum_lines)} checksums to {checksums_file.relative_to(ROOT)}")

    # Write MANIFEST.tsv
    manifest_file = ROOT / "MANIFEST.tsv"
    tsv_content = "\n".join("\t".join(row) for row in manifest_rows) + "\n"
    manifest_file.write_text(tsv_content, encoding="utf-8")
    print(f"Wrote {len(manifest_rows) - 1} entries to {manifest_file.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
