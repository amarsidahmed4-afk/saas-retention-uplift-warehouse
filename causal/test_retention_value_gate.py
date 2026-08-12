import pytest
import pandas as pd
from retention_value_gate import RetentionValueGate

def test_value_gate_initialization():
    gate = RetentionValueGate(csm_hourly_cost=50.0, required_roi_multiple=3.0)
    assert gate.threshold == 150.0  # 50 * 3
    
    with pytest.raises(ValueError):
        RetentionValueGate(csm_hourly_cost=-10, required_roi_multiple=3.0)

def test_evaluate_single_account():
    gate = RetentionValueGate(csm_hourly_cost=100.0, required_roi_multiple=5.0)
    # Threshold is $500
    
    # Hand-derived test case 1: Passes threshold
    # ARR = $10,000, CATE = 0.10 (10% uplift in retention)
    # EV = $10,000 * 0.10 = $1,000. 
    # $1,000 >= $500 (True)
    res_pass = gate.evaluate_account("acc_1", arr=10000.0, cate=0.10)
    assert res_pass['expected_retention_value'] == 1000.0
    assert res_pass['should_intervene'] is True
    
    # Hand-derived test case 2: Fails threshold (Uplift too low)
    # ARR = $10,000, CATE = 0.02 (2% uplift)
    # EV = $10,000 * 0.02 = $200.
    # $200 >= $500 (False)
    res_fail_uplift = gate.evaluate_account("acc_2", arr=10000.0, cate=0.02)
    assert res_fail_uplift['expected_retention_value'] == 200.0
    assert res_fail_uplift['should_intervene'] is False
    
    # Hand-derived test case 3: Fails threshold (ARR too low)
    # ARR = $1,000, CATE = 0.40 (Huge 40% uplift!)
    # EV = $1,000 * 0.40 = $400.
    # $400 >= $500 (False)
    res_fail_arr = gate.evaluate_account("acc_3", arr=1000.0, cate=0.40)
    assert res_fail_arr['expected_retention_value'] == 400.0
    assert res_fail_arr['should_intervene'] is False

def test_evaluate_batch():
    gate = RetentionValueGate(csm_hourly_cost=50.0, required_roi_multiple=2.0)
    # Threshold = $100
    
    df = pd.DataFrame({
        'account_id': ['a1', 'a2', 'a3'],
        'arr': [1000.0, 5000.0, 200.0],
        'cate': [0.05, 0.20, 0.10]
    })
    
    # Expected EV:
    # a1: 1000 * 0.05 = $50 (<100, False)
    # a2: 5000 * 0.20 = $1000 (>=100, True)
    # a3: 200 * 0.10 = $20 (<100, False)
    
    results = gate.evaluate_batch(df)
    
    assert len(results) == 3
    assert bool(results.loc[results['account_id'] == 'a1', 'should_intervene'].iloc[0]) is False
    assert bool(results.loc[results['account_id'] == 'a2', 'should_intervene'].iloc[0]) is True
    assert bool(results.loc[results['account_id'] == 'a3', 'should_intervene'].iloc[0]) is False
