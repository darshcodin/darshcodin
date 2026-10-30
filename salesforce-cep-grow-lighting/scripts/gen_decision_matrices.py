#!/usr/bin/env python3
"""Generate native BRE Decision Matrix metadata (definition + version with columns)
for the Grow Lighting MN Room Type and DLC Tier lookups. Rows are loaded as data
(CalculationMatrixRow) by scripts/load_matrix_rows.py.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFDIR = os.path.join(ROOT, "force-app", "main", "default", "decisionMatrixDefinition")
VERDIR = os.path.join(ROOT, "force-app", "main", "default", "decisionMatrixVersion")

# (api, label, [(colName, Input|Output, Text|Number), ...])
MATRICES = [
    ("Grow_Lighting_Room_Type", "Grow Lighting Room Type", [
        ("Room_Type", "Input", "Text"),
        ("Hours", "Output", "Number"),
        ("kWh_Factor", "Output", "Number"),
        ("CF", "Output", "Number"),
    ]),
    ("Grow_Lighting_DLC_Tier", "Grow Lighting DLC Tier", [
        ("DLC_Tier", "Input", "Text"),
        ("DLC_Adj", "Output", "Number"),
        ("Effective_Rate", "Output", "Number"),
    ]),
]


def definition(api, label):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<DecisionMatrixDefinition xmlns="http://soap.sforce.com/2006/04/metadata">
    <description>{label} lookup for Grow Lighting MN (TRM-versionable).</description>
    <label>{label}</label>
    <type>Standard</type>
</DecisionMatrixDefinition>
"""


def version(api, label, cols, status="Draft"):
    cols_xml = "\n".join(f"""    <columns>
        <columnType>{ct}</columnType>
        <dataType>{dt}</dataType>
        <displaySequence>{i+1}</displaySequence>
        <name>{name}</name>
    </columns>""" for i, (name, ct, dt) in enumerate(cols))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<DecisionMatrixDefinitionVersion xmlns="http://soap.sforce.com/2006/04/metadata">
{cols_xml}
    <decisionMatrixDefinition>{api}</decisionMatrixDefinition>
    <label>{label} V1</label>
    <startDate>2026-01-01T00:00:00.000Z</startDate>
    <status>{status}</status>
    <versionNumber>1</versionNumber>
</DecisionMatrixDefinitionVersion>
"""


def main():
    import sys
    status = "Active" if "--active" in sys.argv else "Draft"
    os.makedirs(DEFDIR, exist_ok=True)
    os.makedirs(VERDIR, exist_ok=True)
    for api, label, cols in MATRICES:
        open(os.path.join(DEFDIR, f"{api}.decisionMatrixDefinition-meta.xml"), "w").write(definition(api, label))
        open(os.path.join(VERDIR, f"{api}_V1.decisionMatrixVersion-meta.xml"), "w").write(version(api, label, cols, status))
        print(f"wrote {api} (status={status})")


if __name__ == "__main__":
    main()
