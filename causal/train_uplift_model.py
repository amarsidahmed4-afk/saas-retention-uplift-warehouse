import duckdb
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

class PropensityAdjustedTLearner:
    """
    A T-learner that uses Inverse Probability Weighting (IPW) to adjust for 
    treatment assignment bias (confounding) in the bulk data, and calibrates
    against an unconfounded pilot subset.
    """
    def __init__(self, numeric_features, categorical_features):
        self.numeric_features = numeric_features
        self.categorical_features = categorical_features
        
        # Added StandardScaler to fix ConvergenceWarnings and improve numeric feature handling
        self.preprocessor = ColumnTransformer(
            transformers=[
                ('num', StandardScaler(), numeric_features),
                ('cat', OneHotEncoder(drop='first', handle_unknown='ignore'), categorical_features)
            ])
            
        self.propensity_model = Pipeline(steps=[
            ('preprocessor', self.preprocessor),
            ('classifier', LogisticRegression(max_iter=1000, class_weight='balanced'))
        ])
        
        self.model_0 = Pipeline(steps=[
            ('preprocessor', self.preprocessor),
            ('classifier', LogisticRegression(max_iter=1000))
        ])
        
        self.model_1 = Pipeline(steps=[
            ('preprocessor', self.preprocessor),
            ('classifier', LogisticRegression(max_iter=1000))
        ])
        
        self.calibrated_model_0 = None
        self.calibrated_model_1 = None


    def fit(self, X_bulk, y_bulk, w_bulk, X_pilot=None, y_pilot=None, w_pilot=None):
        # 1. Fit Propensity Model on Bulk
        self.propensity_model.fit(X_bulk, w_bulk)
        propensities = self.propensity_model.predict_proba(X_bulk)[:, 1]
        propensities = np.clip(propensities, 0.05, 0.95)
        
        # 2. IPW Weighting
        weights = np.where(w_bulk == 1, 1.0 / propensities, 1.0 / (1.0 - propensities))
        
        # 3. Fit base models on bulk with IPW
        X_0, y_0, weights_0 = X_bulk[w_bulk == 0], y_bulk[w_bulk == 0], weights[w_bulk == 0]
        self.model_0.fit(X_0, y_0, classifier__sample_weight=weights_0)
        
        X_1, y_1, weights_1 = X_bulk[w_bulk == 1], y_bulk[w_bulk == 1], weights[w_bulk == 1]
        self.model_1.fit(X_1, y_1, classifier__sample_weight=weights_1)
        
        # 4. Calibrate against the randomized pilot subset (if provided)
        if X_pilot is not None and y_pilot is not None and w_pilot is not None:
            # Calibrate control model
            X_pilot_0, y_pilot_0 = X_pilot[w_pilot == 0], y_pilot[w_pilot == 0]
            self.calibrated_model_0 = CalibratedClassifierCV(estimator=FrozenEstimator(self.model_0))
            self.calibrated_model_0.fit(X_pilot_0, y_pilot_0)
            
            # Calibrate treated model
            X_pilot_1, y_pilot_1 = X_pilot[w_pilot == 1], y_pilot[w_pilot == 1]
            self.calibrated_model_1 = CalibratedClassifierCV(estimator=FrozenEstimator(self.model_1))
            self.calibrated_model_1.fit(X_pilot_1, y_pilot_1)
        else:
            self.calibrated_model_0 = self.model_0
            self.calibrated_model_1 = self.model_1
            
        return self

    def predict_cate(self, X):
        """
        Predict Conditional Average Treatment Effect (CATE)
        Since the outcome is 'churned', CATE = P(Churn|Control) - P(Churn|Treated)
        """
        prob_churn_0 = self.calibrated_model_0.predict_proba(X)[:, 1]
        prob_churn_1 = self.calibrated_model_1.predict_proba(X)[:, 1]
        return prob_churn_0 - prob_churn_1
        
    def predict_quadrants(self, X, risk_threshold=0.5, uplift_threshold=0.1):
        """
        Segments accounts into 4 causal quadrants based on their predicted behavior.
        
        Risk Threshold: Baseline probability of churn (under control) above which an account is 'at-risk'.
        Uplift Threshold: CATE (churn reduction) above which an account is considered 'persuadable'.
        """
        prob_churn_0 = self.calibrated_model_0.predict_proba(X)[:, 1]
        cate = self.predict_cate(X)
        
        quadrants = []
        for p0, c in zip(prob_churn_0, cate):
            if p0 >= risk_threshold and c >= uplift_threshold:
                quadrants.append("Persuadable")     # High risk, high uplift -> TARGET
            elif p0 >= risk_threshold and c < uplift_threshold:
                quadrants.append("Lost Cause")      # High risk, low uplift -> LEAVE ALONE (will churn anyway)
            elif p0 < risk_threshold and c < uplift_threshold:
                quadrants.append("Sure Thing")      # Low risk, low uplift -> LEAVE ALONE (safe without touch)
            else:
                quadrants.append("Sleeping Dog")    # Low risk, high uplift (rare/anomalous) or negative CATE -> DO NOT TOUCH (might trigger churn)
                
        return pd.Series(quadrants, index=X.index)


def train_t_learner(db_path="warehouse.duckdb"):
    con = duckdb.connect(db_path, read_only=True)
    df = con.execute("SELECT * FROM fct_account_retention").fetchdf()
    
    df['plan_tier'] = df['plan_tier'].astype('category')
    df['billing_interval'] = df['billing_interval'].astype('category')
    
    numeric_features = [
        'arr', 'seats', 'login_frequency', 'feature_adoption', 
        'session_depth', 'ticket_volume', 'severe_tickets'
    ]
    categorical_features = ['plan_tier', 'billing_interval']
    
    df_bulk = df[df['is_pilot'] == 0].copy()
    df_pilot = df[df['is_pilot'] == 1].copy()
    
    X_train = df_bulk[numeric_features + categorical_features]
    y_train = df_bulk['is_churned']
    w_train = df_bulk['is_treated']
    
    learner = PropensityAdjustedTLearner(numeric_features, categorical_features)
    
    # Extract pilot data for calibration
    X_pilot = df_pilot[numeric_features + categorical_features]
    y_pilot = df_pilot['is_churned']
    w_pilot = df_pilot['is_treated']
    
    # Fit and calibrate
    learner.fit(X_train, y_train, w_train, X_pilot=X_pilot, y_pilot=y_pilot, w_pilot=w_pilot)
    
    # Evaluate on pilot
    cate_pilot = learner.predict_cate(X_pilot)
    quadrants = learner.predict_quadrants(X_pilot)
    
    print("\n--- Phase v1.1 Propensity-Adjusted T-Learner ---")
    print(f"Average predicted uplift (churn reduction) in pilot: {cate_pilot.mean():.4f}")
    
    print("\n--- Causal Quadrant Segmentation (Pilot Group) ---")
    print(quadrants.value_counts(normalize=True).round(3) * 100)
    
    return learner

if __name__ == "__main__":
    train_t_learner()

