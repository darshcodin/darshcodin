#!/usr/bin/env bash
# Seed TRM reference data (Usage Impact model) for Grow Lighting MN:
#   Group -> 2 effective-dated Versions (flat factors) -> Factor defs + values ->
#   Program-Measure bindings. Invoice date selects the version.
# Usage: bash scripts/seed_trm_data.sh [org-alias] [ids-env-file]
set -euo pipefail
ORG="${1:-cep}"
IDS="${2:-/tmp/claude-0/-home-user-darshcodin/c059615c-5117-5388-bb74-e01f6a8baf31/scratchpad/demo_ids.env}"
export SFDX_DISABLE_DNS_CHECK=true SF_DISABLE_DNS_CHECK=true
# shellcheck disable=SC1090
source "$IDS"
pyjson='import json,sys,re,io; m=re.search(r"\{.*\}",sys.stdin.read(),re.S); d=json.load(io.StringIO(m.group(0)))'
qid(){ sf data query --target-org "$ORG" --query "SELECT Id FROM $1 WHERE $2 LIMIT 1" --json 2>/dev/null | python3 -I -c "$pyjson; r=d['result']['records']; print(r[0]['Id'] if r else '')"; }
cid(){ sf data create record --target-org "$ORG" --sobject "$1" --values "$2" --json 2>/dev/null | python3 -I -c "$pyjson; print(d['result']['id'])"; }
foc(){ local id; id=$(qid "$1" "$2"); [ -z "$id" ] && id=$(cid "$1" "$3"); echo "$id"; }

GROUP_ID=$(foc UsageImpactGroup "Name='MN Grow Lighting - Technical'" "Name='MN Grow Lighting - Technical' Product__c=$PRODUCT_ID")

V2026=$(foc UsageImpactGroupVersion "Name='MN-LIGHT-TRM-2026-v2'" "Name='MN-LIGHT-TRM-2026-v2' UsageImpactGroupId=$GROUP_ID Version=2 StartDate=2026-01-01 Version_Label__c='MN-LIGHT-TRM-2026-v2' TD_Loss_Factor__c=1.08 NTG_Only__c=0.85 NTG_Total__c=0.95 Measure_Life_Years__c=15")
V2024=$(foc UsageImpactGroupVersion "Name='MN-LIGHT-TRM-2024-v1'" "Name='MN-LIGHT-TRM-2024-v1' UsageImpactGroupId=$GROUP_ID Version=1 StartDate=2024-01-01 EndDate=2025-12-31 Version_Label__c='MN-LIGHT-TRM-2024-v1' TD_Loss_Factor__c=1.07 NTG_Only__c=0.80 NTG_Total__c=0.90 Measure_Life_Years__c=14")

# factor definitions (normalized) + per-version values
declare -A FAC
for f in "T&D Loss Factor" "NTG Only" "NTG Total" "Measure Life"; do
  FAC["$f"]=$(foc UsageImpactFactor "Name='$f'" "Name='$f'")
done
gf(){ # version, factorName, value
  local v="$1" fname="$2" val="$3" fid="${FAC[$2]}"
  local existing; existing=$(qid UsageImpactGroupFactor "UsageImpactGroupVersionId='$v' AND UsageImpactFactorId='$fid'")
  [ -z "$existing" ] && cid UsageImpactGroupFactor "Name='$fname' UsageImpactGroupVersionId=$v UsageImpactFactorId=$fid FactorValue=$val" >/dev/null || true
}
gf "$V2026" "T&D Loss Factor" 1.08; gf "$V2026" "NTG Only" 0.85; gf "$V2026" "NTG Total" 0.95; gf "$V2026" "Measure Life" 15
gf "$V2024" "T&D Loss Factor" 1.07; gf "$V2024" "NTG Only" 0.80; gf "$V2024" "NTG Total" 0.90; gf "$V2024" "Measure Life" 14

# program-measure bindings (version <-> program + product)
for v in "$V2026" "$V2024"; do
  ex=$(qid UsageImpactGroupPgmMeasure "UsageImpactGroupVersionId='$v' AND ProgramId='$PROGRAM_ID' AND Product2Id='$PRODUCT_ID'")
  [ -z "$ex" ] && cid UsageImpactGroupPgmMeasure "Name='Lighting MN Measure Link' UsageImpactGroupVersionId=$v ProgramId=$PROGRAM_ID Product2Id=$PRODUCT_ID" >/dev/null || true
done

{
  echo "GROUP_ID=$GROUP_ID"; echo "V2026=$V2026"; echo "V2024=$V2024"
} | tee -a "$IDS"
echo "TRM seeded (group, 2 versions, factors, bindings)."
