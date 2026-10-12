"""Offline deterministic transport failures, no astronomy query or network access."""
import datetime as dt
import io
from urllib import error
import pytest
from scripts.tap_reliability import (request_bytes,retry_after_seconds,
    TAPExhausted,TAPPermanentError,allwise_irsa_cone,catalog_provider_spec)


class Response:
    status=200
    headers={"Content-Type":"text/csv","Date":"Mon, 12 Oct 2026 12:00:00 GMT"}
    def __init__(self,payload=b"header\n"):self.payload=payload
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.payload[:n]


def http(code,retry_after=None):
    return error.HTTPError("https://example.invalid",code,"bad",
        {"Retry-After":retry_after} if retry_after is not None else {},None)


def test_rate_limit_retry_after_and_raw_hash():
    results=[http(429,"5"),Response(b"a,b\n1,2\n")]
    waits=[]
    def opener(req,timeout):
        result=results.pop(0)
        if isinstance(result,Exception):raise result
        return result
    raw,meta=request_bytes("https://example.invalid",opener=opener,
        sleep=waits.append,random_fraction=lambda:0,attempts=3)
    assert raw==b"a,b\n1,2\n"
    assert waits==[5]
    assert meta["attempt_count"]==2 and len(meta["attempt_log"])==1
    assert len(meta["sha256"])==64


def test_transient_503_backoff_is_exponential_and_bounded():
    events=[http(503),http(502),Response()]
    sleeps=[]
    def opener(*args,**kwargs):
        v=events.pop(0)
        if isinstance(v,Exception):raise v
        return v
    request_bytes("https://example.invalid",opener=opener,
        sleep=sleeps.append,random_fraction=lambda:0.5)
    assert sleeps==[1.5,3.0]


def test_timeout_and_exhaustion_do_not_become_no_match():
    def fail(*a,**k):raise TimeoutError("slow TAP")
    sleeps=[]
    with pytest.raises(TAPExhausted):
        request_bytes("https://example.invalid",opener=fail,attempts=3,
            sleep=sleeps.append,random_fraction=lambda:0)
    assert sleeps==[1,2]


@pytest.mark.parametrize("code",[400,401,403,404,422])
def test_permanent_schema_auth_and_bad_request_no_retry(code):
    calls=[]
    def fail(*a,**kw):
        calls.append(1)
        raise http(code)
    with pytest.raises(TAPPermanentError):
        request_bytes("https://example.invalid",opener=fail,
            sleep=lambda _:pytest.fail("permanent error should not sleep"))
    assert len(calls)==1


def test_successful_empty_response_is_distinct_from_network_error():
    raw,meta=request_bytes("https://example.invalid",
        opener=lambda *a,**k:Response(b"column\n"))
    assert raw==b"column\n" and meta["attempt_count"]==1


def test_retry_after_date_and_invalid_are_safe():
    now=dt.datetime(2026,10,12,tzinfo=dt.timezone.utc)
    assert retry_after_seconds("Mon, 12 Oct 2026 00:00:08 GMT",now)==8
    assert retry_after_seconds("nope",now) is None


def test_oversized_raw_response_rejected_without_retry():
    with pytest.raises(TAPPermanentError,match="byte limit"):
        request_bytes("https://example.invalid",max_bytes=2,
                      opener=lambda *a,**k:Response(b"12345"))


def test_unvalidated_tap_mirror_and_unordered_top1_rejected():
    assert catalog_provider_spec("IRSA_AllWISE")["table"]=="allwise_p3as_psd"
    with pytest.raises(ValueError,match="Unvalidated"):
        catalog_provider_spec("CDS_AllWISE")
    q=allwise_irsa_cone(100.1,-12.1)
    assert "TOP 8" in q and "ORDER BY designation ASC" in q
    assert "TOP 1" not in q
    for ra,dec,radius in [(-1,0,2),(10,91,2),(1,1,300)]:
        with pytest.raises(ValueError):
            allwise_irsa_cone(ra,dec,radius)
