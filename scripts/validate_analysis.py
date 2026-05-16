#!/usr/bin/env python3
"""Validator for aggregated analysis JSON (standalone repo copy)."""
import json
import sys
from pathlib import Path


def validate(path: str, strict_provenance: bool = False) -> int:
    p = Path(path)
    if not p.exists():
        print('ERROR: file not found:', path)
        return 2
    data = json.loads(p.read_text(encoding='utf-8'))
    if 'metrics' not in data or 'comparisons' not in data:
        print('ERROR: missing top-level keys (metrics/comparisons)')
        return 3
    if 'analysis_config' not in data:
        print('ERROR: missing analysis_config')
        return 7
    ac = data['analysis_config']
    for key in ('n_bootstrap', 'n_permutation', 'alpha', 'rng_seed'):
        if key not in ac:
            print('ERROR: analysis_config missing', key)
            return 8
    comps = data['comparisons']
    if not isinstance(comps, list) or len(comps) == 0:
        print('ERROR: comparisons is empty')
        return 4
    base_dir = p.parent
    for c in comps:
        if 'p_value_holm' not in c:
            print('ERROR: missing p_value_holm in comparison:', c.get('a'), 'vs', c.get('b'))
            return 5
        bd = c.get('bootstrap_distribution')
        artifact = c.get('bootstrap_artifact')
        if artifact:
            sidecar = base_dir / artifact
            if not sidecar.exists():
                print('ERROR: bootstrap_artifact missing on disk:', sidecar)
                return 9
            meta = c.get('bootstrap_artifact_meta')
            if meta and not (base_dir / meta).exists():
                print('ERROR: bootstrap_artifact_meta missing:', meta)
                return 10
        elif not bd or not isinstance(bd, list) or len(bd) == 0:
            print('ERROR: empty bootstrap_distribution and no bootstrap_artifact for:', c.get('a'), 'vs', c.get('b'))
            return 6
    if strict_provenance:
        if data.get('requirements_hash') in (None, '', 'N/A'):
            print('ERROR: requirements_hash is missing (strict_provenance)')
            return 11
    elif data.get('requirements_hash') in (None, '', 'N/A'):
        print('WARN: requirements_hash is N/A')
    raw = p.read_text(encoding='utf-8')
    if 'NaN' in raw:
        print('ERROR: JSON contains invalid NaN literal')
        return 12
    print('VALIDATION_OK')
    return 0


if __name__ == '__main__':
    default = 'artifacts/non_oracle_defer_results_2026_05_full_analysis.json'
    path = sys.argv[1] if len(sys.argv) > 1 else default
    strict = '--strict-provenance' in sys.argv
    sys.exit(validate(path, strict_provenance=strict))
