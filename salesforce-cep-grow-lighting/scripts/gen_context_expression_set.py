#!/usr/bin/env python3
"""Generate the context-hydrated Expression Set 'Grow_Lighting_MN_Context_Calc'.

Declares contextDefinitions=GrowLightingContext, so the Context Service hydrates the
input variables (named to match the context node attributes) from the line, and the
engine computes the rebate + initial savings. Same formulas as the variable-based V1.
"""
import os, html

ROOM = [
    ("Cannabis Flower Room", 4255, 1.16, 0.68),
    ("Cannabis Veg Room", 6498, 1.24, 0.89),
    ("Flowering Crops (Tomatoes/Peppers)", 4200, 1.21, 0.76),
    ("Vegetative/Propagation Growth", 6300, 1.21, 0.95),
    ("Microgreens", 6300, 1.21, 0.95),
    ("Clone Room", 6300, 1.21, 0.95),
    ("Combo Veg & Flower Cannabis Room", 5281, 1.20, 0.78),
]
DEF = "Grow_Lighting_MN_Context_Calc"
VER = DEF + "_V1"
# context attribute names (hydrated from the line by GrowLightingContext)
QTY, PPF, WATTS, ROOMF, DLCF = ("FixtureQuantity", "ProposedPPF", "ProposedWatts", "RoomType", "DLCTier")


def case(field, idx):
    arms = "".join(f', "{r[0]}", {r[idx]}' for r in ROOM)
    return f"CASE({field}{arms}, 0)"


HOURS, KWHF, CF = case(ROOMF, 1), case(ROOMF, 2), case(ROOMF, 3)
DLCADJ = f'CASE({DLCF}, "DLC Premium", 1, "DLC Standard", 1, "Non-DLC", 1, 1)'
PPE = f"ROUND({PPF} / {WATTS}, 2)"
BASEW = f"ROUND(({WATTS} * 0.972 * ({PPE})) / (0.783 * 1.08), 0)"

STEPS = [
    ("CalcRebate", "electricRebate", f"{QTY} * {WATTS} * ROUND(0.70 * ({DLCADJ}), 2)"),
    ("CalcPPE", "Prop_PPE", PPE),
    ("CalcBaseW", "Base_W", BASEW),
    ("CalcKW", "customerKW", f"(({BASEW}) - {WATTS}) / 1000 * 1.33 * {QTY}"),
    ("CalcKWH", "customerKWH", f"(({BASEW}) - {WATTS}) / 1000 * {QTY} * ({KWHF}) * ({HOURS})"),
    ("CalcPCKW", "customerPCKW", f"ROUND((({BASEW}) - {WATTS}) / 1000 * 1.33 * {QTY}, 3) * ({CF})"),
    ("CalcIncCost", "incrementalCost", f"{QTY} * {WATTS} * 1.13"),
]
INPUT_VARS = [(QTY, "Numeric", 0), (ROOMF, "Text", 0), (PPF, "Numeric", 2),
              (WATTS, "Numeric", 2), (DLCF, "Text", 0)]
OUT_VARS = [("electricRebate", 2), ("Prop_PPE", 2), ("Base_W", 0), ("customerKW", 4),
            ("customerKWH", 2), ("customerPCKW", 5), ("incrementalCost", 2)]


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dd = os.path.join(root, "force-app/main/default/expressionSetDefinition")
    vd = os.path.join(root, "force-app/main/default/expressionSetVersion")
    os.makedirs(dd, exist_ok=True); os.makedirs(vd, exist_ok=True)

    open(os.path.join(dd, f"{DEF}.expressionSetDefinition-meta.xml"), "w").write(f"""<?xml version="1.0" encoding="UTF-8"?>
<ExpressionSetDefinition xmlns="http://soap.sforce.com/2006/04/metadata">
    <contextDefinitions>GrowLightingContext</contextDefinitions>
    <description>Context-hydrated Grow Lighting MN calculator. Inputs assembled by the Context Service (GrowLightingContext) from the application line; computes rebate + initial savings.</description>
    <interfaceSourceType>Bre</interfaceSourceType>
    <label>Grow Lighting MN Context Calc</label>
    <processType>Bre</processType>
    <template>false</template>
    <versions>
        <fullName>{VER}</fullName>
        <expressionSetDefinition>{DEF}</expressionSetDefinition>
        <interfaceSourceType>Bre</interfaceSourceType>
        <label>Grow Lighting MN Context Calc V1</label>
        <processType>Bre</processType>
        <shouldShowExplExternally>false</shouldShowExplExternally>
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
        <shouldExposExecPathMsgOnly>true</shouldExposExecPathMsgOnly>
        <shouldExposeConditionDetails>false</shouldExposeConditionDetails>
        <shouldShowExplExternally>false</shouldShowExplExternally>
        <stepType>BusinessKnowledgeModel</stepType>
    </steps>""" for i, (n, out, expr) in enumerate(STEPS))

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

    vars_xml = "\n".join([var(n, dt, sc, True) for n, dt, sc in INPUT_VARS] +
                         [var(n, "Numeric", sc, False) for n, sc in OUT_VARS])

    open(os.path.join(vd, f"{VER}.expressionSetVersion-meta.xml"), "w").write(f"""<?xml version="1.0" encoding="UTF-8"?>
<ExpressionSetDefinitionVersion xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>Context-hydrated calc: rebate + initial energy savings for LED Grow Fixture MN v2.</description>
    <expressionSetDefinition>{DEF}</expressionSetDefinition>
    <label>Grow Lighting MN Context Calc V1</label>
    <processType>Bre</processType>
    <rank>1</rank>
    <shouldShowExplExternally>false</shouldShowExplExternally>
    <startDate>2026-01-01T00:00:00.000Z</startDate>
    <status>Draft</status>
{steps}
{vars_xml}
    <versionNumber>1</versionNumber>
</ExpressionSetDefinitionVersion>
""")
    print("wrote", DEF)


if __name__ == "__main__":
    main()
