
# 1. Delete old broken CSVs

Remove-Item -Recurse -Force data

# 2. Generate clean data

python generate_data.py --out-dir data

# 3. Reset database schema (drops and recreates tables cleanly)

docker exec -i ds_interview_postgres psql -U ds_candidate -d ecommerce -f /sql/schema.sql

# 4. Load tables in correct foreign-key order

docker exec ds_interview_postgres psql -U ds_candidate -d ecommerce -c "COPY customers FROM '/data/customers.csv' WITH (FORMAT csv, HEADER true, NULL '')"
docker exec ds_interview_postgres psql -U ds_candidate -d ecommerce -c "COPY products FROM '/data/products.csv' WITH (FORMAT csv, HEADER true, NULL '')"
docker exec ds_interview_postgres psql -U ds_candidate -d ecommerce -c "COPY orders FROM '/data/orders.csv' WITH (FORMAT csv, HEADER true, NULL '')"
docker exec ds_interview_postgres psql -U ds_candidate -d ecommerce -c "COPY order_items FROM '/data/order_items.csv' WITH (FORMAT csv, HEADER true, NULL '')"

# Set MLflow URI

 set MLFLOW_TRACKING_URI=http://localhost:5000

# Run the 13-point EDA, training, and hyperparameter tuning

python training/eda_and_training.py

# Ml flow UI

mlflow ui --backend-store-uri sqlite:///mlflow.db

# Build the Docker image

docker build -t churn-api -f serving/Dockerfile .

# Run the container (Maps MLflow URI to host machine)

# Note: Use 'host.docker.internal' for Mac/Windows. For Linux, use '172.17.0.1'

docker run -d --name churn_api -p 8000:8000 -e MLFLOW_TRACKING_URI="http://host.docker.internal:5000" churn-api

streamlit run serving/app.py

# Run the Population Stability Index (PSI) drift detection script

python monitoring/drift_check.py
