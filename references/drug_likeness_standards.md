# Drug-Likeness Standards and Medicinal Chemistry Guidelines

## 1. Overview
In drug discovery and lead optimization, computational filtering rules evaluate the probability that a small molecule possesses physicochemical properties suitable for oral bioavailability and favorable pharmacokinetics in humans.

---

## 2. Lipinski's Rule of Five (Ro5)

### 2.1 Theoretical Foundation
Formulated by Christopher A. Lipinski in 1997, the Rule of Five identifies physicochemical characteristics common to orally active pharmaceuticals that have advanced to Phase II clinical trials. Compounds failing more than one criterion frequently exhibit poor solubility or permeability.

### 2.2 Boundary Criteria
| Descriptor | Symbol | Upper Limit | Unit | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| Molecular Weight | MW | <= 500.0 | Daltons (Da) | Diffusion rate decreases with increasing molecular size |
| Octanol-Water Partition | LogP (XLogP3) | <= 5.0 | Log scale | Excessive lipophilicity leads to poor aqueous solubility and non-specific binding |
| Hydrogen Bond Donors | HBD | <= 5 | Count | High donor count increases desolvation energy penalty required for membrane transit |
| Hydrogen Bond Acceptors | HBA | <= 10 | Count | Excessive acceptors impede passive diffusion through lipid bilayers |

### 2.3 Compliance Classification
- **Compliant**: 0 violations. High likelihood of favorable oral absorption.
- **Borderline**: 1 violation. Acceptable for many modern synthetic drug classes (e.g., kinase inhibitors).
- **Violation**: 2 or more violations. Significant risk of low oral bioavailability.

---

## 3. Veber Criteria

### 3.1 Theoretical Foundation
Published by Daniel F. Veber et al. in 2002, this standard demonstrated that molecular flexibility and polar surface area are primary determinants of oral bioavailability in rats, independent of molecular weight.

### 3.2 Boundary Criteria
| Descriptor | Symbol | Upper Limit | Unit | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| Rotatable Bonds | NRotB | <= 10 | Count | Increased conformational flexibility penalizes binding entropy and permeation |
| Polar Surface Area | TPSA | <= 140.0 | Angstroms squared (A^2) | Polar surface > 140 A^2 sharply reduces passive cellular permeability |

### 3.3 Compliance Classification
- **Compliant**: Both criteria met.
- **Violation**: One or both criteria exceeded.

---

## 4. Lead-Likeness Criteria (Teague / Oprea)
Lead-likeness criteria define starting chemical space for high-throughput screening leads:
- Molecular Weight: 150 <= MW <= 350 Da
- LogP: -1.0 <= LogP <= 3.0
- Rotatable Bonds: <= 7
- Heavy Atoms: 10 <= Count <= 25

Compounds within lead-like space provide structural room for optimization (adding functional groups) without prematurely exceeding Lipinski boundaries.

---

## 5. Composite Scoring in Pipeline
The `pubchem-database-visualize` skill calculates both Lipinski Ro5 and Veber rules deterministically from PubChem computed properties, providing clear classification tags and violation tallies for research reports.
