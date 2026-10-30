# CEP – Grow Lighting MN · Simple Use Case Calculator

A Salesforce **Clean Energy Program (CEP)** calculator for the *LED Grow Fixture MN v2*
measure, built on the **Business Rules Engine** (Expression Sets + Decision Matrices) —
**configuration over code, no Apex**, per the conceptual solution architecture.

**Target org:** `https://ibm81.lightning.force.com` (My Domain: `ibm81`)

## Scope (first build)
Customer inputs → **rebate** + **initial energy savings** (Proposed PPE, derived
Baseline Watts, kW demand savings, kWh energy savings, peak coincident kW, incremental
cost) + input **validation**. See [`docs/BUILD_SPEC.md`](docs/BUILD_SPEC.md) for the full
mapping, formulas, and a worked example.

## Layout
```
sfdx-project.json                 Salesforce DX project
docs/BUILD_SPEC.md                Design → BRE artifact mapping (source of truth)
data/room_type_matrix.csv         Room Type decision-matrix rows
data/dlc_tier_matrix.csv          DLC Tier decision-matrix rows
scripts/connect_and_inspect.sh    Auth + capability inspection (run once access is open)
force-app/main/default/           BRE metadata (authored after org capabilities confirmed)
```

## How to connect & deploy
Requires: (1) environment network open to `*.salesforce.com` / `*.force.com`,
(2) authentication to the sandbox.

```bash
# Device-code login (headless-friendly — approve the code in any browser):
sf org login device --instance-url https://ibm81.my.salesforce.com --alias cep

# ...or from an SFDX auth URL you provide:
sf org login sfdx-url --sfdx-url-file ./authurl.txt --alias cep

# Inspect what BRE flavor is enabled, then build & deploy:
bash scripts/connect_and_inspect.sh
sf project deploy start --target-org cep
```
