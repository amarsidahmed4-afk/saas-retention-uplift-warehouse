import duckdb
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

class PropensityAdjustedTLearner:
    """
    A T-learner that uses Inverse Probability Weighting (IPW) to adjust for 
    treatment assignment bias (confounding) in the bulk data.
    """
    def __init__(self, numeric_features, categorical_features):
        self.numeric_features = numeric_features
        self.categorical_features = categorical_features
        
        # Shared preprocessor for all internal models
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', 'passthrough', numeric_features),
                ('cat', OneHotEncoder(drop='first', handle_unknown='ignore'), categorical_features)
            ])
            
        # Model to predict P(Treatment | Features)
        self.propensity_model = Pipeline(steps=[
            ('preprocessor', self.preprocessor),
            ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced'))
        ])
        
        # Outcome Model for Control group (no CS touch)
        self.model_0 = Pipeline(steps=[
            ('preprocessor', self.preprocessor),
            ('classifier', LogisticRegression(max_iter=1000))
        ])
        
        # Outcome Model for Treated group (received CS touch)
        self.model_1 = Pipeline(steps=[
            ('preprocessor', self.preprocessor),
            ('classifier', LogisticRegression(max_iter=1000))
        ])

    def fit(self, X, y, w):
        """
        w: treatment indicator array (1 if treated, 0 if control)
        """
        # 1. Fit Propensity Model
        self.propensity_model.fit(X, w)
        propensities = self.propensity_model.predict_proba(X)[:, 1]
        
        # Clip propensities to avoid extreme/infinite weights
        propensities = np.clip(propensities, 0.05, 0.95)
        
        # 2. Calculate Inverse Probability Weights (IPW)
        # Treated: 1/p. Control: 1/(1-p)
        weights = np.where(w == 1, 1.0 / propensities, 1.0 / (1.0 - propensities))
        
        # 3. Fit Control Model (w=0) with sample weights
        X_0, y_0, weights_0 = X[w == 0], y[w == 0], weights[w == 0]
        self.model_0.fit(X_0, y_0, classifier__sample_weight=weights_0)
        
        # 4. Fit Treated Model (w=1) with sample weights
        X_1, y_1, weights_1 = X[w == 1], y[w == 1], weights[w == 1]
        self.model_1.fit(X_1, y_1, classifier__sample_weight=weights_1)
        
        return self

    def predict_cate(self, X):
        """
        Predict Conditional Average Treatment Effect (CATE)
        Since the outcome is 'churned', CATE = P(Churn|Control) - P(Churn|Treated)
        Positive CATE means the treatment successfully reduced churn probability.
        """
        prob_churn_0 = self.model_0.predict_proba(X)[:, 1]
        prob_churn_1 = self.model_1.predict_proba(X)[:, 1]
        
        cate = prob_churn_0 - prob_churn_1
        return cate

def train_t_learner(db_path="warehouse.duckdb"):
    # Connect to DuckDB
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute("SELECT * FROM fct_account_retention").fetchdf()
    
    # Explicit categorical handling as per .clinerules
    df['plan_tier'] = df['plan_tier'].astype('category')
    df['billing_interval'] = df['billing_interval'].astype('category')
    
    numeric_features = [
        'arr', 'seats', 'login_frequency', 'feature_adoption', 
        'session_depth', 'ticket_volume', 'severe_tickets'
    ]
    categorical_features = ['plan_tier', 'billing_interval']
    
    # Separate the deliberately confounded bulk data from the honest randomized pilot
    df_bulk = df[df['is_pilot'] == 0].copy()
    df_pilot = df[df['is_pilot'] == 1].copy()
    
    # 1. Train on Bulk (Confounded) data using IPW
    X_train = df_bulk[numeric_features + categorical_features]
    y_train = df_bulk['is_churned']
    w_train = df_bulk['is_treated']
    
    learner = PropensityAdjustedTLearner(numeric_features, categorical_features)
    learner.fit(X_train, y_train, w_train)
    
    # 2. Evaluate and calibrate strictly on the Pilot (Randomized) data
    X_pilot = df_pilot[numeric_features + categorical_features]
    y_pilot = df_pilot['is_churned']
    w_pilot = df_pilot['is_treated']
    
    cate_pilot = learner.predict_cate(X_pilot)
    
    print("\n--- Phase v1.1 Propensity-Adjusted T-Learner ---")
    print(f"Trained on {len(df_bulk)} confounded bulk accounts.")
    print(f"Evaluated on {len(df_pilot)} randomized pilot accounts.")
    print(f"Average predicted uplift (churn reduction) in pilot: {cate_pilot.mean():.4f}")
    
    # Base model AUCs on the unconfounded pilot
    auc_0 = roc_auc_score(y_pilot[w_pilot==0], learner.model_0.predict_proba(X_pilot[w_pilot==0])[:, 1])
    auc_1 = roc_auc_score(y_pilot[w_pilot==1], learner.model_1.predict_proba(X_pilot[w_pilot==1])[:, 1])
    print(f"Control Model (No CS Touch) AUC on pilot: {auc_0:.4f}")
    print(f"Treated Model (CS Touch) AUC on pilot: {auc_1:.4f}")
    
    return learner

if __name__ == "__main__":
    train_t_learner()
