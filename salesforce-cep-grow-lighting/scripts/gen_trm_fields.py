#!/usr/bin/env python3
"""Generate fields for TRM reference data + the 11 dependent DSM metrics, and
regenerate FLS (admin profile + permission set) covering ALL custom fields.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "force-app", "main", "default", "objects")


def num(p, s):
    return f"    <type>Number</type>\n    <precision>{p}</precision>\n    <scale>{s}</scale>"


def text(n):
    return f"    <type>Text</type>\n    <length>{n}</length>"


def lookup(ref, rlabel, rname):
    return (f"    <type>Lookup</type>\n    <referenceTo>{ref}</referenceTo>\n"
            f"    <relationshipLabel>{rlabel}</relationshipLabel>\n"
            f"    <relationshipName>{rname}</relationshipName>")


def field(api, label, body, desc):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{api}</fullName>
    <description>{desc}</description>
    <label>{label}</label>
{body}
</CustomField>
"""


# (api,label,body,desc)
IAITEM_DEP = [
    ("SM_kW_Gen_PCkW__c", "SM kW Gen (PCkW)", num(14, 5), "Dependent: single-measure generator-level demand savings."),
    ("Gross_Annual_PCkW_Customer__c", "Gross Annual PCkW at Customer", num(14, 5), "Dependent: program-total coincident demand at customer meter."),
    ("Total_Only_Net_kW_Customer_PCkW__c", "Total Only Net kW Cust (PCkW)", num(14, 5), "Dependent: excludes spillover; direct participants only."),
    ("Total_Net_kW_Customer_PCkW__c", "Total Net kW Cust (PCkW)", num(14, 5), "Dependent: includes market spillover effects."),
    ("Total_Net_PCkW_Gen__c", "Total Net PCkW at Gen", num(14, 5), "Dependent: net demand at generator source."),
    ("Gross_Annual_kWh_Customer__c", "Gross Annual kWh at Customer", num(16, 2), "Dependent: gross annual energy savings at customer."),
    ("Program_Net_Annual_Customer_kWh__c", "Program Net Annual Cust kWh", num(16, 2), "Dependent: net annual energy savings at customer."),
    ("Gen_kWh__c", "Gen Electric DSM kWh", num(16, 2), "Dependent: single-measure generator kWh (cooling only)."),
    ("Program_Net_Annual_Generator_kWh__c", "Program Net Annual Gen kWh", num(16, 2), "Dependent: program net savings at generator level."),
    ("Lifetime_Gen_kWh__c", "Lifetime Gen Electric DSM kWh", num(18, 2), "Dependent: full-life generator savings (gross)."),
    ("Lifetime_Net_Gen_kWh__c", "Lifetime Net Gen DSM kWh", num(18, 2), "Dependent: full-life generator savings (net)."),
]
IAITEM_FACTORS = [
    ("TD_Loss_Factor_Used__c", "T&D Loss Factor (used)", num(8, 4), "Lineage: T&D loss factor applied from the TRM version."),
    ("NTG_Only_Used__c", "NTG Only (used)", num(8, 4), "Lineage: net-to-gross (direct participants) applied."),
    ("NTG_Total_Used__c", "NTG Total (used)", num(8, 4), "Lineage: net-to-gross (incl. spillover) applied."),
    ("Measure_Life_Used__c", "Measure Life (used)", num(6, 1), "Lineage: measure life (years) applied."),
    ("Participants_Used__c", "Participants (used)", num(10, 0), "Lineage: participant count applied (1 per application line)."),
]
VERSION_FIELDS = [
    ("Version_Label__c", "Version Label", text(80), "TRM version label stamped on calculated lines."),
    ("TD_Loss_Factor__c", "T&D Loss Factor", num(8, 4), "Flat factor: transmission and distribution loss factor."),
    ("NTG_Only__c", "NTG Only", num(8, 4), "Flat factor: net-to-gross, direct participants only."),
    ("NTG_Total__c", "NTG Total", num(8, 4), "Flat factor: net-to-gross, includes spillover."),
    ("Measure_Life_Years__c", "Measure Life (Years)", num(6, 1), "Flat factor: measure life in years."),
]
GROUP_FIELDS = [
    ("Product__c", "Product", lookup("Product2", "Usage Impact Groups", "Usage_Impact_Groups"), "Measure product this technical TRM group covers."),
]


def write(obj, fields):
    d = os.path.join(BASE, obj, "fields")
    os.makedirs(d, exist_ok=True)
    for api, label, body, desc in fields:
        open(os.path.join(d, f"{api}.field-meta.xml"), "w").write(field(api, label, body, desc))
    print(f"{obj}: +{len(fields)} fields")


def all_custom_fields():
    """Every custom field across the objects, for FLS."""
    import glob
    out = []
    for path in sorted(glob.glob(os.path.join(BASE, "*", "fields", "*.field-meta.xml"))):
        obj = path.split(os.sep)[-3]
        api = os.path.basename(path).replace(".field-meta.xml", "")
        out.append(f"{obj}.{api}")
    return out


def fls_block(fields):
    return "\n".join(f"""    <fieldPermissions>
        <editable>true</editable>
        <field>{f}</field>
        <readable>true</readable>
    </fieldPermissions>""" for f in fields)


def main():
    write("IndividualApplicationItem", IAITEM_DEP + IAITEM_FACTORS)
    write("UsageImpactGroupVersion", VERSION_FIELDS)
    write("UsageImpactGroup", GROUP_FIELDS)

    fields = all_custom_fields()
    body = fls_block(fields)
    open(os.path.join(os.path.dirname(BASE), "profiles", "Admin.profile-meta.xml"), "w").write(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
{body}
</Profile>
""")
    open(os.path.join(os.path.dirname(BASE), "permissionsets", "CEP_Grow_Lighting_Calculator.permissionset-meta.xml"), "w").write(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>CEP Grow Lighting Calculator</label>
    <description>Field access for the Grow Lighting MN rebate calculator (inputs, outputs, dependent metrics, TRM, lineage).</description>
    <hasActivationRequired>false</hasActivationRequired>
{body}
</PermissionSet>
""")
    print(f"FLS regenerated for {len(fields)} custom fields")


if __name__ == "__main__":
    main()
