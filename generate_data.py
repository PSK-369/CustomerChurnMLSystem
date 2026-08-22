import pandas as pd
import numpy as np
import os
import argparse

def generate_data(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    np.random.seed(42)
    
    # 1. Customers
    n_cust = 1_000_000
    countries = np.random.choice(['USA', 'UK', 'India', 'Germany', 'Canada'], n_cust, p=[0.4, 0.2, 0.2, 0.1, 0.1])
    emails = [f"user{i}@example.com" if i % 100 != 0 else "duplicate@example.com" for i in range(n_cust)]
    signup_dates = pd.date_range('2020-01-01', '2024-01-01', periods=n_cust).strftime('%Y-%m-%d')
    
    # Use strings for booleans to prevent Pandas float casting (0.0/1.0)
    marketing_choices = np.random.choice(['true', 'false', ''], n_cust, p=[0.6, 0.3, 0.1])
    
    customers = pd.DataFrame({
        'customer_id': range(1, n_cust + 1),
        'first_name': np.random.choice(['John', 'Jane', 'Alex', 'Sam', ''], n_cust, p=[0.3, 0.3, 0.2, 0.1, 0.1]),
        'last_name': np.random.choice(['Doe', 'Smith', 'Brown', ''], n_cust, p=[0.4, 0.3, 0.2, 0.1]),
        'email': emails,
        'signup_date': signup_dates,
        'country': countries,
        'marketing_opt_in': marketing_choices
    })
    customers.to_csv(f"{out_dir}/customers.csv", index=False)

    # 2. Products
    n_prod = 10_000
    products = pd.DataFrame({
        'product_id': range(1, n_prod + 1),
        'product_name': [f"Product_{i}" for i in range(1, n_prod + 1)],
        'category': np.random.choice(['Electronics', 'Clothing', 'Home', ''], n_prod, p=[0.4, 0.3, 0.2, 0.1]),
        'unit_price': np.random.uniform(10.0, 500.0, n_prod).round(2),
        'active': np.random.choice(['true', 'false'], n_prod, p=[0.9, 0.1])
    })
    products.to_csv(f"{out_dir}/products.csv", index=False)

    # 3. Orders
    n_ord = 3_000_000
    order_dates = pd.date_range('2023-01-01', '2024-08-22', periods=n_ord)
    null_mask = np.random.rand(n_ord) < 0.01
    
    order_dates_series = pd.Series(order_dates).where(~null_mask, pd.NaT)
    order_dates_str = order_dates_series.dt.strftime('%Y-%m-%d %H:%M:%S').replace('NaT', '')
    
    orders = pd.DataFrame({
        'order_id': range(1, n_ord + 1),
        'customer_id': np.random.randint(1, n_cust + 1, n_ord),
        'order_date': order_dates_str,
        'status': np.random.choice(['completed', 'cancelled', 'returned', 'pending'], n_ord, p=[0.7, 0.1, 0.1, 0.1]),
        'order_total': np.random.uniform(20.0, 1000.0, n_ord).round(2)
    })
    orders.to_csv(f"{out_dir}/orders.csv", index=False)

    # 4. Order Items
    n_items = 5_000_000
    order_items = pd.DataFrame({
        'order_item_id': range(1, n_items + 1),
        'order_id': np.random.randint(1, n_ord + 1, n_items),
        'product_id': np.random.randint(1, n_prod + 1, n_items),
        'quantity': np.random.randint(1, 5, n_items),
        'unit_price': np.random.uniform(10.0, 500.0, n_items).round(2)
    })
    order_items.to_csv(f"{out_dir}/order_items.csv", index=False)
    
    print(f"Data generated successfully in {out_dir}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data")
    generate_data(parser.parse_args().out_dir)