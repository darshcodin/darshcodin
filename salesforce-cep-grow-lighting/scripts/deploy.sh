#!/usr/bin/env bash
# Deploy the Grow Lighting MN Calculator Expression Set to the target org.
# Two-phase: deploy as Draft, then activate (BRE won't activate a version in the
# same pass that first creates its steps).
# Usage: bash scripts/deploy.sh [org-alias]
set -euo pipefail
ORG="${1:-cep}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEF="$ROOT/force-app/main/default/expressionSetDefinition/Grow_Lighting_MN_Calculator.expressionSetDefinition-meta.xml"
VER="$ROOT/force-app/main/default/expressionSetVersion/Grow_Lighting_MN_Calculator_V1.expressionSetVersion-meta.xml"
export SFDX_DISABLE_DNS_CHECK=true SF_DISABLE_DNS_CHECK=true

echo "== Phase 1: deploy as Draft =="
sed -i.bak 's#<status>Active</status>#<status>Draft</status>#' "$DEF" "$VER"
sf project deploy start --target-org "$ORG" --source-dir "$ROOT/force-app"

echo "== Phase 2: activate (version file -> Active, definition inline stays Draft) =="
sed -i 's#<status>Draft</status>#<status>Active</status>#' "$VER"
sf project deploy start --target-org "$ORG" --source-dir "$ROOT/force-app"

rm -f "$DEF.bak" "$VER.bak"
echo "== Done. Expression Set 'Grow_Lighting_MN_Calculator' active. =="
