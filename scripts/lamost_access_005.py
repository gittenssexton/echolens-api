"""Read-only public access check of documented official DR9 catalogue page.

Never assumes undocumented API endpoint, login cookies or authorization.
"""
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.request
import urllib.parse
import hashlib

OFFICIAL = "https://www.lamost.org/dr9/v2.0/catalogue"


class PublicLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag.lower()=="a" and "href" in d:
            self.links.append(d["href"])


def main():
    result={"checked_utc":datetime.now(timezone.utc).isoformat(),
            "official_public_catalogue_page":OFFICIAL,
            "fetch_status":"not_attempted",
            "public_lrs_general_csv_or_fits_links":[],
            "official_rows_retrieved":0,
            "reason":"No authenticated action or undocumented endpoint attempted"}
    try:
        req=urllib.request.Request(OFFICIAL,headers={"User-Agent":"EchoLens-Science-005/1.0"})
        with urllib.request.urlopen(req,timeout=25) as response:
            payload=response.read(1_500_000)
            result["http_status"]=response.status
            result["final_url"]=response.url.split("?")[0]
        p=PublicLinkParser()
        p.feed(payload.decode("utf-8",errors="replace"))
        candidates=[]
        for link in p.links:
            link=urllib.parse.urljoin(OFFICIAL,link)
            url=urllib.parse.urlsplit(link)
            if url.hostname not in {"www.lamost.org","lamost.org"}:
                continue
            if url.path.lower().endswith((".csv",".fits",".csv.gz",".fits.gz")):
                candidates.append(urllib.parse.urlunsplit((url.scheme,url.netloc,url.path,"","")))
        result["fetch_status"]="public_html_retrieved"
        result["html_sha256"]=hashlib.sha256(payload).hexdigest()
        result["public_lrs_general_csv_or_fits_links"]=sorted(set(candidates))
        result["reason"]=("Direct static download candidates found (still require explicit source verification)."
             if candidates else "No direct static CSV/FITS links in public HTML. Page may use script/authentication; no official rows accessed.")
    except Exception as exc:
        result["fetch_status"]="public_html_unavailable"
        result["reason"]=type(exc).__name__+": "+str(exc)[:180]
    target=Path("reports/experiment_005/access_check.json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
