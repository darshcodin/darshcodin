# Enhancements — status & findings

Tracking the four enhancements requested after the end-to-end build.

| # | Enhancement | Status |
|---|---|---|
| 2 | TRM reference data (Usage Impact model, invoice-date selection) | ✅ **Done & verified** |
| 3 | 11 dependent Electric DSM roll-up metrics | ✅ **Done & verified** |
| 1 | Switch orchestration to invoke the Expression Set directly | ⚠️ **Org constraint: no BRE runtime API** (details below) |
| 4 | Move the two lookups into Decision Matrices | ⏳ **Needs BRE Decision Matrix Builder UI** |

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

## ⚠️ (1) Invoke the Expression Set directly from the orchestration
`BRERuntime` was assigned, and the Expression Set is deployed, **Active**, and wired to the
Benefit via `Benefit.EligibleAmountExpressionSetId` (the platform's designated hook — verified).
However, **this org does not expose a runtime to invoke a generic `Bre` Expression Set**.
Confirmed, with `BRERuntime` assigned:

- **Connect REST** — no evaluation resource at API v59–v64; `/connect` never lists
  `expression-set`/`business-rules`/`decisioning`.
  `POST …/connect/expression-set/evaluationServices/execute` → `NOT_FOUND`.
- **Apex** — `ConnectApi.BusinessRulesEngine` / `ConnectApi.ExpressionSetEvaluation*` don't exist.
- **Flow** — no `expressionSet`/`evaluateExpressionSet`/… value in the `InvocableActionType`
  enum; no expression-set action in `/actions/standard` or `/actions/custom`.

This org has the BRE **design-time** objects (so expression sets deploy and activate) but not
the BRE **runtime** surface. Specialized expression sets here are invoked through their own
actions (e.g. EU pricing via `eUPricingExecutor`); a generic decisioning `Bre` set has none.

**What this means:** the orchestration keeps computing with Flow formulas that **mirror** the
Expression Set exactly (identical inputs, 11 steps, verified identical numbers) — the correct
no-Apex implementation for this org. The Expression Set stays the governed rules asset
(activation validates its logic; it's linked to the Benefit) and can be exercised in the
**Expression Set Builder → Test** panel in the UI.

In an org with the BRE runtime fully provisioned, finishing (1) is a one-element change: replace
the formula block with a single **Run Expression Set** action passing the five inputs. No other
part of the flow changes.

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
