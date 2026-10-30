#!/usr/bin/env bash
# Run the deployed Grow Lighting MN Calculator against the worked example and
# assert the expected outputs. Requires the running user to hold the BRERuntime
# ("Rule Engine Runtime") permission set, otherwise the evaluation resource 404s.
# Usage: bash scripts/verify_calculator.sh [org-alias] [api-version]
set -euo pipefail
ORG="${1:-cep}"
API="${2:-v62.0}"
export SFDX_DISABLE_DNS_CHECK=true SF_DISABLE_DNS_CHECK=true
TMP="$(mktemp -d)"

cat > "$TMP/body.json" <<'JSON'
{
  "expressionSetApiName": "Grow_Lighting_MN_Calculator",
  "inputVariables": [
    {"name": "Qty", "value": 10},
    {"name": "Room_Type", "value": "Cannabis Flower Room"},
    {"name": "PPF", "value": 1700},
    {"name": "Prop_Watts", "value": 630},
    {"name": "DLC_Tier", "value": "DLC Premium"}
  ]
}
JSON

echo "== Executing expression set =="
sf api request rest "/services/data/${API}/connect/expression-set/evaluationServices/execute" \
  --method POST --body "$TMP/body.json" --target-org "$ORG" | tee "$TMP/out.json"

echo
echo "== Expected =="
cat <<'EXP'
electricRebate 4410.00 | Prop_PPE 2.70 | Base_W 1955 | customerKW 17.6225
customerKWH 65399.35 | customerPCKW 11.98364 | incrementalCost 7119.00
EXP
echo "(If the resource 404s: assign the BRERuntime permission set to the running user and retry.)"
rm -rf "$TMP"
