"""Experiment 006, phase A: discover *documented* ESA ESASky LAMOST DR9 TAP tables.

Read-only TAP_SCHEMA metadata requests. Never query stellar data until the
schema and release equivalence are independently reviewed.
"""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request

from scripts.import_gaia import parse_votable

TAP_URL = "https://sky.esa.int/esasky-tap/tap/sync"
ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "docs/EXPERIMENT_006.md"
TABLE_QUERY = ("SELECT TOP 100 table_name, description FROM TAP_SCHEMA.tables "
               "WHERE LOWER(table_name) LIKE '%lamost%' "
               "OR LOWER(description) LIKE '%lamost%' ORDER BY table_name")
COLUMNS = ("table_name", "column_name", "datatype", "unit", "description")
FILENAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def query_columns(table):
    if not FILENAME_RE.fullmatch(table):
        raise ValueError("Unsafe table metadata name")
    # Names are parsed from ESA TAP_SCHEMA, never received from the user.
    return ("SELECT TOP 800 table_name, column_name, datatype, unit, description "
            "FROM TAP_SCHEMA.columns WHERE table_name = '" + table + "' "
            "ORDER BY column_name")


def read_metadata(raw, required):
    fields, rows = parse_votable(raw)
    if not set(required).issubset(fields):
        raise ValueError("TAP metadata missing essential columns: "+str(set(required)-set(fields)))
    return [{"field":r.get("field")} if False else {name:r.get(name) for name in required} for r in rows]


def tap(query, label, directory):
    params = {"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"votable",
              "MAXREC":"801","QUERY":query}
    payload=urllib.parse.urlencode(params).encode("utf-8")
    request=urllib.request.Request(TAP_URL, data=payload, method="POST",
      headers={"User-Agent":"EchoLens-006-ESASky-schema-research",
               "Content-Type":"application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            raw=response.read(4_000_000)
            http_status=response.status
            headers={k:response.headers.get(k) for k in
                     ("Date","Content-Type","ETag","Last-Modified")}
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as err:
        return {"status":"failed","error":repr(err),"query":query,
                "endpoint":TAP_URL,"name":label}
    # Check QUERY_STATUS and field types before persisting anything.
    try:
        required=("table_name","description") if label=="tables" else COLUMNS
        rows=read_metadata(raw,required)
    except Exception as err:
        return {"status":"rejected","error":repr(err),"query":query,
                "endpoint":TAP_URL,"raw_sha256":digest(raw),"name":label}
    path=directory/(label+".xml.gz")
    path.write_bytes(gzip.compress(raw,mtime=0))
    result={"status":"ok","query":query,"endpoint":TAP_URL,
            "retrieved_utc":datetime.now(timezone.utc).isoformat(),
            "http_status":http_status,"response_headers":headers,
            "raw_sha256":digest(raw),"row_count":len(rows),"rows":rows,
            "archived_raw_response":path.name}
    if len(rows)>=800:
        raise ValueError("Metadata response at possible truncation limit")
    return result


def execute(out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    results={"experiment":"006A","phase":"TAP_SCHEMA metadata discovery",
             "provenance":{"protocol_sha256":digest(PROTOCOL.read_bytes()),
                           "tap_url":TAP_URL,
                           "source_catalog_description":
                           "ESA ESASky LAMOST DR9 General, version equivalence NOT established"},
             "responses":{},"science_catalog_records_queried":0,
             "fiber_offsets_or_dates_confirmed":0}
    a=tap(TABLE_QUERY,"tables",out)
    results["responses"]["tables"]=a
    if a["status"]=="ok":
        tables=[str(r["table_name"]) for r in a["rows"]
                if r["table_name"] is not None
                and FILENAME_RE.fullmatch(str(r["table_name"]))]
        if len(tables)!=len(a["rows"]):
            results["warning"]="Some TAP_SCHEMA names were missing or unsafe; skipped"
        for i,name in enumerate(tables):
            response=tap(query_columns(name),f"columns_{i:02d}",out)
            response["table_name"]=name
            results["responses"][f"columns_{i:02d}"]=response
        results["identified_lamost_tables"]=tables
    else:
        results["identified_lamost_tables"]=[]
    results["status"]=("schema_found" if
        a["status"]=="ok" and results["identified_lamost_tables"] else
        "no_verified_schema")
    results["next_gate"]="Review exact ESA LRS general table/release and names before requesting any 250 obsids."
    (out/"manifest.json").write_text(json.dumps(results,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"status":results["status"],
                      "identified_lamost_tables":results["identified_lamost_tables"],
                      "response_statuses":{k:v["status"] for k,v in results["responses"].items()}},
                     indent=2))
    return results


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",default="reports/experiment_006/schema")
    args=p.parse_args()
    execute(args.output)


if __name__=="__main__":
    main()
