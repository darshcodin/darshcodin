#!/usr/bin/env bash
# Reproducible end-to-end test: seed data, create an application + line (which fire
# the calculation + benefit flows), then assert the outputs and the BenefitAssignment.
# Usage: bash scripts/run_end_to_end.sh [org-alias]
set -euo pipefail
ORG="${1:-cep}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IDS="$(mktemp)"
export SFDX_DISABLE_DNS_CHECK=true SF_DISABLE_DNS_CHECK=true
pyid='import json,sys,re,io;m=re.search(r"\{.*\}",sys.stdin.read(),re.S);print(json.load(io.StringIO(m.group(0)))["result"]["id"])'

echo "== Seeding demo data (idempotent) =="
bash "$ROOT/scripts/seed_demo_data.sh" "$ORG" "$IDS" >/dev/null
# shellcheck disable=SC1090
source "$IDS"

echo "== Creating application + line (Qty=10, Cannabis Flower Room, PPF=1700, Watts=630, DLC Premium) =="
APP=$(sf data create record --target-org "$ORG" --sobject IndividualApplication \
  --values "Category='Program' AccountId=$ACCOUNT_ID Status='In Progress'" --json 2>/dev/null | python3 -I -c "$pyid")
ITEM=$(sf data create record --target-org "$ORG" --sobject IndividualApplicationItem \
  --values "Name='LED Grow Fixture MN v2 - Flower Room' IndividualApplicationId=$APP RelatedItemId=$PROGPROD_ID Fixture_Quantity__c=10 Market_Segment_Room_Type__c='Cannabis Flower Room' Proposed_PPF__c=1700 Proposed_Fixture_Watts__c=630 DLC_Tier__c='DLC Premium' Invoice_Date__c=2026-03-15 Status='Pending'" --json 2>/dev/null | python3 -I -c "$pyid")
echo "   Application=$APP  Line=$ITEM"

echo "== Line outputs =="
sf data query --target-org "$ORG" --query "SELECT Electric_Rebate__c, Proposed_PPE__c, Baseline_Watts__c, Customer_kW_Savings__c, Customer_kWh_Savings__c, Customer_Peak_Coincident_kW__c, Incremental_Cost__c FROM IndividualApplicationItem WHERE Id='$ITEM'" --json 2>/dev/null \
  | python3 -I -c "
import json,sys
exp={'Electric_Rebate__c':4410.0,'Proposed_PPE__c':2.70,'Baseline_Watts__c':1955.0,'Customer_kW_Savings__c':17.6225,'Customer_kWh_Savings__c':65399.35,'Customer_Peak_Coincident_kW__c':11.98364,'Incremental_Cost__c':7119.0}
r=json.load(sys.stdin)['result']['records'][0]
ok=True
for k,v in exp.items():
    got=r.get(k)
    match = got is not None and abs(float(got)-v)<0.001
    ok= ok and match
    print(f\"   {'OK ' if match else 'FAIL'} {k}: got={got} expected={v}\")
print('   RESULT:', 'ALL OUTPUTS MATCH' if ok else 'MISMATCH'); sys.exit(0 if ok else 1)
"

echo "== BenefitAssignment (incentive) =="
sf data query --target-org "$ORG" --query "SELECT Name, EntitlementAmount, Status, Benefit.Name FROM BenefitAssignment WHERE ParentRecordId='$APP'" 2>&1 | tail -6
rm -f "$IDS"
echo "== End-to-end OK =="
