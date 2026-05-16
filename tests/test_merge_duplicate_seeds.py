import json
import subprocess
import sys
from pathlib import Path

ARTIFACTS = Path(__file__).resolve().parents[1] / 'artifacts'
MERGE = ARTIFACTS / 'merge_experiment_results.py'


def _minimal_batch(seed: int) -> dict:
    return {
        'metadata': {'git_commit_sha': 'test'},
        'base_seed': 1,
        'calibration_size': 10,
        'test_size': 20,
        'review_budget': 0.35,
        'seed_results': [
            {
                'seed': seed,
                'diff_accuracy': 0.01,
                'policies': {
                    'model_only': {'accuracy': 0.7, 'review_rate': 0.0},
                    'naive_threshold': {'accuracy': 0.8, 'review_rate': 0.3},
                    'calibrated_defer': {'accuracy': 0.81, 'review_rate': 0.3},
                    'always_review': {'accuracy': 0.87, 'review_rate': 1.0},
                },
            }
        ],
    }


def test_merge_rejects_duplicate_seeds(tmp_path):
    a = tmp_path / 'a.json'
    b = tmp_path / 'b.json'
    out = tmp_path / 'out.json'
    payload = _minimal_batch(42)
    a.write_text(json.dumps(payload), encoding='utf-8')
    b.write_text(json.dumps(payload), encoding='utf-8')
    proc = subprocess.run(
        [sys.executable, str(MERGE), str(a), str(b), '-o', str(out)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert 'duplicate' in (proc.stderr + proc.stdout).lower()
