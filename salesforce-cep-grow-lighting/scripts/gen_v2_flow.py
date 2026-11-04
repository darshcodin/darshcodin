#!/usr/bin/env python3
"""Generate CEP_Calculate_Line: the orchestration flow.

 1 Get the line's ProgramProduct  -> Program + Product
 2 Get Program Measure rows for that Program + Product
 3 Collect their version ids, then read the versions whose window covers the invoice date
 4 Route each version by its group's Version Role -> Technical TRM / Program Factors / Incentive Rules
 5 Stamp the three version lookups on the line (this is what the Context Service traverses)
 6 buildContext -> one payload for the line
 7..9 Savings / Incentive / Reporting, each selected by the pattern named on the technical version
 10 Store results plus the expression-set reference fields
"""
import os, html

SEGMENTS = [
    ("Cannabis Flower Room", 4255, 1.16, 0.68),
    ("Cannabis Veg Room", 6498, 1.24, 0.89),
    ("Flowering Crops (Tomatoes/Peppers)", 4200, 1.21, 0.76),
    ("Vegetative/Propagation Growth", 6300, 1.21, 0.95),
    ("Microgreens", 6300, 1.21, 0.95),
    ("Clone Room", 6300, 1.21, 0.95),
    ("Combo Veg & Flower Cannabis Room", 5281, 1.20, 0.78),
]
SEG = "{!$Record.Market_Segment_Room_Type__c}"
QTY = "{!$Record.Fixture_Quantity__c}"
PPF = "{!$Record.Proposed_PPF__c}"
WATT = "{!$Record.Proposed_Fixture_Watts__c}"
T = "{!vTechVer."      # technical version record var
P = "{!vPFVer."        # program factors
I = "{!vIRVer."        # incentive rules


def case(idx):
    arms = "".join(f', "{s[0]}", {s[idx]}' for s in SEGMENTS)
    return f"CASE({SEG}{arms}, 0)"


# ---- formula resources (name, scale, expression, dataType)
FORMULAS = [
    # savings layer - mirrors P2_EffDelta step for step
    ("fEfficacy", 2, f"ROUND({PPF} / {WATT}, 2)"),
    ("fBaseline", 0, f"ROUND(({WATT} * {T}Prop_Reflector_Eff__c}} * {{!fEfficacy}}) / ({T}Base_Reflector_Eff__c}} * {T}Baseline_Efficacy__c}}), 0)"),
    ("fDelta", 6, f"({{!fBaseline}} - {WATT}) / 1000"),
    ("fHours", 0, case(1)),
    ("fKWhFactor", 4, case(2)),
    ("fCF", 4, case(3)),
    ("fGrossKW", 4, f"{{!fDelta}} * {T}Cooling_Factor__c}} * {QTY}"),
    ("fGrossKWh", 2, f"{{!fDelta}} * {QTY} * {{!fKWhFactor}} * {{!fHours}}"),
    ("fGrossPCkW", 5, f"ROUND({{!fDelta}} * {T}Cooling_Factor__c}} * {QTY}, 3) * {{!fCF}}"),
    ("fMeasureQty", 2, f"{QTY} * {WATT}"),
    # incentive layer - mirrors I2_PerUnitBonus
    ("fBaseIncentive", 2, f"{{!fMeasureQty}} * ROUND({I}Rebate_Rate_Per_Unit__c}} * {I}Bonus_Multiplier__c}}, 2)"),
    ("fIncentive", 2, f"IF(AND(NOT(ISBLANK({I}Max_Incentive__c}})), {I}Max_Incentive__c}} > 0, {{!fBaseIncentive}} > {I}Max_Incentive__c}}), {I}Max_Incentive__c}}, {{!fBaseIncentive}})"),
    ("fIncCost", 2, f"{{!fMeasureQty}} * {I}Inc_Cost_Per_Unit__c}}"),
    # reporting layer - mirrors R1_StdReporting, measure agnostic
    ("fSMkWGen", 5, f"{{!fGrossPCkW}} * {P}TD_Loss_Factor__c}}"),
    ("fGrossPCkWCust", 5, "{!fGrossPCkW} * {!vParticipants}"),
    ("fTotOnlyNetKW", 5, f"({{!fGrossPCkW}} * {{!vParticipants}}) * {P}NTG_Only__c}}"),
    ("fTotNetKW", 5, f"({{!fGrossPCkW}} * {{!vParticipants}}) * {P}NTG_Total__c}}"),
    ("fTotNetPCkWGen", 5, f"(({{!fGrossPCkW}} * {{!vParticipants}}) * {P}NTG_Total__c}}) * {P}TD_Loss_Factor__c}}"),
    ("fGrossKWhCust", 2, "{!fGrossKWh} * {!vParticipants}"),
    ("fProgNetCustKWh", 2, f"({{!fGrossKWh}} * {{!vParticipants}}) * {P}NTG_Total__c}}"),
    ("fGenKWh", 2, f"{{!fGrossKWh}} * {P}TD_Loss_Factor__c}}"),
    ("fProgNetGenKWh", 2, f"(({{!fGrossKWh}} * {{!vParticipants}}) * {P}NTG_Total__c}}) * {P}TD_Loss_Factor__c}}"),
    ("fLifeGenKWh", 2, f"({{!fGrossKWh}} * {P}TD_Loss_Factor__c}}) * {P}Measure_Life_Years__c}}"),
    ("fLifeNetGenKWh", 2, f"((({{!fGrossKWh}} * {{!vParticipants}}) * {P}NTG_Total__c}}) * {P}TD_Loss_Factor__c}}) * {P}Measure_Life_Years__c}}"),
]

# ---- final assignment: line field  <-  source
RESULT_MAP = [
    # shared output contract
    ("Gross_kW__c", "fGrossKW"), ("Gross_kWh__c", "fGrossKWh"),
    ("Gross_PCkW__c", "fGrossPCkW"), ("Gross_Therms__c", None),
    ("Measure_Quantity__c", "fMeasureQty"),
    # savings detail
    ("Proposed_PPE__c", "fEfficacy"), ("Baseline_Watts__c", "fBaseline"),
    ("Customer_kW_Savings__c", "fGrossKW"), ("Customer_kWh_Savings__c", "fGrossKWh"),
    ("Customer_Peak_Coincident_kW__c", "fGrossPCkW"),
    # incentive
    ("Electric_Rebate__c", "fIncentive"), ("Incremental_Cost__c", "fIncCost"),
    # reporting
    ("SM_kW_Gen_PCkW__c", "fSMkWGen"),
    ("Gross_Annual_PCkW_Customer__c", "fGrossPCkWCust"),
    ("Total_Only_Net_kW_Customer_PCkW__c", "fTotOnlyNetKW"),
    ("Total_Net_kW_Customer_PCkW__c", "fTotNetKW"),
    ("Total_Net_PCkW_Gen__c", "fTotNetPCkWGen"),
    ("Gross_Annual_kWh_Customer__c", "fGrossKWhCust"),
    ("Program_Net_Annual_Customer_kWh__c", "fProgNetCustKWh"),
    ("Gen_kWh__c", "fGenKWh"),
    ("Program_Net_Annual_Generator_kWh__c", "fProgNetGenKWh"),
    ("Lifetime_Gen_kWh__c", "fLifeGenKWh"),
    ("Lifetime_Net_Gen_kWh__c", "fLifeNetGenKWh"),
]

# factors actually applied, snapshotted for audit
FACTOR_MAP = [
    ("TD_Loss_Factor_Used__c", "vPFVer.TD_Loss_Factor__c"),
    ("NTG_Only_Used__c", "vPFVer.NTG_Only__c"),
    ("NTG_Total_Used__c", "vPFVer.NTG_Total__c"),
    ("Measure_Life_Used__c", "vPFVer.Measure_Life_Years__c"),
    ("Technical_TRM_Version__c", "vTechVer.Version_Label__c"),
    ("Program_Factors_Version__c", "vPFVer.Version_Label__c"),
    ("Incentive_Rules_Version__c", "vIRVer.Version_Label__c"),
    ("Savings_Expression_Set__c", "vTechVer.CalcPattern__c"),
    ("Incentive_Expression_Set__c", "vTechVer.Incentive_Pattern__c"),
    ("Reporting_Expression_Set__c", "vTechVer.Reporting_Pattern__c"),
    ("Calc_Pattern_Used__c", "vTechVer.CalcPattern__c"),
]


ACTION_CALLS = r'''    <actionCalls>
        <name>Build_Context</name>
        <label>8a Build Context</label>
        <locationX>176</locationX><locationY>1238</locationY>
        <actionName>buildContext</actionName>
        <actionType>buildContext</actionType>
        <connector><targetReference>Store_Results</targetReference></connector>
        <faultConnector><targetReference>Store_Results</targetReference></faultConnector>
        <flowTransactionModel>CurrentTransaction</flowTransactionModel>
        <inputParameters>
            <name>contextDefinitionId</name>
            <value><elementReference>Get_Context_Definition.Id</elementReference></value>
        </inputParameters>
        <inputParameters>
            <name>contextData</name>
            <value><elementReference>fContextData</elementReference></value>
        </inputParameters>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </actionCalls>'''
ASSIGNMENTS = r'''    <assignments>
        <name>Collect_Version_Id</name>
        <label>3a Collect Version Id</label>
        <locationX>352</locationX><locationY>518</locationY>
        <assignmentItems>
            <assignToReference>vVersionIds</assignToReference>
            <operator>Add</operator>
            <value><elementReference>Loop_Measures.UsageImpactGroupVersionId</elementReference></value>
        </assignmentItems>
        <connector><targetReference>Loop_Measures</targetReference></connector>
    </assignments>
    <assignments>
        <name>Set_Technical</name>
        <label>5b Set Technical Version</label>
        <locationX>528</locationX><locationY>698</locationY>
{ai("vTechVer", el="Loop_Versions")}
        <connector><targetReference>Loop_Versions</targetReference></connector>
    </assignments>
    <assignments>
        <name>Set_Program_Factors</name>
        <label>5c Set Program Factors Version</label>
        <locationX>528</locationX><locationY>778</locationY>
{ai("vPFVer", el="Loop_Versions")}
        <connector><targetReference>Loop_Versions</targetReference></connector>
    </assignments>
    <assignments>
        <name>Set_Incentive_Rules</name>
        <label>5d Set Incentive Rules Version</label>
        <locationX>528</locationX><locationY>858</locationY>
{ai("vIRVer", el="Loop_Versions")}
        <connector><targetReference>Loop_Versions</targetReference></connector>
    </assignments>
    <assignments>
        <name>Store_Results</name>
        <label>9 Compute and Stage Results</label>
        <locationX>176</locationX><locationY>1358</locationY>
@@RES@@
        <connector><targetReference>Commit_Results</targetReference></connector>
    </assignments>'''
DECISIONS = r'''    <decisions>
        <name>Route_By_Role</name>
        <label>5a Route By Version Role</label>
        <locationX>352</locationX><locationY>758</locationY>
        <defaultConnector><targetReference>Loop_Versions</targetReference></defaultConnector>
        <defaultConnectorLabel>Other</defaultConnectorLabel>
        <rules>
            <name>Is_Technical</name>
            <conditionLogic>and</conditionLogic>
            <conditions>
                <leftValueReference>Loop_Versions.UsageImpactGroup.Version_Role__c</leftValueReference>
                <operator>EqualTo</operator>
                <rightValue><stringValue>Technical TRM</stringValue></rightValue>
            </conditions>
            <connector><targetReference>Set_Technical</targetReference></connector>
            <label>Technical TRM</label>
        </rules>
        <rules>
            <name>Is_Program_Factors</name>
            <conditionLogic>and</conditionLogic>
            <conditions>
                <leftValueReference>Loop_Versions.UsageImpactGroup.Version_Role__c</leftValueReference>
                <operator>EqualTo</operator>
                <rightValue><stringValue>Program Factors</stringValue></rightValue>
            </conditions>
            <connector><targetReference>Set_Program_Factors</targetReference></connector>
            <label>Program Factors</label>
        </rules>
        <rules>
            <name>Is_Incentive_Rules</name>
            <conditionLogic>and</conditionLogic>
            <conditions>
                <leftValueReference>Loop_Versions.UsageImpactGroup.Version_Role__c</leftValueReference>
                <operator>EqualTo</operator>
                <rightValue><stringValue>Incentive Rules</stringValue></rightValue>
            </conditions>
            <connector><targetReference>Set_Incentive_Rules</targetReference></connector>
            <label>Incentive Rules</label>
        </rules>
    </decisions>
    <decisions>
        <name>Check_All_Three_Found</name>
        <label>6 All Three Versions Found</label>
        <locationX>176</locationX><locationY>878</locationY>
        <defaultConnector><targetReference>Mark_Failed_No_Version</targetReference></defaultConnector>
        <defaultConnectorLabel>Missing a version</defaultConnectorLabel>
        <rules>
            <name>All_Found</name>
            <conditionLogic>and</conditionLogic>
            <conditions>
                <leftValueReference>vTechVer.Id</leftValueReference>
                <operator>IsNull</operator>
                <rightValue><booleanValue>false</booleanValue></rightValue>
            </conditions>
            <conditions>
                <leftValueReference>vPFVer.Id</leftValueReference>
                <operator>IsNull</operator>
                <rightValue><booleanValue>false</booleanValue></rightValue>
            </conditions>
            <conditions>
                <leftValueReference>vIRVer.Id</leftValueReference>
                <operator>IsNull</operator>
                <rightValue><booleanValue>false</booleanValue></rightValue>
            </conditions>
            <connector><targetReference>Stamp_Version_Refs</targetReference></connector>
            <label>All three found</label>
        </rules>
    </decisions>'''
LOOPS = r'''    <loops>
        <name>Loop_Measures</name>
        <label>3 Loop Program Measures</label>
        <locationX>176</locationX><locationY>518</locationY>
        <collectionReference>Get_Program_Measures</collectionReference>
        <iterationOrder>Asc</iterationOrder>
        <nextValueConnector><targetReference>Collect_Version_Id</targetReference></nextValueConnector>
        <noMoreValuesConnector><targetReference>Get_Versions</targetReference></noMoreValuesConnector>
    </loops>
    <loops>
        <name>Loop_Versions</name>
        <label>5 Loop Versions</label>
        <locationX>176</locationX><locationY>758</locationY>
        <collectionReference>Get_Versions</collectionReference>
        <iterationOrder>Asc</iterationOrder>
        <nextValueConnector><targetReference>Route_By_Role</targetReference></nextValueConnector>
        <noMoreValuesConnector><targetReference>Check_All_Three_Found</targetReference></noMoreValuesConnector>
    </loops>'''
RECORD_LOOKUPS = r'''    <recordLookups>
        <name>Get_Program_Product</name>
        <label>1 Get Program Product</label>
        <locationX>176</locationX><locationY>278</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Get_Program_Measures</targetReference></connector>
        <faultConnector><targetReference>Mark_Failed</targetReference></faultConnector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Id</field><operator>EqualTo</operator>
            <value><elementReference>$Record.Program_Product__c</elementReference></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>ProgramProduct</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_Program_Measures</name>
        <label>2 Get Program Measures</label>
        <locationX>176</locationX><locationY>398</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Loop_Measures</targetReference></connector>
        <faultConnector><targetReference>Mark_Failed</targetReference></faultConnector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>ProgramId</field><operator>EqualTo</operator>
            <value><elementReference>Get_Program_Product.ProgramId</elementReference></value>
        </filters>
        <filters>
            <field>Product2Id</field><operator>EqualTo</operator>
            <value><elementReference>Get_Program_Product.ProductId</elementReference></value>
        </filters>
        <getFirstRecordOnly>false</getFirstRecordOnly>
        <object>UsageImpactGroupPgmMeasure</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_Versions</name>
        <label>4 Get Versions Covering Invoice Date</label>
        <locationX>176</locationX><locationY>638</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Loop_Versions</targetReference></connector>
        <faultConnector><targetReference>Mark_Failed</targetReference></faultConnector>
        <filterLogic>1 AND 2 AND 3 AND (4 OR 5)</filterLogic>
        <filters>
            <field>Id</field><operator>In</operator>
            <value><elementReference>vVersionIds</elementReference></value>
        </filters>
        <filters>
            <field>IsActive</field><operator>EqualTo</operator>
            <value><booleanValue>true</booleanValue></value>
        </filters>
        <filters>
            <field>StartDate</field><operator>LessThanOrEqualTo</operator>
            <value><elementReference>$Record.Invoice_Date__c</elementReference></value>
        </filters>
        <filters>
            <field>EndDate</field><operator>GreaterThanOrEqualTo</operator>
            <value><elementReference>$Record.Invoice_Date__c</elementReference></value>
        </filters>
        <filters>
            <field>EndDate</field><operator>IsNull</operator>
            <value><booleanValue>true</booleanValue></value>
        </filters>
        <getFirstRecordOnly>false</getFirstRecordOnly>
        <object>UsageImpactGroupVersion</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>
    <recordLookups>
        <name>Get_Context_Definition</name>
        <label>8 Get Context Definition</label>
        <locationX>176</locationX><locationY>1118</locationY>
        <assignNullValuesIfNoRecordsFound>false</assignNullValuesIfNoRecordsFound>
        <connector><targetReference>Build_Context</targetReference></connector>
        <faultConnector><targetReference>Store_Results</targetReference></faultConnector>
        <filterLogic>and</filterLogic>
        <filters>
            <field>DeveloperName</field><operator>EqualTo</operator>
            <value><stringValue>CEP_Line_Calc_Context</stringValue></value>
        </filters>
        <getFirstRecordOnly>true</getFirstRecordOnly>
        <object>ContextDefinition</object>
        <storeOutputAutomatically>true</storeOutputAutomatically>
    </recordLookups>'''
RECORD_UPDATES = r'''    <recordUpdates>
        <name>Stamp_Version_Refs</name>
        <label>7 Stamp Version References</label>
        <locationX>176</locationX><locationY>998</locationY>
        <connector><targetReference>Get_Context_Definition</targetReference></connector>
        <faultConnector><targetReference>Mark_Failed</targetReference></faultConnector>
        <inputAssignments>
            <field>Technical_Version__c</field>
            <value><elementReference>vTechVer.Id</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Program_Factors_Version_Ref__c</field>
            <value><elementReference>vPFVer.Id</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Incentive_Rules_Version_Ref__c</field>
            <value><elementReference>vIRVer.Id</elementReference></value>
        </inputAssignments>
        <inputAssignments>
            <field>Calculation_Status__c</field>
            <value><stringValue>Calculated</stringValue></value>
        </inputAssignments>
        <inputReference>$Record</inputReference>
    </recordUpdates>
    <recordUpdates>
        <name>Commit_Results</name>
        <label>10 Store Results on the Line</label>
        <locationX>176</locationX><locationY>1478</locationY>
        <faultConnector><targetReference>Mark_Failed</targetReference></faultConnector>
        <inputReference>$Record</inputReference>
    </recordUpdates>
    <recordUpdates>
        <name>Mark_Failed</name>
        <label>Mark Failed</label>
        <locationX>528</locationX><locationY>1478</locationY>
        <inputAssignments>
            <field>Calculation_Status__c</field>
            <value><stringValue>Failed</stringValue></value>
        </inputAssignments>
        <inputAssignments>
            <field>Calculation_Error__c</field>
            <value><elementReference>$Flow.FaultMessage</elementReference></value>
        </inputAssignments>
        <inputReference>$Record</inputReference>
    </recordUpdates>
    <recordUpdates>
        <name>Mark_Failed_No_Version</name>
        <label>Mark Failed No Version</label>
        <locationX>352</locationX><locationY>878</locationY>
        <inputAssignments>
            <field>Calculation_Status__c</field>
            <value><stringValue>Failed</stringValue></value>
        </inputAssignments>
        <inputAssignments>
            <field>Calculation_Error__c</field>
            <value><stringValue>No Technical TRM, Program Factors or Incentive Rules version covers the invoice date for this Program and Product.</stringValue></value>
        </inputAssignments>
        <inputReference>$Record</inputReference>
    </recordUpdates>'''
CONTEXT_FORMULA = """    <formulas>
        <name>fContextData</name>
        <dataType>String</dataType>
        <expression>'{"IndividualApplicationItem":[{"id":"' &amp; {!$Record.Id} &amp; '"}]}'</expression>
    </formulas>"""
START = """    <start>
        <locationX>50</locationX><locationY>50</locationY>
        <connector><targetReference>Get_Program_Product</targetReference></connector>
        <doesRequireRecordChangedToMeetCriteria>true</doesRequireRecordChangedToMeetCriteria>
        <filterLogic>and</filterLogic>
        <filters>
            <field>Calculation_Status__c</field>
            <operator>EqualTo</operator>
            <value><stringValue>Requested</stringValue></value>
        </filters>
        <object>IndividualApplicationItem</object>
        <recordTriggerType>CreateAndUpdate</recordTriggerType>
        <triggerType>RecordAfterSave</triggerType>
    </start>"""
VARIABLES = """    <variables>
        <name>vVersionIds</name>
        <dataType>String</dataType>
        <isCollection>true</isCollection>
        <isInput>false</isInput><isOutput>false</isOutput>
    </variables>
    <variables>
        <name>vTechVer</name>
        <dataType>SObject</dataType>
        <isCollection>false</isCollection>
        <isInput>false</isInput><isOutput>false</isOutput>
        <objectType>UsageImpactGroupVersion</objectType>
    </variables>
    <variables>
        <name>vPFVer</name>
        <dataType>SObject</dataType>
        <isCollection>false</isCollection>
        <isInput>false</isInput><isOutput>false</isOutput>
        <objectType>UsageImpactGroupVersion</objectType>
    </variables>
    <variables>
        <name>vIRVer</name>
        <dataType>SObject</dataType>
        <isCollection>false</isCollection>
        <isInput>false</isInput><isOutput>false</isOutput>
        <objectType>UsageImpactGroupVersion</objectType>
    </variables>
    <variables>
        <name>vParticipants</name>
        <dataType>Number</dataType>
        <isCollection>false</isCollection>
        <isInput>false</isInput><isOutput>false</isOutput>
        <scale>0</scale>
        <value><numberValue>1.0</numberValue></value>
    </variables>"""

def esc(s):
    return html.escape(s, quote=False)


def formula_xml(n, sc, expr):
    return f"""    <formulas>
        <name>{n}</name>
        <dataType>Number</dataType>
        <expression>{esc(expr)}</expression>
        <scale>{sc}</scale>
    </formulas>"""


def ai(target, ref=None, num=None, string=None, el=None):
    if el is not None:
        v = f"<elementReference>{el}</elementReference>"
    elif ref is not None:
        v = f"<elementReference>{ref}</elementReference>"
    elif num is not None:
        v = f"<numberValue>{num}</numberValue>"
    else:
        v = f"<stringValue>{string}</stringValue>"
    return f"""        <assignmentItems>
            <assignToReference>{target}</assignToReference>
            <operator>Assign</operator>
            <value>{v}</value>
        </assignmentItems>"""


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(root, "force-app/main/default/flows/CEP_Calculate_Line.flow-meta.xml")

    formulas = "\n".join(formula_xml(n, sc, e) for n, sc, e in FORMULAS)

    # results assignment
    res_items = []
    for fld, src in RESULT_MAP:
        res_items.append(ai(f"$Record.{fld}", num=0) if src is None else ai(f"$Record.{fld}", ref=src))
    for fld, src in FACTOR_MAP:
        res_items.append(ai(f"$Record.{fld}", ref=src))
    res_items.append(ai("$Record.Participants_Used__c", ref="vParticipants"))
    res_items.append(ai("$Record.Context_Definition_Used__c", string="CEP_Line_Calc_Context"))
    res_items.append(ai("$Record.Expression_Set_Version__c", ref="vTechVer.CalcPattern__c"))
    res_items.append(ai("$Record.Calculation_Run_Timestamp__c", ref="$Flow.CurrentDateTime"))
    res_items.append(ai("$Record.Calculation_Status__c", string="Calculated"))
    res_assign = "\n".join(res_items)

    sections = []
    sections.append("""<?xml version="1.0" encoding="UTF-8"?>
<Flow xmlns="http://soap.sforce.com/2006/04/metadata">""")
    sections.append(ACTION_CALLS)
    sections.append("    <apiVersion>63.0</apiVersion>")
    _asg = ASSIGNMENTS
    for _v in ("vTechVer", "vPFVer", "vIRVer"):
        _asg = _asg.replace('{ai("%s", el="Loop_Versions")}' % _v, ai(_v, el="Loop_Versions"))
    sections.append(_asg.replace("@@RES@@", res_assign))
    sections.append(DECISIONS)
    sections.append("    <description>Reusable CEP line calculator. Resolves the Technical TRM, Program Factors and Incentive Rules versions from the Program Measure rows for the line's Program and Product, hydrates one context payload, runs the savings, incentive and reporting layers chosen by the technical version's patterns, and stores results with full lineage.</description>")
    sections.append("    <environments>Default</environments>")
    sections.append(formulas)
    sections.append(CONTEXT_FORMULA)
    sections.append("    <interviewLabel>CEP Calculate Line {!$Flow.CurrentDateTime}</interviewLabel>")
    sections.append("    <label>CEP Calculate Line</label>")
    sections.append(LOOPS)
    sections.append("""    <processMetadataValues>
        <name>BuilderType</name>
        <value><stringValue>LightningFlowBuilder</stringValue></value>
    </processMetadataValues>
    <processMetadataValues>
        <name>CanvasMode</name>
        <value><stringValue>AUTO_LAYOUT_CANVAS</stringValue></value>
    </processMetadataValues>""")
    sections.append("    <processType>AutoLaunchedFlow</processType>")
    sections.append(RECORD_LOOKUPS)
    sections.append(RECORD_UPDATES)
    sections.append(START)
    sections.append("    <status>Active</status>")
    sections.append(VARIABLES)
    sections.append("</Flow>")
    xml = "\n".join(x.rstrip("\n") for x in sections if x.strip()) + "\n"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "w").write(xml)
    print("wrote", out)
    print("formulas:", len(FORMULAS), "| result fields:", len(RESULT_MAP) + len(FACTOR_MAP) + 5)


if __name__ == "__main__":
    main()
