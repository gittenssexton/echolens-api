"""Audit must fail closed on validation leakage and native-product changes."""
import json
import numpy as np
import pytest
from astropy.io import fits
from scripts import development_image_audit as audit


def test_reserved_role_rejected_even_with_matching_input_hash(tmp_path, monkeypatch):
    root=tmp_path/'project';out=root/'reports/development_image_audit_v12'
    source=root/'reports/calibration_cohort_v10/results.json'
    rows=[{'source_id':str(i),'analysis_role':'calibration_development','joint_ready':True} for i in range(9)]
    rows[3]['analysis_role']='validation_reserved'
    audit.write(source,rows)
    audit.write(out/'design.json',{'development_source_ids':[str(i) for i in range(9)],'readiness_results_sha256':audit.digest(source)})
    monkeypatch.setattr(audit,'ROOT',root);monkeypatch.setattr(audit,'OUT',out)
    with pytest.raises(ValueError,match='Reserved'):
        audit.context()


def native_product(tmp_path, monkeypatch):
    monkeypatch.setattr(audit,'OUT',tmp_path)
    p=tmp_path/'raw'/'123'/'W3.fits';p.parent.mkdir(parents=True)
    h=fits.Header({'BAND':3,'COADDID':'0000p000_ac51','BUNIT':'DN','FILETYPE':'intensity image'})
    fits.writeto(p,np.ones((5,5)),h)
    audit.write(p.with_suffix('.manifest.json'),{'source_id':'123','band':'W3','coadd_id':'0000p000_ac51','raw_sha256':audit.digest(p)})
    return p


def test_native_bytes_tamper_rejected(tmp_path,monkeypatch):
    p=native_product(tmp_path,monkeypatch)
    p.write_bytes(p.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='provenance'):
        audit.image_for('123','W3')


def test_wrong_band_rejected_even_with_updated_hash(tmp_path,monkeypatch):
    p=native_product(tmp_path,monkeypatch)
    with fits.open(p,mode='update') as h:h[0].header['BAND']=1
    meta=json.loads(p.with_suffix('.manifest.json').read_text());meta['raw_sha256']=audit.digest(p)
    audit.write(p.with_suffix('.manifest.json'),meta)
    with pytest.raises(ValueError,match='band'):
        audit.image_for('123','W3')
