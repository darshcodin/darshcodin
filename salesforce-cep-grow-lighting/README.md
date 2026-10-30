# CEP – Grow Lighting MN · Simple Use Case Calculator

A Salesforce **Clean Energy Program (CEP)** calculator for the *LED Grow Fixture MN v2*
measure, built on the **Business Rules Engine** (Expression Sets + Decision Matrices) —
**configuration over code, no Apex**, per the conceptual solution architecture.

**Target org:** `https://ibm81.lightning.force.com` (My Domain: `ibm81`)
**Status:** ✅ **Full end-to-end deployed and verified** on standard CEP objects. No Apex.

This is a complete, working rebate-application process — not just the calculator:
Account + Program Enrollment → Program / Product / Benefit → Individual Application →
Application Line (inputs) → **calculate on submit** → outputs + lineage on the line →
**BenefitAssignment** (the incentive). See [`docs/SOLUTION_ARCHITECTURE.md`](docs/SOLUTION_ARCHITECTURE.md)
and [`docs/DEMO_GUIDE.md`](docs/DEMO_GUIDE.md).

## What's deployed
- **BRE Expression Set** `Grow_Lighting_MN_Calculator` (V1, `UsageType = Bre`) — 5 inputs,
  11 steps producing rebate + PPE + baseline watts + kW/kWh/peak-kW savings + incremental cost.
- **Custom fields** on standard `IndividualApplicationItem` (inputs, outputs, lineage) and `Location`.
- **Record-triggered Flows**: `Grow_Lighting_MN_Calculate_Line` (before-save: computes the line,
  mirrors the Expression Set) and `Grow_Lighting_MN_Create_Benefit_Assignment` (after-save: awards
  the rebate as a `BenefitAssignment`).
- **Screen Flow** `Grow_Lighting_MN_Rebate_Application` — guided capture → results.
- **Permission set** `CEP_Grow_Lighting_Calculator`; FLS on the admin profile.
- **Demo data**: Program, Product, ProgramProduct, Benefit (active, linked to the Expression Set),
  Account, Location, ProgramEnrollment.

Verified worked example (`Qty=10`, Cannabis Flower Room, `PPF=1700`, `Watts=630`, DLC Premium):
rebate **$4,410**, PPE 2.70, Base_W 1955, kW 17.6225, kWh 65,399.35, PCkW 11.98364, inc. cost $7,119.

## Layout
```
sfdx-project.json                 Salesforce DX project
manifest/package.xml              Deployment manifest (fields, flows, ES, perm set, profile)
docs/SOLUTION_ARCHITECTURE.md     End-to-end architecture on standard CEP objects
docs/DEMO_GUIDE.md                How to run the end-to-end demo
docs/BUILD_SPEC.md                Design → BRE artifact mapping + worked example
data/*.csv                        Lookup rows (for the Decision-Matrix enhancement)
scripts/gen_*.py                  Generators (expression set, fields, calc flow, screen flow)
scripts/deploy.sh                 Two-phase ES deploy (draft -> activate)
scripts/seed_demo_data.sh         Idempotent demo data
scripts/run_end_to_end.sh         Reproducible end-to-end test with assertions
scripts/verify_calculator.sh      Live Expression Set run (needs BRERuntime)
force-app/main/default/
  expressionSetDefinition/ expressionSetVersion/   BRE Expression Set
  objects/                 custom fields on IndividualApplicationItem, Location
  flows/                   2 record-triggered + 1 screen flow
  permissionsets/ profiles/                        field access
```

## Deploy to a fresh org
```bash
sf org login sfdx-url --sfdx-url-file ./authurl.txt --alias cep
bash scripts/deploy.sh cep                                   # Expression Set (two-phase)
sf project deploy start --target-org cep --source-dir force-app  # fields, flows, perms
bash scripts/seed_demo_data.sh cep                           # demo data
bash scripts/run_end_to_end.sh cep                           # verify
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
