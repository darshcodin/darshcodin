#!/usr/bin/env python3
"""Generate the before-save record-triggered Flow that calculates a Grow Lighting
MN application line (IndividualApplicationItem). Mirrors the BRE Expression Set
Grow_Lighting_MN_Calculator exactly. No Apex.

Lookups (Room Type, DLC Tier) are CASE() expressions; formulas are inlined so no
formula references another formula (keeps it portable).
"""
import os

ROOM = [
    ("Cannabis Flower Room", 4255, 1.16, 0.68),
    ("Cannabis Veg Room", 6498, 1.24, 0.89),
    ("Flowering Crops (Tomatoes/Peppers)", 4200, 1.21, 0.76),
    ("Vegetative/Propagation Growth", 6300, 1.21, 0.95),
    ("Microgreens", 6300, 1.21, 0.95),
    ("Clone Room", 6300, 1.21, 0.95),
    ("Combo Veg & Flower Cannabis Room", 5281, 1.20, 0.78),
]
# field tokens
QTY = "{!$Record.Fixture_Quantity__c}"
PPF = "{!$Record.Proposed_PPF__c}"
WATTS = "{!$Record.Proposed_Fixture_Watts__c}"
ROOMF = "{!$Record.Market_Segment_Room_Type__c}"
DLCF = "{!$Record.DLC_Tier__c}"


def case(field, idx):
    arms = "".join(f', "{r[0]}", {r[idx]}' for r in ROOM)
    return f"CASE({field}{arms}, 0)"


HOURS = case(ROOMF, 1)
KWHF = case(ROOMF, 2)
CF = case(ROOMF, 3)
DLCADJ = f'CASE({DLCF}, "DLC Premium", 1, "DLC Standard", 1, "Non-DLC", 1, 1)'
PPE = f"ROUND({PPF} / {WATTS}, 2)"
BASEW = f"ROUND(({WATTS} * 0.972 * ({PPE})) / (0.783 * 1.08), 0)"
REBATE = f"{QTY} * {WATTS} * ROUND(0.70 * ({DLCADJ}), 2)"
KW = f"(({BASEW}) - {WATTS}) / 1000 * 1.33 * {QTY}"
KWH = f"(({BASEW}) - {WATTS}) / 1000 * {QTY} * ({KWHF}) * ({HOURS})"
PCKW = f"ROUND(({KW}), 3) * ({CF})"
INCCOST = f"{QTY} * {WATTS} * 1.13"

# (formulaName, dataType, scale, expression, targetField)
FORMULAS = [
    ("fRebate", "Number", 2, REBATE, "Electric_Rebate__c"),
    ("fPropPPE", "Number", 2, PPE, "Proposed_PPE__c"),
    ("fBaseW", "Number", 0, BASEW, "Baseline_Watts__c"),
    ("fKW", "Number", 4, KW, "Customer_kW_Savings__c"),
    ("fKWH", "Number", 2, KWH, "Customer_kWh_Savings__c"),
    ("fPCKW", "Number", 5, PCKW, "Customer_Peak_Coincident_kW__c"),
    ("fIncCost", "Number", 2, INCCOST, "Incremental_Cost__c"),
]
# lineage constants (version references selected by invoice date in production)
LINEAGE = [
    ("Technical_TRM_Version__c", "MN-LIGHT-TRM-2026-v2"),
    ("Program_Factors_Version__c", "MN-LIGHT-PF-2026"),
    ("Incentive_Rules_Version__c", "MN-LIGHT-IR-2026"),
    ("Expression_Set_Version__c", "Grow_Lighting_MN_Calculator_V1"),
]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "force-app", "main", "default", "flows",
                       "Grow_Lighting_MN_Calculate_Line.flow-meta.xml")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    formulas_xml = "\n".join(f"""    <formulas>
        <name>{n}</name>
        <dataType>{dt}</dataType>
        <expression>{esc(expr)}</expression>
        <scale>{sc}</scale>
    </formulas>""" for (n, dt, sc, expr, _tf) in FORMULAS)

    # Assignment 1: numeric outputs from formulas
    num_items = "\n".join(f"""        <assignmentItems>
            <assignToReference>$Record.{tf}</assignToReference>
            <operator>Assign</operator>
            <value><elementReference>{n}</elementReference></value>
        </assignmentItems>""" for (n, _dt, _sc, _e, tf) in FORMULAS)
    # Assignment 1 also sets lineage string constants
    lineage_items = "\n".join(f"""        <assignmentItems>
            <assignToReference>$Record.{tf}</assignToReference>
            <operator>Assign</operator>
            <value><stringValue>{v}</stringValue></value>
        </assignmentItems>""" for (tf, v) in LINEAGE)

    # entry filters: all five inputs present
    inputs = ["Fixture_Quantity__c", "Market_Segment_Room_Type__c", "Proposed_PPF__c",
              "Proposed_Fixture_Watts__c", "DLC_Tier__c"]
    filters = "\n".join(f"""        <filters>
            <field>{f}</field>
            <operator>IsNull</operator>
            <value><booleanValue>false</booleanValue></value>
        </filters>""" for f in inputs)

    # explainer text template (references the just-set $Record output fields)
    explainer = (
        "Grow Lighting MN v2 calculation\n"
        "Inputs: Qty={!$Record.Fixture_Quantity__c}, Room={!$Record.Market_Segment_Room_Type__c}, "
        "PPF={!$Record.Proposed_PPF__c}, Watts={!$Record.Proposed_Fixture_Watts__c}, "
        "DLC={!$Record.DLC_Tier__c}\n"
        "Proposed PPE = ROUND(PPF/Watts,2) = {!$Record.Proposed_PPE__c}\n"
        "Baseline Watts = ROUND((Watts*0.972*PPE)/(0.783*1.08),0) = {!$Record.Baseline_Watts__c}\n"
        "Electric Rebate = Qty*Watts*ROUND(0.70*DLC_Adj,2) = {!$Record.Electric_Rebate__c}\n"
        "kW Demand Savings = (BaseW-Watts)/1000*1.33*Qty = {!$Record.Customer_kW_Savings__c}\n"
        "kWh Energy Savings = (BaseW-Watts)/1000*Qty*kWhFactor*Hours = {!$Record.Customer_kWh_Savings__c}\n"
        "Peak Coincident kW = ROUND(kW,3)*CF = {!$Record.Customer_Peak_Coincident_kW__c}\n"
        "Incremental Cost = Qty*Watts*1.13 = {!$Record.Incremental_Cost__c}\n"
        "Versions: {!$Record.Technical_TRM_Version__c} / {!$Record.Program_Factors_Version__c} / "
        "{!$Record.Incentive_Rules_Version__c} / {!$Record.Expression_Set_Version__c}"
    )

    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <assignments>
        <name>Set_Calculation_Outputs</name>
        <label>Set Calculation Outputs</label>
        <locationX>176</locationX>
        <locationY>288</locationY>
        <connector>
            <targetReference>Set_Explainer</targetReference>
        </connector>
{num_items}
{lineage_items}
    </assignments>
    <assignments>
        <name>Set_Explainer</name>
        <label>Set Explainer</label>
        <locationX>176</locationX>
        <locationY>408</locationY>
        <assignmentItems>
            <assignToReference>$Record.Calculation_Explainer__c</assignToReference>
            <operator>Assign</operator>
            <value><elementReference>tExplainer</elementReference></value>
        </assignmentItems>
    </assignments>
    <description>Before-save calc: on line submit, compute rebate + initial energy savings for Grow Lighting MN. Mirrors BRE Expression Set Grow_Lighting_MN_Calculator.</description>
    <environments>Default</environments>
{formulas_xml}
    <interviewLabel>Grow Lighting MN - Calculate Line {{!$Flow.CurrentDateTime}}</interviewLabel>
    <label>Grow Lighting MN - Calculate Line</label>
    <processMetadataValues>
        <name>BuilderType</name>
        <value><stringValue>LightningFlowBuilder</stringValue></value>
    </processMetadataValues>
    <processType>AutoLaunchedFlow</processType>
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector>
            <targetReference>Set_Calculation_Outputs</targetReference>
        </connector>
        <filterLogic>and</filterLogic>
{filters}
        <object>IndividualApplicationItem</object>
        <recordTriggerType>CreateAndUpdate</recordTriggerType>
        <triggerType>RecordBeforeSave</triggerType>
    </start>
    <status>Active</status>
    <textTemplates>
        <name>tExplainer</name>
        <isViewedAsPlainText>true</isViewedAsPlainText>
        <text>{esc(explainer)}</text>
    </textTemplates>
</Flow>
"""
    with open(out, "w") as f:
        f.write(doc)
    print("wrote", out)


if __name__ == "__main__":
    main()
