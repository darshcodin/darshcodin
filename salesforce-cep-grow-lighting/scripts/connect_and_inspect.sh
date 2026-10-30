#!/usr/bin/env bash
# Inspect the target org to confirm which Business Rules Engine metadata flavor is
# available before authoring Decision Matrix / Expression Set metadata.
# Usage: bash scripts/connect_and_inspect.sh [org-alias]
set -euo pipefail
ORG="${1:-cep}"

echo "== Org identity =="
sf org display --target-org "$ORG"

echo "== Relevant metadata types present =="
sf org list metadata-types --target-org "$ORG" --json \
  | grep -Eio '"xmlName": "(ExpressionSet[A-Za-z]*|DecisionMatrix[A-Za-z]*|CalculationMatrix[A-Za-z]*|DecisionTable)"' \
  | sort -u || echo "(none matched — check BRE/OmniStudio enablement)"

echo "== BRE-related sObjects present =="
sf sobject list --target-org "$ORG" 2>/dev/null \
  | grep -Ei 'ExpressionSet|DecisionMatrix|CalculationMatrix|DecisionTable' | sort -u \
  || echo "(none matched)"
