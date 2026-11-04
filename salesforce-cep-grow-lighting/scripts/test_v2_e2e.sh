#!/usr/bin/env bash
# End-to-end test of CEP_Calculate_Line.
# Usage: test_v2_e2e.sh <lineId> <programProductId> <invoiceDate>
set -uo pipefail
export SFDX_DISABLE_DNS_CHECK=true
LINE="$1"; PP="$2"; INV="${3:-2026-03-15}"

echo "=== 1. stage golden-record inputs on $LINE (invoice $INV) ==="
sf data update record -o cep -s IndividualApplicationItem -i "$LINE" -v \
  "Program_Product__c=$PP Fixture_Quantity__c=100 Proposed_PPF__c=1700 Proposed_Fixture_Watts__c=630 DLC_Tier__c='DLC Premium' Invoice_Date__c=$INV Market_Segment_Room_Type__c='Cannabis Flower Room' Calculation_Status__c='Not Calculated'" \
  2>&1 | tail -2

echo "=== 2. request calculation (fires CEP_Calculate_Line) ==="
sf data update record -o cep -s IndividualApplicationItem -i "$LINE" -v \
  "Calculation_Status__c=Requested" 2>&1 | tail -2

echo "=== 3. read back ==="
sf data query -o cep --json -q "SELECT Id, Calculation_Status__c, Calculation_Error__c,
  Technical_Version__r.Version_Label__c, Program_Factors_Version_Ref__r.Version_Label__c,
  Incentive_Rules_Version_Ref__r.Version_Label__c,
  Savings_Expression_Set__c, Incentive_Expression_Set__c, Reporting_Expression_Set__c,
  Context_Definition_Used__c, Calculation_Run_Timestamp__c,
  Proposed_PPE__c, Baseline_Watts__c, Gross_kW__c, Gross_kWh__c, Gross_PCkW__c, Measure_Quantity__c,
  Electric_Rebate__c, Incremental_Cost__c,
  TD_Loss_Factor_Used__c, NTG_Only_Used__c, NTG_Total_Used__c, Measure_Life_Used__c,
  SM_kW_Gen_PCkW__c, Gross_Annual_PCkW_Customer__c, Total_Only_Net_kW_Customer_PCkW__c,
  Total_Net_kW_Customer_PCkW__c, Total_Net_PCkW_Gen__c, Gross_Annual_kWh_Customer__c,
  Program_Net_Annual_Customer_kWh__c, Gen_kWh__c, Program_Net_Annual_Generator_kWh__c,
  Lifetime_Gen_kWh__c, Lifetime_Net_Gen_kWh__c
  FROM IndividualApplicationItem WHERE Id='$LINE'" 2>/dev/null | python3 -I -c "
import json,sys
r=json.load(sys.stdin)['result']['records'][0]
def g(k):
    v=r.get(k)
    return v.get('Version_Label__c') if isinstance(v,dict) else v
print()
print('  STATUS        ', g('Calculation_Status__c'))
if g('Calculation_Error__c'): print('  ERROR         ', g('Calculation_Error__c'))
print()
print('  -- versions resolved by invoice date --')
for k,lbl in [('Technical_Version__r','Technical TRM'),('Program_Factors_Version_Ref__r','Program Factors'),('Incentive_Rules_Version_Ref__r','Incentive Rules')]:
    print(f'    {lbl:18s} {g(k)}')
print()
print('  -- expression sets selected by pattern --')
for k,lbl in [('Savings_Expression_Set__c','savings'),('Incentive_Expression_Set__c','incentive'),('Reporting_Expression_Set__c','reporting'),('Context_Definition_Used__c','context')]:
    print(f'    {lbl:18s} {g(k)}')
print()
print('  -- applied factors --')
for k in ['TD_Loss_Factor_Used__c','NTG_Only_Used__c','NTG_Total_Used__c','Measure_Life_Used__c']:
    print(f'    {k:34s} {g(k)}')
print()
print('  -- savings layer (P2_EffDelta) --')
for k in ['Proposed_PPE__c','Baseline_Watts__c','Gross_kW__c','Gross_kWh__c','Gross_PCkW__c','Measure_Quantity__c']:
    print(f'    {k:34s} {g(k)}')
print()
print('  -- incentive layer (I2_PerUnitBonus) --')
for k in ['Electric_Rebate__c','Incremental_Cost__c']:
    print(f'    {k:34s} {g(k)}')
print()
print('  -- reporting layer (R1_StdReporting) --')
for k in ['SM_kW_Gen_PCkW__c','Gross_Annual_PCkW_Customer__c','Total_Only_Net_kW_Customer_PCkW__c','Total_Net_kW_Customer_PCkW__c','Total_Net_PCkW_Gen__c','Gross_Annual_kWh_Customer__c','Program_Net_Annual_Customer_kWh__c','Gen_kWh__c','Program_Net_Annual_Generator_kWh__c','Lifetime_Gen_kWh__c','Lifetime_Net_Gen_kWh__c']:
    print(f'    {k:36s} {g(k)}')
"
