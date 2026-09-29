import pathlib
import pytest
from plantpath.maps import compile_map, load_map
from plantpath.project import (
    ProjectionError,
    parse_expression_table,
    project_expression,
)

MAPS_DIR = pathlib.Path(__file__).resolve().parent.parent / "maps" / "src"


def test_parse_expression_table_csv():
    csv_text = "locus,log2FoldChange,padj\nAT3G22370,2.4,0.001\nAT4G35090,-1.5,0.04"
    data = parse_expression_table(csv_text)
    assert "AT3G22370" in data
    assert data["AT3G22370"] == (2.4, 0.001)
    assert data["AT4G35090"] == (-1.5, 0.04)


def test_project_expression_aggregators():
    spec = load_map(MAPS_DIR / "PPA-05_ros_redox.yaml")
    laid_out = compile_map(spec)

    # Provide data for Catalase subunits CAT1 (AT1G20630) and CAT2 (AT4G35090)
    data = {
        "AT1G20630": (1.0, 0.01),
        "AT4G35090": (3.0, 0.001),
    }

    # Mean aggregator
    proj_mean = project_expression(laid_out, data, aggregator="mean")
    assert proj_mean.values["CATALASE_SCAVENGING"].value == 2.0
    assert proj_mean.values["CATALASE_SCAVENGING"].significant is True

    # Extreme aggregator
    proj_ext = project_expression(laid_out, data, aggregator="extreme")
    assert proj_ext.values["CATALASE_SCAVENGING"].value == 3.0


def test_zero_join_refusal():
    spec = load_map(MAPS_DIR / "PPA-01_central_metabolism.yaml")
    laid_out = compile_map(spec)

    # Data completely unrelated to plant loci
    unrelated_data = {"HUMAN_GENE_1": (2.0, 0.01)}
    with pytest.raises(ProjectionError, match="Zero of .* addressable nodes"):
        project_expression(laid_out, unrelated_data)
