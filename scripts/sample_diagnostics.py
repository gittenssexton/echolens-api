"""Offline diagnostics of the frozen pilot; no anomaly scores or distance estimates."""
import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from app.registry import connect, DEFAULT_DB
from scripts.import_gaia import is_reference


def summarize(rows, field):
    values = np.array([r[field] for r in rows if r.get(field) is not None], dtype=float)
    return {'available': len(values), 'missing': len(rows) - len(values),
            'percentiles_5_50_95': np.percentile(values, [5, 50, 95]).tolist() if len(values) else None}


def generate(database, output):
    with connect(database) as conn:
        imports = conn.execute('SELECT manifest_json FROM imports').fetchall()
        rows = [json.loads(r[0]) for r in conn.execute('SELECT raw_json FROM stars ORDER BY source_id')]
    if len(imports) != 1:
        raise ValueError('Pilot diagnostics require exactly one import')
    manifest = json.loads(imports[0][0])
    if len(rows) != manifest['expected_rows']:
        raise ValueError('Registry count differs from source manifest')
    reference = [r for r in rows if is_reference(r)]
    fields = ['phot_g_mean_mag', 'bp_rp', 'parallax', 'parallax_over_error', 'ruwe',
              'ra_error', 'dec_error', 'phot_bp_mean_flux_over_error', 'phot_rp_mean_flux_over_error']
    report = {
        'catalog': 'Gaia DR3', 'raw_sha256': manifest['raw_sha256'],
        'database_sha256': hashlib.sha256(Path(database).read_bytes()).hexdigest(),
        'sample_count': len(rows), 'provisional_reference_count': len(reference),
        'reference_definition': manifest['validation']['provisional_reference_criteria'],
        'negative_parallax_count': sum(r.get('parallax') is not None and r['parallax'] < 0 for r in rows),
        'variable_flag_counts': {flag: sum(r.get('phot_variable_flag') == flag for r in rows)
                                 for flag in sorted({r.get('phot_variable_flag') for r in rows}, key=str)},
        'distributions': {name: {field: summarize(group, field) for field in fields}
                          for name, group in [('all_sources', rows), ('provisional_reference', reference)]},
        'limitations': [
            'Classification-selected random-index pilot; not a volume-complete or magnitude-complete census.',
            'Reference cuts select brighter, better measured sources; unmatched cohort comparisons are biased.',
            'Gaia variability flags are pipeline classifications; NOT_AVAILABLE is not evidence of constant brightness.',
            'Negative measured parallaxes are retained; no inverse-parallax distances are calculated.',
            'Plots summarize observed catalog values and quality indicators, not technosignature evidence.'
        ]
    }
    if report['provisional_reference_count'] != manifest['validation']['provisional_reference_count']:
        raise ValueError('Reference screen differs from validated import')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'sample_diagnostics.json').write_text(json.dumps(report, indent=2) + '\n')
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig = plt.figure(figsize=(13, 9), layout='constrained')
    ax = fig.add_subplot(2, 2, 1, projection='mollweide')
    longitude = np.radians([((r['l'] + 180) % 360) - 180 for r in rows])
    latitude = np.radians([r['b'] for r in rows])
    sky = ax.hexbin(-longitude, latitude, gridsize=55, mincnt=1, cmap='viridis', rasterized=True)
    ax.set_xticklabels(['150°', '120°', '90°', '60°', '30°', '0°', '330°', '300°', '270°', '240°', '210°'])
    fig.colorbar(sky, ax=ax, orientation='horizontal', shrink=.7, pad=.12,
                 label='Source count per projection bin (not equal solid angle)')
    ax.grid(alpha=.25)
    ax.set_title('Sky coverage: Galactic coordinates (10,000 sources)')
    ax.set_xlabel('Longitude increases to the left; density shown in projection bins')
    for position, field, xlabel, bins in [
        (2, 'phot_g_mean_mag', 'Observed Gaia G magnitude', np.linspace(9, 23, 40)),
        (3, 'bp_rp', 'Observed BP − RP color (mag)', np.linspace(-3, 8, 45)),
        (4, 'parallax_over_error', 'Measured parallax / standard error', np.linspace(-20, 100, 60))
    ]:
        ax = fig.add_subplot(2, 2, position)
        for group, label, color in [(rows, 'All sources', '#335d9e'), (reference, 'Provisional reference', '#c66025')]:
            values = [r[field] for r in group if r.get(field) is not None]
            in_range = sum(bins[0] <= v <= bins[-1] for v in values)
            # Weight against every available value, including those outside display limits.
            ax.hist(values, bins=bins, weights=np.full(len(values), 100 / len(values)) if values else [],
                    histtype='step', linewidth=1.8, color=color,
                    label=f'{label}: {len(group)-len(values)} missing, {len(values)-in_range} outside plot')
        ax.set_xlabel(xlabel)
        ax.set_ylabel('Percent of available values per bin')
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=.2)
    fig.suptitle(f'EchoLens Gaia DR3 pilot — observation and control-selection diagnostics\n'
                 f'{len(reference):,} provisional reference candidates; no anomaly or technology scores', fontsize=15)
    fig.savefig(output / 'sample_diagnostics.png', dpi=160)
    plt.close(fig)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=str(DEFAULT_DB))
    parser.add_argument('--output', default='reports')
    args = parser.parse_args()
    result = generate(args.database, args.output)
    print(json.dumps({k: result[k] for k in ('sample_count', 'provisional_reference_count',
                                          'negative_parallax_count', 'variable_flag_counts')}, indent=2))
