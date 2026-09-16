"""
Integration Tests for Unified Profiling Pipeline
Tests end-to-end execution, file generation, schema conformance, and CLI flags.
"""

import json
from pathlib import Path
import pytest
from run_pipeline import run_pipeline


def test_pipeline_execution_mock_by_name(tmp_path: Path):
    out_dir = tmp_path / "aspirin_test"
    code = run_pipeline(name="aspirin", output_dir=str(out_dir), mock=True)
    assert code == 0

    # Verify artifacts exist
    profile_file = out_dir / "compound_profile.json"
    sdf_file = out_dir / "conformer3d.sdf"
    dash_file = out_dir / "dashboard.html"

    assert profile_file.is_file()
    assert sdf_file.is_file()
    assert dash_file.is_file()

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    assert profile["cid"] == 2244
    assert profile["identifiers"]["molecular_formula"] == "C9H8O4"
    assert profile["drug_likeness"]["lipinski_rule_of_five"]["status"] == "COMPLIANT"
    assert profile["has_3d_conformer"] is True


def test_pipeline_execution_mock_by_cid(tmp_path: Path):
    out_dir = tmp_path / "imatinib_test"
    code = run_pipeline(cid=5291, output_dir=str(out_dir), mock=True)
    assert code == 0

    profile_file = out_dir / "compound_profile.json"
    assert profile_file.is_file()

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    assert profile["cid"] == 5291
    assert "imatinib" in profile["identifiers"]["iupac_name"].lower() or "piperazin" in profile["identifiers"]["iupac_name"].lower()


def test_pipeline_execution_mock_by_smiles(tmp_path: Path):
    out_dir = tmp_path / "caffeine_smiles"
    code = run_pipeline(smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C", output_dir=str(out_dir), mock=True)
    assert code == 0

    profile_file = out_dir / "compound_profile.json"
    assert profile_file.is_file()

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)

    assert profile["cid"] == 2519


def test_pipeline_no_criteria():
    code = run_pipeline(mock=True)
    assert code == 1


def test_pipeline_invalid_name(tmp_path: Path):
    out_dir = tmp_path / "invalid_name"
    code = run_pipeline(name="unknown_non_existent_chemical_abc999", output_dir=str(out_dir), mock=True)
    assert code == 1


def test_pipeline_missing_3d_conformer_graceful(tmp_path: Path):
    out_dir = tmp_path / "no_3d_test"
    code = run_pipeline(cid=77777777, output_dir=str(out_dir), mock=True)
    assert code == 0

    profile_file = out_dir / "compound_profile.json"
    sdf_file = out_dir / "conformer3d.sdf"
    dash_file = out_dir / "dashboard.html"

    assert profile_file.is_file()
    assert sdf_file.is_file()
    assert dash_file.is_file()

    with open(profile_file, "r", encoding="utf-8") as f:
        profile = json.load(f)
    assert profile["has_3d_conformer"] is False
