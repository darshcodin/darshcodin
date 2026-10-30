#!/usr/bin/env python3
"""Generate the Grow Lighting MN Calculator Expression Set version metadata.

Keeps the calculation logic in one readable place and emits the verbose BRE XML.
Re-run to re-tune (e.g. string-literal quote style) without hand-editing XML.

Usage: python3 scripts/gen_expression_set.py [--quote single|double]
"""
import argparse
import html
import os

ROOM_TYPES = [
    # (Room_Type, Hours, kWh_Factor, CF)
    ("Cannabis Flower Room", 4255, 1.16, 0.68),
    ("Cannabis Veg Room", 6498, 1.24, 0.89),
    ("Flowering Crops (Tomatoes/Peppers)", 4200, 1.21, 0.76),
    ("Vegetative/Propagation Growth", 6300, 1.21, 0.95),
    ("Microgreens", 6300, 1.21, 0.95),
    ("Clone Room", 6300, 1.21, 0.95),
    ("Combo Veg & Flower Cannabis Room", 5281, 1.20, 0.78),
]
DLC_TIERS = [
    ("DLC Premium", 1.0),
    ("DLC Standard", 1.0),
    ("Non-DLC", 1.0),
]

DEF_NAME = "Grow_Lighting_MN_Calculator"
VERSION_FULLNAME = DEF_NAME + "_V1"


def q(s, quote):
    ch = "'" if quote == "single" else '"'
    return f"{ch}{s}{ch}"


def nested_if(var, pairs, default, quote):
    """Build IF(var == key, val, IF(... , default)) from (key,val) pairs."""
    expr = str(default)
    for key, val in reversed(pairs):
        expr = f"IF({var} == {q(key, quote)}, {val}, {expr})"
    return expr


def build_steps(quote):
    hours_pairs = [(r[0], r[1]) for r in ROOM_TYPES]
    kwh_pairs = [(r[0], r[2]) for r in ROOM_TYPES]
    cf_pairs = [(r[0], r[3]) for r in ROOM_TYPES]
    dlc_pairs = [(t[0], t[1]) for t in DLC_TIERS]

    # (name, label, assignedParameter, expression)
    return [
        ("LookupHours", "Lookup Annual Operating Hours", "Hours",
         nested_if("Room_Type", hours_pairs, 0, quote)),
        ("LookupKwhFactor", "Lookup kWh Savings Factor", "kWh_Factor",
         nested_if("Room_Type", kwh_pairs, 0, quote)),
        ("LookupCF", "Lookup Coincidence Factor", "CF",
         nested_if("Room_Type", cf_pairs, 0, quote)),
        ("LookupDlcAdj", "Lookup DLC Adjustment Factor", "DLC_Adj",
         nested_if("DLC_Tier", dlc_pairs, 1.0, quote)),
        ("CalcElectricRebate", "Calculate Electric Rebate", "electricRebate",
         "Qty * Prop_Watts * ROUND(0.70 * DLC_Adj, 2)"),
        ("CalcProposedPPE", "Calculate Proposed PPE", "Prop_PPE",
         "ROUND(PPF / Prop_Watts, 2)"),
        ("CalcBaselineWatts", "Calculate Baseline Watts (derived)", "Base_W",
         "ROUND((Prop_Watts * 0.972 * Prop_PPE) / (0.783 * 1.08), 0)"),
        ("CalcCustomerKW", "Calculate Customer kW Demand Savings", "customerKW",
         "(Base_W - Prop_Watts) / 1000 * 1.33 * Qty"),
        ("CalcCustomerKWH", "Calculate Customer kWh Energy Savings", "customerKWH",
         "(Base_W - Prop_Watts) / 1000 * Qty * kWh_Factor * Hours"),
        ("CalcCustomerPCKW", "Calculate Customer Peak Coincident kW", "customerPCKW",
         "ROUND(customerKW, 3) * CF"),
        ("CalcIncrementalCost", "Calculate Incremental Cost", "incrementalCost",
         "Qty * Prop_Watts * 1.13"),
    ]


# (name, dataType, decimalPlaces, input, output)
INPUT_VARS = [
    ("Qty", "Numeric", 0, True, False),
    ("Room_Type", "Text", 0, True, False),
    ("PPF", "Numeric", 2, True, False),
    ("Prop_Watts", "Numeric", 2, True, False),
    ("DLC_Tier", "Text", 0, True, False),
]
DERIVED_VARS = [
    ("Hours", "Numeric", 0, False, True),
    ("kWh_Factor", "Numeric", 2, False, True),
    ("CF", "Numeric", 2, False, True),
    ("DLC_Adj", "Numeric", 2, False, True),
    ("Prop_PPE", "Numeric", 2, False, True),
    ("Base_W", "Numeric", 0, False, True),
    ("electricRebate", "Numeric", 2, False, True),
    ("customerKW", "Numeric", 5, False, True),
    ("customerKWH", "Numeric", 2, False, True),
    ("customerPCKW", "Numeric", 5, False, True),
    ("incrementalCost", "Numeric", 2, False, True),
]


def step_xml(seq, name, label, assigned, expr):
    e = html.escape(expr, quote=False)
    return f"""    <steps>
        <actionType>AssignParameterValues</actionType>
        <assignment>
            <assignedParameter>{assigned}</assignedParameter>
            <expression>{e}</expression>
        </assignment>
        <label>{label}</label>
        <name>{name}</name>
        <resultIncluded>true</resultIncluded>
        <sequenceNumber>{seq}</sequenceNumber>
        <shouldExposExecPathMsgOnly>true</shouldExposExecPathMsgOnly>
        <shouldExposeConditionDetails>false</shouldExposeConditionDetails>
        <shouldShowExplExternally>false</shouldShowExplExternally>
        <stepType>BusinessKnowledgeModel</stepType>
    </steps>"""


def var_xml(name, dtype, dp, is_in, is_out):
    return f"""    <variables>
        <collection>false</collection>
        <dataType>{dtype}</dataType>
        <decimalPlaces>{dp}</decimalPlaces>
        <description>{name}</description>
        <input>{str(is_in).lower()}</input>
        <name>{name}</name>
        <output>{str(is_out).lower()}</output>
        <type>Variable</type>
    </variables>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quote", choices=["single", "double"], default="double")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    steps = build_steps(args.quote)
    steps_xml = "\n".join(
        step_xml(i + 1, *s) for i, s in enumerate(steps)
    )
    vars_xml = "\n".join(
        var_xml(*v) for v in (INPUT_VARS + DERIVED_VARS)
    )

    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<ExpressionSetDefinitionVersion xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Core calculator: rebate + initial energy savings for LED Grow Fixture MN v2. Lookups inline (Room Type, DLC Tier); constants per TRM reference data.</description>
    <expressionSetDefinition>{DEF_NAME}</expressionSetDefinition>
    <label>Grow Lighting MN Calculator V1</label>
    <processType>Bre</processType>
    <rank>1</rank>
    <shouldShowExplExternally>false</shouldShowExplExternally>
    <startDate>2026-01-01T00:00:00.000Z</startDate>
    <status>Active</status>
{steps_xml}
{vars_xml}
    <versionNumber>1</versionNumber>
</ExpressionSetDefinitionVersion>
"""
    out = args.out or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "force-app", "main", "default", "expressionSetVersion",
        f"{VERSION_FULLNAME}.expressionSetVersion-meta.xml",
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        f.write(doc)
    print("wrote", out)


if __name__ == "__main__":
    main()
