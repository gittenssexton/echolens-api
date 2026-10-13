import json
import numpy as np
import pytest
from scripts import project_checkpoint_v13 as checkpoint


def test_missing_motion_stays_unresolved():
    source={'ra':359.99,'dec':20,'ref_epoch':2016,'pmra':None,'pmdec':1}
    assert checkpoint.coord(source,2010) is None
    assert checkpoint.coord(source) is not None


def test_proper_motion_wraps_ra():
    source={'ra':359.9999,'dec':0,'ref_epoch':2016,'pmra':3600,'pmdec':0}
    assert checkpoint.coord(source,2017).ra.deg==pytest.approx(.0009)


def test_altered_native_response_rejected(tmp_path):
    p=tmp_path/'original.json';p.write_text('{"value":1}')
    checkpoint.write(p.with_suffix('.manifest.json'),{'sha256':checkpoint.sha(p)})
    p.write_text('{"value":2}')
    with pytest.raises(ValueError,match='changed'):checkpoint.verify(p)


def test_reserved_role_is_rejected(tmp_path,monkeypatch):
    root=tmp_path/'root';out=root/'reports/project_checkpoint_v13';path=root/'reports/calibration_cohort_v10/results.json'
    rows=[{'source_id':str(i),'analysis_role':'calibration_development','joint_ready':True} for i in range(9)]
    rows[0]['analysis_role']='validation_reserved';checkpoint.write(path,rows)
    checkpoint.write(out/'design.json',{'development_source_ids':[str(i) for i in range(9)],'input_sha256':{'reports/calibration_cohort_v10/results.json':checkpoint.sha(path)}})
    monkeypatch.setattr(checkpoint,'ROOT',root);monkeypatch.setattr(checkpoint,'OUT',out)
    with pytest.raises(ValueError,match='reserved'):checkpoint.inputs()
