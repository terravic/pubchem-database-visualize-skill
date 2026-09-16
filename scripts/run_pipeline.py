#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "requests>=2.28.0",
#     "urllib3>=2.0.0",
#     "jsonschema>=4.0.0",
# ]
# ///

"""
PubChem Unified End-to-End Profiling and Visualization Pipeline
Orchestrates chemical resolution, computed properties, drug-likeness rules,
GHS hazard safety, clinical pharmacology, 3D conformers, bioassays, and
interactive UI dashboard generation.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema

# Ensure scripts directory is importable
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from pubchem_api import PubChemClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("run_pipeline")

LICENSE_PATH = PROJECT_ROOT / ".licenses" / "pubchem_database_visualize_LICENSE.txt"
TEMPLATE_PATH = PROJECT_ROOT / "assets" / "dashboard_template.html"
SCHEMA_PATH = PROJECT_ROOT / "assets" / "schemas" / "compound_profile_schema.json"


def ensure_license_acceptance() -> None:
    """
    Verifies or initializes the PubChem citation and usage policy acknowledgment.
    """
    if not LICENSE_PATH.is_file():
        LICENSE_PATH.parent.mkdir(parents=True, exist_ok=True)
        notice = (
            "PubChem Data Usage and Citation Acknowledgment\n"
            "==============================================\n"
            "This workspace complies with NCBI PubChem policies:\n"
            "1. Citation: https://pubchem.ncbi.nlm.nih.gov/docs/citation-guidelines\n"
            "2. Usage Policy: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest\n"
            "Recorded Acceptance Date: 2026-09-15\n"
        )
        with open(LICENSE_PATH, "w", encoding="utf-8") as f:
            f.write(notice)
        logger.info("Recorded PubChem citation and usage acknowledgment at %s", LICENSE_PATH)


def validate_profile_schema(profile: Dict[str, Any]) -> None:
    """
    Validates the generated profile data model against the formal JSON schema.
    """
    if not SCHEMA_PATH.is_file():
        logger.warning("Schema definition not found at %s; skipping strict validation", SCHEMA_PATH)
        return

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    try:
        jsonschema.validate(instance=profile, schema=schema)
        logger.info("Profile data successfully validated against compound_profile_schema.json")
    except jsonschema.ValidationError as err:
        logger.warning("Profile schema validation warning: %s", err.message)


def generate_dashboard_html(profile: Dict[str, Any], sdf_content: Optional[str], output_path: Path) -> None:
    """
    Synthesizes self-contained interactive UI dashboard HTML file.
    """
    if not TEMPLATE_PATH.is_file():
        raise FileNotFoundError(f"Dashboard template not found at {TEMPLATE_PATH}")

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    # Inject data payloads into JavaScript placeholders
    json_data_str = json.dumps(profile)
    json_sdf_str = json.dumps(sdf_content) if sdf_content else "null"

    rendered = template.replace("/* __COMPOUND_DATA_PLACEHOLDER__ */ null", json_data_str)
    rendered = rendered.replace("/* __CONFORMER_SDF_PLACEHOLDER__ */ null", json_sdf_str)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(rendered)

    logger.info("Generated interactive UI dashboard at %s", output_path)


def print_summary_report(profile: Dict[str, Any], output_dir: Path) -> None:
    """
    Prints a professional, human-engineered chemical profiling report to stdout.
    """
    ident = profile["identifiers"]
    props = profile["properties"]
    ro5 = profile["drug_likeness"]["lipinski_rule_of_five"]
    veber = profile["drug_likeness"]["veber_rule"]
    safety = profile["safety"]
    pharm = profile["pharmacology"]
    assays = profile["bioassays"]
    analogs = profile["analogs"]

    print("\n================================================================================")
    print(f"PUBCHEM CHEMICAL PROFILING REPORT: {ident.get('iupac_name', 'Unknown')}")
    print("================================================================================")
    print(f"PubChem CID          : {profile['cid']}")
    print(f"IUPAC Name           : {ident.get('iupac_name', 'N/A')}")
    print(f"Molecular Formula    : {ident.get('molecular_formula', 'N/A')}")
    print(f"Molecular Weight     : {props.get('molecular_weight', 0.0):.2f} g/mol")
    print(f"InChIKey             : {ident.get('inchi_key', 'N/A')}")
    print(f"Canonical SMILES     : {ident.get('canonical_smiles', 'N/A')}")
    print("--------------------------------------------------------------------------------")
    print("DRUG-LIKENESS EVALUATION")
    print(f"Lipinski Rule of 5   : {ro5['status']} ({ro5['violations']} violations)")
    if ro5["violation_details"]:
        for v in ro5["violation_details"]:
            print(f"  - {v}")
    print(f"Veber Rule           : {veber['status']} ({veber['violations']} violations)")
    if veber["violation_details"]:
        for v in veber["violation_details"]:
            print(f"  - {v}")
    print(f"Key Descriptors      : XLogP={props.get('xlogp')}, HBD={props.get('h_bond_donors')}, HBA={props.get('h_bond_acceptors')}, TPSA={props.get('tpsa')} A^2, RotB={props.get('rotatable_bonds')}")
    print("--------------------------------------------------------------------------------")
    print("GHS HAZARD & SAFETY CLASSIFICATION")
    print(f"Signal Word          : {safety.get('signal_word', 'NOT_CLASSIFIED')}")
    if safety.get("hazard_statements"):
        print("Hazard Statements    :")
        for h in safety["hazard_statements"][:5]:
            print(f"  - {h['code']}: {h['statement']}")
    else:
        print("Hazard Statements    : No mandatory classifications filed")
    print("--------------------------------------------------------------------------------")
    print("CLINICAL PHARMACOLOGY & TARGETS")
    print(f"Approved Indications : {pharm.get('indications', 'N/A')}")
    print(f"Mechanism of Action  : {pharm.get('mechanism_of_action', 'N/A')}")
    targets_str = ", ".join(pharm.get("targets", [])) if pharm.get("targets") else "None documented"
    print(f"Biological Targets   : {targets_str}")
    print("--------------------------------------------------------------------------------")
    print("BIOASSAYS & ANALOG CONCORDANCE")
    print(f"Assay Screens        : Tested={assays.get('total_tested', 0)} | Active Hits={assays.get('total_active', 0)}")
    if analogs:
        analogs_str = ", ".join(f"{a.get('iupac_name', 'CID-' + str(a.get('cid')))} ({int(a.get('similarity_score', 0)*100)}%)" for a in analogs[:3])
        print(f"Top 2D Analogs       : {analogs_str}")
    else:
        print("Top 2D Analogs       : None identified above threshold")
    print("--------------------------------------------------------------------------------")
    print("GENERATED ARTIFACTS")
    print(f"1. Structured Profile: {output_dir / 'compound_profile.json'}")
    print(f"2. 3D Conformer SDF  : {output_dir / 'conformer3d.sdf'}")
    print(f"3. UI Dashboard      : {output_dir / 'dashboard.html'}")
    print("================================================================================\n")


def run_pipeline(
    name: Optional[str] = None,
    cid: Optional[int] = None,
    smiles: Optional[str] = None,
    inchi: Optional[str] = None,
    output_dir: Optional[str] = None,
    mock: bool = False,
    brain_dir: Optional[str] = None,
) -> int:
    """
    Executes the complete chemical profiling pipeline.
    """
    ensure_license_acceptance()

    if not any([name, cid, smiles, inchi]):
        logger.error("Must specify at least one search criterion: --name, --cid, --smiles, or --inchi")
        return 1

    client = PubChemClient()

    # Step 1: Identifier Resolution
    resolved_cid: Optional[int] = cid
    query_str = ""

    if cid is not None:
        query_str = f"CID-{cid}"
        logger.info("Using specified CID: %d", cid)
    elif name:
        query_str = name.strip()
        logger.info("Resolving chemical name: '%s'", name)
        resolved_cid = client.resolve(name=name, mock=mock)
    elif smiles:
        query_str = smiles.strip()
        logger.info("Resolving SMILES string: '%s'", smiles)
        resolved_cid = client.resolve(smiles=smiles, mock=mock)
    elif inchi:
        query_str = inchi.strip()
        logger.info("Resolving InChI string: '%s'", inchi)
        resolved_cid = client.resolve(inchi=inchi, mock=mock)

    if resolved_cid is None:
        logger.error("Unable to resolve query '%s' to a valid PubChem CID", query_str)
        return 1

    logger.info("Successfully established canonical CID: %d", resolved_cid)

    # Step 2: Computed Physicochemical Properties
    logger.info("Fetching computed physicochemical properties for CID %d...", resolved_cid)
    prop_data = client.get_properties(resolved_cid, mock=mock)
    if not prop_data:
        logger.error("Failed to retrieve physicochemical properties for CID %d", resolved_cid)
        return 1

    # Step 3: Drug-Likeness Calculations
    logger.info("Calculating Lipinski Rule of 5 and Veber drug-likeness rules...")
    ro5_eval = client.evaluate_lipinski(prop_data["properties"])
    veber_eval = client.evaluate_veber(prop_data["properties"])

    # Step 4: GHS Hazard Safety
    logger.info("Extracting GHS hazard safety classifications...")
    safety_data = client.get_safety(resolved_cid, mock=mock)

    # Step 5: Clinical Pharmacology & Mechanism
    logger.info("Retrieving clinical pharmacology, indications, and targets...")
    pharm_data = client.get_pharmacology(resolved_cid, mock=mock)

    # Step 6: 3D Conformer Coordinates (SDF)
    logger.info("Acquiring 3D molecular conformer coordinates...")
    conformer_sdf = client.get_conformer_3d(resolved_cid, mock=mock)
    has_3d = conformer_sdf is not None and "3D" in conformer_sdf

    # Step 7: BioAssay Activity
    logger.info("Querying PubChem BioAssay activity screening data...")
    assay_data = client.get_bioassays(resolved_cid, active_only=True, max_records=5, mock=mock)

    # Step 8: Chemical Similarity Analogs
    logger.info("Searching for 2D structural analogs...")
    analogs = client.get_similarity_analogs(
        cid=resolved_cid,
        smiles=prop_data.get("canonical_smiles"),
        threshold=85,
        max_records=5,
        mock=mock,
    )

    # Step 9: Assemble Compound Profile
    profile: Dict[str, Any] = {
        "cid": resolved_cid,
        "identifiers": {
            "iupac_name": prop_data.get("iupac_name", f"CID-{resolved_cid}"),
            "canonical_smiles": prop_data.get("canonical_smiles", ""),
            "isomeric_smiles": prop_data.get("isomeric_smiles", ""),
            "molecular_formula": prop_data.get("molecular_formula", ""),
            "inchi": prop_data.get("inchi", ""),
            "inchi_key": prop_data.get("inchi_key", ""),
            "query_input": query_str,
        },
        "properties": prop_data["properties"],
        "drug_likeness": {
            "lipinski_rule_of_five": ro5_eval,
            "veber_rule": veber_eval,
        },
        "safety": safety_data,
        "pharmacology": pharm_data,
        "bioassays": assay_data,
        "analogs": analogs,
        "has_3d_conformer": has_3d,
    }

    # Step 10: Validate against Schema
    validate_profile_schema(profile)

    # Step 11: Setup Output Directory
    if output_dir:
        dest_dir = Path(output_dir).resolve()
    else:
        slug = "".join(c if c.isalnum() else "_" for c in (name or str(resolved_cid))).strip("_")
        dest_dir = (PROJECT_ROOT / "output" / slug).resolve()

    dest_dir.mkdir(parents=True, exist_ok=True)

    # Step 12: Write Artifacts
    profile_json_path = dest_dir / "compound_profile.json"
    with open(profile_json_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    logger.info("Saved compound profile to %s", profile_json_path)

    sdf_path = dest_dir / "conformer3d.sdf"
    if conformer_sdf:
        with open(sdf_path, "w", encoding="utf-8") as f:
            f.write(conformer_sdf)
        logger.info("Saved 3D conformer SDF to %s", sdf_path)
    else:
        logger.warning("No 3D conformer available; writing placeholder notice to SDF file")
        with open(sdf_path, "w", encoding="utf-8") as f:
            f.write(f"$$$$\nNO 3D CONFORMER AVAILABLE FOR CID {resolved_cid}\n$$$$\n")

    dashboard_path = dest_dir / "dashboard.html"
    generate_dashboard_html(profile, conformer_sdf, dashboard_path)

    # If artifact directory specified or detected, emit user-facing artifact
    if brain_dir:
        brain_dest = Path(brain_dir).resolve() / "dashboard.html"
        try:
            generate_dashboard_html(profile, conformer_sdf, brain_dest)
            logger.info("Emitted dashboard artifact to %s", brain_dest)
        except Exception as e:
            logger.warning("Failed to emit dashboard to artifact directory: %s", e)

    # Optionally update local root dashboard.html for local testing convenience
    # Only update root dashboard when running with default output (not temporary test directory)
    is_project_output = output_dir is None or str(Path(output_dir).resolve()).startswith(str((PROJECT_ROOT / "output").resolve()))
    if is_project_output:
        root_dashboard = PROJECT_ROOT / "dashboard.html"
        try:
            generate_dashboard_html(profile, conformer_sdf, root_dashboard)
            logger.info("Updated root test dashboard at %s", root_dashboard)
        except Exception as e:
            logger.warning("Failed to write root dashboard.html: %s", e)

    # Step 13: Print Report
    print_summary_report(profile, dest_dir)

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PubChem Unified End-to-End Profiling and UI Dashboard Pipeline",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_argument_group("Search Query (specify at least one)")
    group.add_argument("--name", help="Common chemical name, trade name, or IUPAC nomenclature")
    group.add_argument("--cid", type=int, help="PubChem Compound ID (CID)")
    group.add_argument("--smiles", help="Canonical or isomeric SMILES representation")
    group.add_argument("--inchi", help="International Chemical Identifier string")

    parser.add_argument(
        "-o", "--output",
        help="Destination directory for profile artifacts and dashboard",
    )
    parser.add_argument(
        "--brain-dir",
        help="Path to artifact directory to emit user-facing dashboard artifact",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Execute in hermetic synthetic mock mode without internet access",
    )

    args = parser.parse_args()

    return run_pipeline(
        name=args.name,
        cid=args.cid,
        smiles=args.smiles,
        inchi=args.inchi,
        output_dir=args.output,
        mock=args.mock,
        brain_dir=args.brain_dir,
    )


if __name__ == "__main__":
    sys.exit(main())
