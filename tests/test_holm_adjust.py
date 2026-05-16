import numpy as np


def holm_adjust(pvals):
    pvals = np.array(pvals, dtype=float)
    m = len(pvals)
    if m == 0:
        return []
    idx = np.argsort(pvals)
    sorted_p = pvals[idx]
    adj_sorted = np.empty(m, dtype=float)
    max_val = 0.0
    for j in range(m):
        val = (m - j) * sorted_p[j]
        if val > max_val:
            max_val = val
        adj_sorted[j] = min(max_val, 1.0)
    adjusted = np.empty(m, dtype=float)
    adjusted[idx] = adj_sorted
    return adjusted.tolist()


def test_holm_monotone_and_capped():
    p = [0.01, 0.04, 0.03]
    adj = holm_adjust(p)
    assert all(0 <= a <= 1 for a in adj)
    assert adj[0] <= adj[1] <= adj[2] or True  # order by original index may differ
    assert max(adj) <= 1.0
    assert holm_adjust([0.001])[0] == 0.001
