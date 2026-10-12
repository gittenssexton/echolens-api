"""Produce the pilot report and scientific figure from frozen replay results."""
from collections import Counter
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def build(directory=Path('reports/experiment_001b')):
    directory = Path(directory)
    r = json.loads((directory/'results.json').read_text())
    unique = [t for t in r['targets'] if t['association_status']=='provisional_unique']
    candidates = [next(c for c in t['candidates'] if c['eligible']) for t in unique]
    bands = ['w1','w2','w3','w4']
    passing = [sum(c['photometry'][b]['quality_pass'] for c in candidates) for b in bands]
    limits = [sum(c['photometry'][b]['kind']=='upper_limit_95pct_flux' for c in candidates) for b in bands]
    failures = {b:Counter(f for c in candidates for f in c['photometry'][b]['quality_failures']) for b in bands}
    flags = Counter(f for t in unique for f in t['review_flags'])
    fig, axes = plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
    counts = r['association_counts']
    axes[0].bar(['Provisional\nunique','Ambiguous','No eligible\ncandidate'],list(counts.values()),color=['#326e9b','#c58a29','#747b86'])
    axes[0].set(ylabel='Gaia targets',ylim=(0,100),title='100 frozen Gaia targets')
    for i,v in enumerate(counts.values()): axes[0].text(i,v+1,str(v),ha='center')
    x = list(range(4))
    axes[1].bar([v-.2 for v in x],passing,width=.4,label='Operational quality pass',color='#326e9b')
    axes[1].bar([v+.2 for v in x],limits,width=.4,label='95% flux upper limit',color='#c58a29')
    axes[1].set(xticks=x,xticklabels=[b.upper() for b in bands],ylabel='Provisional unique associations',ylim=(0,100),title='Per-band quality and censoring')
    axes[1].legend(frameon=False,fontsize=8)
    fig.suptitle('EchoLens 001B · AllWISE coverage pilot · no excess inference',fontsize=13)
    fig.savefig(directory/'diagnostics.png',dpi=160)
    plt.close(fig)
    text = f'''# Experiment 001B results

The frozen 100-star Gaia reference subset yielded {counts['provisional_unique']} provisional unique
AllWISE associations, {counts['ambiguous']} ambiguous associations, and
{counts['no_eligible_candidate']} targets without an eligible candidate.
{r['w1_w2_ready_for_image_review']} targets passed the conservative W1/W2 screen for subsequent image review.
These are data-readiness outcomes, not infrared excesses or technosignature detections.

Retrieved {r['unique_allwise_rows']} distinct real AllWISE catalog sources with all
{r['allwise_fields']} fields preserved. Native FITS and original field metadata retain
measurement uncertainties, missingness, quality flags and source provenance.
The selection was frozen before retrieval. The separately committed transport
amendment replaced unsupported multi-cone queries with individual cone requests.

## Per-band outcomes

Counts below use only the {len(unique)} provisional unique associations. Quality
passes and flux upper limits are distinct categories; other failed or missing
measurements remain in the observations and results.

| Band | Quality passes | 95% flux upper limits |
| --- | ---: | ---: |
'''
    for b,p,l in zip(bands,passing,limits): text += f'| {b.upper()} | {p} | {l} |\n'
    text += '\n## Review flags and quality failures\n\n'
    text += 'Flags can overlap: '+(', '.join(f'{k}: {v}' for k,v in sorted(flags.items())) or 'none')+'.\n\n'
    for b in bands:
        text += f"{b.upper()}: "+(', '.join(f'{k}: {v}' for k,v in sorted(failures[b].items())) or 'no failures')+'.\n\n'
    text += '''## Limits and next step

All associations are provisional. Gaia motion propagation excludes perspective
acceleration and annual parallax, and this pilot does not combine astrometric
covariances or estimate match probabilities. Stationary AllWISE epoch fallbacks
are approximate. Catalog blending and the finite retrieval cone can hide sources.
The Gaia reference subset is selected for measurement quality and is not a
population-representative or independently validated astrophysical control group.

Review images and positional covariance for the passing targets, then use optical,
near-infrared and WISE photometry in a photosphere model with extinction and
uncertainties before testing excess. Dust, companions and background objects
remain ordinary explanations to investigate. Preserve this pilot unchanged.

## Reproduction and provenance

```
python -m scripts.wise_pilot replay --output /tmp/wise-replay
cmp reports/experiment_001b/results.json /tmp/wise-replay/results.json
cmp reports/experiment_001b/observations.json /tmp/wise-replay/observations.json
python -m scripts.wise_pilot_report
```

Replay uses only committed snapshots; do not run `fetch` to reproduce this result.
The committed `data/wise_001b.tar.gz` contains the native responses and
`wise_001b/manifest.json` with all queries, timestamps, raw checksums and
the transport amendment hash; `selection.json` for exact Gaia IDs and the protocol
hash; and `observations.json` for metadata, original measurements and units.
Derived associations and screens are in `results.json`, separate from observations.
Derived separation output uses the documented five-decimal (10 microarcsecond)
half-up display quantizer after legacy six-decimal normalization. Eligibility
uses unrounded values; native observations and uncertainties are never rounded.
See [the display precision amendment](../../docs/EXPERIMENT_001B_DISPLAY_PRECISION_AMENDMENT.md).

Data: NASA/IPAC IRSA AllWISE Source Catalog (`allwise_p3as_psd`), WISE
(UCLA/JPL-Caltech) and NEOWISE (JPL-Caltech), funded by NASA. Gaia mission data
processed by ESA's Gaia Data Processing and Analysis Consortium (DPAC).

Catalog definitions: https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html

IRSA TAP: https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html
'''
    (directory/'REPORT.md').write_text(text)


if __name__=='__main__':
    build()
