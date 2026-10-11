"""Execute the frozen Experiment 001A feasibility pilot offline."""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from scripts.import_gaia import is_reference, parse_snapshot, validate

ROOT = Path(__file__).resolve().parents[1]
PARAMETERS = {'g_mag': .5, 'bp_rp': .25, 'abs_b_deg': 10,
              'parallax_snr_factor': 2, 'ruwe_factor': 2}
FIELDS = ('phot_g_mean_mag', 'bp_rp', 'b', 'parallax_over_error', 'ruwe')
STAGES = ('G magnitude', 'color', 'absolute Galactic latitude', 'parallax SNR', 'RUWE')


def covariates(row):
    invalid = [name for name in FIELDS if row.get(name) is None
               or not math.isfinite(row[name])
               or (name in ('parallax_over_error', 'ruwe') and row[name] <= 0)]
    return None if invalid else [row[FIELDS[0]], row[FIELDS[1]], abs(row[FIELDS[2]]),
                                 row[FIELDS[3]], row[FIELDS[4]]], invalid


def differences(a, b):
    return [abs(a[0]-b[0])/.5, abs(a[1]-b[1])/.25, abs(a[2]-b[2])/10,
            abs(math.log2(a[3]/b[3])), abs(math.log2(a[4]/b[4]))]


def maximum_matching(edges, order):
    """Deterministic augmenting paths; maximize count, without control reuse."""
    owner = {}
    def augment(target, visited):
        for control in edges[target]:
            if control in visited:
                continue
            visited.add(control)
            if control not in owner or augment(owner[control], visited):
                owner[control] = target
                return True
        return False
    for target in order:
        augment(target, set())
    return {target: control for control, target in owner.items()}


def execute(output, selection=None):
    output = Path(output)
    selection = Path(selection or ROOT/'reports/experiment_001a/selection.json')
    frozen = json.loads(selection.read_text())
    protocol = ROOT/'docs/EXPERIMENT_001A.md'
    if hashlib.sha256(protocol.read_bytes()).hexdigest() != frozen['protocol_sha256']:
        raise ValueError('Frozen protocol changed')
    if frozen['tolerances'] != PARAMETERS or frozen['minimum_matched_targets'] != 50:
        raise ValueError('Unregistered matching policy')
    payload = gzip.decompress((ROOT/'data/gaia_dr3.raw.gz').read_bytes())
    if hashlib.sha256(payload).hexdigest() != frozen['raw_sha256']:
        raise ValueError('Frozen observations changed')
    manifest = json.loads((ROOT/'data/gaia_dr3.manifest.json').read_text())
    _, rows = parse_snapshot(payload, manifest, ROOT/'data')
    validate(rows, 10000)
    controls = sorted([r['source_id'] for r in rows if is_reference(r)], key=int)
    target_ids = [r['source_id'] for r in sorted([r for r in rows if not is_reference(r)],
        key=lambda r: (hashlib.sha256((frozen['selection_salt']+r['source_id']).encode()).hexdigest(),
                       int(r['source_id'])))[:100]]
    if controls != frozen['control_source_ids'] or target_ids != frozen['target_source_ids']:
        raise ValueError('Frozen source selection changed')
    by_id = {r['source_id']: r for r in rows}
    control_vectors = {sid: covariates(by_id[sid])[0] for sid in controls}
    if any(v is None for v in control_vectors.values()):
        raise ValueError('Reference screen produced missing matching covariates')
    records, edges = {}, {}
    for sid in target_ids:
        vector, invalid = covariates(by_id[sid])
        eligible, counts = [], [0]*5
        if vector is not None:
            for control, other in control_vectors.items():
                scaled = differences(vector, other)
                for stage in range(5):
                    if all(d <= 1 for d in scaled[:stage+1]):
                        counts[stage] += 1
                if all(d <= 1 for d in scaled):
                    eligible.append((sum(d*d for d in scaled), int(control), control))
        edges[sid] = [item[2] for item in sorted(eligible)]
        records[sid] = {'source_id': sid, 'covariates': vector,
                        'missing_or_nonpositive_fields': invalid,
                        'cumulative_eligible_counts': dict(zip(STAGES, counts)),
                        'eligible_control_ids': edges[sid]}
    assignment = maximum_matching(edges, target_ids)
    for sid, record in records.items():
        control = assignment.get(sid)
        record['assigned_control_id'] = control
        record['status'] = ('matched' if control else 'unusable_covariates' if record['missing_or_nonpositive_fields']
                            else 'no_eligible_control' if not edges[sid] else 'control_competition')
        if control:
            record['control_covariates'] = control_vectors[control]
            record['absolute_tolerance_scaled_differences'] = differences(record['covariates'], control_vectors[control])
    if len(set(assignment.values())) != len(assignment) or set(target_ids)&set(controls):
        raise ValueError('Control reuse or target/control overlap')
    result = {'experiment': '001A', 'algorithm': frozen['algorithm'],
              'selection_sha256': hashlib.sha256(selection.read_bytes()).hexdigest(),
              'protocol_sha256': frozen['protocol_sha256'], 'raw_sha256': frozen['raw_sha256'],
              'target_count': 100, 'reference_pool_count': len(controls),
              'matched_target_count': len(assignment), 'matched_fraction': len(assignment)/100,
              'operational_criterion_met': len(assignment) >= 50,
              'status_counts': {status: sum(r['status']==status for r in records.values()) for status in
                                ('matched','unusable_covariates','no_eligible_control','control_competition')},
              'targets_with_any_eligible_control_by_stage': {
                  stage: sum(r['cumulative_eligible_counts'][stage]>0 for r in records.values()) for stage in STAGES},
              'covariate_order': list(FIELDS[:2])+['abs_b_deg']+list(FIELDS[3:]),
              'tolerances': PARAMETERS, 'targets': list(records.values()),
              'interpretation': 'Control feasibility only; no anomaly score, significance test or technology inference.'}
    output.mkdir(parents=True, exist_ok=True)
    (output/'results.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    return result


def plot_result(result, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout='constrained')
    counts = result['status_counts']
    labels = ['Matched', 'Missing or nonpositive\nmatching inputs', 'No eligible\ncontrol', 'Control\ncompetition']
    values = list(counts.values())
    axes[0].bar(labels, values, color=['#24856a','#a0a9b5','#ce803c','#715a9c'])
    axes[0].set_title('Final assignments: all 100 targets retained')
    axes[0].set_ylabel('Targets')
    for i, value in enumerate(values):
        axes[0].text(i, value+1, str(value), ha='center')
    stages = ['Usable inputs', 'G magnitude', 'Color', 'Sky latitude', 'Parallax SNR', 'RUWE']
    values = [100-counts['unusable_covariates'], *result['targets_with_any_eligible_control_by_stage'].values()]
    axes[1].barh(stages[::-1], values[::-1], color='#335d9e')
    axes[1].set_xlim(0,100)
    axes[1].set_xlabel('Targets with at least one eligible control after cumulative cuts')
    axes[1].set_title('Where matching support is lost')
    for i, value in enumerate(values[::-1]):
        axes[1].text(value+1, i, str(value), va='center')
    for ax in axes:
        ax.spines[['top','right']].set_visible(False)
    fig.suptitle('EchoLens Experiment 001A — 3/100 matched; operational criterion ≥50/100 not met\n'
                 'Real Gaia observations; control feasibility only, no technosignature inference', fontsize=13)
    fig.savefig(Path(output)/'diagnostics.png', dpi=160)
    plt.close(fig)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', default='reports/experiment_001a')
    p.add_argument('--plot', action='store_true', help='Requires requirements-analysis.txt')
    args = p.parse_args()
    result = execute(args.output)
    if args.plot:
        plot_result(result, args.output)
    print(json.dumps({k: result[k] for k in ('target_count','reference_pool_count','matched_target_count',
        'operational_criterion_met','status_counts','targets_with_any_eligible_control_by_stage')}, indent=2))
