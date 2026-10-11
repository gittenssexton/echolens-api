import json
from pathlib import Path

NOTEBOOK = Path(__file__).with_name('R01_GBT_Cloud_Acquisition.ipynb')


def test_notebook_cells_compile():
    notebook = json.loads(NOTEBOOK.read_text())
    assert notebook['nbformat'] == 4
    assert notebook['cells'][0]['cell_type'] == 'markdown'
    for cell in notebook['cells']:
        if cell['cell_type'] == 'code':
            src = ''.join(cell['source'])
            if not src.lstrip().startswith('%pip'):
                compile(src, '<R01-colab-cell>', 'exec')


def test_config_and_record_selection_fail_closed():
    notebook = json.loads(NOTEBOOK.read_text())
    setup = ''.join(notebook['cells'][2]['source'])
    before_network = setup.split('resp = requests.get(ARCHIVE_PAGE')[0]
    g = {}
    exec(compile(before_network, '<configuration>', 'exec'), g)
    assert g['RUN_DOWNLOAD'] is False
    assert g['EXPECTED_BYTES'] == 3276424687
    assert g['TARGET'] == 'NGC6822'
    assert not g['approved_host']('https://evil.example.com/record.h5')
    assert g['approved_host']('https://blpd0.ssl.berkeley.edu/record.h5')

    html = '''<table><tr><td>2019-12-24 21:09:59</td><td>GBT</td><td>NGC6822</td><td>3276424687</td><td><a href="https://blpd0.ssl.berkeley.edu/record.h5">Download</a></td></tr>
      <tr><td>2019-12-24 21:15:20</td><td>HIP96950</td><td>3272829862</td></tr></table>'''
    rows = g['archive_row_candidates'](html)
    assert len(rows) == 1
    assert rows[0][1] == ['https://blpd0.ssl.berkeley.edu/record.h5']


def test_no_unauthorized_bulk_transfer():
    notebook = json.loads(NOTEBOOK.read_text())
    all_code = '\n'.join(''.join(c['source']) for c in notebook['cells'] if c['cell_type'] == 'code')
    assert 'RUN_DOWNLOAD = False' in all_code
    assert 'if count > EXPECTED_BYTES:' in all_code
    assert "int(result['size']) == count" in all_code
    assert "result.get('md5Checksum') == md5_hex" in all_code
