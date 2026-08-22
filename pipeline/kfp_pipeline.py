from kfp import dsl
from kfp.dsl import InputPath, OutputPath, component

@component(base_image="python:3.9", packages_to_install=["psycopg2-binary", "pandas"])
def extract_data(db_uri: str, output_csv: OutputPath(str)):  # pyright: ignore[reportInvalidTypeForm]
    import psycopg2
    import pandas as pd

    query = """
    WITH customer_stats AS (
        SELECT customer_id,
               COUNT(order_id) AS total_orders,
               MAX(order_date) AS last_order_date,
               AVG(order_total) AS avg_order_value
        FROM orders
        WHERE status = 'completed'
        GROUP BY customer_id
    )
    SELECT c.customer_id,
           c.country,
            c.signup_date,
            c.marketing_opt_in,
           COALESCE(cs.total_orders, 0) AS total_orders,
           COALESCE(cs.avg_order_value, 0) AS avg_order_value,
           EXTRACT(DAY FROM CURRENT_DATE - COALESCE(cs.last_order_date::date, CURRENT_DATE))
               AS days_since_last_order,
           CASE WHEN cs.last_order_date < CURRENT_DATE - INTERVAL '90 days'
                     OR cs.last_order_date IS NULL THEN 1 ELSE 0 END AS churned
    FROM customers AS c
    LEFT JOIN customer_stats AS cs ON c.customer_id = cs.customer_id
    """

    with psycopg2.connect(db_uri) as conn:
        df = pd.read_sql_query(query, conn)
    df.to_csv(output_csv, index=False)

@component(base_image="python:3.9", packages_to_install=["pandas"])
def transform_data(input_csv: InputPath(str), output_csv: OutputPath(str)):  # pyright: ignore[reportInvalidTypeForm]
    import pandas as pd
    df = pd.read_csv(input_csv)
    required_columns = {
        'customer_id', 'country', 'signup_date', 'marketing_opt_in',
        'total_orders', 'churned',
    }
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        raise ValueError(f"Missing required columns: {sorted(missing_columns)}")
    df = df.dropna(subset=['churned']).drop_duplicates(subset=['customer_id'])
    df['total_orders'] = df['total_orders'].clip(lower=0)
    df['signup_date'] = pd.to_datetime(df['signup_date'], errors='coerce')
    df['signup_year'] = df['signup_date'].dt.year.fillna(2020).astype(int)
    df['signup_month'] = df['signup_date'].dt.month.fillna(1).astype(int)
    df['country_encoded'] = pd.Categorical(df['country']).codes
    df = df.drop(columns=['country', 'signup_date', 'avg_order_value', 'days_since_last_order'])
    df.to_csv(output_csv, index=False)

@component(base_image="python:3.9", packages_to_install=["pandas"])
def validate_data(input_csv: InputPath(str)):  # pyright: ignore[reportInvalidTypeForm]
    import pandas as pd
    df = pd.read_csv(input_csv)
    if df.empty:
        raise ValueError("Validation failed: extracted dataset is empty")
    if not df['churned'].isin([0, 1]).all():
        raise ValueError("Validation failed: churn labels must be 0 or 1")
    if not df['customer_id'].is_unique:
        raise ValueError("Validation failed: duplicate customer IDs found")
    print("Data validation passed")

@dsl.pipeline(name="churn-data-pipeline", description="Extract, Transform, Validate")
def churn_pipeline(db_uri: str):
    ext = extract_data(db_uri=db_uri)
    trans = transform_data(input_csv=ext.output)
    validate_data(input_csv=trans.output)
