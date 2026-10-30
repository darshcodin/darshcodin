# UI guides — the three remaining steps

Hands-on steps for the items that need the Salesforce UI (or a licensing check),
for org `ibm81` (`https://ibm81.lightning.force.com`).

---

## A. See the Expression Set actually compute ($4,410) — Test panel

This confirms the BRE Expression Set `Grow_Lighting_MN_Calculator` produces the right
numbers, even though this org can't call it from Flow.

1. **Setup** (gear icon) → Quick Find: **Expression Sets** → open **Grow Lighting MN Calculator**.
   (Or open the **Business Rules Engine** app → Expression Sets.)
2. Make sure the version shows **Active** (V1). Click into the version to open the **Expression
   Set Builder**.
3. Click **Test** (top-right; may be labelled *Test* / *Simulate* / *Debug*).
4. Enter the input variables:

   | Variable | Value |
   |---|---|
   | `Qty` | 10 |
   | `Room_Type` | Cannabis Flower Room |
   | `PPF` | 1700 |
   | `Prop_Watts` | 630 |
   | `DLC_Tier` | DLC Premium |

5. **Run**. Expected outputs:

   | Output | Value |
   |---|---|
   | `electricRebate` | 4410.00 |
   | `Prop_PPE` | 2.70 |
   | `Base_W` | 1955 |
   | `customerKW` | 17.6225 |
   | `customerKWH` | 65399.35 |
   | `customerPCKW` | 11.98364 |
   | `incrementalCost` | 7119.00 |

   The **Decision Explainer** on the test result shows each step — the same lineage the line
   item stores.

---

## B. Build the two Decision Matrices (enhancement 4)

Moves the Room Type and DLC Tier lookups out of inline `IF()` into native Decision Matrices,
so a new TRM filing is a data change on the matrix. Row data is ready in `data/*.csv`.

### B1. Create the matrices
1. **Setup** → Quick Find: **Decision Matrices** → **New** (or Business Rules Engine app →
   Decision Matrices → New).
2. **Matrix 1 — "Grow Lighting Room Type"**, type **Standard**. Define columns:

   | Column | Type | Data type |
   |---|---|---|
   | `Room_Type` | Input | Text |
   | `Hours` | Output | Number |
   | `kWh_Factor` | Output | Number |
   | `CF` | Output | Number |

3. **Matrix 2 — "Grow Lighting DLC Tier"**, type **Standard**. Columns:

   | Column | Type | Data type |
   |---|---|---|
   | `DLC_Tier` | Input | Text |
   | `DLC_Adj` | Output | Number |
   | `Effective_Rate` | Output | Number |

### B2. Load the rows
Use **Upload CSV** on each matrix version (or add rows manually). The CSVs match the columns:

- Matrix 1 ← `data/room_type_matrix.csv`

  | Room_Type | Hours | kWh_Factor | CF |
  |---|---|---|---|
  | Cannabis Flower Room | 4255 | 1.16 | 0.68 |
  | Cannabis Veg Room | 6498 | 1.24 | 0.89 |
  | Flowering Crops (Tomatoes/Peppers) | 4200 | 1.21 | 0.76 |
  | Vegetative/Propagation Growth | 6300 | 1.21 | 0.95 |
  | Microgreens | 6300 | 1.21 | 0.95 |
  | Clone Room | 6300 | 1.21 | 0.95 |
  | Combo Veg & Flower Cannabis Room | 5281 | 1.20 | 0.78 |

- Matrix 2 ← `data/dlc_tier_matrix.csv` (all tiers post-2024 → DLC_Adj 1.0, $0.70/W)

4. **Activate** each matrix version.

### B3. Wire into the Expression Set
In the Expression Set Builder for `Grow_Lighting_MN_Calculator`, replace the first lookup
steps with **Decision Matrix** steps:
- Add a *Decision Matrix* step → select **Grow Lighting Room Type**, map input `Room_Type`,
  capture outputs into `Hours`, `kWh_Factor`, `CF`.
- Add a *Decision Matrix* step → **Grow Lighting DLC Tier**, map `DLC_Tier` → `DLC_Adj`.
- Keep the arithmetic steps unchanged. Save and activate a new version.

### B4. Pull it back into the repo
```bash
sf project retrieve start --target-org cep \
  -m "DecisionMatrixDefinition:Grow_Lighting_Room_Type" \
  -m "DecisionMatrixDefinition:Grow_Lighting_DLC_Tier" \
  -m "ExpressionSetDefinitionVersion:Grow_Lighting_MN_Calculator_V2"
```
Ping me after B1–B2 and I'll do B3–B4 and re-verify.

> Results don't change — the matrix values equal the inline-lookup values the flow already uses.

---

## C. Enable the BRE runtime (enhancement 1) — what to ask

To have the orchestration *call* the Expression Set (instead of the mirrored Flow formulas),
the org needs the **Business Rules Engine runtime** — not just the design-time objects it has
today. Ask your Salesforce admin / Account Executive:

1. **"Does our org's edition/add-on include the Business Rules Engine *runtime* (executing
   Expression Sets via API/Flow), or only the design-time builder?"**
   Evidence to share: the objects (`ExpressionSet`, `DecisionMatrixDefinition`) exist and sets
   activate, but there is **no** `/connect/expression-set/evaluationServices/execute` resource
   (404 at API v59–v64), no `ConnectApi` BRE Apex, and no expression-set `InvocableActionType`
   for Flow — with the **`BRERuntime`** permission set already assigned.
2. **"If it's licensed, what needs enabling?"** (e.g. a Business Rules Engine setup toggle /
   feature, or a permission-set *license* beyond the `BRERuntime` permission set).
3. Confirm it's intended for **Energy & Utilities Cloud / Clean Energy Program** use (our case).

Once the runtime is live, finishing (1) is a one-element change: in
`Grow_Lighting_MN_Calculate_Line`, replace the formula block with a single **Run Expression
Set** action passing `Qty, Room_Type, PPF, Prop_Watts, DLC_Tier` and reading the outputs back
onto the line. Nothing else changes. Ping me and I'll make and verify that change.
