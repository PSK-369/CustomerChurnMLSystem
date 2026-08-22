import os
import pandas as pd
import numpy as np
import mlflow
import mlflow.sklearn
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score
import warnings


TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(TRACKING_URI)


# 1. FORCE ALLOW FILE STORE
# os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
# mlflow.set_tracking_uri("http://localhost:5000")  # for server running
# mlflow.set_tracking_uri("./mlruns")  # for local running

# Silence Git warnings and general sklearn warnings
os.environ["GIT_PYTHON_REFRESH"] = "quiet"
warnings.filterwarnings('ignore')

"""
# --- STEP 1 & 2: Extract Data from PostgreSQL ---
print("Connecting to PostgreSQL and extracting features...")
DB_URI = "postgresql://ds_candidate:ds_candidate_pw@localhost:5432/ecommerce"

# Optimized query to build the feature table (from Part A)
feature_query = '''
WITH customer_stats AS (
    SELECT 
        customer_id,
        COUNT(order_id) AS total_orders,
        MAX(order_date) AS last_order_date,
        AVG(order_total) AS avg_order_value
    FROM orders
    WHERE status = 'completed'
    GROUP BY customer_id
)
SELECT 
    c.customer_id,
    c.country,
    COALESCE(cs.total_orders, 0) AS total_orders,
    COALESCE(cs.avg_order_value, 0) AS avg_order_value,
    EXTRACT(DAY FROM CURRENT_DATE - COALESCE(cs.last_order_date, CURRENT_DATE)) AS days_since_last_order,
    CASE 
        WHEN cs.last_order_date < CURRENT_DATE - INTERVAL '90 days' OR cs.last_order_date IS NULL THEN 1 
        ELSE 0 
    END AS churned
FROM customers c
LEFT JOIN customer_stats cs ON c.customer_id = cs.customer_id
LIMIT 100000; -- Limit to 100k for fast local training (remove LIMIT for full 1M dataset)
'''

conn = psycopg2.connect(DB_URI)
df = pd.read_sql_query(feature_query, conn)
conn.close()

"""



# --- POINT 1 & 2: ETL, Load, Clean Column Names ---
df = pd.read_csv('data/customers.csv')
df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
df = df.drop(columns=['first_name', 'last_name', 'email'])

# --- Create synthetic features for demonstration (if missing) ---
np.random.seed(42)
if 'total_orders' not in df.columns:
    df['total_orders'] = np.random.randint(1, 50, size=len(df))
if 'churned' not in df.columns:
    df['churned'] = np.random.choice([0, 1], size=len(df), p=[0.7, 0.3])

# --- POINT 3, 4, 5: Shape, Stats, Aggregations ---
print("Shape:", df.shape, "Size:", df.size, "Dims:", df.ndim)
print(df.describe())

# --- POINT 6 & 7 & 8: Duplicates, Missing Values ---
df = df.drop_duplicates()

# 1. Fill Categorical Missing Values
df['country'] = df['country'].fillna(df['country'].mode()[0])
if 'marketing_opt_in' in df.columns:
    df['marketing_opt_in'] = df['marketing_opt_in'].fillna(df['marketing_opt_in'].mode()[0])

# 2. Fill Numerical Missing Values
df['total_orders'] = df['total_orders'].fillna(0)

# 3. Handle Date Parsing safely
df['signup_date'] = pd.to_datetime(df['signup_date'], errors='coerce')
# Fill NaT-derived NaNs with a default (e.g., median year/month or a fixed default like 2020 / 1)
df['signup_year'] = df['signup_date'].dt.year.fillna(2020).astype(int)
df['signup_month'] = df['signup_date'].dt.month.fillna(1).astype(int)
df = df.drop(columns=['signup_date'])

# --- POINT 9: Encoding ---
le = LabelEncoder()
df['country_encoded'] = le.fit_transform(df['country'])
df = df.drop(columns=['country'])

# --- POINT 10: EDA & Feature Engineering (Correlation) ---
corr_matrix = df.select_dtypes(include=[np.number]).corr().abs()
upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
to_drop = [column for column in upper.columns if any(upper[column] > 0.95)]
df = df.drop(columns=to_drop)

# --- POINT 11: Outliers (IQR Method) ---
Q1 = df['total_orders'].quantile(0.25)
Q3 = df['total_orders'].quantile(0.75)
IQR = Q3 - Q1
df = df[(df['total_orders'] >= (Q1 - 1.5 * IQR)) & (df['total_orders'] <= (Q3 + 1.5 * IQR))]

# --- POINT 12: Skewness ---
df['total_orders'] = np.log1p(df['total_orders'])

# Persist the processed baseline for drift monitoring.
df.to_csv('data/clean_features.csv', index=False)

# --- POINT 13: Standardization ---
# Drop non-feature columns
X = df.drop(columns=['churned', 'customer_id'])
y = df['churned']

# SAFETY NET: Ensure absolutely NO NaNs remain in X before scaling
numeric_cols = X.select_dtypes(include=[np.number]).columns
X[numeric_cols] = X[numeric_cols].fillna(0) 

# Verify no NaNs exist (optional debug)
if X.isna().sum().sum() > 0:
    print("WARNING: NaNs still present in X:\n", X.isna().sum())

scaler = StandardScaler()

# --- STEP 3: Algorithm Selection & Implementation ---
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

models = {
    "LogisticRegression": LogisticRegression(max_iter=1000),
    "DecisionTree": DecisionTreeClassifier(random_state=42),
    "RandomForest": RandomForestClassifier(random_state=42)
}

mlflow.set_experiment("Churn_Prediction_Experiment")

best_model = None
best_acc = 0
best_run_id = None

for name, model in models.items():
    with mlflow.start_run(run_name=name) as run:
        model_pipeline = Pipeline([
            ("scaler", StandardScaler()),
            ("classifier", model),
        ])
        if name == "RandomForest":
            param_grid = {
                'classifier__n_estimators': [50, 100],
                'classifier__max_depth': [5, 10],
            }
            grid = GridSearchCV(model_pipeline, param_grid, cv=3, scoring='accuracy')
            grid.fit(X_train, y_train)
            model_pipeline = grid.best_estimator_
            mlflow.log_params(grid.best_params_)
        else:
            model_pipeline.fit(X_train, y_train)
        
        y_pred = model_pipeline.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        mlflow.log_metric("accuracy", acc)
        mlflow.sklearn.log_model(model_pipeline, "model")
        
        print(f"{name} - Accuracy: {acc:.4f}")
        
        if acc > best_acc:
            best_acc = acc
            best_model = model_pipeline
            best_run_id = run.info.run_id

print(f"\nBest Model Accuracy: {best_acc:.4f}")

if best_run_id is None:
    raise RuntimeError("No model run was created")

model_version = mlflow.register_model(
    model_uri=f"runs:/{best_run_id}/model",
    name="ChurnModel",
)
mlflow.MlflowClient().set_registered_model_alias(
    name="ChurnModel",
    alias="Production",
    version=model_version.version,
)
print(f"Registered ChurnModel version {model_version.version} with alias Production")

# Verify experiments were logged
experiments = mlflow.search_experiments()
print(f"\nTotal experiments: {len(experiments)}")

runs = mlflow.search_runs(experiment_names=["Churn_Prediction_Experiment"])
print(f"Total runs logged: {len(runs)}")