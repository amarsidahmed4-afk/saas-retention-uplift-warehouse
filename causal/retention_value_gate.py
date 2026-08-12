import pandas as pd

class RetentionValueGate:
    """
    Evaluates whether a Customer Success intervention is financially justified based
    on the Expected Retention Value (EV).
    
    Formula per .clinerules:
    Expected_Retention_Value = ARR * CATE_retention
    Trigger CS outreach only if EV >= required_ROI_multiple * CSM_hourly_cost
    """
    def __init__(self, csm_hourly_cost: float, required_roi_multiple: float):
        if csm_hourly_cost <= 0:
            raise ValueError("CSM hourly cost must be strictly positive.")
        if required_roi_multiple <= 0:
            raise ValueError("Required ROI multiple must be strictly positive.")
            
        self.csm_hourly_cost = csm_hourly_cost
        self.required_roi_multiple = required_roi_multiple
        self.threshold = csm_hourly_cost * required_roi_multiple

    def evaluate_account(self, account_id: str, arr: float, cate: float) -> dict:
        """
        Evaluates a single account's ROI for a CS touch.
        """
        if arr < 0:
            raise ValueError(f"ARR cannot be negative for account {account_id}.")
            
        # Expected Retention Value = The dollar amount saved by the intervention
        expected_retention_value = arr * cate
        
        # Decision gate: is the dollar amount saved greater than our required ROI?
        should_intervene = expected_retention_value >= self.threshold
        
        return {
            "account_id": account_id,
            "arr": arr,
            "cate": cate,
            "expected_retention_value": expected_retention_value,
            "threshold": self.threshold,
            "should_intervene": should_intervene
        }

    def evaluate_batch(self, df: pd.DataFrame, arr_col: str = "arr", cate_col: str = "cate", account_col: str = "account_id") -> pd.DataFrame:
        """
        Evaluates a batch of accounts. 
        Returns a DataFrame appended with the financial decision logic.
        """
        missing_cols = [col for col in [arr_col, cate_col, account_col] if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns in DataFrame: {missing_cols}")
            
        results = df.copy()
        
        # Expected Retention Value
        results['expected_retention_value'] = results[arr_col] * results[cate_col]
        results['roi_threshold'] = self.threshold
        
        # Decision Gate
        results['should_intervene'] = results['expected_retention_value'] >= self.threshold
        
        return results
