#!/usr/bin/env python3
"""Generate custom field metadata for the end-to-end Grow Lighting MN demo.

Adds input, output and lineage fields to the standard IndividualApplicationItem
(the application line item) and county / fuel type to Location.
"""
import os

ROOM_TYPES = [
    "Cannabis Flower Room", "Cannabis Veg Room",
    "Flowering Crops (Tomatoes/Peppers)", "Vegetative/Propagation Growth",
    "Microgreens", "Clone Room", "Combo Veg & Flower Cannabis Room",
]
DLC_TIERS = ["DLC Premium", "DLC Standard", "Non-DLC"]
FUEL_TYPES = ["Electric", "Gas", "Dual Fuel"]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.path.join(ROOT, "force-app", "main", "default", "objects")


def picklist_valueset(values):
    vals = "\n".join(
        f"""                <value>
                    <fullName>{v}</fullName>
                    <default>false</default>
                    <label>{v}</label>
                </value>""" for v in values
    )
    return f"""    <type>Picklist</type>
    <valueSet>
        <restricted>true</restricted>
        <valueSetDefinition>
            <sorted>false</sorted>
{vals}
        </valueSetDefinition>
    </valueSet>"""


def field(api, label, body, description, required=False):
    req = "    <required>true</required>\n" if required else ""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<CustomField xmlns="http://soap.sforce.com/2006/04/metadata">
    <fullName>{api}</fullName>
    <description>{description}</description>
    <label>{label}</label>
{req}{body}
</CustomField>
"""


def number(precision, scale):
    return f"""    <type>Number</type>
    <precision>{precision}</precision>
    <scale>{scale}</scale>"""


def currency(precision, scale):
    return f"""    <type>Currency</type>
    <precision>{precision}</precision>
    <scale>{scale}</scale>"""


def text(length):
    return f"""    <type>Text</type>
    <length>{length}</length>"""


def longtext(length, lines):
    return f"""    <type>LongTextArea</type>
    <length>{length}</length>
    <visibleLines>{lines}</visibleLines>"""


def date():
    return "    <type>Date</type>"


# (api, label, body, description)
IAITEM_FIELDS = [
    # --- customer inputs (M&V) ---
    ("Fixture_Quantity__c", "Fixture Quantity", number(9, 0), "Input: proposed fixture quantity (Qty)."),
    ("Market_Segment_Room_Type__c", "Market Segment / Room Type", picklist_valueset(ROOM_TYPES), "Input: room type; drives Hours, kWh factor and coincidence factor."),
    ("Proposed_PPF__c", "Proposed PPF (umol/s)", number(10, 2), "Input: proposed photosynthetic photon flux from fixture spec sheet (PPF)."),
    ("Proposed_Fixture_Watts__c", "Proposed Fixture Watts", number(10, 2), "Input: proposed fixture watts (Prop_Watts)."),
    ("DLC_Tier__c", "DLC Tier", picklist_valueset(DLC_TIERS), "Input: DesignLights Consortium tier."),
    ("Invoice_Date__c", "Invoice Date", date(), "Equipment purchase date; selects TRM reference versions."),
    # --- calculated outputs ---
    ("Electric_Rebate__c", "Electric Rebate", currency(16, 2), "Output: calculated electric rebate (incentive)."),
    ("Proposed_PPE__c", "Proposed PPE", number(10, 2), "Output: proposed photosynthetic photon efficacy (umol/J)."),
    ("Baseline_Watts__c", "Baseline Watts (derived)", number(10, 0), "Output: derived baseline fixture watts (Base_W)."),
    ("Customer_kW_Savings__c", "Customer kW Demand Savings", number(14, 4), "Output: customer kW demand savings."),
    ("Customer_kWh_Savings__c", "Customer kWh Energy Savings", number(16, 2), "Output: customer annual kWh energy savings."),
    ("Customer_Peak_Coincident_kW__c", "Customer Peak Coincident kW", number(14, 5), "Output: peak coincident kW savings."),
    ("Incremental_Cost__c", "Incremental Cost", currency(16, 2), "Output: estimated incremental cost of the LED upgrade."),
    # --- lineage / audit ---
    ("Technical_TRM_Version__c", "Technical TRM Version", text(80), "Lineage: Technical TRM reference version used."),
    ("Program_Factors_Version__c", "Program Factors Version", text(80), "Lineage: Program Factors reference version used."),
    ("Incentive_Rules_Version__c", "Incentive Rules Version", text(80), "Lineage: Incentive Rules reference version used."),
    ("Expression_Set_Version__c", "Expression Set Version", text(80), "Lineage: BRE Expression Set version used."),
    ("Calculation_Explainer__c", "Calculation Explainer", longtext(32768, 12), "Lineage: step-by-step explanation of the calculation."),
]

LOCATION_FIELDS = [
    ("County__c", "County", text(80), "County of the service address; maps to climate zone."),
    ("Customer_Fuel_Type__c", "Customer Fuel Type", picklist_valueset(FUEL_TYPES), "Customer fuel type at the premise."),
]


def write_fields(obj, fields):
    d = os.path.join(BASE, obj, "fields")
    os.makedirs(d, exist_ok=True)
    for api, label, body, desc in fields:
        with open(os.path.join(d, f"{api}.field-meta.xml"), "w") as f:
            f.write(field(api, label, body, desc))
    print(f"{obj}: wrote {len(fields)} fields")


if __name__ == "__main__":
    write_fields("IndividualApplicationItem", IAITEM_FIELDS)
    write_fields("Location", LOCATION_FIELDS)
