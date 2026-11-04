#!/usr/bin/env python3
"""Generate the three layered Expression Sets.

  P2_EffDelta      savings  - efficiency-delta pattern, one of N savings patterns
  I2_PerUnitBonus  incentive - per-unit rate with bonus multiplier and cap
  R1_StdReporting  reporting - net/lifetime DSM metrics, SHARED BY EVERY MEASURE

Every savings pattern must emit the same output contract
(Gross_kW, Gross_kWh, Gross_PCkW, Gross_Therms, Measure_Quantity);
that contract is what lets one reporting set serve all measures.
"""
import os, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DD = os.path.join(ROOT, "force-app/main/default/expressionSetDefinition")
VD = os.path.join(ROOT, "force-app/main/default/expressionSetVersion")

SEGMENTS = [
    ("Cannabis Flower Room", 4255, 1.16, 0.68),
    ("Cannabis Veg Room", 6498, 1.24, 0.89),
    ("Flowering Crops (Tomatoes/Peppers)", 4200, 1.21, 0.76),
    ("Vegetative/Propagation Growth", 6300, 1.21, 0.95),
    ("Microgreens", 6300, 1.21, 0.95),
    ("Clone Room", 6300, 1.21, 0.95),
    ("Combo Veg & Flower Cannabis Room", 5281, 1.20, 0.78),
]


def seg_case(idx):
    arms = "".join(f', "{s[0]}", {s[idx]}' for s in SEGMENTS)
    return f"CASE(SegmentCode{arms}, 0)"


HOURS, KWHF, CF = seg_case(1), seg_case(2), seg_case(3)

EFF = "ROUND(ProposedOutput / ProposedInput, 2)"
BASEIN = f"ROUND((ProposedInput * PropReflectorEff * ({EFF})) / (BaseReflectorEff * BaselineEfficacy), 0)"
DELTA = f"(({BASEIN}) - ProposedInput) / 1000"

# ---------------------------------------------------------------- P2_EffDelta
P2 = {
    "api": "P2_EffDelta",
    "label": "P2 Efficiency Delta Savings",
    "desc": "Savings pattern: derives a baseline input from the proposed unit's output efficacy, then takes the difference. Serves any measure whose savings come from an efficacy improvement. Emits the standard gross output contract.",
    "context": "CEP_Line_Calc_Context",
    "inputs": [
        ("Quantity", "Numeric", 2), ("SegmentCode", "Text", 0),
        ("ProposedOutput", "Numeric", 2), ("ProposedInput", "Numeric", 2),
        ("BaselineEfficacy", "Numeric", 4), ("PropReflectorEff", "Numeric", 4),
        ("BaseReflectorEff", "Numeric", 4), ("CoolingFactor", "Numeric", 4),
    ],
    "steps": [
        ("CalcEfficacy",   "Proposed_Efficacy", EFF, 2),
        ("CalcBaseline",   "Baseline_Input",    BASEIN, 0),
        ("CalcGrossKW",    "Gross_kW",          f"{DELTA} * CoolingFactor * Quantity", 4),
        ("CalcGrossKWH",   "Gross_kWh",         f"{DELTA} * Quantity * ({KWHF}) * ({HOURS})", 2),
        ("CalcGrossPCkW",  "Gross_PCkW",        f"ROUND({DELTA} * CoolingFactor * Quantity, 3) * ({CF})", 5),
        ("CalcGrossTherms","Gross_Therms",      "0", 2),
        ("CalcMeasureQty", "Measure_Quantity",  "Quantity * ProposedInput", 2),
    ],
}

# ------------------------------------------------------------ I2_PerUnitBonus
BASE_INC = "Measure_Quantity * ROUND(RatePerUnit * BonusMultiplier, 2)"
I2 = {
    "api": "I2_PerUnitBonus",
    "label": "I2 Per Unit Bonus Incentive",
    "desc": "Incentive pattern: a per-unit rate times a bonus multiplier, capped at a maximum. Serves any measure paid per unit of its billing basis. Measure_Quantity is handed in from whichever savings pattern ran.",
    "context": "CEP_Line_Calc_Context",
    "inputs": [
        ("Measure_Quantity", "Numeric", 2), ("RatePerUnit", "Numeric", 4),
        ("BonusMultiplier", "Numeric", 4), ("MaxIncentive", "Numeric", 2),
        ("IncCostPerUnit", "Numeric", 4),
    ],
    "steps": [
        ("CalcBaseIncentive", "Base_Incentive",   BASE_INC, 2),
        ("CalcIncrementalCost","Incremental_Cost","Measure_Quantity * IncCostPerUnit", 2),
        ("CalcCappedIncentive","Incentive_Amount",
         f"IF(AND(MaxIncentive > 0, ({BASE_INC}) > MaxIncentive), MaxIncentive, {BASE_INC})", 2),
    ],
}

# ------------------------------------------------------------ R1_StdReporting
R1 = {
    "api": "R1_StdReporting",
    "label": "R1 Standard Net and Lifetime Reporting",
    "desc": "Reporting pattern: turns the gross output contract into the eleven net and lifetime DSM metrics using the Program Factors version. Measure agnostic - one active version serves every electric measure in the portfolio.",
    "context": "CEP_Line_Calc_Context",
    "inputs": [
        ("Gross_kW", "Numeric", 4), ("Gross_kWh", "Numeric", 2), ("Gross_PCkW", "Numeric", 5),
        ("TDLoss", "Numeric", 4), ("NTGOnly", "Numeric", 4), ("NTGTotal", "Numeric", 4),
        ("MeasureLife", "Numeric", 0), ("Participants", "Numeric", 0),
    ],
    "steps": [
        ("CalcSMkWGen",        "SM_kW_Gen_PCkW",          "Gross_PCkW * TDLoss", 5),
        ("CalcGrossPCkWCust",  "Gross_Annual_PCkW_Cust",  "Gross_PCkW * Participants", 5),
        ("CalcTotOnlyNetKW",   "Total_Only_Net_kW",       "(Gross_PCkW * Participants) * NTGOnly", 5),
        ("CalcTotNetKW",       "Total_Net_kW",            "(Gross_PCkW * Participants) * NTGTotal", 5),
        ("CalcTotNetPCkWGen",  "Total_Net_PCkW_Gen",      "((Gross_PCkW * Participants) * NTGTotal) * TDLoss", 5),
        ("CalcGrossKWhCust",   "Gross_Annual_kWh_Cust",   "Gross_kWh * Participants", 2),
        ("CalcProgNetCustKWh", "Prog_Net_Annual_Cust_kWh","(Gross_kWh * Participants) * NTGTotal", 2),
        ("CalcGenKWh",         "Gen_kWh",                 "Gross_kWh * TDLoss", 2),
        ("CalcProgNetGenKWh",  "Prog_Net_Annual_Gen_kWh", "((Gross_kWh * Participants) * NTGTotal) * TDLoss", 2),
        ("CalcLifeGenKWh",     "Lifetime_Gen_kWh",        "(Gross_kWh * TDLoss) * MeasureLife", 2),
        ("CalcLifeNetGenKWh",  "Lifetime_Net_Gen_kWh",    "((((Gross_kWh * Participants) * NTGTotal) * TDLoss)) * MeasureLife", 2),
    ],
}


def var(name, dt, sc, is_in):
    return f"""    <variables>
        <collection>false</collection>
        <dataType>{dt}</dataType>
        <decimalPlaces>{sc}</decimalPlaces>
        <description>{name}</description>
        <input>{'true' if is_in else 'false'}</input>
        <name>{name}</name>
        <output>{'false' if is_in else 'true'}</output>
        <type>Variable</type>
    </variables>"""


def build(spec):
    api, ver = spec["api"], spec["api"] + "_V1"
    os.makedirs(DD, exist_ok=True); os.makedirs(VD, exist_ok=True)

    open(os.path.join(DD, f"{api}.expressionSetDefinition-meta.xml"), "w").write(
f"""<?xml version="1.0" encoding="UTF-8"?>
<ExpressionSetDefinition xmlns="http://soap.sforce.com/2006/04/metadata">
    <contextDefinitions>{spec['context']}</contextDefinitions>
    <description>{spec['desc'][:250]}</description>
    <interfaceSourceType>Bre</interfaceSourceType>
    <label>{spec['label']}</label>
    <processType>Bre</processType>
    <template>false</template>
    <versions>
        <fullName>{ver}</fullName>
        <expressionSetDefinition>{api}</expressionSetDefinition>
        <interfaceSourceType>Bre</interfaceSourceType>
        <label>{spec['label']} V1</label>
        <processType>Bre</processType>
        <shouldShowExplExternally>true</shouldShowExplExternally>
        <startDate>2026-01-01T00:00:00.000Z</startDate>
        <status>Draft</status>
        <versionNumber>1</versionNumber>
    </versions>
</ExpressionSetDefinition>
""")

    steps = "\n".join(f"""    <steps>
        <actionType>AssignParameterValues</actionType>
        <assignment>
            <assignedParameter>{out}</assignedParameter>
            <expression>{html.escape(expr, quote=False)}</expression>
        </assignment>
        <label>{n}</label>
        <name>{n}</name>
        <resultIncluded>true</resultIncluded>
        <sequenceNumber>{i+1}</sequenceNumber>
        <shouldExposExecPathMsgOnly>false</shouldExposExecPathMsgOnly>
        <shouldExposeConditionDetails>true</shouldExposeConditionDetails>
        <shouldShowExplExternally>true</shouldShowExplExternally>
        <stepType>BusinessKnowledgeModel</stepType>
    </steps>""" for i, (n, out, expr, _sc) in enumerate(spec["steps"]))

    vars_xml = "\n".join(
        [var(n, dt, sc, True) for n, dt, sc in spec["inputs"]] +
        [var(out, "Numeric", sc, False) for _n, out, _e, sc in spec["steps"]])

    open(os.path.join(VD, f"{ver}.expressionSetVersion-meta.xml"), "w").write(
f"""<?xml version="1.0" encoding="UTF-8"?>
<ExpressionSetDefinitionVersion xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>{spec['desc'][:250]}</description>
    <expressionSetDefinition>{api}</expressionSetDefinition>
    <label>{spec['label']} V1</label>
    <processType>Bre</processType>
    <rank>1</rank>
    <shouldShowExplExternally>true</shouldShowExplExternally>
    <startDate>2026-01-01T00:00:00.000Z</startDate>
    <status>Draft</status>
{steps}
{vars_xml}
    <versionNumber>1</versionNumber>
</ExpressionSetDefinitionVersion>
""")
    print(f"  {api:18s} inputs={len(spec['inputs']):2d} steps={len(spec['steps']):2d} outputs={len(spec['steps'])}")


if __name__ == "__main__":
    for s in (P2, I2, R1):
        build(s)
