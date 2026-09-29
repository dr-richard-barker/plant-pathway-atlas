import pytest
from plantpath.ortho import Coverage, Ortholog, OrthologyError, project_orthologs


def test_identity_projection():
    loci = ["AT1G01010", "AT2G02020"]
    ortho_map, cov = project_orthologs(loci, target_species="arabidopsis_thaliana")
    assert cov.fraction_mapped == 1.0
    assert len(ortho_map) == 2
    assert ortho_map["AT1G01010"][0].target_id == "AT1G01010"


def test_offline_matrix_projection():
    loci = ["AT3G22370"]  # AOX1A
    matrix = {
        "AT3G22370": [
            {"target_species": "oryza_sativa", "target_id": "Os04g0600300", "homology_type": "ortholog_one2one"}
        ]
    }
    ortho_map, cov = project_orthologs(
        loci, target_species="oryza_sativa", offline_matrix=matrix
    )
    assert cov.fraction_mapped == 1.0
    assert ortho_map["AT3G22370"][0].target_id == "Os04g0600300"


def test_zero_hit_refusal():
    loci = ["AT1G99999"]
    with pytest.raises(OrthologyError, match="Zero loci mapped"):
        project_orthologs(loci, target_species="human", offline_matrix={})
