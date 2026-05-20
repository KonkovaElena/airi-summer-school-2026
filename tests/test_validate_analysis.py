import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
VALIDATE = REPO / 'scripts' / 'validate_analysis.py'
ARTIFACTS = Path(__file__).resolve().parents[1] / 'artifacts'


def _valid_analysis(tmp_path, inline_bootstrap: bool = False):
    comp = {
        'a': 'calibrated_defer',
        'b': 'naive_threshold',
        'p_value': 0.001,
        'p_value_holm': 0.003,
        'mean_diff': 0.0024,
        'ci_95': [0.0015, 0.0033],
    }
    if inline_bootstrap:
        comp['bootstrap_distribution'] = [0.001, 0.002, 0.003]
    else:
        blob = tmp_path / 'bootstrap_calibrated_defer_vs_naive_threshold.npy.gz'
        blob.write_bytes(b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x02\xff\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00')
        meta = tmp_path / 'bootstrap_calibrated_defer_vs_naive_threshold.npy.gz.meta.json'
        meta.write_text('{"n": 3}', encoding='utf-8')
        comp['bootstrap_artifact'] = blob.name
        comp['bootstrap_artifact_meta'] = meta.name
    return {
        'metrics': {
            'model_only': {'mean_accuracy': 0.7187, 'mean_review_rate': 0.0},
            'naive_threshold': {'mean_accuracy': 0.8105, 'mean_review_rate': 0.3492},
            'calibrated_defer': {'mean_accuracy': 0.8129, 'mean_review_rate': 0.3396},
            'always_review': {'mean_accuracy': 0.8752, 'mean_review_rate': 1.0},
        },
        'comparisons': [comp],
        'analysis_config': {
            'n_bootstrap': 5000,
            'n_permutation': 10000,
            'alpha': 0.05,
            'rng_seed': 0,
        },
        'requirements_hash': 'abc123',
    }


def test_validate_ok_inline(tmp_path):
    p = tmp_path / 'analysis.json'
    p.write_text(json.dumps(_valid_analysis(tmp_path, inline_bootstrap=True)), encoding='utf-8')
    proc = subprocess.run(
        [sys.executable, str(VALIDATE), str(p), '--strict-provenance'],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert 'VALIDATION_OK' in proc.stdout


def test_validate_fails_missing_config(tmp_path):
    p = tmp_path / 'bad.json'
    data = _valid_analysis(tmp_path, inline_bootstrap=True)
    del data['analysis_config']
    p.write_text(json.dumps(data), encoding='utf-8')
    proc = subprocess.run([sys.executable, str(VALIDATE), str(p)], capture_output=True, text=True)
    assert proc.returncode != 0


def test_validate_ok_sidecar_artifact(tmp_path):
    p = tmp_path / 'sidecar.json'
    p.write_text(json.dumps(_valid_analysis(tmp_path, inline_bootstrap=False)), encoding='utf-8')
    proc = subprocess.run([sys.executable, str(VALIDATE), str(p)], capture_output=True, text=True)
    assert proc.returncode == 0
