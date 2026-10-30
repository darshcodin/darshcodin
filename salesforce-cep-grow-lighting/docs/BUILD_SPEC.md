# Grow Lighting – MN · Simple Use Case Calculator — Build Spec

Salesforce **CEP** (Clean Energy Program Management on Energy & Utilities Cloud).
Technique: **Business Rules Engine** — Expression Sets + Decision Matrices. **No Apex.**
Scope: **Core calculator** — customer inputs → rebate + initial energy savings + validation.

Source of truth: `Simple_Use_Cases_for_Energy_Savings__Rebate_Calculation_Grow_Lighting.pdf`
and `CEP_Conceptual_Solution_Architecture.pptx`.

---

## 1. Program / Product context

| Field | Value |
|---|---|
| Program | Lighting – MN |
| Product | MN – Lighting Efficiency Rebate |
| Measure Group | Grow Lighting |
| Measure | LED Grow Fixture MN v2 |
| Complexity | Simple (single fuel · electric · savings formula) |

---

## 2. Inputs (Expression Set input variables)

| Variable | Type | Source | Notes |
|---|---|---|---|
| `Qty` | Number (0 dp) | Customer input | Proposed fixture quantity, integer ≥ 1 |
| `Room_Type` | Text | Customer input | Picklist, 7 values (drives Room Type matrix) |
| `PPF` | Number (2 dp) | Customer input | Proposed PPF (µmol/s) from fixture spec sheet |
| `Prop_Watts` | Number (2 dp) | Customer input | Proposed fixture watts (kW/fixture × 1000) |
| `DLC_Tier` | Text | Customer input | DLC Premium / DLC Standard / Non-DLC |

---

> **Implementation note.** In the deployed build the two lookups below are implemented as
> inline `IF()` expressions inside the Expression Set (identical results, fewer moving parts,
> guaranteed deployable). Promoting them to native **Decision Matrices** — keyed by
> jurisdiction + program + effective dates — is the recommended next step, because that is
> what makes new TRM filings a *data* change (new matrix version) rather than a logic change.
> The matrix rows are kept ready in `data/*.csv`.

## 3. Lookups (inline today; Decision Matrices next)

### 3.1 `Grow_Lighting_Room_Type`
- **Input key:** `Room_Type` (equals)
- **Outputs:** `Hours`, `kWh_Factor`, `CF`
- Data: `data/room_type_matrix.csv`

| Room_Type | Hours | kWh_Factor | CF |
|---|---|---|---|
| Cannabis Flower Room | 4255 | 1.16 | 0.68 |
| Cannabis Veg Room | 6498 | 1.24 | 0.89 |
| Flowering Crops (Tomatoes/Peppers) | 4200 | 1.21 | 0.76 |
| Vegetative/Propagation Growth | 6300 | 1.21 | 0.95 |
| Microgreens | 6300 | 1.21 | 0.95 |
| Clone Room | 6300 | 1.21 | 0.95 |
| Combo Veg & Flower Cannabis Room | 5281 | 1.20 | 0.78 |

### 3.2 `Grow_Lighting_DLC_Tier`
- **Input key:** `DLC_Tier` (equals)
- **Outputs:** `DLC_Adj`, `Effective_Rate`
- Data: `data/dlc_tier_matrix.csv`

| DLC_Tier | DLC_Adj | Effective_Rate |
|---|---|---|
| DLC Premium | 1.0 | 0.70 |
| DLC Standard | 1.0 | 0.70 |
| Non-DLC | 1.0 | 0.70 |

> Post-2024 all tiers use adjustment = 1.0 → effective $0.70/W. Matrix keeps it
> data-driven so a future TRM filing changes data, not logic.

---

## 4. Program / Product constants (literals in the Expression Set)

| Name | Value | Used in |
|---|---|---|
| Rebate rate ($/W) | 0.70 | Rebate |
| Proposed Reflector Efficiency | 0.972 | Baseline Watts |
| Baseline Reflector Efficiency | 0.783 | Baseline Watts |
| Baseline PPE standard (µmol/J) | 1.08 | Baseline Watts |
| Cooling demand factor | 1.33 | kW demand savings |
| Incremental cost per watt ($) | 1.13 | Incremental cost |

---

## 5. Calculation steps (Expression Set, in order)

| # | Output variable | Expression |
|---|---|---|
| 1 | `Hours`, `kWh_Factor`, `CF` | **Matrix** `Grow_Lighting_Room_Type` keyed by `Room_Type` |
| 2 | `DLC_Adj` | **Matrix** `Grow_Lighting_DLC_Tier` keyed by `DLC_Tier` |
| 3 | `electricRebate` | `Qty * Prop_Watts * ROUND(0.70 * DLC_Adj, 2)` |
| 4 | `Prop_PPE` | `ROUND(PPF / Prop_Watts, 2)` |
| 5 | `Base_W` | `ROUND((Prop_Watts * 0.972 * Prop_PPE) / (0.783 * 1.08), 0)` |
| 6 | `customerKW` | `(Base_W - Prop_Watts) / 1000 * 1.33 * Qty` |
| 7 | `customerKWH` | `(Base_W - Prop_Watts) / 1000 * Qty * kWh_Factor * Hours` |
| 8 | `customerPCKW` | `ROUND(customerKW, 3) * CF` |
| 9 | `incrementalCost` | `Qty * Prop_Watts * 1.13` |

### Outputs returned
`electricRebate`, `Prop_PPE`, `Base_W`, `customerKW`, `customerKWH`,
`customerPCKW`, `incrementalCost` (+ echo of `Hours`, `kWh_Factor`, `CF`, `DLC_Adj`).

---

## 6. Validation rules (pre-calculation, applicable to lighting)

| Rule | Condition |
|---|---|
| No blanks | `Qty`, `Room_Type`, `PPF`, `Prop_Watts`, `DLC_Tier` all present |
| Inputs > 0 | `Qty > 0`, `PPF > 0`, `Prop_Watts > 0` |
| No negative values | all numeric inputs ≥ 0 |
| Valid measure | Room_Type ∈ the 7 matrix keys; DLC_Tier ∈ 3 tiers |
| Acceptable customer type for measure | room type belongs to Grow Lighting set |

> The PDF's generic measure template also lists "Acceptable Cool BTUh" and
> "Acceptable Cost per Cooling Ton" — these belong to HVAC measures, not lighting,
> so they are out of scope for this measure.

---

## 7. Worked example (for test / verification)

Inputs: `Qty = 10`, `Room_Type = Cannabis Flower Room`, `PPF = 1700`, `Prop_Watts = 630`, `DLC_Tier = DLC Premium`

Lookups: `Hours = 4255`, `kWh_Factor = 1.16`, `CF = 0.68`, `DLC_Adj = 1.0`

| Output | Expected |
|---|---|
| `electricRebate` | 10 × 630 × ROUND(0.70×1.0,2)=0.70 → **4,410.00** |
| `Prop_PPE` | ROUND(1700/630,2) = **2.70** |
| `Base_W` | ROUND((630×0.972×2.70)/(0.783×1.08),0) = ROUND(1653.37/0.84564,0) = **1955** |
| `customerKW` | (1955−630)/1000 × 1.33 × 10 = 1.325×1.33×10 = **17.6225** |
| `customerKWH` | (1955−630)/1000 × 10 × 1.16 × 4255 = 1.325×10×1.16×4255 = **65,399.35** |
| `customerPCKW` | ROUND(17.6225,3) × 0.68 = 17.623×0.68 = **11.98364** |
| `incrementalCost` | 10 × 630 × 1.13 = **7,119.00** |

Full expected result set (to assert against a live run):

| Output | Expected |
|---|---|
| electricRebate | 4410.00 |
| Prop_PPE | 2.70 |
| Base_W | 1955 |
| customerKW | 17.6225 |
| customerKWH | 65399.35 |
| customerPCKW | 11.98364 |
| incrementalCost | 7119.00 |

---

## 8. What was built & deployed

Target org `ibm81` runs the **native Business Rules Engine** (`ExpressionSetDefinition`,
`ExpressionSetDefinitionVersion`, `DecisionMatrixDefinition`) alongside OmniStudio
`CalculationMatrix`. The calculator is a native BRE Expression Set of type **`Bre`**.

Deployed metadata (under `force-app/main/default/`):
- `expressionSetDefinition/Grow_Lighting_MN_Calculator.expressionSetDefinition-meta.xml`
- `expressionSetVersion/Grow_Lighting_MN_Calculator_V1.expressionSetVersion-meta.xml`
  — 5 input variables, 11 derived/output variables, 11 ordered `AssignParameterValues` steps.

Status in org: **Active** (`ExpressionSet.ApiName = Grow_Lighting_MN_Calculator`, `UsageType = Bre`).
Activation is itself a server-side validation: BRE rejects a version with invalid expressions,
variables, or string literals, so an *Active* version proves the formula syntax is valid.

### Deployment sequence (two-phase — matters for a fresh org)
BRE won't activate a version in the same pass that first creates its steps. So:
1. Deploy with both statuses `Draft` → creates definition + version + steps.
2. Flip the **version file** status to `Active` (keep the definition's inline `<versions>` as
   `Draft`) and redeploy → activates. See `scripts/deploy.sh`.

### Verifying the numbers (live run)
Runtime evaluation requires the **`BRERuntime`** ("Rule Engine Runtime") permission set on the
running user; without it the Connect evaluation resource returns `NOT_FOUND`. Once assigned:
`bash scripts/verify_calculator.sh` runs the worked example and asserts the table above.

### Recommended enhancements (beyond core scope)
- Move Room Type + DLC Tier lookups into native **Decision Matrices** (TRM-version friendly).
- Add the orchestration **Flow** on Individual Application Line Item submit (per architecture).
- Add the 11 dependent Electric DSM roll-up metrics.
- Add a permission set granting designer/runtime access for program users.
