#!/usr/bin/env bash
# Seed one Benefit per calculated metric (rebate + savings) for the Savings Store
# (Option A). Each Benefit carries a Metric_Code__c; the after-save flow creates a
# BenefitAssignment per metric mapped to the application. Idempotent.
# Usage: bash scripts/seed_benefit_metrics.sh [org-alias] [ids-env-file]
set -euo pipefail
ORG="${1:-cep}"
IDS="${2:-/tmp/claude-0/-home-user-darshcodin/c059615c-5117-5388-bb74-e01f6a8baf31/scratchpad/demo_ids.env}"
export SFDX_DISABLE_DNS_CHECK=true SF_DISABLE_DNS_CHECK=true
# shellcheck disable=SC1090
source "$IDS"
pyjson='import json,sys,re,io; m=re.search(r"\{.*\}",sys.stdin.read(),re.S); d=json.load(io.StringIO(m.group(0)))'
qid(){ sf data query --target-org "$ORG" --query "SELECT Id FROM $1 WHERE $2 LIMIT 1" --json 2>/dev/null | python3 -I -c "$pyjson; r=d['result']['records']; print(r[0]['Id'] if r else '')"; }
cid(){ sf data create record --target-org "$ORG" --sobject "$1" --values "$2" --json 2>/dev/null | python3 -I -c "$pyjson; print(d['result']['id'])"; }

# code|Benefit Name  (rebate benefit already exists; just set its Metric_Code__c)
sf data update record --target-org "$ORG" --sobject Benefit --record-id "$BENEFIT_ID" --values "Metric_Code__c=ELECTRIC_REBATE" >/dev/null 2>&1 || true

metrics=(
  "CUSTOMER_KW|Customer kW Demand Savings"
  "CUSTOMER_KWH|Customer kWh Energy Savings"
  "CUSTOMER_PCKW|Peak Coincident kW"
  "SM_KW_GEN|SM kW Gen (PCkW)"
  "GROSS_PCKW_CUST|Gross Annual PCkW at Customer"
  "TOTAL_ONLY_NET_KW|Total Only Net kW Customer"
  "TOTAL_NET_KW|Total Net kW Customer"
  "TOTAL_NET_PCKW_GEN|Total Net PCkW at Gen"
  "GROSS_KWH_CUST|Gross Annual kWh at Customer"
  "PROG_NET_CUST_KWH|Program Net Annual Customer kWh"
  "GEN_KWH|Gen Electric DSM kWh"
  "PROG_NET_GEN_KWH|Program Net Annual Generator kWh"
  "LIFETIME_GEN_KWH|Lifetime Gen kWh"
  "LIFETIME_NET_GEN_KWH|Lifetime Net Gen kWh"
)
for m in "${metrics[@]}"; do
  code="${m%%|*}"; name="${m##*|}"
  existing=$(qid Benefit "Metric_Code__c='$code' AND Product2Id='$PRODUCT_ID'")
  if [ -z "$existing" ]; then
    id=$(cid Benefit "Name='$name' BenefitTypeId=$BENTYPE_ID ProgramId=$PROGRAM_ID Product2Id=$PRODUCT_ID IsActive=true BenefitStatus='Active' Metric_Code__c=$code")
    echo "  created $code -> $id"
  else
    sf data update record --target-org "$ORG" --sobject Benefit --record-id "$existing" --values "IsActive=true BenefitStatus='Active'" >/dev/null 2>&1 || true
    echo "  exists  $code -> $existing"
  fi
done
echo "Benefit metrics seeded."
