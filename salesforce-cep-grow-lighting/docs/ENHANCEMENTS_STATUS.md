# Enhancements — status & findings

Tracking the four enhancements requested after the end-to-end build.

| # | Enhancement | Status |
|---|---|---|
| 2 | TRM reference data (Usage Impact model, invoice-date selection) | ✅ **Done & verified** |
| 3 | 11 dependent Electric DSM roll-up metrics | ✅ **Done & verified** |
| 1 | Switch orchestration to invoke the Expression Set directly | ⚠️ **Org constraint: no BRE runtime API** (details below) |
| 4 | Move the two lookups into Decision Matrices | ✅ **Matrices built, populated & active** — consuming them via the ES is gated on the same BRE runtime as (1) |

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

## ✅ (4) Decision Matrices for the Room Type and DLC Tier lookups
Both matrices are **built, populated and active** — done headlessly, no UI required.
(An earlier note here said this needed the UI; that was wrong. The blocker then was a stale,
empty matrix left by a failed delete, which made every redeploy look like a conflicting
"subsequent version." From a clean slate it deploys fine.)

**How it's structured:**
- `DecisionMatrixDefinition` (metadata): `label` + `type` Standard.
- `DecisionMatrixDefinitionVersion` (metadata): the **columns** — `columnType` Input|Output,
  `dataType` Text|Number, `displaySequence`, `name`. Deploy the definition **and** version
  together from a clean slate (the version must carry the columns at creation).
- **Rows are data**, stored on the backing `CalculationMatrixVersion` as `CalculationMatrixRow`
  records with `InputData`/`OutputData` JSON — e.g.
  `{"Room_Type":"Cannabis Flower Room"}` → `{"Hours":4255,"kWh_Factor":1.16,"CF":0.68}`.
  Loaded via the data API, not metadata.

**Deployed & verified:**
- `Grow_Lighting_Room_Type` — input `Room_Type`; outputs `Hours`, `kWh_Factor`, `CF`; **7 rows**.
- `Grow_Lighting_DLC_Tier` — input `DLC_Tier`; outputs `DLC_Adj`, `Effective_Rate`; **3 rows**.
- Both version status **Active**; row data queried back and confirmed correct.

Build it anywhere:
```bash
python3 scripts/gen_decision_matrices.py            # Draft metadata
sf project deploy start --target-org cep --source-dir force-app/main/default/decisionMatrixDefinition --source-dir force-app/main/default/decisionMatrixVersion
python3 scripts/load_matrix_rows.py cep             # rows from data/*.csv
python3 scripts/gen_decision_matrices.py --active   # flip to Active
sf project deploy start --target-org cep --source-dir force-app/main/default/decisionMatrixVersion
```

**Remaining — Expression Set V2 that consumes the matrices.** Investigated the reference
mechanism directly (deploy-time formula validation, ~28 probes):
- A matrix lookup is **not** a `stepType` (`ExpsSetStepType`) or `actionType` value.
- It is a **formula function**: `MAP("Grow_Lighting_Room_Type", Room_Type)` is recognized and
  returns the matched row as a *string→string map* (confirmed by the type error:
  `FunctionMap$StringToStringMap … incompatible with NUMBER`).
- But there is no `ExpsSetDataType` to hold a map, and no accessible getter — `[...]`, `.col`,
  and `GET`/`GETVALUE`/`VALUEAT`/… are all rejected. `VLOOKUP` is for **context sObjects**
  (`$ObjectType field reference`), not matrices.

So the exact matrix-lookup formula is **Builder-generated** (the Expression Set Builder writes
it when you drag in a Decision Matrix), and it can't be reliably hand-authored from metadata —
and the resulting V2 couldn't execute here anyway (the runtime gap from (1)).

**Clean way to finish V2:** in the Expression Set Builder, add a *Decision Matrix* step to
`Grow_Lighting_MN_Calculator` referencing `Grow Lighting Room Type` (and `Grow Lighting DLC
Tier`), save as a new version, then:
```bash
sf project retrieve start --target-org cep -m "ExpressionSetDefinitionVersion:Grow_Lighting_MN_Calculator_V2"
```
That gives the exact step/formula metadata, which drops straight into this repo.

The matrices already hold the exact lookup values the flow uses, so results are unchanged either
way — a new TRM filing becomes a data change on the matrix instead of a formula edit.
