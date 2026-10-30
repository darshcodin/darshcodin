# CEP Grow Lighting MN — End-to-End Solution Architecture

How the *LED Grow Fixture MN v2* measure runs end to end on **standard** Salesforce
Public Sector + Energy & Utilities objects, driven by the **Business Rules Engine**.
No custom objects, no Apex — configuration over code.

## Why this architecture
The conceptual solution deck maps 1:1 to objects this org already has. Rather than invent
a data model, we reuse the standard one and add only *fields* where the platform has none
(county, fuel type on Location; the measure's inputs/outputs/lineage on the line item).
That keeps us on the platform's upgrade path and makes new TRM filings a **data** change.

## Object model (all standard)

| Layer | Object | Role in this measure |
|---|---|---|
| Program mgmt | `Program` | "Lighting – MN" program |
| | `Product2` | "MN – Lighting Efficiency Rebate" measure product |
| | `ProgramProduct` | links the measure product to the program |
| | `ProductClassification` / `AttributeDefinition` | measure attribute catalog (inputs) |
| Reference data (TRM) | `UsageImpactGroup` / `UsageImpactGroupVersion` | Technical TRM / Program Factors / Incentive Rules **versions** |
| | `UsageImpactFactor` / `UsageImpactGroupFactor` | the versioned factor values (CF, NTG, line loss, rates…) |
| | `UsageImpactGroupPgmMeasure` | binds a version to Program + Product (invoice-date selected) |
| Application | `Account` | the customer / grower |
| | `Location` (+ `County__c`, `Customer_Fuel_Type__c`) | service premise |
| | `IndividualApplication` | the rebate application |
| | `IndividualApplicationItem` (+ input/output/lineage fields) | the **measure line** |
| Calculation | `ExpressionSet` `Grow_Lighting_MN_Calculator` | BRE savings + rebate engine |
| | `Flow` (orchestration) | assembles inputs on line submit, runs the engine |
| Results | `Benefit` (+ `EligibleAmountExpressionSetId`) | the rebate benefit, natively tied to the engine |
| | `BenefitAssignment` | the incentive awarded to this application |
| | output fields on `IndividualApplicationItem` | the 50+ savings values, side by side |
| Audit | lineage fields + `Calculation_Explainer__c` | versions used + step-by-step explanation |

### The key platform affordance
`Benefit.EligibleAmountExpressionSetId` is a **standard** lookup to an `ExpressionSet`.
The platform is purpose-built to compute a benefit's amount from a BRE expression set — so
our calculator is not bolted on, it sits exactly where Salesforce expects the rebate logic.

## End-to-end process (one pass per submitted line)

```
Account + Location (county, fuel type)
        │
        ▼
IndividualApplication  ──<  IndividualApplicationItem (RelatedItem = ProgramProduct)
  (Category = Program)         inputs: Qty, Room Type, PPF, Prop Watts, DLC Tier, Invoice Date
        │
        ▼  ① line submitted  → orchestration Flow
        │
        ├─ ② version resolution : Program + Product + Invoice Date
        │        → UsageImpactGroupPgmMeasure → Technical / Program Factors / Incentive Rules
        ├─ ③ context assembly   : inputs + resolved factors
        ├─ ④ run calculation    : Expression Set  Grow_Lighting_MN_Calculator
        │        → electricRebate, Prop_PPE, Base_W, customerKW, customerKWH,
        │          customerPCKW, incrementalCost
        ├─ ⑤ write results      : outputs onto the line item;
        │                         BenefitAssignment (incentive) under the application
        └─ ⑥ lineage            : version refs + Calculation_Explainer__c on the line
        │
        ▼
"Why this number?"  — explainer on the line · "Which lines used this version?" — report on refs
```

## Demo walk-through (what the Screen Flow shows)
1. **Applicant & premise** — pick the grower Account and service Location (county / fuel type).
2. **Measure line** — Program "Lighting – MN" / Product "MN – Lighting Efficiency Rebate";
   enter Fixture Qty, Room Type, PPF, Fixture Watts, DLC Tier, Invoice Date.
3. **Submit** — orchestration runs the calculation.
4. **Result** — rebate + kW/kWh/peak-kW savings shown, with the versions used.
5. **Records created** — `IndividualApplication`, `IndividualApplicationItem` (inputs + outputs
   + lineage), and a `BenefitAssignment` for the rebate — all visible in the org.

## Design decisions
- **Standard objects first** — only fields added, no custom objects.
- **Reuse the shared calculation** — one Expression Set; the orchestration never re-implements
  the formulas.
- **Data-driven TRM** — factor values live on `UsageImpactGroup` versions, selected by invoice
  date; a new filing is a new version (data), not new logic.
- **Every result traceable** — the line stores the versions + an explainer; incentive is a
  `BenefitAssignment`, savings are typed fields on the line (one row, values side by side —
  option B in the deck's storage decision).
