#!/usr/bin/env bash
# Seed end-to-end demo data for Grow Lighting MN on standard objects (idempotent:
# find-or-create by Name). Writes created IDs to an env file sourced by later steps.
# Usage: bash scripts/seed_demo_data.sh [org-alias] [ids-out-file]
set -euo pipefail
ORG="${1:-cep}"
OUT="${2:-/tmp/claude-0/-home-user-darshcodin/c059615c-5117-5388-bb74-e01f6a8baf31/scratchpad/demo_ids.env}"
export SFDX_DISABLE_DNS_CHECK=true SF_DISABLE_DNS_CHECK=true

# robust: pull first JSON object out of mixed output
pyjson='import json,sys,re; m=re.search(r"\{.*\}",sys.stdin.read(),re.S); d=json.load(__import__("io").StringIO(m.group(0)))'

query_id() { # $1 object, $2 where
  sf data query --target-org "$ORG" --query "SELECT Id FROM $1 WHERE $2 LIMIT 1" --json 2>/dev/null \
    | python3 -I -c "$pyjson; r=d['result']['records']; print(r[0]['Id'] if r else '')"
}
create_id() { # $1 object, $2 values
  sf data create record --target-org "$ORG" --sobject "$1" --values "$2" --json 2>/dev/null \
    | python3 -I -c "$pyjson; print(d['result']['id'])"
}
foc() { # find-or-create: $1 object, $2 nameField=val where-clause, $3 full create values
  local id; id=$(query_id "$1" "$2")
  if [ -z "$id" ]; then id=$(create_id "$1" "$3"); fi
  echo "$id"
}

ES_ID=$(query_id ExpressionSet "ApiName='Grow_Lighting_MN_Calculator'")
echo "ExpressionSet: $ES_ID"

PROGRAM_ID=$(foc Program "Name='Lighting - MN'" "Name='Lighting - MN'")
PRODUCT_ID=$(foc Product2 "Name='MN - Lighting Efficiency Rebate'" "Name='MN - Lighting Efficiency Rebate' ProductCode='MN-LIGHT-EFF' IsActive=true")
PROGPROD_ID=$(foc ProgramProduct "ProgramId='$PROGRAM_ID' AND ProductId='$PRODUCT_ID'" "Name='Lighting - MN / Lighting Efficiency Rebate' ProgramId=$PROGRAM_ID ProductId=$PRODUCT_ID")
UOM_ID=$(query_id UnitOfMeasure "Name='US Dollars'")
BENTYPE_ID=$(foc BenefitType "Name='Energy Efficiency Rebate'" "Name='Energy Efficiency Rebate' ProcessType='PublicSector' UnitofMeasureId=$UOM_ID")
BENEFIT_ID=$(foc Benefit "Name='MN Lighting Efficiency Rebate'" "Name='MN Lighting Efficiency Rebate' BenefitTypeId=$BENTYPE_ID ProgramId=$PROGRAM_ID Product2Id=$PRODUCT_ID EligibleAmountExpressionSetId=$ES_ID IsActive=true BenefitStatus='Active'")
# ensure active even if the benefit already existed
sf data update record --target-org "$ORG" --sobject Benefit --record-id "$BENEFIT_ID" --values "IsActive=true BenefitStatus='Active'" >/dev/null 2>&1 || true
ACCOUNT_ID=$(foc Account "Name='Green Valley Growers'" "Name='Green Valley Growers'")
LOCATION_ID=$(foc Location "Name='Green Valley Growers - Grow Facility'" "Name='Green Valley Growers - Grow Facility' LocationType='Commercial' AccountId=$ACCOUNT_ID County__c='Hennepin' Customer_Fuel_Type__c='Electric'")
ENROLLMENT_ID=$(foc ProgramEnrollment "ProgramId='$PROGRAM_ID' AND AccountId='$ACCOUNT_ID'" "Name='Green Valley Growers - Lighting MN' ProgramId=$PROGRAM_ID AccountId=$ACCOUNT_ID Status='In Progress' IsActive=true StartDate=2026-01-01")
# ensure enrollment active even if it already existed (required for BenefitAssignment)
sf data update record --target-org "$ORG" --sobject ProgramEnrollment --record-id "$ENROLLMENT_ID" --values "IsActive=true StartDate=2026-01-01" >/dev/null 2>&1 || true

{
  echo "ES_ID=$ES_ID"; echo "PROGRAM_ID=$PROGRAM_ID"; echo "PRODUCT_ID=$PRODUCT_ID"
  echo "PROGPROD_ID=$PROGPROD_ID"; echo "BENTYPE_ID=$BENTYPE_ID"; echo "BENEFIT_ID=$BENEFIT_ID"
  echo "ACCOUNT_ID=$ACCOUNT_ID"; echo "LOCATION_ID=$LOCATION_ID"; echo "ENROLLMENT_ID=$ENROLLMENT_ID"
} | tee "$OUT"
echo "Seeded. IDs written to $OUT"
