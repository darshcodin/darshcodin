#!/usr/bin/env python3
"""Generate CEP_Line_Calc_Context: one reusable context for every measure line.

Root node = the application line. Three sibling nodes = the resolved Technical TRM,
Program Factors and Incentive Rules versions. The flow passes the line id and the
three version ids; the Context Service returns one payload the Expression Sets read.
"""
import os

DEF = "CEP_Line_Calc_Context"

# (nodeName, object, [(contextAttr, sourceField, dataType)])
NODES = [
    ("CalcLine", "IndividualApplicationItem", [
        # --- the line's own input fields
        ("Quantity",        "Fixture_Quantity__c",         "number"),
        ("SegmentCode",     "Market_Segment_Room_Type__c", "string"),
        ("ProposedOutput",  "Proposed_PPF__c",             "number"),
        ("ProposedInput",   "Proposed_Fixture_Watts__c",   "number"),
        ("EquipmentTier",   "DLC_Tier__c",                 "string"),
        ("InvoiceDate",     "Invoice_Date__c",             "date"),
        # --- Technical TRM version, traversed through the lookup the flow sets in step 3
        ("BaselineEfficacy", "Technical_Version__r.Baseline_Efficacy__c",  "number"),
        ("PropReflectorEff", "Technical_Version__r.Prop_Reflector_Eff__c", "number"),
        ("BaseReflectorEff", "Technical_Version__r.Base_Reflector_Eff__c", "number"),
        ("CoolingFactor",    "Technical_Version__r.Cooling_Factor__c",     "number"),
        ("CalcPattern",      "Technical_Version__r.CalcPattern__c",        "string"),
        ("TechVersionLabel", "Technical_Version__r.Version_Label__c",      "string"),
        # --- Program Factors version
        ("TDLoss",         "Program_Factors_Version_Ref__r.TD_Loss_Factor__c",     "number"),
        ("NTGOnly",        "Program_Factors_Version_Ref__r.NTG_Only__c",           "number"),
        ("NTGTotal",       "Program_Factors_Version_Ref__r.NTG_Total__c",          "number"),
        ("MeasureLife",    "Program_Factors_Version_Ref__r.Measure_Life_Years__c", "number"),
        ("PFVersionLabel", "Program_Factors_Version_Ref__r.Version_Label__c",      "string"),
        # --- Incentive Rules version
        ("RatePerUnit",     "Incentive_Rules_Version_Ref__r.Rebate_Rate_Per_Unit__c", "number"),
        ("BonusMultiplier", "Incentive_Rules_Version_Ref__r.Bonus_Multiplier__c",     "number"),
        ("MaxIncentive",    "Incentive_Rules_Version_Ref__r.Max_Incentive__c",        "number"),
        ("IncCostPerUnit",  "Incentive_Rules_Version_Ref__r.Inc_Cost_Per_Unit__c",    "number"),
        ("IRVersionLabel",  "Incentive_Rules_Version_Ref__r.Version_Label__c",        "string"),
    ]),
]


def node_mapping(node, obj, attrs):
    maps = "".join(f"""                <contextAttributeMappings>
                    <contextAttrHydrationDetails>
                        <objectName>{obj}</objectName>
                        <queryAttribute>{src}</queryAttribute>
                    </contextAttrHydrationDetails>
                    <contextAttribute>{ca}</contextAttribute>
                    <contextInputAttributeName>{ca}</contextInputAttributeName>
                </contextAttributeMappings>
""" for ca, src, _dt in attrs)
    return f"""            <contextNodeMappings>
{maps}                <contextNode>{node}</contextNode>
                <object>{obj}</object>
            </contextNodeMappings>
"""


def node_def(node, attrs):
    a = "".join(f"""            <contextAttributes>
                <dataType>{dt}</dataType>
                <fieldType>input</fieldType>
                <key>false</key>
                <title>{ca}</title>
                <value>false</value>
            </contextAttributes>
""" for ca, _src, dt in attrs)
    return f"""        <contextNodes>
{a}            <displayName>{node}</displayName>
            <title>{node}</title>
            <transposable>false</transposable>
        </contextNodes>
"""


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(root, "force-app/main/default/contextDefinitions")
    os.makedirs(d, exist_ok=True)

    mappings = "".join(node_mapping(n, o, a) for n, o, a in NODES)
    nodes = "".join(node_def(n, a) for n, _o, a in NODES)

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<ContextDefinition xmlns="http://soap.sforce.com/2006/04/metadata">
    <contextDefinitionVersions>
        <contextMappings>
            <contextMappingIntents>
                <mappingIntent>hydration</mappingIntent>
            </contextMappingIntents>
{mappings}            <default>true</default>
            <description>Hydrate one application line plus its three resolved reference-data versions</description>
            <title>CEPLineCalcMapping</title>
        </contextMappings>
{nodes}        <isActive>true</isActive>
        <startDate>2026-01-01 00:00:00</startDate>
        <versionNumber>1</versionNumber>
    </contextDefinitionVersions>
    <contextTtl>10</contextTtl>
    <description>Reusable calculation context for any CEP measure line. Root node is the application line; three sibling nodes carry the Technical TRM, Program Factors and Incentive Rules versions selected by invoice date.</description>
    <isProtected>false</isProtected>
    <masterLabel>CEP Line Calc Context</masterLabel>
    <title>{DEF}</title>
</ContextDefinition>
"""
    p = os.path.join(d, f"{DEF}.contextDefinition-meta.xml")
    open(p, "w").write(xml)
    print("wrote", p)
    print("nodes:", ", ".join(n for n, _o, _a in NODES))
    print("attributes:", sum(len(a) for _n, _o, a in NODES))


if __name__ == "__main__":
    main()
