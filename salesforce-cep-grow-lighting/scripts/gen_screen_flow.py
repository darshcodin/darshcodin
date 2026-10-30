#!/usr/bin/env python3
"""Generate the guided Screen Flow 'Grow Lighting MN - Rebate Application'.

Captures the measure inputs, creates the IndividualApplication + line item (which
fire the before/after-save flows that calculate and award the rebate), then shows
the results. Reuses the same calculation — no duplicated logic.
"""
import os

ROOM_TYPES = [
    "Cannabis Flower Room", "Cannabis Veg Room",
    "Flowering Crops (Tomatoes/Peppers)", "Vegetative/Propagation Growth",
    "Microgreens", "Clone Room", "Combo Veg & Flower Cannabis Room",
]
DLC_TIERS = ["DLC Premium", "DLC Standard", "Non-DLC"]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def choice(name, val):
    return f"""    <choices>
        <name>{name}</name>
        <choiceText>{esc(val)}</choiceText>
        <dataType>String</dataType>
        <value><stringValue>{esc(val)}</stringValue></value>
    </choices>"""


def choice_name(prefix, i):
    return f"{prefix}_{i}"


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "force-app", "main", "default", "flows",
                       "Grow_Lighting_MN_Rebate_Application.flow-meta.xml")

    room_choices = [choice_name("chRoom", i) for i in range(len(ROOM_TYPES))]
    dlc_choices = [choice_name("chDlc", i) for i in range(len(DLC_TIERS))]
    choices_xml = "\n".join(
        [choice(n, v) for n, v in zip(room_choices, ROOM_TYPES)] +
        [choice(n, v) for n, v in zip(dlc_choices, DLC_TIERS)]
    )
    room_refs = "\n".join(f"            <choiceReferences>{c}</choiceReferences>" for c in room_choices)
    dlc_refs = "\n".join(f"            <choiceReferences>{c}</choiceReferences>" for c in dlc_choices)

    results_text = esc(
        "<b>Rebate and Savings - {!Get_Item.Name}</b><br/><br/>"
        "Electric Rebate (incentive): <b>${!Get_Item.Electric_Rebate__c}</b><br/>"
        "Proposed PPE: {!Get_Item.Proposed_PPE__c} umol/J<br/>"
        "Baseline Watts (derived): {!Get_Item.Baseline_Watts__c} W<br/>"
        "Customer kW Demand Savings: {!Get_Item.Customer_kW_Savings__c} kW<br/>"
        "Customer kWh Energy Savings: {!Get_Item.Customer_kWh_Savings__c} kWh/yr<br/>"
        "Peak Coincident kW: {!Get_Item.Customer_Peak_Coincident_kW__c} kW<br/>"
        "Incremental Cost: ${!Get_Item.Incremental_Cost__c}<br/><br/>"
        "Versions: {!Get_Item.Technical_TRM_Version__c} / "
        "{!Get_Item.Program_Factors_Version__c} / {!Get_Item.Incentive_Rules_Version__c}<br/><br/>"
        "<b>18 Benefit Assignments</b> (rebate + all savings metrics) were created on the "
        "application. <a href=\"/{!Create_Application}\" target=\"_blank\">Open the Application "
        "to view Benefit Assignments</a>."
    )

    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
{choices_xml}
    <description>Guided Grow Lighting MN rebate application: capture inputs, create the application and line (which calculate and award the rebate), then show results.</description>
    <environments>Default</environments>
    <interviewLabel>Grow Lighting MN - Rebate Application {{!$Flow.CurrentDateTime}}</interviewLabel>
    <label>Grow Lighting MN - Rebate Application</label>
    <processMetadataValues>
        <name>BuilderType</name>
        <value><stringValue>LightningFlowBuilder</stringValue></value>
    </processMetadataValues>
    <processType>Flow</processType>
    <recordCreates>
        <name>Create_Application</name>
        <label>Create Application</label>
        <locationX>176</locationX>
        <locationY>518</locationY>
        <connector><targetReference>Create_Item</targetReference></connector>
        <inputAssignments>
            <field>AccountId</field>
            <value><elementReference>Get_Account.Id</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Category</field>
            <value><stringValue>Program</stringValue></value>
        </inputAssignments>
        <inputAssignments>
            <field>Status</field>
            <value><stringValue>In Progress</stringValue></value>
        </inputAssignments>
        <object>IndividualApplication</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordCreates>
    <recordCreates>
        <name>Create_Item</name>
        <label>Create Application Line</label>
        <locationX>176</locationX>
        <locationY>638</locationY>
        <connector><targetReference>Get_Item</targetReference></connector>
        <inputAssignments>
            <field>DLC_Tier__c</field>
            <value><elementReference>in_DLC_Tier</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Fixture_Quantity__c</field>
            <value><elementReference>in_Quantity</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>IndividualApplicationId</field>
            <value><elementReference>Create_Application</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Invoice_Date__c</field>
            <value><elementReference>in_Invoice_Date</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Market_Segment_Room_Type__c</field>
            <value><elementReference>in_Room_Type</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Name</field>
            <value><stringValue>LED Grow Fixture MN v2</stringValue></value>
        </inputAssignments>
        <inputAssignments>
            <field>Proposed_Fixture_Watts__c</field>
            <value><elementReference>in_Fixture_Watts</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Proposed_PPF__c</field>
            <value><elementReference>in_PPF</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>RelatedItemId</field>
            <value><elementReference>Get_Program_Product.Id</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Status</field>
            <value><stringValue>Pending</stringValue></value>
        </inputAssignments>
        <object>IndividualApplicationItem</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordCreates>
    <recordLookups>
        <name>Get_Account</name>
        <label>Get Demo Account</label>
        <locationX>176</locationX>
        <locationY>158</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Get_Program_Product</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Name</field>
            <operator>EqualTo</operator>
            <value><stringValue>Green Valley Growers</stringValue></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>Account</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_Item</name>
        <label>Get Calculated Line</label>
        <locationX>176</locationX>
        <locationY>758</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Screen_Results</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Id</field>
            <operator>EqualTo</operator>
            <value><elementReference>Create_Item</elementReference></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>IndividualApplicationItem</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_Product</name>
        <label>Get Product</label>
        <locationX>176</locationX>
        <locationY>50</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Get_Account</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Name</field>
            <operator>EqualTo</operator>
            <value><stringValue>MN - Lighting Efficiency Rebate</stringValue></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>Product2</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_Program_Product</name>
        <label>Get Program Product</label>
        <locationX>176</locationX>
        <locationY>278</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Screen_Inputs</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>ProductId</field>
            <operator>EqualTo</operator>
            <value><elementReference>Get_Product.Id</elementReference></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>ProgramProduct</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <screens>
        <name>Screen_Inputs</name>
        <label>Measure Inputs</label>
        <locationX>176</locationX>
        <locationY>398</locationY>
        <allowBack>true</allowBack>
        <allowFinish>true</allowFinish>
        <allowPause>false</allowPause>
        <connector><targetReference>Create_Application</targetReference></connector>
        <fields>
            <name>in_Quantity</name>
            <dataType>Number</dataType>
            <fieldText>Fixture Quantity</fieldText>
            <fieldType>InputField</fieldType>
            <isRequired>true</isRequired>
            <scale>0</scale>
        </fields>
        <fields>
            <name>in_Room_Type</name>
{room_refs}
            <dataType>String</dataType>
            <fieldText>Market Segment / Room Type</fieldText>
            <fieldType>DropdownBox</fieldType>
            <isRequired>true</isRequired>
        </fields>
        <fields>
            <name>in_PPF</name>
            <dataType>Number</dataType>
            <fieldText>Proposed PPF (umol/s)</fieldText>
            <fieldType>InputField</fieldType>
            <isRequired>true</isRequired>
            <scale>2</scale>
        </fields>
        <fields>
            <name>in_Fixture_Watts</name>
            <dataType>Number</dataType>
            <fieldText>Proposed Fixture Watts</fieldText>
            <fieldType>InputField</fieldType>
            <isRequired>true</isRequired>
            <scale>2</scale>
        </fields>
        <fields>
            <name>in_DLC_Tier</name>
{dlc_refs}
            <dataType>String</dataType>
            <fieldText>DLC Tier</fieldText>
            <fieldType>DropdownBox</fieldType>
            <isRequired>true</isRequired>
        </fields>
        <fields>
            <name>in_Invoice_Date</name>
            <dataType>Date</dataType>
            <fieldText>Invoice Date</fieldText>
            <fieldType>InputField</fieldType>
            <isRequired>true</isRequired>
        </fields>
        <showFooter>true</showFooter>
        <showHeader>true</showHeader>
    </screens>
    <screens>
        <name>Screen_Results</name>
        <label>Rebate and Savings</label>
        <locationX>176</locationX>
        <locationY>878</locationY>
        <allowBack>false</allowBack>
        <allowFinish>true</allowFinish>
        <allowPause>false</allowPause>
        <fields>
            <name>dispResults</name>
            <fieldText>{results_text}</fieldText>
            <fieldType>DisplayText</fieldType>
        </fields>
        <showFooter>true</showFooter>
        <showHeader>true</showHeader>
    </screens>
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector><targetReference>Get_Product</targetReference></connector>
    </start>
    <status>Active</status>
</Flow>
"""
    with open(out, "w") as f:
        f.write(doc)
    print("wrote", out)


if __name__ == "__main__":
    main()
