#!/usr/bin/env python3
"""Generate the after-save Flow that maps ALL calculated metrics (rebate + savings)
to the application as BenefitAssignments (Savings Store - Option A).

Per metric: Get the metric's Benefit (by Metric_Code__c) -> Create a BenefitAssignment
under the application, with the typed value in Calculated_Value__c. No Apex.
"""
import os

# (code, line field, unit, is_rebate)
METRICS = [
    ("ELECTRIC_REBATE", "Electric_Rebate__c", "USD", True),
    ("PROPOSED_PPE", "Proposed_PPE__c", "umol/J", False),
    ("BASELINE_WATTS", "Baseline_Watts__c", "W", False),
    ("INCREMENTAL_COST", "Incremental_Cost__c", "USD", False),
    ("CUSTOMER_KW", "Customer_kW_Savings__c", "kW", False),
    ("CUSTOMER_KWH", "Customer_kWh_Savings__c", "kWh", False),
    ("CUSTOMER_PCKW", "Customer_Peak_Coincident_kW__c", "kW", False),
    ("SM_KW_GEN", "SM_kW_Gen_PCkW__c", "kW", False),
    ("GROSS_PCKW_CUST", "Gross_Annual_PCkW_Customer__c", "kW", False),
    ("TOTAL_ONLY_NET_KW", "Total_Only_Net_kW_Customer_PCkW__c", "kW", False),
    ("TOTAL_NET_KW", "Total_Net_kW_Customer_PCkW__c", "kW", False),
    ("TOTAL_NET_PCKW_GEN", "Total_Net_PCkW_Gen__c", "kW", False),
    ("GROSS_KWH_CUST", "Gross_Annual_kWh_Customer__c", "kWh", False),
    ("PROG_NET_CUST_KWH", "Program_Net_Annual_Customer_kWh__c", "kWh", False),
    ("GEN_KWH", "Gen_kWh__c", "kWh", False),
    ("PROG_NET_GEN_KWH", "Program_Net_Annual_Generator_kWh__c", "kWh", False),
    ("LIFETIME_GEN_KWH", "Lifetime_Gen_kWh__c", "kWh", False),
    ("LIFETIME_NET_GEN_KWH", "Lifetime_Net_Gen_kWh__c", "kWh", False),
]


def get_benefit(code, product_ref, next_ref, y):
    return f"""    <recordLookups>
        <name>Get_Benefit_{code}</name>
        <label>Get Benefit {code}</label>
        <locationX>176</locationX>
        <locationY>{y}</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Create_BA_{code}</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Product2Id</field>
            <operator>EqualTo</operator>
            <value><elementReference>{product_ref}</elementReference></value>
        </filters>
        <filters>
            <field>Metric_Code__c</field>
            <operator>EqualTo</operator>
            <value><stringValue>{code}</stringValue></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>Benefit</object>
        <queriedFields>Id</queriedFields>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>"""


def create_ba(code, field, unit, is_rebate, next_ref, y):
    extra = ""
    if is_rebate:
        extra = f"""        <inputAssignments>
            <field>EntitlementAmount</field>
            <value><elementReference>$Record.{field}</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>TotalApprovedAmount</field>
            <value><elementReference>$Record.{field}</elementReference></value>
        </inputAssignments>
"""
    conn = f"<connector><targetReference>{next_ref}</targetReference></connector>" if next_ref else ""
    return f"""    <recordCreates>
        <name>Create_BA_{code}</name>
        <label>Create Benefit Assignment {code}</label>
        <locationX>176</locationX>
        <locationY>{y}</locationY>
        {conn}
        <inputAssignments>
            <field>BenefitId</field>
            <value><elementReference>Get_Benefit_{code}.Id</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Calculated_Value__c</field>
            <value><elementReference>$Record.{field}</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>EnrolleeId</field>
            <value><elementReference>Get_Application.AccountId</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Metric_Code__c</field>
            <value><stringValue>{code}</stringValue></value>
        </inputAssignments>
        <inputAssignments>
            <field>Metric_Unit__c</field>
            <value><stringValue>{unit}</stringValue></value>
        </inputAssignments>
        <inputAssignments>
            <field>ParentRecordId</field>
            <value><elementReference>$Record.IndividualApplicationId</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>ProgramEnrollmentId</field>
            <value><elementReference>Get_Enrollment.Id</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Status</field>
            <value><stringValue>Active</stringValue></value>
        </inputAssignments>
{extra}        <object>BenefitAssignment</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordCreates>"""


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "force-app", "main", "default", "flows",
                       "Grow_Lighting_MN_Create_Benefit_Assignment.flow-meta.xml")

    # setup lookups
    setup = f"""    <recordLookups>
        <name>Get_Program_Product</name>
        <label>Get Program Product</label>
        <locationX>176</locationX>
        <locationY>288</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Get_Application</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters><field>Id</field><operator>EqualTo</operator><value><elementReference>$Record.RelatedItemId</elementReference></value></filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>ProgramProduct</object>
        <queriedFields>Id</queriedFields>
        <queriedFields>ProductId</queriedFields>
        <queriedFields>ProgramId</queriedFields>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_Application</name>
        <label>Get Application</label>
        <locationX>176</locationX>
        <locationY>408</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Get_Enrollment</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters><field>Id</field><operator>EqualTo</operator><value><elementReference>$Record.IndividualApplicationId</elementReference></value></filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>IndividualApplication</object>
        <queriedFields>Id</queriedFields>
        <queriedFields>AccountId</queriedFields>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_Enrollment</name>
        <label>Get Program Enrollment</label>
        <locationX>176</locationX>
        <locationY>528</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Get_Benefit_{METRICS[0][0]}</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters><field>ProgramId</field><operator>EqualTo</operator><value><elementReference>Get_Program_Product.ProgramId</elementReference></value></filters>
        <filters><field>AccountId</field><operator>EqualTo</operator><value><elementReference>Get_Application.AccountId</elementReference></value></filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>ProgramEnrollment</object>
        <queriedFields>Id</queriedFields>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>"""

    gets, creates = [], []
    y = 700
    for i, (code, field, unit, is_rebate) in enumerate(METRICS):
        nxt = f"Get_Benefit_{METRICS[i+1][0]}" if i + 1 < len(METRICS) else None
        gets.append(get_benefit(code, "Get_Program_Product.ProductId", None, y))
        creates.append(create_ba(code, field, unit, is_rebate, nxt, y + 60))
        y += 120

    doc = f"""<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>62.0</apiVersion>
    <description>After-save: map all calculated metrics (rebate + savings) to the application as BenefitAssignments (Savings Store - Option A). One Benefit per metric; typed value in Calculated_Value__c.</description>
    <environments>Default</environments>
    <interviewLabel>Grow Lighting MN - Create Benefit Assignment {{!$Flow.CurrentDateTime}}</interviewLabel>
    <label>Grow Lighting MN - Create Benefit Assignment</label>
    <processMetadataValues><name>BuilderType</name><value><stringValue>LightningFlowBuilder</stringValue></value></processMetadataValues>
    <processType>AutoLaunchedFlow</processType>
{chr(10).join(creates)}
{setup}
{chr(10).join(gets)}
    <start>
        <locationX>50</locationX>
        <locationY>0</locationY>
        <connector><targetReference>Get_Program_Product</targetReference></connector>
        <filterLogic>and</filterLogic>
        <filters><field>Electric_Rebate__c</field><operator>IsNull</operator><value><booleanValue>false</booleanValue></value></filters>
        <filters><field>RelatedItemId</field><operator>IsNull</operator><value><booleanValue>false</booleanValue></value></filters>
        <object>IndividualApplicationItem</object>
        <recordTriggerType>Create</recordTriggerType>
        <triggerType>RecordAfterSave</triggerType>
    </start>
    <status>Active</status>
</Flow>
"""
    with open(out, "w") as f:
        f.write(doc)
    print("wrote", out, "with", len(METRICS), "metric benefit-assignments")


if __name__ == "__main__":
    main()
