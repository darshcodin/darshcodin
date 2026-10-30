#!/usr/bin/env python3
"""Load Decision Matrix rows (CalculationMatrixRow) from the CSV data files.

Maps each matrix by DeveloperName -> its version -> backing CalculationMatrixVersion,
clears existing rows, then creates one row per CSV line (InputData/OutputData JSON).
Idempotent. Usage: python3 scripts/load_matrix_rows.py [org-alias]
"""
import csv
import json
import os
import subprocess
import sys
import tempfile

ORG = sys.argv[1] if len(sys.argv) > 1 else "cep"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = {**os.environ, "SFDX_DISABLE_DNS_CHECK": "true", "SF_DISABLE_DNS_CHECK": "true"}

# matrix DeveloperName -> (csv file, input column, [output columns])
MATRICES = {
    "Grow_Lighting_Room_Type": ("room_type_matrix.csv", "Room_Type", ["Hours", "kWh_Factor", "CF"]),
    "Grow_Lighting_DLC_Tier": ("dlc_tier_matrix.csv", "DLC_Tier", ["DLC_Adj", "Effective_Rate"]),
}


def sf_json(args):
    out = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True, env=ENV).stdout
    return json.loads(out)


def query(soql):
    return sf_json(["data", "query", "--target-org", ORG, "--query", soql])["result"]["records"]


def rest(method, path, body=None):
    args = ["sf", "api", "request", "rest", path, "--method", method, "--target-org", ORG]
    if body is not None:
        f = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(body, f); f.close()
        args += ["--body", f"@{f.name}"]
    out = subprocess.run(args, capture_output=True, text=True, env=ENV).stdout
    try:
        return json.loads(out)
    except Exception:
        return out


def backing_cmv(dev_name):
    d = query(f"SELECT Id FROM DecisionMatrixDefinition WHERE DeveloperName='{dev_name}'")
    if not d:
        return None
    v = query(f"SELECT Id FROM DecisionMatrixDefinitionVersion WHERE DecisionMatrixDefinitionId='{d[0]['Id']}' ORDER BY VersionNumber DESC")
    if not v:
        return None
    c = query(f"SELECT Id FROM CalculationMatrixVersion WHERE DecisionMatrixDefinitionVerId='{v[0]['Id']}'")
    return c[0]["Id"] if c else None


def num(s):
    f = float(s)
    return int(f) if f.is_integer() else f


def main():
    for dev_name, (csv_file, in_col, out_cols) in MATRICES.items():
        cmv = backing_cmv(dev_name)
        if not cmv:
            print(f"!! {dev_name}: no backing CalculationMatrixVersion (deploy the matrix first)")
            continue
        # clear existing rows (per-record delete; matrix enforces unique input hash keys)
        existing = query(f"SELECT Id FROM CalculationMatrixRow WHERE CalculationMatrixVersionId='{cmv}'")
        for r in existing:
            subprocess.run(["sf", "data", "delete", "record", "--target-org", ORG,
                            "--sobject", "CalculationMatrixRow", "--record-id", r["Id"]],
                           capture_output=True, text=True, env=ENV)
        # build rows
        records = []
        with open(os.path.join(ROOT, "data", csv_file)) as f:
            for i, row in enumerate(csv.DictReader(f), start=1):
                input_data = {in_col: row[in_col]}
                output_data = {c: num(row[c]) for c in out_cols}
                records.append({
                    "attributes": {"type": "CalculationMatrixRow"},
                    "Name": str(i),
                    "CalculationMatrixVersionId": cmv,
                    "InputData": json.dumps(input_data),
                    "OutputData": json.dumps(output_data),
                })
        res = rest("POST", "/services/data/v62.0/composite/sobjects",
                   {"allOrNone": True, "records": records})
        ok = sum(1 for r in res if isinstance(r, dict) and r.get("success")) if isinstance(res, list) else 0
        print(f"{dev_name}: loaded {ok}/{len(records)} rows into {cmv}")
        if ok != len(records):
            print("   detail:", res)


if __name__ == "__main__":
    main()
