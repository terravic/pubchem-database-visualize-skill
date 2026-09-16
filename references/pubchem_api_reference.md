# PubChem PUG REST and PUG View API Technical Reference

## 1. Overview
The National Center for Biotechnology Information (NCBI) PubChem project provides two programmatic web service interfaces:
1. **PUG REST (Power User Gateway REST)**: Optimized for structured chemical record lookups, identifier conversions, computed 2D/3D properties, similarity searches, and assay summaries.
2. **PUG View**: Optimized for structured extraction of report sections (such as GHS Safety Classification, Pharmacology, and Biochemical Interactions) from PubChem Compound and Substance pages.

---

## 2. Usage Policies and Rate Limiting
- **Request Rate Limit**: NCBI permits a maximum of 5 requests per second per IP address.
- **Volume Limit**: No more than 400 requests in any rolling 60-second window.
- **Dynamic Service Throttling**: PubChem tracks user requests. Exceeding limits triggers an HTTP 429 status code. Continued abuse results in temporary IP blocking (HTTP 503).
- **HTTP User-Agent**: All programmatic requests should declare an informative User-Agent string containing the application name and contact details.

---

## 3. PUG REST Endpoints Specification

### 3.1 Base URL
`https://pubchem.ncbi.nlm.nih.gov/rest/pug`

### 3.2 Identifier Resolution
- **Resolve Name to CID**:
  `GET /compound/name/{name}/cids/JSON`
  Returns a list of matching CIDs. The first CID represents the primary canonical match.
- **Resolve SMILES to CID**:
  `GET /compound/smiles/{smiles}/cids/JSON`
  Resolves a standard SMILES string to the associated CID.
- **Resolve InChI to CID**:
  `POST /compound/inchi/cids/JSON` with form body `inchi={inchi_string}`.

### 3.3 Computed Physicochemical Properties
- **Fetch Specific Properties**:
  `GET /compound/cid/{cid}/property/{PropertyList}/JSON`
  Common properties requested:
  `MolecularFormula,MolecularWeight,CanonicalSMILES,IsomericSMILES,InChI,InChIKey,IUPACName,XLogP,ExactMass,TPSA,Complexity,HBondDonorCount,HBondAcceptorCount,RotatableBondCount,HeavyAtomCount`

### 3.4 3D and 2D Molecular Coordinates
- **Retrieve 3D Conformer SDF**:
  `GET /compound/cid/{cid}/SDF?record_type=3d`
  Returns the 3D coordinate record in Structure Data File (SDF) format. If no 3D conformer has been computed for the compound, HTTP 404 is returned.
- **Retrieve 2D Structure SDF**:
  `GET /compound/cid/{cid}/SDF`
  Returns the 2D coordinate representation in SDF format.

### 3.5 Chemical Similarity Search
- **2D Similarity via SMILES**:
  `GET /compound/similarity/smiles/{smiles}/JSON?Threshold={threshold}&MaxRecords={max_records}`
  Returns a list of CIDs matching the query compound above the defined Tanimoto similarity threshold (e.g., 85%).

### 3.6 BioAssay Summaries
- **Assay Summary by CID**:
  `GET /compound/cid/{cid}/assaysummary/CSV`
  Returns tabular assay activity records including Assay ID (AID), Assay Name, Activity Outcome (`Active`, `Inactive`, `Inconclusive`), and Target Name.

---

## 4. PUG View Endpoints Specification

### 4.1 Base URL
`https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON`

### 4.2 GHS Safety Classification
- **Request**:
  `GET /rest/pug_view/data/compound/{cid}/JSON?heading=GHS+Classification`
- **Response Structure**:
  Returns a hierarchical JSON tree. The section contains:
  - `Signal`: Text string representing hazard intensity (`Danger`, `Warning`).
  - `GHS Hazard Statements`: List of H-statements with codes (e.g., `H302`, `H315`) and descriptions.
  - `Precautionary Statement Codes`: List of P-statements (e.g., `P264`, `P280`).
  - `Pictograms`: Array of pictogram image links and standard classification labels.

### 4.3 Pharmacology and Mechanisms
- **Request**:
  `GET /rest/pug_view/data/compound/{cid}/JSON?heading=Pharmacology`
- **Response Structure**:
  Returns sections containing:
  - `FDA Approved Indications`: Therapeutic descriptions from FDA labels.
  - `Mechanism of Action`: Biochemical pathway inhibition, receptor modulation, or enzymatic activity.
  - `Biological Targets`: Known protein and macromolecular targets.

---

## 5. HTTP Status Codes and Error Handling
- `200 OK`: Request succeeded.
- `400 Bad Request`: Input syntax or query parameters invalid.
- `404 Not Found`: Chemical identifier not found or 3D conformer not available.
- `429 Too Many Requests`: Rate limit exceeded. Exponential backoff required.
- `503 Service Unavailable`: NCBI server busy or IP throttled.
