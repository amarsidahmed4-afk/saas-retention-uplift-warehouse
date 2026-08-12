import pytest
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from train_uplift_model import train_v1_model

def test_v1_model_trains():
    """
    Ensures the v1 proxy model can successfully train and return a valid Pipeline object.
    Requires DuckDB mart to be populated.
    """
    model = train_v1_model()
    
    assert model is not None
    assert isinstance(model, Pipeline), "Model should be a scikit-learn Pipeline"
    
    # Check if classifier is LogisticRegression
    assert type(model.named_steps['classifier']).__name__ == 'LogisticRegression'
