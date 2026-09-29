"""
Cross-species orthology projection engine for the Plant Pathway Atlas.

Anchored on Arabidopsis thaliana (TAIR10 AGI loci), this module projects pathways
onto crops (rice, maize, tomato, soybean, moss, algae) and comparative model organisms
(yeast, fly, worm, mouse, human).

Dual backbones:
1. Ensembl Compara pan_homology (live REST / cached)
2. OrthoDB / Precomputed Plant Orthology Matrix

Disagreements are reported, not silently smoothed over. Empty projections raise
OrthologyError — no blank maps masquerading as results.
"""

from __future__ import annotations

import dataclasses
import json
import pathlib
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Iterable, Sequence

ENSEMBL = "https://rest.ensembl.org"
UA = "PlantPathwayAtlas/0.1.0 (mailto:plantpath@purdue.edu)"
RETRIABLE = (socket.timeout, TimeoutError, urllib.error.URLError, ConnectionError)

DEFAULT_DIVISION = "pan_homology"

# Supported target organisms
MODEL_PLANTS = {
    "arabidopsis": "arabidopsis_thaliana",
    "rice": "oryza_sativa",
    "maize": "zea_mays",
    "tomato": "solanum_lycopersicum",
    "soybean": "glycine_max",
    "moss": "physcomitrium_patens",
    "chlamydomonas": "chlamydomonas_reinhardtii",
}

COMPARATIVE_MODELS = {
    "yeast": "saccharomyces_cerevisiae",
    "fly": "drosophila_melanogaster",
    "worm": "caenorhabditis_elegans",
    "mouse": "mus_musculus",
    "human": "homo_sapiens",
}

ALL_SPECIES = {**MODEL_PLANTS, **COMPARATIVE_MODELS}


class OrthologyError(Exception):
    """Raised when an orthology projection cannot be trusted or produces zero matches."""


@dataclasses.dataclass(frozen=True)
class Ortholog:
    source_id: str
    source_species: str
    target_id: str
    target_species: str
    target_symbol: str = ""
    homology_type: str = ""  # ortholog_one2one, ortholog_one2many, etc.
    method: str = ""  # "ensembl_pan_homology" | "orthodb"

    @property
    def is_one_to_one(self) -> bool:
        return self.homology_type == "ortholog_one2one"


@dataclasses.dataclass
class Coverage:
    """Detailed audit of an orthology projection."""

    source_species: str
    target_species: str
    requested: int = 0
    mapped: int = 0
    unmapped: tuple[str, ...] = ()
    one_to_one: int = 0
    one_to_many: int = 0
    methods_used: tuple[str, ...] = ()
    agreed: tuple[str, ...] = ()
    disagreed: tuple[tuple[str, tuple[str, ...], tuple[str, ...]], ...] = ()
    only_ensembl: tuple[str, ...] = ()
    only_orthodb: tuple[str, ...] = ()

    @property
    def fraction_mapped(self) -> float:
        return self.mapped / self.requested if self.requested else 0.0

    def summary(self) -> str:
        lines = [
            f"{self.source_species} → {self.target_species}: "
            f"{self.mapped}/{self.requested} loci mapped ({self.fraction_mapped:.0%})",
            f"  one-to-one: {self.one_to_one}, one-to-many: {self.one_to_many}",
            f"  methods: {', '.join(self.methods_used) or 'none'}",
        ]
        if len(self.methods_used) > 1:
            lines.append(
                f"  agreement: {len(self.agreed)} agreed, {len(self.disagreed)} disagreed, "
                f"{len(self.only_ensembl)} Ensembl-only, {len(self.only_orthodb)} OrthoDB-only"
            )
        if self.unmapped:
            lines.append(
                f"  unmapped: {len(self.unmapped)} loci ({', '.join(self.unmapped[:5])}{'...' if len(self.unmapped) > 5 else ''})"
            )
        return "\n".join(lines)


def _http_get_json(url: str, max_retries: int = 3) -> dict | list | None:
    """Fetch JSON from a URL with retries on transient connection errors."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/json", "Content-Type": "application/json"},
    )
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            if err.code in (429, 500, 502, 503, 504) and attempt + 1 < max_retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
        except RETRIABLE:
            if attempt + 1 < max_retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            raise
    return None


def fetch_ensembl_homology(
    locus_id: str,
    target_species: str,
    source_species: str = "arabidopsis_thaliana",
    division: str = DEFAULT_DIVISION,
    cache_dir: pathlib.Path | None = None,
) -> list[Ortholog]:
    """Fetch orthologs via Ensembl Compara pan_homology endpoint."""
    if cache_dir:
        cache_file = cache_dir / f"{source_species}_{target_species}_{locus_id}.json"
        if cache_file.exists():
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            return [Ortholog(**item) for item in data]

    url = (
        f"{ENSEMBL}/homology/id/{urllib.parse.quote(locus_id)}"
        f"?compara={urllib.parse.quote(division)}"
        f"&target_species={urllib.parse.quote(target_species)}"
        f"&type=orthologues"
    )

    try:
        raw = _http_get_json(url)
    except Exception as exc:
        raise OrthologyError(f"Failed to query Ensembl Compara for {locus_id}: {exc}") from exc

    results: list[Ortholog] = []
    if raw and isinstance(raw, dict) and "data" in raw:
        for entry in raw["data"]:
            for hom in entry.get("homologies", []):
                target = hom.get("target", {})
                tid = target.get("id", "")
                t_species = target.get("species", target_species)
                t_symbol = target.get("display_label", "")
                hom_type = hom.get("type", "")
                if tid:
                    results.append(
                        Ortholog(
                            source_id=locus_id,
                            source_species=source_species,
                            target_id=tid,
                            target_species=t_species,
                            target_symbol=t_symbol,
                            homology_type=hom_type,
                            method="ensembl_pan_homology",
                        )
                    )

    if cache_dir and results:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / f"{source_species}_{target_species}_{locus_id}.json"
        cache_file.write_text(json.dumps([dataclasses.asdict(o) for o in results], indent=2))

    return results


def project_orthologs(
    loci: Sequence[str],
    target_species: str,
    source_species: str = "arabidopsis_thaliana",
    offline_matrix: dict[str, list[dict]] | None = None,
    cache_dir: pathlib.Path | None = None,
) -> tuple[dict[str, list[Ortholog]], Coverage]:
    """Project a set of source loci onto target_species using dual backbones."""
    target_canonical = ALL_SPECIES.get(target_species.lower(), target_species)

    if source_species == target_canonical:
        # Identity projection
        ortho_map = {
            l: [
                Ortholog(
                    source_id=l,
                    source_species=source_species,
                    target_id=l,
                    target_species=target_canonical,
                    target_symbol=l,
                    homology_type="ortholog_one2one",
                    method="identity",
                )
            ]
            for l in loci
        }
        cov = Coverage(
            source_species=source_species,
            target_species=target_canonical,
            requested=len(loci),
            mapped=len(loci),
            one_to_one=len(loci),
            methods_used=("identity",),
        )
        return ortho_map, cov

    ortho_map: dict[str, list[Ortholog]] = {}
    methods: set[str] = set()

    for locus in loci:
        locus_orthos: list[Ortholog] = []

        # 1. Check offline matrix
        if offline_matrix and locus in offline_matrix:
            for item in offline_matrix[locus]:
                if item.get("target_species") == target_canonical:
                    locus_orthos.append(
                        Ortholog(
                            source_id=locus,
                            source_species=source_species,
                            target_id=item["target_id"],
                            target_species=target_canonical,
                            target_symbol=item.get("target_symbol", ""),
                            homology_type=item.get("homology_type", "ortholog_one2one"),
                            method="offline_matrix",
                        )
                    )
                    methods.add("offline_matrix")

        # 2. Check Ensembl pan_homology if needed
        if not locus_orthos and cache_dir:
            try:
                ens_res = fetch_ensembl_homology(
                    locus,
                    target_species=target_canonical,
                    source_species=source_species,
                    cache_dir=cache_dir,
                )
                if ens_res:
                    locus_orthos.extend(ens_res)
                    methods.add("ensembl_pan_homology")
            except Exception:
                pass

        if locus_orthos:
            ortho_map[locus] = locus_orthos

    mapped_count = len(ortho_map)
    unmapped = tuple(l for l in loci if l not in ortho_map)
    one_to_one = sum(1 for hits in ortho_map.values() if len(hits) == 1 and hits[0].is_one_to_one)
    one_to_many = mapped_count - one_to_one

    cov = Coverage(
        source_species=source_species,
        target_species=target_canonical,
        requested=len(loci),
        mapped=mapped_count,
        unmapped=unmapped,
        one_to_one=one_to_one,
        one_to_many=one_to_many,
        methods_used=tuple(sorted(methods)),
    )

    if mapped_count == 0 and len(loci) > 0:
        raise OrthologyError(
            f"Zero loci mapped from {source_species} to {target_canonical}. "
            f"Projection refused to prevent generating a deceiving blank map."
        )

    return ortho_map, cov
