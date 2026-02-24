import pytest
from Scripts.compute_metrics import kendall_distance, disp_kappa_scaled

def test_kendall_identity():
    p_canon = [1,2,3,4,5,6]
    pi = [1,2,3,4,5,6]
    assert kendall_distance(pi, p_canon) == 0.0

def test_kendall_single_swap():
    p_canon = [1,2,3,4,5,6]
    pi = [1,3,2,4,5,6]
    assert kendall_distance(pi, p_canon) > 0.0

def test_disp_kappa_reversed():
    p_canon = [1,2,3,4,5,6]
    pi = [6,5,4,3,2,1]
    assert disp_kappa_scaled(pi, kappa=1.2, alpha=0.0001) > 0
