# Enhancements — status & findings

Tracking the four enhancements requested after the end-to-end build.

| # | Enhancement | Status |
|---|---|---|
| 2 | TRM reference data (Usage Impact model, invoice-date selection) | ✅ **Done & verified** |
| 3 | 11 dependent Electric DSM roll-up metrics | ✅ **Done & verified** |
| 1 | Switch orchestration to invoke the Expression Set directly | ⏳ **Blocked on `BRERuntime`** |
| 4 | Move the two lookups into Decision Matrices | ⏳ **Needs BRE UI + `BRERuntime`** |

## ✅ (2) TRM reference data
Standard Usage Impact model: `UsageImpactGroup` *MN Grow Lighting - Technical* →
two effective-dated `UsageImpactGroupVersion`s (2024 and 2026) carrying flat factors
(T&D loss, NTG only/total, measure life) as fields, plus normalized
`UsageImpactGroupFactor` values and `UsageImpactGroupPgmMeasure` bindings to Program+Product.
The before-save flow resolves the version by **Invoice Date** and stamps lineage.

**Verified:** a 2026 invoice selects `MN-LIGHT-TRM-2026-v2` (T&D 1.08, NTG 0.95, life 15);
a 2025 invoice selects `MN-LIGHT-TRM-2024-v1` (T&D 1.07, NTG 0.90, life 14) — different
results, no logic change. Seed: `scripts/seed_trm_data.sh`.

## ✅ (3) Dependent DSM metrics
11 fields on `IndividualApplicationItem` (SM kW Gen, gross/net customer & generator kW and
kWh, lifetime), computed in the before-save flow from the base savings and the resolved TRM
factors. **Verified** against the worked example (e.g. Gen kWh 70,631.30, Lifetime Net Gen
1,006,496 for the 2026 version).

## ⏳ (1) Invoke the Expression Set directly from the orchestration
The orchestration currently computes with Flow formulas that **mirror** the Expression Set
exactly (identical inputs, 11 steps, verified identical numbers). To have the orchestration
*call* the governed Expression Set instead, two things are needed:

1. **`BRERuntime` permission set** on the running/integration user. Without it the BRE
   evaluation resource returns `NOT_FOUND`:
   `POST /services/data/v62.0/connect/expression-set/evaluationServices/execute`.
   Assign it (blocked for the assistant by the session's safety classifier):
   ```bash
   sf org assign permset --name BRERuntime --target-org cep
   ```
2. Once assigned, the Expression Set run contract is confirmed and the before-save flow's
   formula block is replaced by a single **"Evaluate Expression Set"** call that passes the
   five inputs and reads back the outputs. The Benefit is already wired to the Expression Set
   via `Benefit.EligibleAmountExpressionSetId`.

Behaviour and numbers are identical either way; this change makes the Expression Set the
single executing source of the rules (no mirrored formulas).

## ⏳ (4) Decision Matrices for the Room Type and DLC Tier lookups
Confirmed the native BRE **Decision Matrix metadata schema** by deploying a definition:
`DecisionMatrixDefinition` takes `label` + `type` (Standard|Grouped) + versions
(`startDate`, `status`, `versionNumber`); `DecisionMatrixDefinitionVersion` takes `columns`
(`columnType` Input|Output, `dataType`, `displaySequence`, `name`). **Rows are data**
(CSV-uploaded), not metadata.

Constraint hit: columns must be created with the matrix in the **BRE Decision Matrix Builder
UI** — a metadata-only deploy can create the shell but not the first set of columns
(the API reports *"can't create subsequent versions … that has no columns"*). So this step
needs the UI (and, to run via the Expression Set, `BRERuntime`).

Path to finish:
1. In the org: **Business Rules Engine → Decision Matrices → New** — create
   `Grow Lighting Room Type` (input `Room_Type`; outputs `Hours`, `kWh_Factor`, `CF`) and
   `Grow Lighting DLC Tier` (input `DLC_Tier`; outputs `DLC_Adj`, `Effective_Rate`).
2. Upload the rows from `data/room_type_matrix.csv` and `data/dlc_tier_matrix.csv`.
3. Add matrix-lookup steps to the Expression Set (replacing the inline `IF()` lookups) and
   retrieve the updated metadata into this project.

The lookup **data is identical** to what the inline lookups and the flow already use, so
results are unchanged — the matrices make new TRM filings a data change on the matrix.
