from io import BytesIO
import numpy as np
import pytest
from astropy.table import Table,MaskedColumn
from astropy.io.votable import from_table,writeto
from scripts.gaia_model_readiness import decode,scalar,spectrum_id,one_source,SID

def test_binary_votable_keeps_exact_64bit_identifier_and_null():
    table=Table({'source_id':np.array([int(SID)],dtype=np.int64),'solution_id':np.array([4545469030156206080],dtype=np.int64)})
    table['temperature']=MaskedColumn([0.0],mask=[True])
    output=BytesIO();writeto(from_table(table),output,tabledata_format='binary2')
    row=one_source(decode(output.getvalue()))
    assert row['source_id']==SID and row['solution_id']=='4545469030156206080'
    assert row['temperature'] is None

@pytest.mark.parametrize('status',['ERROR','OVERFLOW'])
def test_failed_or_truncated_query_is_rejected(status):
    raw=f'<VOTABLE><RESOURCE><INFO name="QUERY_STATUS" value="{status}"/></RESOURCE></VOTABLE>'.encode()
    with pytest.raises(ValueError):decode(raw,True)

def test_partially_masked_coefficient_array_keeps_valid_components():
    assert scalar(np.ma.array([1.,2.,3.],mask=[False,True,False]))==[1.,None,3.]
    assert scalar(np.array(2.5))==2.5

def test_spectrum_identity_mismatch_is_rejected():
    with pytest.raises(ValueError):spectrum_id([{'params':{'source_id':'123'},'rows':[]}])
    with pytest.raises(ValueError):spectrum_id([{'params':{},'rows':[]}])

def test_single_source_lookup_does_not_accept_empty_or_multiple_rows():
    with pytest.raises(ValueError):one_source([{'rows':[]}])
    with pytest.raises(ValueError):one_source([{'rows':[{'source_id':SID},{'source_id':SID}]}])
