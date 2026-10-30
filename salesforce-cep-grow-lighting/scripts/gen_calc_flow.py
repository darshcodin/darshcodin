#!/usr/bin/env python3
"""Generate the before-save record-triggered Flow for a Grow Lighting MN line.

Does: TRM version resolution by invoice date -> read flat factors -> compute the
base outputs (mirrors BRE Expression Set Grow_Lighting_MN_Calculator) -> compute
the 11 dependent Electric DSM metrics -> stamp lineage. No Apex.
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
QTY = "{!$Record.Fixture_Quantity__c}"
PPF = "{!$Record.Proposed_PPF__c}"
WATTS = "{!$Record.Proposed_Fixture_Watts__c}"
ROOMF = "{!$Record.Market_Segment_Room_Type__c}"
DLCF = "{!$Record.DLC_Tier__c}"


def case(field, idx):
    arms = "".join(f', "{r[0]}", {r[idx]}' for r in ROOM)
    return f"CASE({field}{arms}, 0)"


HOURS, KWHF, CF = case(ROOMF, 1), case(ROOMF, 2), case(ROOMF, 3)
DLCADJ = f'CASE({DLCF}, "DLC Premium", 1, "DLC Standard", 1, "Non-DLC", 1, 1)'
PPE = f"ROUND({PPF} / {WATTS}, 2)"
BASEW = f"ROUND(({WATTS} * 0.972 * ({PPE})) / (0.783 * 1.08), 0)"

# base formulas: (name, scale, expression, targetField)
BASE_FORMULAS = [
    ("fRebate", 2, f"{QTY} * {WATTS} * ROUND(0.70 * ({DLCADJ}), 2)", "Electric_Rebate__c"),
    ("fPropPPE", 2, PPE, "Proposed_PPE__c"),
    ("fBaseW", 0, BASEW, "Baseline_Watts__c"),
    ("fKW", 4, f"(({BASEW}) - {WATTS}) / 1000 * 1.33 * {QTY}", "Customer_kW_Savings__c"),
    ("fKWH", 2, f"(({BASEW}) - {WATTS}) / 1000 * {QTY} * ({KWHF}) * ({HOURS})", "Customer_kWh_Savings__c"),
    ("fPCKW", 5, f"ROUND((({BASEW}) - {WATTS}) / 1000 * 1.33 * {QTY}, 3) * ({CF})", "Customer_Peak_Coincident_kW__c"),
    ("fIncCost", 2, f"{QTY} * {WATTS} * 1.13", "Incremental_Cost__c"),
]

# factor-used fields set from the resolved TRM version
FACTOR_ITEMS = [
    ("TD_Loss_Factor_Used__c", "ref", "Get_TRM_Version.TD_Loss_Factor__c"),
    ("NTG_Only_Used__c", "ref", "Get_TRM_Version.NTG_Only__c"),
    ("NTG_Total_Used__c", "ref", "Get_TRM_Version.NTG_Total__c"),
    ("Measure_Life_Used__c", "ref", "Get_TRM_Version.Measure_Life_Years__c"),
    ("Technical_TRM_Version__c", "ref", "Get_TRM_Version.Version_Label__c"),
    ("Participants_Used__c", "num", "1"),
    ("Program_Factors_Version__c", "str", "MN-LIGHT-PF-2026"),
    ("Incentive_Rules_Version__c", "str", "MN-LIGHT-IR-2026"),
    ("Expression_Set_Version__c", "str", "Grow_Lighting_MN_Calculator_V1"),
]

# dependent metrics reference $Record fields set in the first assignment (base + factors)
kWc = "{!$Record.Customer_Peak_Coincident_kW__c}"
kWhc = "{!$Record.Customer_kWh_Savings__c}"
TD = "{!$Record.TD_Loss_Factor_Used__c}"
NO = "{!$Record.NTG_Only_Used__c}"
NT = "{!$Record.NTG_Total_Used__c}"
ML = "{!$Record.Measure_Life_Used__c}"
P = "{!$Record.Participants_Used__c}"

DEP_FORMULAS = [
    ("dSMkWGen", 5, f"{kWc} * {TD}", "SM_kW_Gen_PCkW__c"),
    ("dGrossPCkW", 5, f"{kWc} * {P}", "Gross_Annual_PCkW_Customer__c"),
    ("dTotalOnlyNetkW", 5, f"({kWc} * {P}) * {NO}", "Total_Only_Net_kW_Customer_PCkW__c"),
    ("dTotalNetkW", 5, f"({kWc} * {P}) * {NT}", "Total_Net_kW_Customer_PCkW__c"),
    ("dTotalNetPCkWGen", 5, f"(({kWc} * {P}) * {NT}) * {TD}", "Total_Net_PCkW_Gen__c"),
    ("dGrosskWh", 2, f"{kWhc} * {P}", "Gross_Annual_kWh_Customer__c"),
    ("dProgNetCustkWh", 2, f"({kWhc} * {P}) * {NT}", "Program_Net_Annual_Customer_kWh__c"),
    ("dGenkWh", 2, f"{kWhc} * {TD}", "Gen_kWh__c"),
    ("dProgNetGenkWh", 2, f"(({kWhc} * {P}) * {NT}) * {TD}", "Program_Net_Annual_Generator_kWh__c"),
    ("dLifetimeGenkWh", 2, f"({kWhc} * {TD}) * {ML}", "Lifetime_Gen_kWh__c"),
    ("dLifetimeNetGenkWh", 2, f"((({kWhc} * {P}) * {NT}) * {TD}) * {ML}", "Lifetime_Net_Gen_kWh__c"),
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def formula_xml(n, sc, expr, dt="Number"):
    return f"""    <formulas>
        <name>{n}</name>
        <dataType>{dt}</dataType>
        <expression>{esc(expr)}</expression>
        <scale>{sc}</scale>
    </formulas>"""


def ai_ref(target, ref):
    return f"""        <assignmentItems>
            <assignToReference>$Record.{target}</assignToReference>
            <operator>Assign</operator>
            <value><elementReference>{ref}</elementReference></value>
        </assignmentItems>"""


def ai_str(target, val):
    return f"""        <assignmentItems>
            <assignToReference>$Record.{target}</assignToReference>
            <operator>Assign</operator>
            <value><stringValue>{val}</stringValue></value>
        </assignmentItems>"""


def ai_num(target, val):
    return f"""        <assignmentItems>
            <assignToReference>$Record.{target}</assignToReference>
            <operator>Assign</operator>
            <value><numberValue>{val}</numberValue></value>
        </assignmentItems>"""


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "force-app", "main", "default", "flows",
                       "Grow_Lighting_MN_Calculate_Line.flow-meta.xml")

    # formulas block (base + dependent)
    formulas = "\n".join(formula_xml(n, sc, e) for (n, sc, e, _t) in BASE_FORMULAS + DEP_FORMULAS)

    # assignment 1: base outputs + factors/lineage
    a1_items = "\n".join(ai_ref(t, n) for (n, _sc, _e, t) in BASE_FORMULAS)
    for (target, kind, val) in FACTOR_ITEMS:
        a1_items += "\n" + (ai_ref(target, val) if kind == "ref" else
                            ai_num(target, val) if kind == "num" else ai_str(target, val))

    # assignment 2: dependent metrics
    a2_items = "\n".join(ai_ref(t, n) for (n, _sc, _e, t) in DEP_FORMULAS)

    inputs = ["Fixture_Quantity__c", "Market_Segment_Room_Type__c", "Proposed_PPF__c",
              "Proposed_Fixture_Watts__c", "DLC_Tier__c"]
    filters = "\n".join(f"""        <filters>
            <field>{f}</field>
            <operator>IsNull</operator>
            <value><booleanValue>false</booleanValue></value>
        </filters>""" for f in inputs)

    explainer = (
        "Grow Lighting MN v2 calculation\n"
        "Inputs: Qty={!$Record.Fixture_Quantity__c}, Room={!$Record.Market_Segment_Room_Type__c}, "
        "PPF={!$Record.Proposed_PPF__c}, Watts={!$Record.Proposed_Fixture_Watts__c}, "
        "DLC={!$Record.DLC_Tier__c}, Invoice={!$Record.Invoice_Date__c}\n"
        "TRM version (by invoice date): {!$Record.Technical_TRM_Version__c} "
        "[T&D={!$Record.TD_Loss_Factor_Used__c}, NTG_Only={!$Record.NTG_Only_Used__c}, "
        "NTG_Total={!$Record.NTG_Total_Used__c}, Life={!$Record.Measure_Life_Used__c}]\n"
        "Proposed PPE = ROUND(PPF/Watts,2) = {!$Record.Proposed_PPE__c}\n"
        "Baseline Watts = ROUND((Watts*0.972*PPE)/(0.783*1.08),0) = {!$Record.Baseline_Watts__c}\n"
        "Electric Rebate = Qty*Watts*ROUND(0.70*DLC_Adj,2) = {!$Record.Electric_Rebate__c}\n"
        "kW Demand Savings = {!$Record.Customer_kW_Savings__c}; kWh = {!$Record.Customer_kWh_Savings__c}; "
        "Peak Coincident kW = {!$Record.Customer_Peak_Coincident_kW__c}\n"
        "Incremental Cost = {!$Record.Incremental_Cost__c}\n"
        "Dependent DSM: SM kW Gen={!$Record.SM_kW_Gen_PCkW__c}, Net kW Cust={!$Record.Total_Net_kW_Customer_PCkW__c}, "
        "Gen kWh={!$Record.Gen_kWh__c}, Lifetime Net Gen kWh={!$Record.Lifetime_Net_Gen_kWh__c}"
    )

    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <assignments>
        <name>Set_Calculation_Outputs</name>
        <label>Set Calculation Outputs</label>
        <locationX>176</locationX>
        <locationY>528</locationY>
        <connector><targetReference>Set_Dependent_Metrics</targetReference></connector>
{a1_items}
    </assignments>
    <assignments>
        <name>Set_Dependent_Metrics</name>
        <label>Set Dependent DSM Metrics</label>
        <locationX>176</locationX>
        <locationY>648</locationY>
        <connector><targetReference>Set_Explainer</targetReference></connector>
{a2_items}
    </assignments>
    <assignments>
        <name>Set_Explainer</name>
        <label>Set Explainer</label>
        <locationX>176</locationX>
        <locationY>768</locationY>
        <assignmentItems>
            <assignToReference>$Record.Calculation_Explainer__c</assignToReference>
            <operator>Assign</operator>
            <value><elementReference>tExplainer</elementReference></value>
        </assignmentItems>
    </assignments>
    <description>Before-save: resolve TRM version by invoice date, compute rebate + initial energy savings (mirrors BRE Expression Set) + 11 dependent DSM metrics + lineage.</description>
    <environments>Default</environments>
{formulas}
    <interviewLabel>Grow Lighting MN - Calculate Line {{!$Flow.CurrentDateTime}}</interviewLabel>
    <label>Grow Lighting MN - Calculate Line</label>
    <processMetadataValues>
        <name>BuilderType</name>
        <value><stringValue>LightningFlowBuilder</stringValue></value>
    </processMetadataValues>
    <processType>AutoLaunchedFlow</processType>
    <recordLookups>
        <name>Get_Program_Product</name>
        <label>Get Program Product</label>
        <locationX>176</locationX>
        <locationY>168</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Get_TRM_Group</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Id</field>
            <operator>EqualTo</operator>
            <value><elementReference>$Record.RelatedItemId</elementReference></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>ProgramProduct</object>
        <queriedFields>Id</queriedFields>
        <queriedFields>ProductId</queriedFields>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_TRM_Group</name>
        <label>Get TRM Group</label>
        <locationX>176</locationX>
        <locationY>288</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Get_TRM_Version</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Product__c</field>
            <operator>EqualTo</operator>
            <value><elementReference>Get_Program_Product.ProductId</elementReference></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>UsageImpactGroup</object>
        <queriedFields>Id</queriedFields>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_TRM_Version</name>
        <label>Get TRM Version (by invoice date)</label>
        <locationX>176</locationX>
        <locationY>408</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Set_Calculation_Outputs</targetReference></connector>
        <filterLogic>1 AND (2 OR 3)</filterLogic>
        <filters>
            <field>StartDate</field>
            <operator>LessThanOrEqualTo</operator>
            <value><elementReference>$Record.Invoice_Date__c</elementReference></value>
        </filters>
        <filters>
            <field>EndDate</field>
            <operator>GreaterThanOrEqualTo</operator>
            <value><elementReference>$Record.Invoice_Date__c</elementReference></value>
        </filters>
        <filters>
            <field>EndDate</field>
            <operator>IsNull</operator>
            <value><booleanValue>true</booleanValue></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>UsageImpactGroupVersion</object>
        <queriedFields>Id</queriedFields>
        <queriedFields>Version_Label__c</queriedFields>
        <queriedFields>TD_Loss_Factor__c</queriedFields>
        <queriedFields>NTG_Only__c</queriedFields>
        <queriedFields>NTG_Total__c</queriedFields>
        <queriedFields>Measure_Life_Years__c</queriedFields>
        <sortField>Version</sortField>
        <sortOrder>Desc</sortOrder>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector><targetReference>Get_Program_Product</targetReference></connector>
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
