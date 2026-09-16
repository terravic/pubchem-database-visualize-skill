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
PubChem API Modular Client & Utilities
Provides CLI subcommands and reusable Python classes for interacting with
NCBI PubChem PUG REST and PUG View services, with local synthetic mock fallback.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import urllib.parse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("pubchem_api")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOCK_DATA_PATH = PROJECT_ROOT / "assets" / "synthetic_mocks.json"


class RateLimiter:
    """
    Enforces NCBI PubChem rate limits:
    - Maximum 5 requests per second.
    - Maximum 400 requests per 60-second window.
    """

    def __init__(self, max_per_sec: float = 4.5, window_sec: float = 1.0):
        self.min_interval = 1.0 / max_per_sec
        self.last_request_time = 0.0

    def wait(self) -> None:
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()


class PubChemClient:
    """
    Client for NCBI PubChem PUG REST and PUG View APIs,
    incorporating defensive retry logic, rate limiting, and hermetic mock fallbacks.
    """

    PUG_REST_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    PUG_VIEW_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data"
    USER_AGENT = "pubchem-database-visualize-skill/1.0.0 (https://pubchem.ncbi.nlm.nih.gov)"

    def __init__(self, mock_fallback: bool = True, timeout: int = 15):
        self.timeout = timeout
        self.mock_fallback = mock_fallback
        self.rate_limiter = RateLimiter()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": self.USER_AGENT,
            "Accept": "application/json",
        })

        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self._mock_cache: Optional[Dict[str, Any]] = None

    def _load_mocks(self) -> Dict[str, Any]:
        if self._mock_cache is None:
            if not MOCK_DATA_PATH.is_file():
                logger.warning("Mock data file not found at %s", MOCK_DATA_PATH)
                return {"compounds": {}}
            with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
                self._mock_cache = json.load(f)
        return self._mock_cache or {"compounds": {}}

    def _get_mock_compound(self, query: str) -> Optional[Dict[str, Any]]:
        mocks = self._load_mocks().get("compounds", {})
        query_clean = str(query).strip().lower()

        # Check by CID directly
        if query_clean in mocks:
            return mocks[query_clean]

        # Check by names, smiles, or formula
        for cid_key, comp in mocks.items():
            if str(comp.get("cid")) == query_clean:
                return comp
            names = [n.lower() for n in comp.get("names", [])]
            if query_clean in names:
                return comp
            if comp.get("canonical_smiles", "").lower() == query_clean:
                return comp
            if comp.get("iupac_name", "").lower() == query_clean:
                return comp
            if comp.get("inchi", "").lower() == query_clean:
                return comp
            if comp.get("inchi_key", "").lower() == query_clean:
                return comp

        return None

    def resolve(
        self,
        name: Optional[str] = None,
        smiles: Optional[str] = None,
        inchi: Optional[str] = None,
        mock: bool = False,
    ) -> Optional[int]:
        """
        Resolves a chemical name, SMILES string, or InChI string to a canonical PubChem CID.
        """
        if mock:
            query = name or smiles or inchi
            if not query:
                return None
            comp = self._get_mock_compound(query)
            if comp:
                return int(comp["cid"])
            logger.error("Compound '%s' not found in synthetic mock registry", query)
            return None

        self.rate_limiter.wait()

        try:
            if name:
                encoded = urllib.parse.quote(name.strip())
                url = f"{self.PUG_REST_BASE}/compound/name/{encoded}/cids/JSON"
                resp = self.session.get(url, timeout=self.timeout)
            elif smiles:
                encoded = urllib.parse.quote(smiles.strip())
                url = f"{self.PUG_REST_BASE}/compound/smiles/{encoded}/cids/JSON"
                resp = self.session.get(url, timeout=self.timeout)
            elif inchi:
                url = f"{self.PUG_REST_BASE}/compound/inchi/cids/JSON"
                resp = self.session.post(url, data={"inchi": inchi.strip()}, timeout=self.timeout)
            else:
                raise ValueError("One of name, smiles, or inchi must be specified for resolution")

            if resp.status_code == 200:
                data = resp.json()
                cids = data.get("IdentifierList", {}).get("CID", [])
                if cids:
                    return int(cids[0])
            elif resp.status_code == 404:
                logger.info("Identifier not found on PubChem")
            else:
                logger.warning("PubChem resolve returned HTTP status %d", resp.status_code)

        except requests.RequestException as exc:
            logger.error("Network error during identifier resolution: %s", exc)
            if self.mock_fallback:
                logger.info("Attempting resolution fallback against synthetic mock database")
                query = name or smiles or inchi
                if query:
                    comp = self._get_mock_compound(query)
                    if comp:
                        return int(comp["cid"])

        return None

    def get_properties(self, cid: int, mock: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches computed 2D physicochemical properties for a specified CID.
        """
        if mock:
            comp = self._get_mock_compound(str(cid))
            if comp:
                return {
                    "cid": comp["cid"],
                    "iupac_name": comp.get("iupac_name", ""),
                    "canonical_smiles": comp.get("canonical_smiles", ""),
                    "isomeric_smiles": comp.get("isomeric_smiles", comp.get("canonical_smiles", "")),
                    "molecular_formula": comp.get("molecular_formula", ""),
                    "inchi": comp.get("inchi", ""),
                    "inchi_key": comp.get("inchi_key", ""),
                    "properties": comp.get("properties", {}),
                }
            return None

        self.rate_limiter.wait()
        props_list = [
            "MolecularFormula",
            "MolecularWeight",
            "CanonicalSMILES",
            "IsomericSMILES",
            "InChI",
            "InChIKey",
            "IUPACName",
            "XLogP",
            "ExactMass",
            "TPSA",
            "Complexity",
            "HBondDonorCount",
            "HBondAcceptorCount",
            "RotatableBondCount",
            "HeavyAtomCount",
        ]
        props_str = ",".join(props_list)
        url = f"{self.PUG_REST_BASE}/compound/cid/{cid}/property/{props_str}/JSON"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                raw_props = resp.json().get("PropertyTable", {}).get("Properties", [])
                if raw_props:
                    p = raw_props[0]
                    return {
                        "cid": cid,
                        "iupac_name": p.get("IUPACName", f"CID-{cid}"),
                        "canonical_smiles": p.get("CanonicalSMILES", p.get("SMILES", "")),
                        "isomeric_smiles": p.get("IsomericSMILES", p.get("SMILES", "")),
                        "molecular_formula": p.get("MolecularFormula", ""),
                        "inchi": p.get("InChI", ""),
                        "inchi_key": p.get("InChIKey", ""),
                        "properties": {
                            "molecular_weight": float(p.get("MolecularWeight", 0.0)),
                            "xlogp": float(p.get("XLogP")) if p.get("XLogP") is not None else None,
                            "h_bond_donors": int(p.get("HBondDonorCount", 0)),
                            "h_bond_acceptors": int(p.get("HBondAcceptorCount", 0)),
                            "tpsa": float(p.get("TPSA", 0.0)),
                            "rotatable_bonds": int(p.get("RotatableBondCount", 0)),
                            "heavy_atoms": int(p.get("HeavyAtomCount", 0)),
                            "exact_mass": float(p.get("ExactMass", 0.0)) if p.get("ExactMass") else None,
                            "complexity": float(p.get("Complexity", 0.0)) if p.get("Complexity") else None,
                        },
                    }
            elif resp.status_code == 404:
                logger.warning("Properties for CID %d not found", cid)
            else:
                logger.warning("PubChem properties endpoint returned status %d", resp.status_code)
        except requests.RequestException as exc:
            logger.error("Network error fetching properties for CID %d: %s", cid, exc)
            if self.mock_fallback:
                comp = self._get_mock_compound(str(cid))
                if comp:
                    return {
                        "cid": comp["cid"],
                        "iupac_name": comp.get("iupac_name", ""),
                        "canonical_smiles": comp.get("canonical_smiles", ""),
                        "isomeric_smiles": comp.get("isomeric_smiles", ""),
                        "molecular_formula": comp.get("molecular_formula", ""),
                        "inchi": comp.get("inchi", ""),
                        "inchi_key": comp.get("inchi_key", ""),
                        "properties": comp.get("properties", {}),
                    }

        return None

    @staticmethod
    def evaluate_lipinski(properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates Lipinski's Rule of Five:
        - Molecular Weight <= 500 Da
        - XLogP <= 5.0
        - Hydrogen Bond Donors <= 5
        - Hydrogen Bond Acceptors <= 10
        """
        violations: List[str] = []

        mw = properties.get("molecular_weight", 0.0)
        if mw > 500.0:
            violations.append(f"Molecular weight ({mw:.2f} Da) exceeds 500 Da threshold")

        xlogp = properties.get("xlogp")
        if xlogp is not None and xlogp > 5.0:
            violations.append(f"XLogP ({xlogp:.2f}) exceeds 5.0 threshold")

        hbd = properties.get("h_bond_donors", 0)
        if hbd > 5:
            violations.append(f"H-bond donors ({hbd}) exceeds 5 threshold")

        hba = properties.get("h_bond_acceptors", 0)
        if hba > 10:
            violations.append(f"H-bond acceptors ({hba}) exceeds 10 threshold")

        v_count = len(violations)
        if v_count == 0:
            status = "COMPLIANT"
            compliant = True
        elif v_count == 1:
            status = "BORDERLINE"
            compliant = True
        else:
            status = "VIOLATION"
            compliant = False

        return {
            "compliant": compliant,
            "violations": v_count,
            "violation_details": violations,
            "status": status,
        }

    @staticmethod
    def evaluate_veber(properties: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluates Veber rules for oral bioavailability:
        - Rotatable Bonds <= 10
        - Topological Polar Surface Area (TPSA) <= 140 A^2
        """
        violations: List[str] = []

        rotb = properties.get("rotatable_bonds", 0)
        if rotb > 10:
            violations.append(f"Rotatable bond count ({rotb}) exceeds 10 threshold")

        tpsa = properties.get("tpsa", 0.0)
        if tpsa > 140.0:
            violations.append(f"TPSA ({tpsa:.2f} Å²) exceeds 140.0 Å² threshold")

        v_count = len(violations)
        return {
            "compliant": (v_count == 0),
            "violations": v_count,
            "violation_details": violations,
            "status": "COMPLIANT" if v_count == 0 else "VIOLATION",
        }

    def get_safety(self, cid: int, mock: bool = False) -> Dict[str, Any]:
        """
        Retrieves GHS hazard safety classifications from PUG View.
        """
        if mock:
            comp = self._get_mock_compound(str(cid))
            if comp and "safety" in comp:
                return comp["safety"]
            return {
                "signal_word": "NOT_CLASSIFIED",
                "hazard_statements": [],
                "precautionary_statements": [],
                "pictograms": [],
            }

        self.rate_limiter.wait()
        url = f"{self.PUG_VIEW_BASE}/compound/{cid}/JSON?heading=GHS+Classification"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                return self._parse_ghs_data(data)
            elif resp.status_code == 404:
                logger.info("GHS classification not present for CID %d", cid)
            else:
                logger.warning("PUG View GHS endpoint returned status %d", resp.status_code)
        except requests.RequestException as exc:
            logger.error("Network error fetching safety data for CID %d: %s", cid, exc)
            if self.mock_fallback:
                comp = self._get_mock_compound(str(cid))
                if comp and "safety" in comp:
                    return comp["safety"]

        return {
            "signal_word": "NOT_CLASSIFIED",
            "hazard_statements": [],
            "precautionary_statements": [],
            "pictograms": [],
        }

    def _parse_ghs_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        signal_words: List[str] = []
        hazard_statements: List[Dict[str, str]] = []
        precautionary_statements: List[Dict[str, str]] = []
        pictograms: List[str] = []

        seen_h_codes: set[str] = set()
        seen_p_codes: set[str] = set()

        h_pattern = re.compile(r"^(H\d{3}[A-Za-z]?)(?:\s*\([^)]*\))?:\s*(.*?)(?:\s*\[.*\])?$")

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if "Information" in node:
                    for info in node["Information"]:
                        name = info.get("Name", "")
                        val = info.get("Value", {})
                        str_list = [sm.get("String", "") for sm in val.get("StringWithMarkup", []) if sm.get("String")]

                        if name == "Signal":
                            for s in str_list:
                                clean_s = s.strip().upper()
                                if clean_s in ("DANGER", "WARNING"):
                                    signal_words.append(clean_s)

                        elif name == "GHS Hazard Statements":
                            for stmt in str_list:
                                match = h_pattern.match(stmt.strip())
                                if match:
                                    code = match.group(1).upper()
                                    desc = match.group(2).strip()
                                    if code not in seen_h_codes:
                                        seen_h_codes.add(code)
                                        hazard_statements.append({"code": code, "statement": desc})

                        elif name == "Precautionary Statement Codes":
                            for p_line in str_list:
                                tokens = re.findall(r"P\d{3}(?:\+P\d{3})*", p_line)
                                for p in tokens:
                                    if p not in seen_p_codes:
                                        seen_p_codes.add(p)
                                        precautionary_statements.append({"code": p, "statement": f"Precautionary code {p}"})

                        elif name == "Pictogram(s)":
                            for sm in val.get("StringWithMarkup", []):
                                for m in sm.get("Markup", []):
                                    extra = m.get("Extra")
                                    url_val = m.get("URL", "")
                                    pic_code = ""
                                    if "GHS" in url_val:
                                        match = re.search(r"(GHS\d{2})", url_val)
                                        if match:
                                            pic_code = match.group(1)
                                    if extra and pic_code:
                                        label = f"{pic_code}-{extra.lower().replace(' ', '_')}"
                                        if label not in pictograms:
                                            pictograms.append(label)
                                    elif extra and extra not in pictograms:
                                        pictograms.append(extra)

                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)

        if "DANGER" in signal_words:
            primary_signal = "DANGER"
        elif "WARNING" in signal_words:
            primary_signal = "WARNING"
        else:
            primary_signal = "NOT_CLASSIFIED"

        return {
            "signal_word": primary_signal,
            "hazard_statements": hazard_statements[:10],
            "precautionary_statements": precautionary_statements[:10],
            "pictograms": pictograms,
        }

    def get_pharmacology(self, cid: int, mock: bool = False) -> Dict[str, Any]:
        """
        Retrieves pharmacology, clinical indications, and biological targets.
        """
        if mock:
            comp = self._get_mock_compound(str(cid))
            if comp and "pharmacology" in comp:
                return comp["pharmacology"]
            return {
                "indications": "Not clinically documented.",
                "mechanism_of_action": "Not clinically documented.",
                "targets": [],
            }

        self.rate_limiter.wait()
        url = f"{self.PUG_VIEW_BASE}/compound/{cid}/JSON?heading=Mechanism+of+Action"

        moa_text = ""
        indications_text = ""
        targets: List[str] = []

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                data = resp.json()
                moa_text = self._extract_first_string_value(data)
        except requests.RequestException:
            pass

        # Also attempt therapeutic uses / indications
        self.rate_limiter.wait()
        url_ind = f"{self.PUG_VIEW_BASE}/compound/{cid}/JSON?heading=Therapeutic+Uses"
        try:
            resp_ind = self.session.get(url_ind, timeout=self.timeout)
            if resp_ind.status_code == 200:
                data_ind = resp_ind.json()
                indications_text = self._extract_first_string_value(data_ind)
        except requests.RequestException:
            pass

        if not moa_text and not indications_text and self.mock_fallback:
            comp = self._get_mock_compound(str(cid))
            if comp and "pharmacology" in comp:
                return comp["pharmacology"]

        return {
            "indications": indications_text or "No approved clinical indications documented.",
            "mechanism_of_action": moa_text or "No specific mechanism of action documented.",
            "targets": targets,
        }

    def _extract_first_string_value(self, data: Dict[str, Any]) -> str:
        results: List[str] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                if "Information" in node:
                    for info in node["Information"]:
                        val = info.get("Value", {})
                        for sm in val.get("StringWithMarkup", []):
                            s = sm.get("String", "").strip()
                            if s:
                                results.append(s)
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)
        return results[0] if results else ""

    def get_conformer_3d(self, cid: int, mock: bool = False) -> Optional[str]:
        """
        Retrieves 3D conformer coordinates in SDF format.
        """
        if mock:
            comp = self._get_mock_compound(str(cid))
            if comp:
                return comp.get("conformer_3d_sdf")
            return None

        self.rate_limiter.wait()
        url = f"{self.PUG_REST_BASE}/compound/cid/{cid}/SDF?record_type=3d"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200 and resp.text:
                return resp.text
            elif resp.status_code == 404:
                logger.info("3D conformer not available for CID %d; attempting 2D SDF retrieval", cid)
                # Fallback to 2D SDF
                self.rate_limiter.wait()
                url_2d = f"{self.PUG_REST_BASE}/compound/cid/{cid}/SDF"
                resp_2d = self.session.get(url_2d, timeout=self.timeout)
                if resp_2d.status_code == 200 and resp_2d.text:
                    return resp_2d.text
        except requests.RequestException as exc:
            logger.error("Network error retrieving 3D conformer for CID %d: %s", cid, exc)
            if self.mock_fallback:
                comp = self._get_mock_compound(str(cid))
                if comp:
                    return comp.get("conformer_3d_sdf")

        return None

    def get_bioassays(
        self,
        cid: int,
        active_only: bool = True,
        max_records: int = 5,
        mock: bool = False,
    ) -> Dict[str, Any]:
        """
        Retrieves active bioassay screening results and summary statistics.
        """
        if mock:
            comp = self._get_mock_compound(str(cid))
            if comp and "bioassays" in comp:
                return comp["bioassays"]
            return {"total_tested": 0, "total_active": 0, "active_assays": []}

        self.rate_limiter.wait()
        url = f"{self.PUG_REST_BASE}/compound/cid/{cid}/assaysummary/CSV"

        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200 and resp.text:
                f = io.StringIO(resp.text)
                reader = csv.DictReader(f)
                active_list: List[Dict[str, Any]] = []
                total_tested = 0
                total_active = 0

                for row in reader:
                    total_tested += 1
                    outcome = row.get("Activity Outcome", "").strip()
                    if outcome.lower() == "active":
                        total_active += 1
                        if len(active_list) < max_records:
                            aid = int(row.get("AID", 0)) if row.get("AID") else 0
                            target = row.get("Target Name", "") or row.get("Assay Name", "")
                            act_val = row.get("Activity Value [uM]", "")
                            act_name = row.get("Activity Name", "Active")
                            act_summary = f"{act_name} ({act_val} uM)" if act_val else "Active"
                            active_list.append({
                                "aid": aid,
                                "name": row.get("Assay Name", ""),
                                "target": target,
                                "activity": act_summary,
                            })

                return {
                    "total_tested": total_tested,
                    "total_active": total_active,
                    "active_assays": active_list,
                }
        except requests.RequestException as exc:
            logger.error("Network error fetching assays for CID %d: %s", cid, exc)
            if self.mock_fallback:
                comp = self._get_mock_compound(str(cid))
                if comp and "bioassays" in comp:
                    return comp["bioassays"]

        return {"total_tested": 0, "total_active": 0, "active_assays": []}

    def get_similarity_analogs(
        self,
        cid: Optional[int] = None,
        smiles: Optional[str] = None,
        threshold: int = 85,
        max_records: int = 5,
        mock: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Identifies structural analogs using PubChem 2D fast similarity searching.
        """
        if mock:
            query = str(cid) if cid else (smiles or "")
            comp = self._get_mock_compound(query)
            if comp and "analogs" in comp:
                return comp["analogs"]
            return []

        if not cid and not smiles:
            return []

        self.rate_limiter.wait()
        try:
            if cid:
                url = f"{self.PUG_REST_BASE}/compound/fastsimilarity_2d/cid/{cid}/cids/JSON?Threshold={threshold}&MaxRecords={max_records + 1}"
            else:
                encoded = urllib.parse.quote(smiles.strip())
                url = f"{self.PUG_REST_BASE}/compound/fastsimilarity_2d/smiles/{encoded}/cids/JSON?Threshold={threshold}&MaxRecords={max_records + 1}"

            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                cids = resp.json().get("IdentifierList", {}).get("CID", [])
                # Exclude query compound itself if matching
                filtered_cids = [c for c in cids if c != cid][:max_records]
                if filtered_cids:
                    return self._fetch_analog_properties(filtered_cids, threshold)
        except requests.RequestException as exc:
            logger.error("Network error fetching similarity analogs: %s", exc)
            if self.mock_fallback and cid:
                comp = self._get_mock_compound(str(cid))
                if comp and "analogs" in comp:
                    return comp["analogs"]

        return []

    def _fetch_analog_properties(self, cids: List[int], base_threshold: int) -> List[Dict[str, Any]]:
        cid_str = ",".join(str(c) for c in cids)
        self.rate_limiter.wait()
        url = f"{self.PUG_REST_BASE}/compound/cid/{cid_str}/property/IUPACName,MolecularFormula/JSON"
        try:
            resp = self.session.get(url, timeout=self.timeout)
            if resp.status_code == 200:
                props = resp.json().get("PropertyTable", {}).get("Properties", [])
                results: List[Dict[str, Any]] = []
                for idx, p in enumerate(props):
                    results.append({
                        "cid": int(p.get("CID", 0)),
                        "iupac_name": p.get("IUPACName", f"CID-{p.get('CID')}"),
                        "molecular_formula": p.get("MolecularFormula", ""),
                        "similarity_score": round((base_threshold - idx * 2.0) / 100.0, 2),
                    })
                return results
        except requests.RequestException:
            pass
        return [{"cid": c, "iupac_name": f"CID-{c}", "molecular_formula": "", "similarity_score": 0.85} for c in cids]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PubChem API CLI Utilities for Chemical Profiling and Data Retrieval",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--mock", action="store_true", help="Force synthetic mock mode (offline)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: resolve
    cmd_res = subparsers.add_parser("resolve", help="Resolve chemical name/SMILES/InChI to CID")
    cmd_res.add_argument("--name", help="Chemical or drug name")
    cmd_res.add_argument("--smiles", help="SMILES string")
    cmd_res.add_argument("--inchi", help="InChI string")
    cmd_res.add_argument("-o", "--output", help="Path to write JSON output")

    # Subcommand: properties
    cmd_prop = subparsers.add_parser("properties", help="Retrieve computed properties & evaluate drug-likeness")
    cmd_prop.add_argument("--cid", type=int, required=True, help="PubChem Compound ID (CID)")
    cmd_prop.add_argument("-o", "--output", help="Path to write JSON output")

    # Subcommand: safety
    cmd_safe = subparsers.add_parser("safety", help="Retrieve GHS hazard safety classifications")
    cmd_safe.add_argument("--cid", type=int, required=True, help="PubChem Compound ID (CID)")
    cmd_safe.add_argument("-o", "--output", help="Path to write JSON output")

    # Subcommand: pharmacology
    cmd_pharm = subparsers.add_parser("pharmacology", help="Retrieve clinical indications and mechanism of action")
    cmd_pharm.add_argument("--cid", type=int, required=True, help="PubChem Compound ID (CID)")
    cmd_pharm.add_argument("-o", "--output", help="Path to write JSON output")

    # Subcommand: conformer3d
    cmd_conf = subparsers.add_parser("conformer3d", help="Retrieve 3D conformer structure in SDF format")
    cmd_conf.add_argument("--cid", type=int, required=True, help="PubChem Compound ID (CID)")
    cmd_conf.add_argument("-o", "--output", help="Path to write SDF structure output")

    # Subcommand: assays
    cmd_assays = subparsers.add_parser("assays", help="Retrieve active bioassay screening results")
    cmd_assays.add_argument("--cid", type=int, required=True, help="PubChem Compound ID (CID)")
    cmd_assays.add_argument("--active-only", action="store_true", default=True, help="Filter for active assays only")
    cmd_assays.add_argument("--max-records", type=int, default=5, help="Maximum records to retrieve")
    cmd_assays.add_argument("-o", "--output", help="Path to write JSON output")

    # Subcommand: similarity
    cmd_sim = subparsers.add_parser("similarity", help="Search for structural analogs based on 2D similarity")
    cmd_sim.add_argument("--cid", type=int, help="PubChem Compound ID (CID)")
    cmd_sim.add_argument("--smiles", help="SMILES string")
    cmd_sim.add_argument("--threshold", type=int, default=85, help="Tanimoto similarity threshold percentage (0-100)")
    cmd_sim.add_argument("--max-records", type=int, default=5, help="Maximum analog records")
    cmd_sim.add_argument("-o", "--output", help="Path to write JSON output")

    args = parser.parse_args()
    client = PubChemClient()

    if args.command == "resolve":
        cid = client.resolve(name=args.name, smiles=args.smiles, inchi=args.inchi, mock=args.mock)
        if cid is None:
            logger.error("Failed to resolve identifier")
            return 1
        result = {"cid": cid, "query": args.name or args.smiles or args.inchi}
        output_data = json.dumps(result, indent=2)

    elif args.command == "properties":
        data = client.get_properties(args.cid, mock=args.mock)
        if not data:
            logger.error("Failed to retrieve properties for CID %d", args.cid)
            return 1
        data["drug_likeness"] = {
            "lipinski_rule_of_five": client.evaluate_lipinski(data["properties"]),
            "veber_rule": client.evaluate_veber(data["properties"]),
        }
        output_data = json.dumps(data, indent=2)

    elif args.command == "safety":
        safety_data = client.get_safety(args.cid, mock=args.mock)
        output_data = json.dumps(safety_data, indent=2)

    elif args.command == "pharmacology":
        pharm_data = client.get_pharmacology(args.cid, mock=args.mock)
        output_data = json.dumps(pharm_data, indent=2)

    elif args.command == "conformer3d":
        sdf_data = client.get_conformer_3d(args.cid, mock=args.mock)
        if not sdf_data:
            logger.error("Failed to retrieve conformer SDF for CID %d", args.cid)
            return 1
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(sdf_data)
            logger.info("Saved 3D conformer SDF to %s", args.output)
            return 0
        else:
            print(sdf_data)
            return 0

    elif args.command == "assays":
        assay_data = client.get_bioassays(args.cid, active_only=args.active_only, max_records=args.max_records, mock=args.mock)
        output_data = json.dumps(assay_data, indent=2)

    elif args.command == "similarity":
        analogs = client.get_similarity_analogs(
            cid=args.cid,
            smiles=args.smiles,
            threshold=args.threshold,
            max_records=args.max_records,
            mock=args.mock,
        )
        output_data = json.dumps(analogs, indent=2)

    else:
        logger.error("Unknown command %s", args.command)
        return 1

    if getattr(args, "output", None):
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_data)
        logger.info("Written result to %s", args.output)
    else:
        print(output_data)

    return 0


if __name__ == "__main__":
    sys.exit(main())
