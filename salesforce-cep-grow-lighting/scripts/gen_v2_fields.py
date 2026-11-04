#!/usr/bin/env python3
"""Generate custom fields for the reusable 3-layer calculator architecture."""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "force-app", "main", "default", "objects")

HDR = '<?xml version="1.0" encoding="UTF-8"?>\n<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">\n'


def num(name, label, prec, scale, desc=""):
    return HDR + f"""    <fullName>{name}</fullName>
    <externalId>false</externalId>
    <label>{label}</label>
    <precision>{prec}</precision>
    <required>false</required>
    <scale>{scale}</scale>
    <description>{desc}</description>
    <trackHistory>false</trackHistory>
    <type>Number</type>
    <unique>false</unique>
</CustomField>\n"""


def txt(name, label, length, desc=""):
    return HDR + f"""    <fullName>{name}</fullName>
    <externalId>false</externalId>
    <label>{label}</label>
    <length>{length}</length>
    <required>false</required>
    <description>{desc}</description>
    <trackHistory>false</trackHistory>
    <type>Text</type>
    <unique>false</unique>
</CustomField>\n"""


def curr(name, label, prec, scale, desc=""):
    return HDR + f"""    <fullName>{name}</fullName>
    <externalId>false</externalId>
    <label>{label}</label>
    <precision>{prec}</precision>
    <required>false</required>
    <scale>{scale}</scale>
    <description>{desc}</description>
    <trackHistory>false</trackHistory>
    <type>Currency</type>
</CustomField>\n"""


def dt(name, label, desc=""):
    return HDR + f"""    <fullName>{name}</fullName>
    <externalId>false</externalId>
    <label>{label}</label>
    <required>false</required>
    <description>{desc}</description>
    <trackHistory>false</trackHistory>
    <type>DateTime</type>
</CustomField>\n"""


def lookup(name, label, target, rel_name, desc=""):
    return HDR + f"""    <fullName>{name}</fullName>
    <deleteConstraint>SetNull</deleteConstraint>
    <externalId>false</externalId>
    <label>{label}</label>
    <referenceTo>{target}</referenceTo>
    <relationshipLabel>{label}</relationshipLabel>
    <relationshipName>{rel_name}</relationshipName>
    <required>false</required>
    <description>{desc}</description>
    <trackHistory>false</trackHistory>
    <type>Lookup</type>
</CustomField>\n"""


def picklist(name, label, values, desc=""):
    vals = "".join(f"""                <value>
                    <fullName>{v}</fullName>
                    <default>false</default>
                    <label>{v}</label>
                </value>\n""" for v in values)
    return HDR + f"""    <fullName>{name}</fullName>
    <externalId>false</externalId>
    <label>{label}</label>
    <required>false</required>
    <description>{desc}</description>
    <trackHistory>false</trackHistory>
    <type>Picklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetDefinition>
            <sorted>false</sorted>
{vals}        </valueSetDefinition>
    </valueSet>
</CustomField>\n"""


FIELDS = {
    # ---- UsageImpactGroup: identifies which of the three version families a group holds
    "UsageImpactGroup": [
        ("Version_Role__c", picklist("Version_Role__c", "Version Role",
            ["Technical TRM", "Program Factors", "Incentive Rules"],
            "Which of the three reference-data families this group holds. The calculate flow uses it to pick one version of each role.")),
    ],

    # ---- UsageImpactGroupVersion: pattern selectors + parameters
    "UsageImpactGroupVersion": [
        ("CalcPattern__c", txt("CalcPattern__c", "Calc Pattern", 80,
            "API name of the savings Expression Set this technical version drives, e.g. P2_EffDelta. This is the reusability hook: a new measure points at an existing pattern instead of needing a new rule set.")),
        ("Incentive_Pattern__c", txt("Incentive_Pattern__c", "Incentive Pattern", 80,
            "API name of the incentive Expression Set, e.g. I2_PerUnitBonus.")),
        ("Reporting_Pattern__c", txt("Reporting_Pattern__c", "Reporting Pattern", 80,
            "API name of the net/lifetime reporting Expression Set, e.g. R1_StdReporting.")),
        # savings parameters (Technical TRM role)
        ("Baseline_Efficacy__c", num("Baseline_Efficacy__c", "Baseline Efficacy", 10, 4,
            "Program baseline efficacy used by the efficiency-delta pattern, e.g. 1.08 umol/J.")),
        ("Prop_Reflector_Eff__c", num("Prop_Reflector_Eff__c", "Proposed Reflector Efficiency", 6, 4, "")),
        ("Base_Reflector_Eff__c", num("Base_Reflector_Eff__c", "Baseline Reflector Efficiency", 6, 4, "")),
        ("Cooling_Factor__c", num("Cooling_Factor__c", "Cooling Interaction Factor", 6, 4,
            "Cooling interaction factor applied to demand savings, e.g. 1.33.")),
        # incentive parameters (Incentive Rules role)
        ("Rebate_Rate_Per_Unit__c", num("Rebate_Rate_Per_Unit__c", "Rebate Rate Per Unit", 10, 4,
            "Incentive rate per unit of the measure's billing unit, e.g. 0.70 per watt.")),
        ("Bonus_Multiplier__c", num("Bonus_Multiplier__c", "Bonus Multiplier", 6, 4,
            "Tier or bonus multiplier applied to the base rate. 1.00 means no bonus.")),
        ("Max_Incentive__c", curr("Max_Incentive__c", "Maximum Incentive", 16, 2,
            "Cap applied to the calculated incentive. Blank means uncapped.")),
        ("Inc_Cost_Per_Unit__c", num("Inc_Cost_Per_Unit__c", "Incremental Cost Per Unit", 10, 4,
            "Incremental measure cost per unit, e.g. 1.13 per watt.")),
    ],

    # ---- IndividualApplicationItem: routing inputs, ES reference fields, generic output contract
    "IndividualApplicationItem": [
        ("Program_Product__c", lookup("Program_Product__c", "Program Product", "ProgramProduct",
            "Grow_Lighting_Lines",
            "The program/product pairing for this line. The calculate flow reads its Program and Product to find the matching Program Measure rows.")),
        # resolved version references (step 3 output)
        ("Technical_Version__c", lookup("Technical_Version__c", "Technical TRM Version Ref", "UsageImpactGroupVersion",
            "Technical_Version_Lines",
            "The Technical TRM version whose effective window covered the invoice date at calculation time.")),
        ("Program_Factors_Version_Ref__c", lookup("Program_Factors_Version_Ref__c", "Program Factors Version Ref",
            "UsageImpactGroupVersion", "Program_Factors_Lines",
            "The Program Factors version selected by invoice date.")),
        ("Incentive_Rules_Version_Ref__c", lookup("Incentive_Rules_Version_Ref__c", "Incentive Rules Version Ref",
            "UsageImpactGroupVersion", "Incentive_Rules_Lines",
            "The Incentive Rules version selected by invoice date.")),
        # which expression sets actually ran (step 8 reference fields)
        ("Savings_Expression_Set__c", txt("Savings_Expression_Set__c", "Savings Expression Set", 80,
            "API name of the savings Expression Set the flow invoked, taken from the technical version's Calc Pattern.")),
        ("Incentive_Expression_Set__c", txt("Incentive_Expression_Set__c", "Incentive Expression Set", 80,
            "API name of the incentive Expression Set the flow invoked.")),
        ("Reporting_Expression_Set__c", txt("Reporting_Expression_Set__c", "Reporting Expression Set", 80,
            "API name of the net/lifetime reporting Expression Set the flow invoked.")),
        ("Calc_Pattern_Used__c", txt("Calc_Pattern_Used__c", "Calc Pattern Used", 80,
            "The Calc Pattern value read from the technical version. Kept for lineage even if the pattern is later repointed.")),
        ("Context_Definition_Used__c", txt("Context_Definition_Used__c", "Context Definition Used", 80,
            "API name of the Context Definition that hydrated the payload.")),
        ("Calculation_Run_Timestamp__c", dt("Calculation_Run_Timestamp__c", "Calculation Run Timestamp", "")),
        ("Calculation_Status__c", picklist("Calculation_Status__c", "Calculation Status",
            ["Not Calculated", "Calculated", "Failed"], "")),
        ("Calculation_Error__c", txt("Calculation_Error__c", "Calculation Error", 255,
            "Fault message from the calculate flow when calculation status is Failed.")),
        # generic savings output contract - every savings pattern must populate these
        ("Gross_kW__c", num("Gross_kW__c", "Gross kW", 14, 4,
            "Shared output contract: gross connected demand savings. Every savings Expression Set must populate this, which is what lets one reporting Expression Set serve every measure.")),
        ("Gross_kWh__c", num("Gross_kWh__c", "Gross kWh", 16, 2,
            "Shared output contract: gross annual energy savings.")),
        ("Gross_Therms__c", num("Gross_Therms__c", "Gross Therms", 16, 2,
            "Shared output contract: gross annual gas savings. Zero for electric-only measures.")),
        ("Gross_PCkW__c", num("Gross_PCkW__c", "Gross Peak Coincident kW", 14, 5,
            "Shared output contract: gross peak-coincident demand savings.")),
        ("Measure_Quantity__c", num("Measure_Quantity__c", "Measure Quantity", 10, 2,
            "Shared output contract: the unit count the incentive pattern multiplies by.")),
        ("Measure_Unit_Basis__c", txt("Measure_Unit_Basis__c", "Measure Unit Basis", 40,
            "The billing unit the incentive rate applies to, e.g. Watts, Horsepower, SqFt.")),
    ],
}


def main():
    total = 0
    for obj, fields in FIELDS.items():
        d = os.path.join(BASE, obj, "fields")
        os.makedirs(d, exist_ok=True)
        for name, body in fields:
            with open(os.path.join(d, f"{name}.field-meta.xml"), "w") as fh:
                fh.write(body)
            total += 1
        print(f"  {obj}: {len(fields)} fields")
    print(f"total {total}")


if __name__ == "__main__":
    main()
