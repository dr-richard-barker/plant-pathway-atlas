#!/usr/bin/env python3
"""
Build the self-contained GitHub Pages site in docs/.

Synchronizes:
- maps/svg/ -> docs/maps/svg/
- maps/sbgn/ -> docs/maps/sbgn/
- catalog/ -> docs/catalog/
- spatial/data/ -> docs/spatial/data/
- CITATION.cff -> docs/CITATION.cff
"""

from __future__ import annotations

import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def sync_tree(src: pathlib.Path, dst: pathlib.Path):
    if not src.exists():
        return
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, target)


def main():
    print("Building self-contained GitHub Pages site in docs/...")

    # 1. Sync maps
    sync_tree(ROOT / "maps" / "svg", DOCS / "maps" / "svg")
    sync_tree(ROOT / "maps" / "sbgn", DOCS / "maps" / "sbgn")

    # 2. Sync catalog
    sync_tree(ROOT / "catalog", DOCS / "catalog")

    # 3. Sync spatial data
    sync_tree(ROOT / "spatial" / "data", DOCS / "spatial" / "data")

    # 4. Copy CITATION.cff and LICENSE
    shutil.copy2(ROOT / "CITATION.cff", DOCS / "CITATION.cff")
    shutil.copy2(ROOT / "LICENSE", DOCS / "LICENSE")
    shutil.copy2(ROOT / "LICENSE-DATA", DOCS / "LICENSE-DATA")

    # 5. Ensure .nojekyll exists
    (DOCS / ".nojekyll").write_text("# Disable Jekyll\n", encoding="utf-8")

    print(f"Successfully assembled self-contained docs/ site at {DOCS}")


if __name__ == "__main__":
    main()
