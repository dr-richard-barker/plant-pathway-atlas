"""
Omics data projection engine for the Plant Pathway Atlas.

Maps measured differential expression, proteomics abundance, or metabolomics levels
onto pathway map nodes with transparent multi-locus aggregation and strict refusal
rules (never emits deceiving blank maps).
"""

from __future__ import annotations

import csv
import dataclasses
import io
import pathlib
import re
import statistics
from typing import Callable, Iterable, Sequence

from .maps import LaidOutMap
from .ortho import Coverage, Ortholog, OrthologyError, project_orthologs


class ProjectionError(Exception):
    """Raised when a data projection is invalid, empty, or misleading."""


AGGREGATORS: dict[str, Callable[[Sequence[float]], float]] = {
    "mean": lambda vals: statistics.fmean(vals),
    "median": lambda vals: statistics.median(vals),
    "extreme": lambda vals: max(vals, key=abs),
    "min": min,
    "max": max,
}

AGI_PATTERN = re.compile(r"^AT[1-5MC]G\d{5}$", re.IGNORECASE)


@dataclasses.dataclass
class NodeValue:
    node_id: str
    value: float
    n_loci: int
    loci_used: tuple[str, ...]
    loci_missing: tuple[str, ...]
    aggregator: str
    significant: bool | None = None
    p_adj: float | None = None
    via_orthologs: tuple[str, ...] = ()


@dataclasses.dataclass
class Projection:
    """The outcome of projecting an omics dataset onto a pathway map."""

    map_id: str
    study: str
    contrast: str
    organism: str
    aggregator: str
    values: dict[str, NodeValue]
    nodes_total: int
    nodes_without_loci: tuple[str, ...]
    nodes_unmatched: tuple[str, ...]
    alpha: float = 0.05
    ortholog_coverage: Coverage | None = None

    @property
    def nodes_with_data(self) -> int:
        return len(self.values)

    @property
    def fraction_covered(self) -> float:
        addressable = self.nodes_total - len(self.nodes_without_loci)
        return self.nodes_with_data / addressable if addressable else 0.0

    def provenance(self) -> str:
        """Publication caption sentence detailing data origin and coverage."""
        bits = [
            f"Data: {self.study} ({self.contrast})",
            f"Organism: {self.organism}",
            f"Coverage: {self.nodes_with_data}/{self.nodes_total - len(self.nodes_without_loci)} nodes ({self.fraction_covered:.0%})",
            f"Aggregator: {self.aggregator}",
        ]
        if self.ortholog_coverage:
            bits.append(f"Orthology: {self.ortholog_coverage.mapped}/{self.ortholog_coverage.requested} loci")
        return " | ".join(bits)


def parse_expression_table(
    content: str | pathlib.Path,
    locus_col: str | None = None,
    val_col: str | None = None,
    padj_col: str | None = None,
) -> dict[str, tuple[float, float | None]]:
    """Parse a CSV/TSV table into a dictionary mapping locus -> (value, padj)."""
    if isinstance(content, pathlib.Path):
        text = content.read_text(encoding="utf-8")
    else:
        text = str(content)

    # Sniff delimiter
    first_line = text.strip().split("\n")[0]
    delimiter = "\t" if "\t" in first_line else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)

    rows = [r for r in reader if r and not r[0].startswith("#")]
    if not rows:
        raise ProjectionError("The expression table is empty.")

    header = [h.strip() for h in rows[0]]
    body = rows[1:]

    # Infer locus column if not given
    locus_idx = 0
    if locus_col and locus_col in header:
        locus_idx = header.index(locus_col)
    else:
        # Check first row tokens
        for idx, col_name in enumerate(header):
            col_lower = col_name.lower()
            if any(k in col_lower for k in ("locus", "gene", "id", "agi", "tair")):
                locus_idx = idx
                break

    # Infer value column
    val_idx = 1
    if val_col and val_col in header:
        val_idx = header.index(val_col)
    else:
        for idx, col_name in enumerate(header):
            col_lower = col_name.lower()
            if any(k in col_lower for k in ("log2fc", "logfc", "fc", "diff", "value", "abundance", "stat")):
                val_idx = idx
                break

    # Infer padj column
    padj_idx = None
    if padj_col and padj_col in header:
        padj_idx = header.index(padj_col)
    else:
        for idx, col_name in enumerate(header):
            col_lower = col_name.lower()
            if any(k in col_lower for k in ("padj", "fdr", "qval", "adj.p.val", "pvalue", "p_adj")):
                padj_idx = idx
                break

    data: dict[str, tuple[float, float | None]] = {}
    for r in body:
        if len(r) <= max(locus_idx, val_idx):
            continue
        gene_id = r[locus_idx].strip()
        if not gene_id:
            continue
        try:
            val = float(r[val_idx])
        except ValueError:
            continue

        padj = None
        if padj_idx is not None and len(r) > padj_idx:
            try:
                padj = float(r[padj_idx])
            except ValueError:
                pass

        data[gene_id.upper()] = (val, padj)

    return data


def project_expression(
    laid_out_map: LaidOutMap,
    expression_data: dict[str, tuple[float, float | None]],
    *,
    study: str = "Dataset",
    contrast: str = "Treated vs Control",
    organism: str = "Arabidopsis thaliana",
    aggregator: str = "mean",
    alpha: float = 0.05,
    ortholog_map: dict[str, list[Ortholog]] | None = None,
    ortholog_coverage: Coverage | None = None,
) -> Projection:
    """Project parsed expression data onto the nodes of a LaidOutMap."""
    if aggregator not in AGGREGATORS:
        raise ValueError(f"Unknown aggregator {aggregator!r}. Choose from {list(AGGREGATORS.keys())}")

    agg_fn = AGGREGATORS[aggregator]
    values: dict[str, NodeValue] = {}
    nodes_without_loci: list[str] = []
    nodes_unmatched: list[str] = []

    for node in laid_out_map.nodes:
        # Extract loci associated with node
        raw_loci = node.payload.get("loci", [])
        if not raw_loci and node.subunits:
            raw_loci = [s.get("locus", "") for s in node.subunits if s.get("locus")]
        if not raw_loci and node.family_loci:
            raw_loci = node.family_loci

        loci = [l.strip().upper() for l in raw_loci if l.strip()]

        if not loci:
            nodes_without_loci.append(node.id)
            continue

        # Look up loci in expression data (or via orthologs)
        node_vals: list[float] = []
        node_padjs: list[float] = []
        used_loci: list[str] = []
        missing_loci: list[str] = []
        via_orthos: list[str] = []

        for locus in loci:
            if locus in expression_data:
                v, p = expression_data[locus]
                node_vals.append(v)
                if p is not None:
                    node_padjs.append(p)
                used_loci.append(locus)
            elif ortholog_map and locus in ortholog_map:
                # Check target orthologs
                matched_ortho = False
                for ortho in ortholog_map[locus]:
                    tid = ortho.target_id.upper()
                    tsym = ortho.target_symbol.upper()
                    target_key = tid if tid in expression_data else (tsym if tsym in expression_data else None)
                    if target_key:
                        v, p = expression_data[target_key]
                        node_vals.append(v)
                        if p is not None:
                            node_padjs.append(p)
                        used_loci.append(locus)
                        via_orthos.append(f"{locus}->{target_key}")
                        matched_ortho = True
                        break
                if not matched_ortho:
                    missing_loci.append(locus)
            else:
                missing_loci.append(locus)

        if node_vals:
            aggregated_val = agg_fn(node_vals)
            # Node is significant if any component subunit or locus meets alpha
            is_sig = any(p <= alpha for p in node_padjs) if node_padjs else None
            min_padj = min(node_padjs) if node_padjs else None

            values[node.id] = NodeValue(
                node_id=node.id,
                value=aggregated_val,
                n_loci=len(loci),
                loci_used=tuple(used_loci),
                loci_missing=tuple(missing_loci),
                aggregator=aggregator,
                significant=is_sig,
                p_adj=min_padj,
                via_orthologs=tuple(via_orthos),
            )
        else:
            nodes_unmatched.append(node.id)

    total_addressable = len(laid_out_map.nodes) - len(nodes_without_loci)
    if total_addressable > 0 and len(values) == 0:
        raise ProjectionError(
            f"Zero of {total_addressable} addressable nodes matched any identifiers in the expression dataset. "
            f"Check identifier namespace (e.g. AGI loci like AT1G01010 vs symbols)."
        )

    return Projection(
        map_id=laid_out_map.id,
        study=study,
        contrast=contrast,
        organism=organism,
        aggregator=aggregator,
        values=values,
        nodes_total=len(laid_out_map.nodes),
        nodes_without_loci=tuple(nodes_without_loci),
        nodes_unmatched=tuple(nodes_unmatched),
        alpha=alpha,
        ortholog_coverage=ortholog_coverage,
    )
