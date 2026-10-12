"""Bounded HTTP/TAP reliability for EchoLens research acquisition.

Transport only. Scientific catalog definitions and identities are not interchangeable.
Uses stdlib urllib; deterministic unit tests inject opener, sleeper and RNG.
"""
from __future__ import annotations
import datetime as dt
import email.utils
import hashlib
import json
import random
import socket
import time
from urllib import error, request

TRANSIENT_HTTP={408,429,500,502,503,504}


class TAPPermanentError(RuntimeError):
    """Nonretryable response, including bad ADQL, invalid schema, auth failure."""


class TAPExhausted(RuntimeError):
    """Transient response persisted past total per-request attempt budget."""


def retry_after_seconds(value, now=None):
    if value is None:
        return None
    value=str(value).strip()
    try:
        return max(0.0,float(value))
    except (TypeError,ValueError):
        try:
            when=email.utils.parsedate_to_datetime(value)
            if when.tzinfo is None:
                when=when.replace(tzinfo=dt.timezone.utc)
            return max(0.0,(when-(now or dt.datetime.now(dt.timezone.utc))).total_seconds())
        except (TypeError,ValueError,OverflowError):
            return None


def request_bytes(url, *, data=None, headers=None, timeout=90, attempts=4,
                  max_bytes=50_000_000, max_wait=60, opener=None,
                  sleep=None, random_fraction=None, audit=None):
    """Retry ONLY transient errors; never silently return another catalog's bytes.

    Per-attempt timeout applies separately; retry cap + delay are finite.
    Return immutable raw response and provenance. No requests are made at import.
    """
    if attempts<1 or attempts>8 or timeout<=0 or max_bytes<=0 or max_wait<0:
        raise ValueError("Invalid bounded retry configuration")
    opener=opener or request.urlopen
    sleep=sleep or time.sleep
    random_fraction=random_fraction or random.random
    history=[]
    for i in range(attempts):
        req=request.Request(url,data=data,headers=headers or {},
                            method="POST" if data is not None else "GET")
        try:
            with opener(req,timeout=timeout) as response:
                raw=response.read(max_bytes+1)
                if len(raw)>max_bytes:
                    raise TAPPermanentError("Response exceeds configured byte limit")
                status=getattr(response,"status",200)
                if status in TRANSIENT_HTTP:
                    raise error.HTTPError(url,status,"Transient status",
                        getattr(response,"headers",{}),None)
                if status>=400:
                    raise TAPPermanentError("Nonretryable HTTP "+str(status))
                provenance={"request_url":url,"method":req.get_method(),
                    "attempt_count":i+1,"attempt_log":history,
                    "http_status":status,"received_bytes":len(raw),
                    "sha256":hashlib.sha256(raw).hexdigest(),
                    "response_headers":{k:response.headers.get(k) for k in
                        ("Date","Content-Type","ETag","Last-Modified")}}
                if audit is not None:audit.extend(history)
                return raw,provenance
        except error.HTTPError as exc:
            status=exc.code
            if status not in TRANSIENT_HTTP:
                raise TAPPermanentError(f"Nonretryable HTTP {status} for {url}") from exc
            reason="http_"+str(status)
            ra=retry_after_seconds(exc.headers.get("Retry-After")) if exc.headers else None
        except (error.URLError,TimeoutError,socket.timeout,ConnectionError,OSError) as exc:
            reason=type(exc).__name__
            ra=None
        if i+1==attempts:
            history.append({"attempt":i+1,"transient_error":reason,"retry":False})
            if audit is not None:audit.extend(history)
            raise TAPExhausted(f"TAP request failed after {attempts} attempts: {reason}")
        jitter=float(random_fraction())
        if not 0<=jitter<=1:
            raise ValueError("Random retry fraction outside [0,1]")
        backoff=min(max_wait,2**i*(1+jitter))
        seconds=min(max_wait,max(backoff,ra or 0))
        history.append({"attempt":i+1,"transient_error":reason,"retry":True,
                        "retry_after_s":ra,"sleep_s":seconds})
        sleep(seconds)
    raise AssertionError("unreachable")


def encode_tap(endpoint, adql, fmt="csv", maxrec="9"):
    """Preserve provider's own table/schema; never transplant IRSA ADQL to CDS."""
    from urllib.parse import urlencode
    params={"REQUEST":"doQuery","LANG":"ADQL","FORMAT":fmt,
            "QUERY":adql,"MAXREC":str(maxrec)}
    return endpoint+"?"+urlencode(params)


def allwise_irsa_cone(ra,dec,radius_arcsec=2):
    import math
    if not all(isinstance(x,(int,float)) and math.isfinite(x)
               for x in (ra,dec,radius_arcsec)):
        raise ValueError("Nonfinite cone request")
    if not (0<=ra<360 and -90<=dec<=90 and 0<radius_arcsec<=30):
        raise ValueError("Invalid coordinate or unconstrained radius")
    fields=("designation,ra,dec,w1mpro,w1sigmpro,w2mpro,w2sigmpro,"
            "w3mpro,w3sigmpro,w4mpro,w4sigmpro,w3snr,w4snr,"
            "cc_flags,ext_flg,ph_qual")
    return (f"SELECT TOP 8 {fields} FROM allwise_p3as_psd "
        f"WHERE CONTAINS(POINT('ICRS',ra,dec),"
        f"CIRCLE('ICRS',{ra!r},{dec!r},{radius_arcsec/3600!r}))=1 "
        "ORDER BY designation ASC")


def catalog_provider_spec(provider):
    """Never assume cross-provider field/table equivalence."""
    if provider=="IRSA_AllWISE":
        return {"endpoint":"https://irsa.ipac.caltech.edu/TAP/sync",
                "table":"allwise_p3as_psd","schema":"IRSA-native"}
    raise ValueError("Unvalidated provider/table: no silent TAP mirror fallback")
