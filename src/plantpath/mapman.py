"""
MapMan BIN hierarchy and Mercator functional annotation ontology.

Provides hierarchical classification across MapMan4/Mercator4 categories, mapping
Arabidopsis AGI loci and orthologs to functional BIN codes.
"""

from __future__ import annotations

import dataclasses
import pathlib
from typing import Sequence

import yaml


@dataclasses.dataclass
class MapManBin:
    """A single functional BIN in the MapMan tree."""

    code: str  # e.g. "1.1.1.1"
    name: str  # e.g. "photosystem II polypeptide subunits"
    description: str = ""
    parent: str | None = None
    children: list[str] = dataclasses.field(default_factory=list)
    loci: list[str] = dataclasses.field(default_factory=list)

    @property
    def level(self) -> int:
        return len(self.code.split("."))


class MapManOntology:
    """Repository and query interface for MapMan functional BINs."""

    def __init__(self):
        self.bins: dict[str, MapManBin] = {}
        self.locus_to_bins: dict[str, list[str]] = {}

    def add_bin(self, code: str, name: str, description: str = "", loci: Sequence[str] | None = None) -> MapManBin:
        parts = code.split(".")
        parent_code = ".".join(parts[:-1]) if len(parts) > 1 else None

        bin_obj = MapManBin(
            code=code,
            name=name,
            description=description,
            parent=parent_code,
            loci=list(loci or []),
        )
        self.bins[code] = bin_obj

        if parent_code and parent_code in self.bins:
            if code not in self.bins[parent_code].children:
                self.bins[parent_code].children.append(code)

        for l in bin_obj.loci:
            l_up = l.strip().upper()
            self.locus_to_bins.setdefault(l_up, []).append(code)

        return bin_obj

    def get_bin(self, code: str) -> MapManBin | None:
        return self.bins.get(code)

    def search_bins(self, query: str) -> list[MapManBin]:
        q = query.lower()
        return [b for b in self.bins.values() if q in b.code.lower() or q in b.name.lower()]

    def get_descendants(self, code: str) -> list[MapManBin]:
        results: list[MapManBin] = []
        queue = [code]
        while queue:
            curr = queue.pop(0)
            if curr in self.bins:
                b = self.bins[curr]
                if curr != code:
                    results.append(b)
                queue.extend(b.children)
        return results

    def load_from_yaml(self, path: pathlib.Path) -> None:
        """Load MapMan BINs from a YAML definitions file."""
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        for item in data.get("bins", []):
            self.add_bin(
                code=str(item["code"]),
                name=item["name"],
                description=item.get("description", ""),
                loci=item.get("loci", []),
            )
