"""
Unit Tests for PubChem API Client & Chemical Descriptors
Tests resolver, property fetchers, Lipinski/Veber rules, safety parser, and mock fallbacks.
"""

import pytest
from pubchem_api import PubChemClient, RateLimiter


def test_rate_limiter_interval():
    limiter = RateLimiter(max_per_sec=10.0)
    assert limiter.min_interval == 0.1
    limiter.wait()
    assert limiter.last_request_time > 0.0


def test_resolve_mock_by_name(mock_client: PubChemClient):
    cid = mock_client.resolve(name="aspirin", mock=True)
    assert cid == 2244

    cid_alt = mock_client.resolve(name="acetylsalicylic acid", mock=True)
    assert cid_alt == 2244


def test_resolve_mock_by_smiles(mock_client: PubChemClient):
    smiles = "CC(=O)OC1=CC=CC=C1C(=O)O"
    cid = mock_client.resolve(smiles=smiles, mock=True)
    assert cid == 2244


def test_resolve_mock_by_inchi(mock_client: PubChemClient):
    inchi = "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)"
    cid = mock_client.resolve(inchi=inchi, mock=True)
    assert cid == 2244


def test_resolve_mock_non_existent(mock_client: PubChemClient):
    cid = mock_client.resolve(name="completely_unknown_molecule_xyz123", mock=True)
    assert cid is None


def test_get_properties_mock_aspirin(mock_client: PubChemClient):
    data = mock_client.get_properties(2244, mock=True)
    assert data is not None
    assert data["cid"] == 2244
    assert data["iupac_name"] == "2-acetyloxybenzoic acid"
    assert data["molecular_formula"] == "C9H8O4"

    props = data["properties"]
    assert props["molecular_weight"] == 180.16
    assert props["xlogp"] == 1.2
    assert props["h_bond_donors"] == 1
    assert props["h_bond_acceptors"] == 4
    assert props["tpsa"] == 63.6
    assert props["rotatable_bonds"] == 2


def test_lipinski_evaluation_compliant():
    # Aspirin properties
    props = {
        "molecular_weight": 180.16,
        "xlogp": 1.2,
        "h_bond_donors": 1,
        "h_bond_acceptors": 4,
    }
    eval_result = PubChemClient.evaluate_lipinski(props)
    assert eval_result["compliant"] is True
    assert eval_result["violations"] == 0
    assert eval_result["status"] == "COMPLIANT"
    assert len(eval_result["violation_details"]) == 0


def test_lipinski_evaluation_borderline():
    # 1 violation (MW > 500)
    props = {
        "molecular_weight": 520.0,
        "xlogp": 3.0,
        "h_bond_donors": 2,
        "h_bond_acceptors": 6,
    }
    eval_result = PubChemClient.evaluate_lipinski(props)
    assert eval_result["compliant"] is True
    assert eval_result["violations"] == 1
    assert eval_result["status"] == "BORDERLINE"
    assert len(eval_result["violation_details"]) == 1


def test_lipinski_evaluation_violation():
    # Atorvastatin properties: MW > 500 and XLogP > 5.0
    props = {
        "molecular_weight": 558.6,
        "xlogp": 5.7,
        "h_bond_donors": 4,
        "h_bond_acceptors": 5,
    }
    eval_result = PubChemClient.evaluate_lipinski(props)
    assert eval_result["compliant"] is False
    assert eval_result["violations"] == 2
    assert eval_result["status"] == "VIOLATION"
    assert len(eval_result["violation_details"]) == 2


def test_veber_evaluation():
    # Compliant case
    props_good = {"rotatable_bonds": 2, "tpsa": 63.6}
    res_good = PubChemClient.evaluate_veber(props_good)
    assert res_good["compliant"] is True
    assert res_good["status"] == "COMPLIANT"

    # Violation case: RotB > 10
    props_bad = {"rotatable_bonds": 12, "tpsa": 150.0}
    res_bad = PubChemClient.evaluate_veber(props_bad)
    assert res_bad["compliant"] is False
    assert res_bad["violations"] == 2
    assert res_bad["status"] == "VIOLATION"


def test_get_safety_mock(mock_client: PubChemClient):
    safety = mock_client.get_safety(2244, mock=True)
    assert safety["signal_word"] == "WARNING"
    assert len(safety["hazard_statements"]) >= 1
    assert any(h["code"] == "H302" for h in safety["hazard_statements"])
    assert "GHS07-harmful" in safety["pictograms"]

    # Benign sugar test
    benign = mock_client.get_safety(88888888, mock=True)
    assert benign["signal_word"] == "NOT_CLASSIFIED"
    assert len(benign["hazard_statements"]) == 0


def test_get_pharmacology_mock(mock_client: PubChemClient):
    pharm = mock_client.get_pharmacology(5291, mock=True)
    assert "leukemia" in pharm["indications"].lower()
    assert "tyrosine kinase" in pharm["mechanism_of_action"].lower()
    assert len(pharm["targets"]) > 0


def test_get_conformer_3d_mock(mock_client: PubChemClient):
    sdf = mock_client.get_conformer_3d(2244, mock=True)
    assert sdf is not None
    assert "2244" in sdf
    assert "V2000" in sdf
    assert "$$$$" in sdf

    # Test compound with no 3D conformer
    no_3d = mock_client.get_conformer_3d(77777777, mock=True)
    assert no_3d is None


def test_get_bioassays_mock(mock_client: PubChemClient):
    assays = mock_client.get_bioassays(2244, mock=True)
    assert assays["total_tested"] == 1420
    assert assays["total_active"] == 18
    assert len(assays["active_assays"]) == 3


def test_get_similarity_analogs_mock(mock_client: PubChemClient):
    analogs = mock_client.get_similarity_analogs(cid=2244, mock=True)
    assert len(analogs) == 3
    assert analogs[0]["iupac_name"] == "salicylic acid"
    assert analogs[0]["similarity_score"] >= 0.85
