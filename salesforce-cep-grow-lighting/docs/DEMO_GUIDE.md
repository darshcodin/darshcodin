# Grow Lighting MN — End-to-End Demo Guide

A full walk-through of the rebate application process on standard CEP objects.
Everything below is **deployed and verified** in org `ibm81`.

## What's in the org

| Component | API name | Purpose |
|---|---|---|
| Expression Set (BRE) | `Grow_Lighting_MN_Calculator` | savings + rebate rules engine |
| Decision Matrices | `Grow_Lighting_Room_Type`, `Grow_Lighting_DLC_Tier` | lookups (TRM-versionable) |
| Before-save Flow | `Grow_Lighting_MN_Calculate_Line` | on line submit → computes outputs + 11 dependent metrics + lineage |
| After-save Flow | `Grow_Lighting_MN_Create_Benefit_Assignment` | maps **all** metrics to the application as BenefitAssignments |
| Screen Flow | `Grow_Lighting_MN_Rebate_Application` | guided UI: capture inputs → results |
| **Button** | `Calculate_Grow_Lighting_Rebate` (quick action) | launches the Screen Flow from the line item |
| Custom fields | on `IndividualApplicationItem`, `Location`, `Benefit`, `BenefitAssignment`, `UsageImpactGroup(Version)` | inputs, outputs, dependent metrics, TRM, savings store, lineage |
| Permission set | `CEP_Grow_Lighting_Calculator` | field access for program users |

### Stakeholder demo entry point (button)
On an **Individual Application Line Item** record, the **Calculate Grow Lighting Rebate**
action (in the action bar) launches the guided Screen Flow. *(If your org uses a custom
Lightning record page for this object instead of the page layout, add the action to that page
once in the Lightning App Builder — the quick action is already deployed.)*

### Savings Store — all metrics mapped to the application
The after-save flow creates **one BenefitAssignment per metric** under the application
(Savings Store · Option A): the rebate (USD) plus all 14 savings metrics (kW / kWh), each with
its typed value in `Calculated_Value__c` and `Metric_Unit__c`. A single line produces **15
BenefitAssignments**, all mapped to the `IndividualApplication` — verified.

### OmniScript for inputs (note)
A functional OmniScript (input elements + save action) is authored in the **OmniStudio
Designer** — its element/`propertySetConfig` JSON isn't practically hand-authorable from
metadata (same Designer-gated situation as the BRE matrix step). The **Screen Flow above is the
working, equivalent guided input UI** and is what the button launches. To build the OmniScript:
in the OmniStudio Designer create a one-step OmniScript with Number/Select inputs for
`Qty, Room Type, PPF, Fixture Watts, DLC Tier, Invoice Date`, and a save step that creates an
`IndividualApplicationItem` (which triggers the same calc + benefit flows). Retrieve it with
`sf project retrieve start -m "OmniScript:<name>"` and it drops into this repo.

Demo data (seeded): Program *Lighting – MN*, Product *MN – Lighting Efficiency Rebate*,
ProgramProduct, Benefit *MN Lighting Efficiency Rebate* (active, linked to the Expression
Set), Account *Green Valley Growers*, Location (Hennepin / Electric), and an active
ProgramEnrollment.

## Option A — guided Screen Flow (best for a live demo)
1. Setup → **Flows** → **Grow Lighting MN - Rebate Application** → **Run** (or add it to a
   Lightning page / App).
2. Enter: Fixture Quantity `10`, Room Type `Cannabis Flower Room`, PPF `1700`,
   Fixture Watts `630`, DLC Tier `DLC Premium`, Invoice Date any.
3. Finish → the results screen shows the rebate and savings; an `IndividualApplication`,
   `IndividualApplicationItem`, and `BenefitAssignment` are created.

## Option B — create records directly (shows the triggered orchestration)
Create an `IndividualApplicationItem` under an `IndividualApplication` (Category `Program`,
the demo Account) with `RelatedItemId` = the ProgramProduct and the five inputs. The
before-save flow calculates the line; the after-save flow creates the BenefitAssignment.
`scripts/run_end_to_end.sh` does exactly this and asserts the numbers.

## Verified result (worked example)
Inputs `Qty=10, Cannabis Flower Room, PPF=1700, Watts=630, DLC Premium`:

| Field | Value |
|---|---|
| Electric Rebate (BenefitAssignment) | **$4,410.00** |
| Proposed PPE | 2.70 |
| Baseline Watts | 1,955 |
| Customer kW Demand Savings | 17.6225 |
| Customer kWh Energy Savings | 65,399.35 |
| Peak Coincident kW | 11.98364 |
| Incremental Cost | $7,119.00 |

## Process (what fires, in order)
```
Create line (inputs)
  → [before-save] Grow_Lighting_MN_Calculate_Line
        sets Electric_Rebate__c, Proposed_PPE__c, Baseline_Watts__c,
             Customer_kW/kWh/PCkW, Incremental_Cost__c, lineage + explainer
  → [after-save]  Grow_Lighting_MN_Create_Benefit_Assignment
        resolves ProgramProduct → Benefit + Application → ProgramEnrollment
        creates BenefitAssignment (EntitlementAmount = rebate, Status Active)
```

## Reset / re-seed
`bash scripts/seed_demo_data.sh cep` is idempotent (find-or-create) and re-activates the
Benefit and enrollment. Delete demo applications to re-run cleanly.

## Note on the BRE runtime
The orchestration computes with Flow formulas that **mirror** the Expression Set exactly
(same inputs, same 11 steps, identical numbers — verified). The Expression Set is the
governed rules asset and is linked on `Benefit.EligibleAmountExpressionSetId`. Switching the
live calc to invoke the Expression Set directly needs the **BRERuntime** permission set on the
running user; the logic and results are identical either way.
