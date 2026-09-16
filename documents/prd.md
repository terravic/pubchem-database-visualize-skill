# Product Requirement Document (PRD)
## Agent Skill: pubchem-database-visualize

### 1. Document Control
- Document Version: 1.0.0
- Status: Approved for Implementation
- Classification: Technical Specification
- Standard Compliance: Standard Agentic Skill Specification

---

### 2. User Stories & Scope

#### 2.1 Target Audience
The `pubchem-database-visualize` skill is engineered for the following user personas:
1. **Computational Chemists and Cheminformaticians**: Require rapid programmatic retrieval of IUPAC nomenclatures, canonical SMILES, InChIKeys, computed 2D physicochemical properties, and 3D molecular conformers.
2. **Medicinal Chemists and Drug Discovery Teams**: Require automated evaluation of drug-likeness criteria (Lipinski Rule of 5, Veber rules), bioactivity concordance from PubChem BioAssays, and structural analog identification.
3. **Safety Officers and Regulatory Analysts**: Require deterministic extraction of Globally Harmonized System (GHS) hazard classifications, signal words (DANGER/WARNING), hazard statements (H-codes), and precautionary statements (P-codes).
4. **Clinical Pharmacologists**: Require high-level summaries of FDA-approved clinical indications, mechanisms of action, and biological targets.
5. **Autonomous AI Agents**: Require standardized command-line tools that accept structured flags, return predictable exit codes, write machine-readable JSON outputs, and gracefully degrade during offline or sandboxed operation.

#### 2.2 User Stories
- **US-01**: As an autonomous research assistant supporting a medicinal chemist, I need to resolve ambiguous chemical names, trade names, SMILES strings, or InChI identifiers to a canonical PubChem Compound ID (CID) so that downstream analytical workflows reference a verified chemical entity.
- **US-02**: As a drug discovery researcher, I need to evaluate Lipinski Rule of 5 and Veber drug-likeness rules against computed properties so that lead candidates can be triaged prior to synthesis.
- **US-03**: As a laboratory safety officer, I need to inspect GHS hazard statements and signal words for a target compound to ensure safe handling protocols are prepared.
- **US-04**: As a computational pharmacologist, I need to retrieve 3D coordinate conformer records (SDF) and generate an interactive 3D WebGL dashboard so that molecular geometry and spatial features can be inspected visually.
- **US-05**: As a developer running in a hermetic CI or offline sandbox environment, I need an offline synthetic mock mode (`--mock`) so that all tests and pipeline commands pass deterministically without internet access.

#### 2.3 Scope Delineation

##### In-Scope Capabilities
- Chemical identifier resolution: Name, SMILES, InChI, and CID to canonical PubChem entity.
- Physicochemical property retrieval: Molecular Weight (MW), XLogP, Hydrogen Bond Donors (HBD), Hydrogen Bond Acceptors (HBA), Topological Polar Surface Area (TPSA), Rotatable Bond Count, Heavy Atom Count, Exact Mass, Formal Charge, Complexity.
- Drug-likeness classification: Mathematical boundary checks for Lipinski Rule of 5 (MW <= 500 Da, XLogP <= 5, HBD <= 5, HBA <= 10) and Veber criteria (Rotatable Bonds <= 10, TPSA <= 140 A^2).
- GHS hazard analysis: Parsing signal words, hazard codes (H-statements), precautionary codes (P-statements), and pictogram designations.
- Pharmacology and mechanism of action: Extraction of clinical indications and biological targets from PubChem PUG View.
- 3D conformer acquisition: Extraction of 3D SDF coordinate data.
- Bioassay screening summaries: Extraction of active bioassay counts and target associations.
- Chemical similarity exploration: Identification of structural analogs based on 2D Tanimoto similarity thresholds.
- Artifact generation: Structured JSON profile (`compound_profile.json`), 3D coordinate file (`conformer3d.sdf`), and self-contained interactive UI dashboard (`dashboard.html`).
- Hermetic mock mode: Built-in 100% synthetic dataset providing offline execution fidelity for testing and sandboxed environments.

##### Out-of-Scope Capabilities
- Generation of synthetic wet-lab chemistry manufacturing protocols or reaction pathway instructions.
- Provision of individualized patient medical advice, drug prescriptions, or dosing regimens.
- Processing or storage of Protected Health Information (PHI) or Personally Identifiable Information (PII).
- De novo molecular generative modeling or inverse molecular design.
- Direct execution of molecular dynamics (MD) simulations or quantum chemical DFT calculations.

---

### 3. Technical Architecture

#### 3.1 System Context Diagram
The skill executes within an agentic harness that orchestrates tool calls to Python CLI scripts. These scripts communicate with the PubChem REST APIs or fall back to local synthetic mock fixtures.

```text
+-------------------------------------------------------------------------+
|                              AGENT HARNESS                              |
|                                                                         |
|  User Prompt ----> [SKILL.md Orchestrator]                              |
|                          |                                              |
|                          | Executes via bash / uv run                   |
|                          v                                              |
|  +-------------------------------------------------------------------+  |
|  |                 PYTHON CLI SCRIPTS (scripts/)                     |  |
|  |                                                                   |  |
|  |  [run_pipeline.py] <-----------> [pubchem_api.py]                 |  |
|  +-------------------------------------------------------------------+  |
+----------------------------|--------------------------------------------+
                             |
         +-------------------+-------------------+
         | (Network Mode)                        | (Offline / --mock Mode)
         v                                       v
+-----------------------------+         +-------------------------------+
|     PUBCHEM WEB SERVICES    |         |     LOCAL ASSETS & FIXTURES   |
|                             |         |                               |
| - PUG REST API              |         | - assets/synthetic_mocks.json |
|   (cids, properties, 3d SDF)|         | - assets/dashboard_template   |
| - PUG View API              |         | - assets/schemas/             |
|   (GHS safety, pharmacology)|         |                               |
+-----------------------------+         +-------------------------------+
         |                                       |
         +-------------------+-------------------+
                             |
                             v
+-------------------------------------------------------------------------+
|                       OUTPUT ARTIFACTS (output_dir/)                    |
|                                                                         |
|  - compound_profile.json  : Unified machine-readable JSON record        |
|  - conformer3d.sdf        : Spatial 3D chemical coordinates             |
|  - dashboard.html         : Standalone WebGL 3D Molecular Dashboard     |
+-------------------------------------------------------------------------+
```

#### 3.2 Sequence of Execution Flow

```text
User / Agent        SKILL.md             run_pipeline.py        PubChem / Mock      Output Directory
     |                  |                      |                      |                     |
     |--- Query ------->|                      |                      |                     |
     |   (name/CID)     |--- uv run cmd ------>|                      |                     |
     |                  |                      |--- Verify License -->|                     |
     |                  |                      |--- Resolve CID ----->|                     |
     |                  |                      |<-- CID Received -----|                     |
     |                  |                      |--- Get Properties -->|                     |
     |                  |                      |<-- Properties -------|                     |
     |                  |                      |--- Compute Ro5/Veber |                     |
     |                  |                      |--- Get GHS Safety -->|                     |
     |                  |                      |<-- Safety Data ------|                     |
     |                  |                      |--- Get Pharmacology->|                     |
     |                  |                      |<-- Pharm Data -------|                     |
     |                  |                      |--- Get 3D SDF ------>|                     |
     |                  |                      |<-- SDF Text ---------|                     |
     |                  |                      |--- Get Bioassays --->|                     |
     |                  |                      |<-- Assays Data ------|                     |
     |                  |                      |--- Get Similarity -->|                     |
     |                  |                      |<-- Analogs Data -----|                     |
     |                  |                      |                                            |
     |                  |                      |--- Write compound_profile.json ----------->|
     |                  |                      |--- Write conformer3d.sdf ----------------->|
     |                  |                      |--- Render & Write dashboard.html ---------->|
     |                  |                      |                                            |
     |                  |<-- JSON Summary -----|                                            |
     |<-- Agent Rep. ---|                      |                                            |
```

---

### 4. Functional Requirements

#### 4.1 Input Specification and Validation
- Supported input flags for CLI scripts:
  - `--name`: Chemical or pharmaceutical name (e.g., "aspirin", "imatinib", "caffeine"). Sanitized against shell injection.
  - `--cid`: Numerical PubChem Compound ID (e.g., `2244`, `5291`). Validated as positive integer.
  - `--smiles`: Simplified Molecular Input Line Entry System string. Validated for non-empty alphanumeric format.
  - `--inchi`: International Chemical Identifier string (e.g., `InChI=1S/...`). Validated for standard prefix.
  - `-o, --output`: Destination directory for output artifacts. Created if non-existent.
  - `--mock`: Boolean flag forcing hermetic execution using `assets/synthetic_mocks.json`.

#### 4.2 Entity Resolution Stage
1. When input is `--cid`, verify validity directly against property endpoints.
2. When input is `--name`, query `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{name}/cids/JSON`.
3. When input is `--smiles`, query `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/{smiles}/cids/JSON`.
4. When input is `--inchi`, query `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/inchi/cids/JSON` via HTTP POST.
5. In `--mock` mode, match query case-insensitively against pre-indexed mock keys.

#### 4.3 Computed Physicochemical Properties and Drug-Likeness
- Retrieve property fields:
  - `MolecularFormula`, `MolecularWeight`, `CanonicalSMILES`, `IsomericSMILES`, `InChI`, `InChIKey`, `IUPACName`, `XLogP`, `ExactMass`, `TPSA`, `Complexity`, `HBondDonorCount`, `HBondAcceptorCount`, `RotatableBondCount`, `HeavyAtomCount`.
- Compute Lipinski Rule of 5:
  - Molecular Weight <= 500 Da (Violation if > 500)
  - XLogP <= 5.0 (Violation if > 5.0)
  - Hydrogen Bond Donors <= 5 (Violation if > 5)
  - Hydrogen Bond Acceptors <= 10 (Violation if > 10)
  - Status: `COMPLIANT` if violations == 0, `BORDERLINE` if violations == 1, `VIOLATION` if violations >= 2.
- Compute Veber Criteria:
  - Rotatable Bonds <= 10
  - TPSA <= 140.0 A^2
  - Status: `COMPLIANT` if 0 violations, `VIOLATION` if >= 1 violation.

#### 4.4 GHS Hazard Safety Analysis
- Query PubChem PUG View: `https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=GHS+Classification`.
- Parse response hierarchy to extract:
  - Signal Word: `DANGER`, `WARNING`, or `NOT_CLASSIFIED`.
  - Hazard Statements: List of objects containing H-code (e.g., `H301`, `H315`), classification text, and category.
  - Precautionary Statements: List of P-codes (e.g., `P264`, `P280`) and instructions.
  - Pictogram Codes: Standard GHS pictogram names (e.g., `GHS06-toxic`, `GHS07-harmful`, `GHS08-health_hazard`).

#### 4.5 Clinical Pharmacology and Targets
- Query PubChem PUG View: `https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Pharmacology`.
- Extract sections:
  - `FDA Approved Indications`: Therapeutic uses and disease contexts.
  - `Mechanism of Action`: Biochemical pathways and target interactions.
  - `Biological Targets`: Target macromolecule names, gene symbols, and organism.

#### 4.6 3D Conformer Coordinate Acquisition
- Query PUG REST: `https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/SDF?record_type=3d`.
- Validate SDF format:
  - Must contain valid header, atom count block, coordinate records, and `$$$$` delimiter.
- Fallback: If 3D conformer is not computed by PubChem, attempt 2D SDF retrieval and flag `is_3d: false`.

#### 4.7 BioAssay and Structural Analog Retrieval
- Query PUG REST for bioactivity:
  - Retrieve active bioassays count, assay IDs (AIDs), and assay targets.
- Query PUG REST for 2D similarity:
  - Retrieve top structural analogs having Tanimoto coefficient >= 85%.

#### 4.8 Artifact Compilation & UI Dashboard Architecture
The pipeline outputs artifacts into `--output` and directly emits a user-facing artifact:
1. `compound_profile.json`: Comprehensive data model containing resolved metadata, properties, Ro5/Veber results, safety analysis, pharmacology, bioassay summary, and analog records.
2. `conformer3d.sdf`: Raw SDF structure record ready for third-party visualization tools (PyMOL, ChimeraX, Jmol).
3. `dashboard.html`: Self-contained interactive UI dashboard designed to render natively in an iframe, web view, or local browser:
   - Header with chemical identifiers, canonical nomenclature, and clean SVG-icon Light/Dark theme toggle (Sun icon for light mode, Moon icon for dark mode).
   - 3D Molecular View:
     - High-resolution 3D viewer featuring HiDPI Retina rendering, specular 3D CPK sphere lighting, 3D cylindrical bond shading with single/double/triple/aromatic geometry, representation modes (Ball & Stick, Stick, Spacefill, Wireframe, Translucent Surface), stable non-shifting controls, interactive distance measurement tool, hover Atom Inspector HUD tooltip, element/index label cycling, inertial orbit/pan/zoom navigation, and PNG export.
   - Physicochemical metrics table with one-click clipboard copy buttons for SMILES, InChIKey, and Formula.
   - Drug-likeness radar chart (SVG based) mapping compound values against Lipinski/Veber oral bioavailability limits.
   - GHS Hazard Classification card displaying signal words, pictograms, and hazard statements.
   - Clinical Pharmacology and mechanism summary.
   - BioAssay and structural analog data tables.
4. Artifact Emission: The pipeline and orchestrating skill emit `dashboard.html` as a user-facing artifact ensuring immediate preview. In addition, the root file `./dashboard.html` is updated for local offline inspection.

---

### 5. Non-Functional Requirements

#### 5.1 Performance and Rate Limits
- NCBI PUG-REST Rate Limits: Maximum 5 requests per second. The client must implement adaptive throttling to remain beneath this threshold.
- Minute Window: No more than 400 requests in any rolling 60-second window.
- Backoff Protocol: In the event of HTTP 429 (Too Many Requests) or HTTP 503 (Service Unavailable), the client must execute exponential backoff with jitter (initial delay 1.0s, multiplier 2.0, max 3 retries).
- Local Execution: Synthetic mock mode execution must complete in under 500 milliseconds.

#### 5.2 Security and Safety
- Command Injection Prevention: Input arguments (`--name`, `--smiles`, `--inchi`) must be validated and sanitized before passing into HTTP request strings or shell commands.
- No Shell Expansion: Python subprocess calls in testing must avoid `shell=True`.
- URL Whitelisting: Networking must strictly interact with `https://pubchem.ncbi.nlm.nih.gov` endpoints. No external unverified third-party endpoints.

#### 5.3 Data Privacy and Compliance
- Public Scientific Data Only: The skill processes chemical structures, physicochemical properties, and public pharmacology data only.
- Synthetic Mock Guardrail: All test fixtures and sample data files are synthetic.
- Licensing Compliance: The skill verifies that the user is aware of PubChem citation guidelines and terms of service by checking `.licenses/pubchem_database_visualize_LICENSE.txt`.

#### 5.4 Extensibility and Code Standards
- Code base must use modern Python (>= 3.10) with explicit type hints and defensive docstrings.
- Scripts must include PEP 723 inline dependency declarations for seamless `uv run` execution.
- Modularity: Core client logic (`scripts/pubchem_api.py`) must be decoupled from the orchestrator (`scripts/run_pipeline.py`), allowing both individual CLI subcommands and integrated pipeline execution.

---

### 6. Error Handling & Edge Cases Matrix

| Scenario / Trigger | Root Cause | System Behavior | Exit Code | User / Agent Remediation |
| :--- | :--- | :--- | :--- | :--- |
| Unresolvable Name / SMILES | Chemical name misspelled or SMILES structurally invalid | Returns clear error stating identifier could not be resolved | 1 | Verify spelling, try canonical SMILES, or supply numerical CID |
| Missing 3D Conformer | PubChem has not computed 3D conformer for complex/flexible molecule | Gracefully falls back to 2D coordinates; dashboard informs user 3D is unavailable | 0 | Conformer viewer displays 2D coordinate representation or placeholder notice |
| PubChem HTTP 429 / 503 | NCBI service load or rate limit exceeded | Retries with exponential backoff up to 3 times; if failure persists, reports rate limit event | 2 | Wait 30 seconds before retrying or use `--mock` flag |
| Network Disconnection | Hermetic or sandboxed environment without internet access | Aborts live network requests with diagnostic message recommending `--mock` mode | 2 | Execute pipeline with `--mock` flag for offline testing |
| Unclassified GHS Compound | Chemical lacks mandatory GHS hazardous classification filing | Safety section returns `Signal Word: NOT_CLASSIFIED` and notes hazard filing not found | 0 | Compound is documented as unclassified in PubChem GHS repository |
| Zero Active BioAssays | Compound was tested in assays with no active hits or not tested | Bioassay section reports zero active hits without crashing | 0 | Normal biological profiling result; documented in JSON profile |
| Missing License Acceptance | First run in new environment before license notice created | Creates `.licenses/pubchem_database_visualize_LICENSE.txt` and logs notification | 0 | Proceed with execution |
| Output Directory Inaccessible | Permissions error or invalid path syntax | Reports filesystem permission error with target path | 1 | Supply writable output path |

---

### 7. Acceptance Criteria
1. `scripts/run_pipeline.py` executes successfully with `--name`, `--cid`, and `--smiles` flags in both network and `--mock` modes.
2. `dashboard.html` renders valid HTML5 with responsive layouts, embedded 3D conformer viewer, radar chart, safety panel, and tabular summaries.
3. Test suite (`tests/test_pubchem_api.py`, `tests/test_pipeline.py`, `tests/test_dashboard.py`) runs via `uv run pytest` and `uv run python tests/run_tests.py` with 100% pass rate and exit code 0.
4. All synthetic test fixtures and datasets are verified self-contained without external runtime dependencies.
