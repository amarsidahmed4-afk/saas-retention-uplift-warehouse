import duckdb
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

def train_v1_model(db_path="warehouse.duckdb"):
    # Connect to DuckDB
    con = duckdb.connect(db_path, read_only=True)
    
    # Read the mart
    query = "SELECT * FROM fct_account_retention"
    df = con.execute(query).fetchdf()
    
    # As per .clinerules: explicit categorical handling
    # Convert nominal columns to pandas categorical type explicitly
    df['plan_tier'] = df['plan_tier'].astype('category')
    df['billing_interval'] = df['billing_interval'].astype('category')
    
    # Features and target
    # For v1, a simple proxy model predicting churn
    # Later (v1.1) we'll build the T-learner to predict CATE.
    
    numeric_features = [
        'arr', 'seats', 'login_frequency', 'feature_adoption', 
        'session_depth', 'ticket_volume', 'severe_tickets',
        'is_treated' # Adding treatment as a feature for now as a simple proxy
    ]
    categorical_features = ['plan_tier', 'billing_interval']
    
    X = df[numeric_features + categorical_features]
    y = df['is_churned']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', 'passthrough', numeric_features),
            ('cat', OneHotEncoder(drop='first'), categorical_features)
        ])
    
    # Pipeline with simple Logistic Regression
    clf = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('classifier', LogisticRegression(max_iter=1000))
    ])
    
    # Train
    clf.fit(X_train, y_train)
    
    # Predict & Evaluate
    preds = clf.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, preds)
    
    print(f"v1 Proxy Model (Logistic Regression) - ROC AUC: {auc:.4f}")
    print("This is a simple proxy model. The actual T-learner and decision gate will be in v1.1.")
    
    return clf

if __name__ == "__main__":
    train_v1_model()
