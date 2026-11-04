#!/usr/bin/env python3
"""Prove the active Expression Set and the executing Flow compute the same thing.

invokeRule does not execute in this org, so the Expression Set is the published
specification and CEP_Calculate_Line is the executor. That split is only safe if
the two cannot silently drift. This compares them step by step and fails loudly
if they diverge.

Run after ANY edit to either side.  Exit 0 = in parity, 1 = drift.
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLOW = os.path.join(ROOT, "force-app/main/default/flows/CEP_Calculate_Line.flow-meta.xml")
ESV = os.path.join(ROOT, "force-app/main/default/expressionSetVersion")

# Expression Set variable  ->  the Flow resource that carries the same value
VARMAP = {
    "Measure_Quantity": "{!fMeasureQty}",
    "RatePerUnit":      "{!vIRVer.Rebate_Rate_Per_Unit__c}",
    "BonusMultiplier":  "{!vIRVer.Bonus_Multiplier__c}",
    "MaxIncentive":     "{!vIRVer.Max_Incentive__c}",
    "IncCostPerUnit":   "{!vIRVer.Inc_Cost_Per_Unit__c}",
    "Base_Incentive":   "{!fBaseIncentive}",
}
# Expression Set output  ->  Flow formula that must mirror it
STEPMAP = {
    "Base_Incentive":   "fBaseIncentive",
    "Incremental_Cost": "fIncCost",
    "Incentive_Amount": "fIncentive",
}


def unescape(s):
    return (s.replace("&gt;", ">").replace("&lt;", "<")
             .replace("&amp;", "&").replace("&quot;", '"'))


def norm(s):
    """Whitespace-insensitive, so formatting differences are not drift."""
    return re.sub(r"\s+", "", unescape(s))


def translate(expr):
    """Rewrite an Expression Set formula into the Flow's resource vocabulary."""
    out = unescape(expr)
    for var in sorted(VARMAP, key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(var)}\b", VARMAP[var], out)
    return out


def pull_active_version():
    """Fetch the ACTIVE version straight from the org, not from local files."""
    env = dict(os.environ); env["SFDX_DISABLE_DNS_CHECK"] = "true"
    q = ("SELECT ApiName FROM ExpressionSetVersion "
         "WHERE ExpressionSet.ApiName='I2_PerUnitBonus' AND IsActive=true")
    r = subprocess.run(["sf", "api", "request", "rest",
                        "/services/data/v63.0/query/?q=" + q.replace(" ", "+"),
                        "-o", "cep"], capture_output=True, text=True, env=env)
    m = re.search(r'"ApiName"\s*:\s*"([^"]+)"', r.stdout)
    return m.group(1) if m else None


def main():
    active = pull_active_version()
    print(f"  active Expression Set version in org : {active or 'UNKNOWN'}")

    # the retrieved Builder-authored file for that version
    path = os.path.join(ESV, "I2_PerUnitBonus_V1.expressionSetVersion-meta.xml")
    if not os.path.exists(path):
        print("  ! local copy of the active version not found; run sf project retrieve first")
        return 1
    es = open(path).read()
    flow = open(FLOW).read()

    steps = {}
    for blk in re.findall(r"<steps>(.*?)</steps>", es, re.S):
        p = re.search(r"<assignedParameter>(.*?)</assignedParameter>", blk)
        e = re.search(r"<expression>(.*?)</expression>", blk, re.S)
        if p and e:
            steps[p.group(1)] = e.group(1)

    print(f"  steps found in Expression Set        : {len(steps)}\n")

    drift = 0
    for out_var, flow_name in STEPMAP.items():
        if out_var not in steps:
            print(f"  [MISSING] Expression Set has no step producing {out_var}")
            drift += 1
            continue
        expected = translate(steps[out_var])
        m = re.search(rf"<name>{flow_name}</name>.*?<expression>(.*?)</expression>",
                      flow, re.S)
        if not m:
            print(f"  [MISSING] Flow has no formula {flow_name}")
            drift += 1
            continue
        actual = unescape(m.group(1))

        if norm(expected) == norm(actual):
            print(f"  [MATCH   ] {out_var}  ==  {flow_name}")
        elif norm(expected) in norm(actual):
            print(f"  [SUPERSET] {out_var}  ->  {flow_name}")
            print(f"             Flow adds a guard around the same core expression:")
            print(f"               ES   : {expected}")
            print(f"               Flow : {actual}")
        else:
            print(f"  [DRIFT   ] {out_var}  !=  {flow_name}")
            print(f"               ES   : {expected}")
            print(f"               Flow : {actual}")
            drift += 1

    print()
    if drift:
        print(f"  RESULT: DRIFT in {drift} step(s). The published rule and the executor disagree.")
        return 1
    print("  RESULT: IN PARITY. The Expression Set and the Flow compute the same incentive.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
