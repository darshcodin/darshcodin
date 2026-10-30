# CEP – Grow Lighting MN · Simple Use Case Calculator

A Salesforce **Clean Energy Program (CEP)** calculator for the *LED Grow Fixture MN v2*
measure, built on the **Business Rules Engine** (Expression Sets + Decision Matrices) —
**configuration over code, no Apex**, per the conceptual solution architecture.

**Target org:** `https://ibm81.lightning.force.com` (My Domain: `ibm81`)
**Status:** ✅ Deployed and **Active** as a native BRE Expression Set (`UsageType = Bre`).

## Scope (first build)
Customer inputs → **rebate** + **initial energy savings** (Proposed PPE, derived
Baseline Watts, kW demand savings, kWh energy savings, peak coincident kW, incremental
cost) + input **validation**. See [`docs/BUILD_SPEC.md`](docs/BUILD_SPEC.md) for the full
mapping, formulas, worked example, and build outcome.

## What's deployed
A native **Business Rules Engine Expression Set** `Grow_Lighting_MN_Calculator` (version V1):
- 5 input variables: `Qty`, `Room_Type`, `PPF`, `Prop_Watts`, `DLC_Tier`
- 11 ordered calculation steps producing `electricRebate`, `Prop_PPE`, `Base_W`,
  `customerKW`, `customerKWH`, `customerPCKW`, `incrementalCost`
- Room Type and DLC Tier lookups inline (`IF()`); matrix rows kept in `data/*.csv` for the
  Decision-Matrix enhancement. **No Apex.**

## Layout
```
sfdx-project.json                 Salesforce DX project
manifest/package.xml              Deployment manifest
docs/BUILD_SPEC.md                Design → BRE artifact mapping + build outcome (source of truth)
data/room_type_matrix.csv         Room Type lookup rows (for Decision Matrix enhancement)
data/dlc_tier_matrix.csv          DLC Tier lookup rows (for Decision Matrix enhancement)
scripts/connect_and_inspect.sh    Auth + capability inspection
scripts/gen_expression_set.py     Generator for the Expression Set version XML
scripts/deploy.sh                 Two-phase deploy (draft -> activate)
scripts/verify_calculator.sh      Live run + assertion of the worked example
force-app/main/default/
  expressionSetDefinition/        Grow_Lighting_MN_Calculator
  expressionSetVersion/           Grow_Lighting_MN_Calculator_V1 (steps + variables)
```

## Deploy & verify
```bash
# 1) Auth (headless): from a machine logged into the org, export the auth URL and load it:
#    sf org auth show-sfdx-auth-url --target-org cep   # paste force://... into authurl.txt
sf org login sfdx-url --sfdx-url-file ./authurl.txt --alias cep

# 2) Deploy (two-phase: draft then activate)
bash scripts/deploy.sh cep

# 3) Verify numbers (needs BRERuntime perm set on the running user)
bash scripts/verify_calculator.sh cep
```

To regenerate the version XML after a logic change: `python3 scripts/gen_expression_set.py`.
