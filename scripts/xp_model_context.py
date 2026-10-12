"""Acquire small, explicitly theoretical atmosphere inputs and dust-map context.

These files are never catalog observations or fitted stellar parameters.
"""
import gzip,hashlib,json,urllib.request
from pathlib import Path
from datetime import datetime,timezone
from io import BytesIO
import numpy as np
from astropy.io import fits
from scripts.xp_covariance import OUT,write,sha

def main():
    directory=OUT/'model_context';directory.mkdir(parents=True,exist_ok=True);models=[]
    for metal in ['ckm05','ckp00']:
        for temperature in [4750,5000,5250]:
            name=f'{metal}_{temperature}';path=directory/f'{name}.fits.gz';mp=directory/f'{name}.manifest.json'
            if mp.exists():
                m=json.loads(mp.read_text());raw=gzip.decompress(path.read_bytes())
                if sha(raw)!=m['raw_sha256']:raise ValueError('Model hash mismatch')
            else:
                url=f'https://ssb.stsci.edu/trds/grid/ck04models/{metal}/{name}.fits'
                req=urllib.request.Request(url,headers={'User-Agent':'EchoLens/XP-model-input-audit'})
                with urllib.request.urlopen(req,timeout=35) as r:raw=r.read(2000001)
                if len(raw)>2000000 or not raw.startswith(b'SIMPLE'):raise ValueError('Expected small native atmosphere FITS')
                path.write_bytes(gzip.compress(raw,mtime=0));m={'url':url,'retrieved_utc':datetime.now(timezone.utc).isoformat(),'raw_sha256':sha(raw),'file':str(path.relative_to(OUT)),'classification':'theoretical atmosphere, not catalog observation'};write(mp,m)
            with fits.open(BytesIO(raw)) as hdus:
                if hdus[0].header.get('TEFF')!=temperature or hdus[0].header.get('LOG_Z')!=(-.5 if metal=='ckm05' else 0):raise ValueError('Atmosphere parameter/header mismatch')
                table=hdus[1].data;w=np.asarray(table['WAVELENGTH'],float)
                if not (np.isfinite(w).all() and (np.diff(w)>0).all()):raise ValueError('Invalid atmosphere wavelength grid')
                for gravity in ['g25','g30','g35']:
                    f=np.asarray(table[gravity],float)
                    if not np.isfinite(f).all() or (f<0).any() or not (f>0).any():raise ValueError('Invalid model flux column')
                models.append({'file':m['file'],'temperature_K':temperature,'metallicity_dex':-.5 if metal=='ckm05' else 0,'gravity_columns_checked':['g25','g30','g35'],'wavelength_range_angstrom':[float(w[0]),float(w[-1])],'rows':len(w),'column_units':{c.name:c.unit for c in hdus[1].columns},'model_header':{k:hdus[0].header.get(k) for k in ['TEFF','LOG_Z','METAL','FLUXUNIT']}})
            print('Preserved theoretical input',name,flush=True)
    write(OUT/'model_input_summary.json',{'classification':'model-input availability audit; no fit or stellar classification','models':models,'grid_interpolation_not_yet_validated':True,'dust_map_is_2D_context_not_stellar_extinction':True})
if __name__=='__main__':main()
