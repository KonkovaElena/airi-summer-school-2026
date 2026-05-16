import json
import math

from compute_and_plot_results import json_sanitize


def test_json_sanitize_replaces_nan_with_null():
    assert json_sanitize(float('nan')) is None
    assert json_sanitize({'x': float('nan'), 'y': [1.0, float('inf')]}) == {'x': None, 'y': [1.0, None]}


def test_dump_no_nan_literal():
    payload = json_sanitize({'a': float('nan'), 'b': 1.0})
    raw = json.dumps(payload, allow_nan=False)
    assert 'NaN' not in raw
    assert 'null' in raw
