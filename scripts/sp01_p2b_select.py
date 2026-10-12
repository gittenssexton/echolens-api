"""Freeze prospective SP01-P2B source selection from GALAH catalogue metadata.

No spectra, anomaly scores, network requests, or generated astronomical observations.
Preserve native 64-bit Gaia source IDs as decimal STRINGS; never via floats.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import re

PROTOCOL = 'echolens-sp01-p2b-v1'
EXPOSED = {'3064554891927687296', '6053735173729807872', '6130627011126533760'}
REQUIRED = (
    'gaiadr3_source_id','sobject_id','teff','logg','fe_h',
    'snr_px_ccd2','snr_px_ccd3','flag_sp','flag_red',
    'phot_g_mean_mag','bp_rp','ruwe'
)
POSITIVE_REQUIRED = ('gaiadr3_source_id','classification','reference_url')
STRATA = ('cool_low','cool_high','warm_low','warm_high')

class SelectionBlocked(ValueError):
    """Not enough preregistered sources; preserve inputs, no completed manifest."""


def exact_source_id(value: str, *, field: str) -> str:
    value = value.strip()
    if not re.fullmatch(r'[1-9][0-9]{8,18}', value):
        raise ValueError(f'{field} must be an unrounded positive decimal identifier: {value!r}')
    if int(value) >= 2**63:
        raise ValueError(f'{field} exceeds signed 64-bit range')
    return value


def digest_file(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_input(path:Path, columns)->list[dict]:
    with path.open(newline='',encoding='utf-8-sig') as f:
        rdr=csv.DictReader(f)
        if rdr.fieldnames is None:
            raise ValueError(f'empty CSV {path.name}')
        absent = sorted(set(columns)-set(rdr.fieldnames))
        if absent:
            raise ValueError(f'missing required columns in {path.name}: {absent}')
        return list(rdr)


def numeric(row:dict,key:str)->float:
    try:
        value=float(row[key])
    except (ValueError,TypeError,KeyError) as exc:
        raise ValueError(f'missing/unparseable {key}') from exc
    if not math.isfinite(value):
        raise ValueError(f'nonfinite {key}')
    return value


def intflag(row:dict,key:str)->int:
    raw=str(row[key]).strip()
    if not re.fullmatch(r'[0-9]+',raw):
        raise ValueError(f'invalid integer {key}')
    return int(raw)


def ordinary_eligible(row:dict)->tuple[bool,str|None]:
    try:
        if intflag(row,'flag_sp')!=0 or intflag(row,'flag_red')!=0:
            return False,'flag_not_zero'
        teff,logg,feh=(numeric(row,k) for k in ('teff','logg','fe_h'))
        g,bprp,ruwe=(numeric(row,k) for k in ('phot_g_mean_mag','bp_rp','ruwe'))
        snr2,snr3=(numeric(row,k) for k in ('snr_px_ccd2','snr_px_ccd3'))
        if not (4800<=teff<6400 and 4.0<=logg<=4.65 and -.8<=feh<=.5):
            return False,'ordinary_stellar_parameter_window'
        if not (snr2>30 and snr3>30 and ruwe<1.4):
            return False,'ordinary_quality_window'
        if not (0<g<30 and -1<bprp<6 and ruwe>0):
            return False,'ordinary_photometry_window'
    except ValueError as exc:
        return False,'invalid_or_missing_'+str(exc).split()[0]
    return True,None


def stratum(row:dict)->str:
    t='cool' if numeric(row,'teff')<5600 else 'warm'
    s='low' if numeric(row,'snr_px_ccd3')<60 else 'high'
    return t+'_'+s


def hash_rank(source_id:str)->str:
    return hashlib.sha256((PROTOCOL+':'+source_id).encode('ascii')).hexdigest()


def build(catalog:Path, positives:Path, *, raw_source_sha256:str, catalog_source:str)->dict:
    if not re.fullmatch(r'[a-fA-F0-9]{64}',raw_source_sha256):
        raise ValueError('native upstream raw catalogue SHA-256 is required')
    if not catalog_source.strip():
        raise ValueError('catalogue release, query and source reference required')
    records=csv_input(catalog,REQUIRED)
    positive_rows=csv_input(positives,POSITIVE_REQUIRED)
    groups:dict[str,list[dict]]=defaultdict(list)
    for row in records:
        sid=exact_source_id(row['gaiadr3_source_id'],field='gaiadr3_source_id')
        vid=exact_source_id(row['sobject_id'],field='sobject_id')
        groups[sid].append(dict(row,sobject_id=vid))
    positives_map={}
    for row in positive_rows:
        sid=exact_source_id(row['gaiadr3_source_id'],field='positive Gaia ID')
        if sid in positives_map:
            raise ValueError('duplicate independent positive labels for one source')
        if not row['classification'].strip() or not row['reference_url'].strip().startswith(('https://','http://')):
            raise ValueError('positive labels need nonblank classification and external literature URL')
        positives_map[sid]={'classification':row['classification'].strip(),
                             'reference_url':row['reference_url'].strip()}
    if not positives_map:
        raise SelectionBlocked('No independently labelled positive-source input')
    invalid_counts=Counter()
    eligible={k:[] for k in STRATA}
    positive_pool=[]
    for sid,visits in groups.items():
        # Observations of same physical Gaia source are never independent stars.
        representative=min(visits,key=lambda r:int(r['sobject_id']))
        if sid in EXPOSED:
            invalid_counts['development_exposed']+=1
            continue
        if sid in positives_map:
            positive_pool.append((sid,representative,visits,positives_map[sid]))
            continue
        ok,reason=ordinary_eligible(representative)
        if not ok:
            invalid_counts[reason]+=1
            continue
        eligible[stratum(representative)].append((sid,representative,visits,None))
    counts={k:len(v) for k,v in eligible.items()}
    if any(counts[k]<10 for k in STRATA) or len(positive_pool)<10:
        raise SelectionBlocked('Insufficient source-level candidates; no frozen manifest written. '
                               +json.dumps({'available_ordinary_by_stratum':counts,
                                            'available_independently_labeled_positives':len(positive_pool),
                                            'excluded_reasons':dict(invalid_counts)},sort_keys=True))
    selected=[]
    for k in STRATA:
        candidates=sorted(eligible[k],key=lambda t:hash_rank(t[0]))[:10]
        for i,item in enumerate(candidates):
            selected.append(make_row(item,'calibration' if i<5 else 'holdout',k))
    for item in sorted(positive_pool,key=lambda t:hash_rank(t[0]))[:10]:
        selected.append(make_row(item,'natural_positive_only','positive'))
    ids=[x['gaia_dr3_source_id'] for x in selected]
    if len(selected)!=50 or len(ids)!=len(set(ids)) or EXPOSED.intersection(ids):
        raise AssertionError('manifest uniqueness/exposure invariant broken')
    return {'schema':PROTOCOL,'research_stage':'engineering source cohort only; no downloaded spectra',
        'science_ready':False,'source_selection_uses_spectra':False,
        'catalog_release_and_query':catalog_source,'catalog_raw_sha256':raw_source_sha256.lower(),
        'catalog_csv_sha256':digest_file(catalog),'positive_label_csv_sha256':digest_file(positives),
        'rules':{'ordinary_per_stratum':10,'calibration_per_stratum':5,'holdout_per_stratum':5,
                 'natural_positives':10,'previously_exposed_ids':sorted(EXPOSED)},
        'input_rows':len(records),'distinct_catalog_sources':len(groups),
        'preselection_excluded_source_counts':dict(sorted(invalid_counts.items())),
        'eligible_ordinary_counts_per_stratum':counts,'labelled_positive_count':len(positive_pool),
        'cohort_counts':dict(sorted(Counter(x['role'] for x in selected).items())),
        'selected_sources':selected}


def make_row(item,role,stratum_name):
    sid,representative,visits,positive=item
    return {'gaia_dr3_source_id':sid,'representative_sobject_id':representative['sobject_id'],
        'all_known_visit_sobject_ids':sorted(set(r['sobject_id'] for r in visits),key=int),
        'role':role,'stratum':stratum_name,'selection_sha256':hash_rank(sid),
        'teff':representative['teff'],'logg':representative['logg'],'fe_h':representative['fe_h'],
        'snr_px_ccd2':representative['snr_px_ccd2'],
        'snr_px_ccd3':representative['snr_px_ccd3'],
        'flag_sp':representative['flag_sp'],'flag_red':representative['flag_red'],
        'G_mag':representative['phot_g_mean_mag'],'bp_rp':representative['bp_rp'],
        'ruwe':representative['ruwe'],
        'positive_classification':positive['classification'] if positive else '',
        'positive_reference_url':positive['reference_url'] if positive else ''}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog-csv',required=True,type=Path)
    parser.add_argument('--positive-csv',required=True,type=Path)
    parser.add_argument('--raw-source-sha256',required=True)
    parser.add_argument('--catalog-source',required=True)
    parser.add_argument('--manifest-json',required=True,type=Path)
    parser.add_argument('--manifest-csv',required=True,type=Path)
    args=parser.parse_args()
    try:
        result=build(args.catalog_csv,args.positive_csv,
                     raw_source_sha256=args.raw_source_sha256,catalog_source=args.catalog_source)
    except SelectionBlocked as exc:
        parser.exit(status=2,message='BLOCKED: '+str(exc)+'\n')
    args.manifest_json.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    columns=[k for k in result['selected_sources'][0] if k!='all_known_visit_sobject_ids']+['all_known_visit_sobject_ids']
    with args.manifest_csv.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns)
        writer.writeheader()
        for row in result['selected_sources']:
            copy=dict(row,all_known_visit_sobject_ids=';'.join(row['all_known_visit_sobject_ids']))
            writer.writerow(copy)
    print(json.dumps({'selected':50,'source_level_splits':result['cohort_counts'],
                      'catalog_csv_sha256':result['catalog_csv_sha256']},indent=2))

if __name__=='__main__':
    main()
