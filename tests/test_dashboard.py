"""
Tests for UI Dashboard Generation & HTML Structure
Validates theme toggle, SVG iconography, static 3D chemical structure canvas, and 3D viewer hooks.
"""

import json
from pathlib import Path
import pytest
from run_pipeline import generate_dashboard_html


def test_dashboard_html_generation(tmp_path: Path):
    sample_profile = {
        "cid": 2244,
        "identifiers": {
            "iupac_name": "2-acetyloxybenzoic acid",
            "canonical_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "isomeric_smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "molecular_formula": "C9H8O4",
            "inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
            "inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            "query_input": "aspirin",
        },
        "properties": {
            "molecular_weight": 180.16,
            "xlogp": 1.2,
            "h_bond_donors": 1,
            "h_bond_acceptors": 4,
            "tpsa": 63.6,
            "rotatable_bonds": 2,
            "heavy_atoms": 13,
            "exact_mass": 180.042,
            "complexity": 212.0,
        },
        "drug_likeness": {
            "lipinski_rule_of_five": {
                "compliant": True,
                "violations": 0,
                "violation_details": [],
                "status": "COMPLIANT",
            },
            "veber_rule": {
                "compliant": True,
                "violations": 0,
                "violation_details": [],
                "status": "COMPLIANT",
            },
        },
        "safety": {
            "signal_word": "WARNING",
            "hazard_statements": [{"code": "H302", "statement": "Harmful if swallowed"}],
            "precautionary_statements": [],
            "pictograms": ["GHS07-harmful"],
        },
        "pharmacology": {
            "indications": "Test indications",
            "mechanism_of_action": "Test MoA",
            "targets": ["COX-1"],
        },
        "bioassays": {
            "total_tested": 100,
            "total_active": 5,
            "active_assays": [],
        },
        "analogs": [],
        "has_3d_conformer": True,
    }

    sample_sdf = "2244\n -Test-\n$$$$\n"
    out_html = tmp_path / "test_dashboard.html"

    generate_dashboard_html(sample_profile, sample_sdf, out_html)

    assert out_html.is_file()
    content = out_html.read_text(encoding="utf-8")

    # Verify structural HTML tags
    assert "<!DOCTYPE html>" in content
    assert "<html" in content
    assert "</html>" in content

    # Verify essential DOM component IDs and view titles
    assert "3D Molecular View" in content
    assert 'id="molviewer"' in content
    assert 'id="physics-canvas"' in content
    assert 'id="radar-svg"' in content
    assert 'id="properties-list"' in content
    assert 'id="hazard-statements"' in content

    # Verify Light / Dark theme toggle button and clean SVG icons
    assert 'id="theme-toggle-btn"' in content
    assert 'sun-icon' in content
    assert 'moon-icon' in content

    # Verify Unified 3D Viewer Toolbar controls and Inspector
    assert 'id="btn-ballstick"' in content
    assert 'id="btn-stick"' in content
    assert 'id="btn-sphere"' in content
    assert 'id="btn-wireframe"' in content
    assert 'id="btn-label-toggle"' in content
    assert 'id="btn-measure"' in content
    assert 'id="btn-spin"' in content
    assert 'id="atom-tooltip"' in content
    assert 'id="viewer-hud"' in content

    # Verify copy buttons
    assert 'copy-btn' in content

    # Verify native zero-dependency visualization engines
    assert 'class Molecule3DViewer' in content
    assert 'class Static3DStructureViewer' in content
    assert 'canvas-3d' in content

    # Verify data payloads were injected and placeholders replaced
    assert "/* __COMPOUND_DATA_PLACEHOLDER__ */ null" not in content
    assert "/* __CONFORMER_SDF_PLACEHOLDER__ */ null" not in content
    assert "2-acetyloxybenzoic acid" in content
    assert "BSYNRYMUTXBXSQ-UHFFFAOYSA-N" in content
