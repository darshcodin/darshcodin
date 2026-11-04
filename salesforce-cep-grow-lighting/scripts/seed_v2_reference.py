#!/usr/bin/env python3
"""Seed the three-role reference-data model and wire it to Program + Product."""
import json, os, subprocess, sys

ORG = "cep"
API = "v63.0"
PRODUCT_ID = "01thm000000rOYrAAM"   # MN - Lighting Efficiency Rebate


def rest(path, method="GET", body=None):
    cmd = ["sf", "api", "request", "rest", path, "--method", method, "-o", ORG]
    if body is not None:
        cmd += ["--body", json.dumps(body)]
    env = dict(os.environ)
    env["SFDX_DISABLE_DNS_CHECK"] = "true"
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = r.stdout.strip()
    try:
        return json.loads(out)
    except Exception:
        return {"_raw": out, "_err": r.stderr.strip()[:300]}


def soql(q):
    import urllib.parse
    return rest(f"/services/data/{API}/query/?q={urllib.parse.quote(q)}")


def create(obj, fields):
    r = rest(f"/services/data/{API}/sobjects/{obj}", "POST", fields)
    if isinstance(r, list):
        print(f"   ! {obj}: {r[0].get('message')}")
        return None
    if r.get("id"):
        return r["id"]
    print(f"   ! {obj}: {r}")
    return None


def foc(obj, where, fields, label):
    """find-or-create"""
    r = soql(f"SELECT Id FROM {obj} WHERE {where} LIMIT 1")
    recs = r.get("records") or []
    if recs:
        print(f"   = {label}: exists {recs[0]['Id']}")
        return recs[0]["Id"]
    i = create(obj, fields)
    print(f"   + {label}: {i}")
    return i


print("1. Program and ProgramProduct")
prog = foc("Program", "Name='Lighting - MN'",
           {"Name": "Lighting - MN", "Status": "Active",
            "StartDate": "2024-01-01", "EndDate": "2030-12-31"}, "Program Lighting - MN")
pp = foc("ProgramProduct", f"ProgramId='{prog}' AND ProductId='{PRODUCT_ID}'",
         {"Name": "MN Lighting Efficiency Rebate", "ProgramId": prog, "ProductId": PRODUCT_ID},
         "ProgramProduct")

print("\n2. Usage Impact Groups, one per version role")
GROUPS = [
    ("MN Lighting Technical TRM",    "Technical TRM"),
    ("MN Lighting Program Factors",  "Program Factors"),
    ("MN Lighting Incentive Rules",  "Incentive Rules"),
]
gids = {}
for name, role in GROUPS:
    gids[role] = foc("UsageImpactGroup", f"Name='{name}'",
                     {"Name": name, "Type": "Production", "IsActive": True,
                      "Version_Role__c": role, "Product__c": PRODUCT_ID}, f"{role}")

print("\n3. Versions with effective windows")
VERSIONS = [
    # role, name, version, start, end, extra fields
    ("Technical TRM", "MN-LIGHT-TECH-2024-v1", 1, "2024-01-01", "2025-12-31", {
        "Baseline_Efficacy__c": 1.05, "Prop_Reflector_Eff__c": 0.972,
        "Base_Reflector_Eff__c": 0.783, "Cooling_Factor__c": 1.33,
        "CalcPattern__c": "P2_EffDelta", "Incentive_Pattern__c": "I2_PerUnitBonus",
        "Reporting_Pattern__c": "R1_StdReporting"}),
    ("Technical TRM", "MN-LIGHT-TECH-2026-v2", 2, "2026-01-01", None, {
        "Baseline_Efficacy__c": 1.08, "Prop_Reflector_Eff__c": 0.972,
        "Base_Reflector_Eff__c": 0.783, "Cooling_Factor__c": 1.33,
        "CalcPattern__c": "P2_EffDelta", "Incentive_Pattern__c": "I2_PerUnitBonus",
        "Reporting_Pattern__c": "R1_StdReporting"}),
    ("Program Factors", "MN-LIGHT-PF-2024", 1, "2024-01-01", "2025-12-31", {
        "TD_Loss_Factor__c": 1.07, "NTG_Only__c": 0.80,
        "NTG_Total__c": 0.90, "Measure_Life_Years__c": 14}),
    ("Program Factors", "MN-LIGHT-PF-2026", 2, "2026-01-01", None, {
        "TD_Loss_Factor__c": 1.08, "NTG_Only__c": 0.85,
        "NTG_Total__c": 0.95, "Measure_Life_Years__c": 15}),
    ("Incentive Rules", "MN-LIGHT-IR-2024", 1, "2024-01-01", "2025-12-31", {
        "Rebate_Rate_Per_Unit__c": 0.60, "Bonus_Multiplier__c": 1.00,
        "Max_Incentive__c": 40000, "Inc_Cost_Per_Unit__c": 1.10}),
    ("Incentive Rules", "MN-LIGHT-IR-2026", 2, "2026-01-01", None, {
        "Rebate_Rate_Per_Unit__c": 0.70, "Bonus_Multiplier__c": 1.00,
        "Max_Incentive__c": 50000, "Inc_Cost_Per_Unit__c": 1.13}),
]
vids = {}
for role, label, vnum, start, end, extra in VERSIONS:
    f = {"Name": label, "UsageImpactGroupId": gids[role], "Version": vnum,
         "StartDate": start, "IsActive": True, "Version_Label__c": label}
    if end:
        f["EndDate"] = end
    f.update(extra)
    vids[label] = foc("UsageImpactGroupVersion", f"Name='{label}'", f, label)

print("\n4. Program Measure junction rows (Program + Product -> each version)")
for label, vid in vids.items():
    if not vid:
        continue
    foc("UsageImpactGroupPgmMeasure",
        f"ProgramId='{prog}' AND Product2Id='{PRODUCT_ID}' AND UsageImpactGroupVersionId='{vid}'",
        {"Name": f"MN Lighting - {label}", "ProgramId": prog, "Product2Id": PRODUCT_ID,
         "UsageImpactGroupVersionId": vid}, f"PgmMeasure {label}")

print("\nDONE")
print("program_product_id =", pp)
