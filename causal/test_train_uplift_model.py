import pytest
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from train_uplift_model import train_t_learner, PropensityAdjustedTLearner

def test_t_learner_model_trains():
    """
    Ensures the v1.1 T-Learner model can successfully train and return a valid PropensityAdjustedTLearner object.
    Requires DuckDB mart to be populated.
    """
    learner = train_t_learner()
    
    assert learner is not None
    assert isinstance(learner, PropensityAdjustedTLearner), "Model should be a PropensityAdjustedTLearner"
    
    # Check if internal base outcome models are pipelines
    assert isinstance(learner.model_0, Pipeline)
    assert isinstance(learner.model_1, Pipeline)
    
    # Ensure it implements predict_cate
    assert hasattr(learner, 'predict_cate')
    assert callable(learner.predict_cate)
