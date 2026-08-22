import streamlit as st
import requests
import os

st.title("Customer Churn Predictor")
st.write("Enter customer details to predict 90-day churn risk.")
API_URL = os.getenv("API_URL", "http://localhost:8000")

total_orders = st.number_input("Total Orders", min_value=0, value=5)
country_encoded = st.selectbox("Country Code", [0, 1, 2, 3, 4])
signup_year = st.number_input("Signup Year", min_value=1900, max_value=2100, value=2020)
signup_month = st.number_input("Signup Month", min_value=1, max_value=12, value=1)
marketing_opt_in = st.checkbox("Marketing opt-in")

if st.button("Predict"):
    payload = {
        "total_orders": total_orders,
        "country_encoded": country_encoded,
        "signup_year": signup_year,
        "signup_month": signup_month,
        "marketing_opt_in": marketing_opt_in,
    }
    try:
        response = requests.post(f"{API_URL.rstrip('/')}/predict", json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        st.metric("Churn Probability", f"{result['probability']:.2%}")
        if result['churn_risk'] == 1:
            st.error("High Risk: Trigger retention campaign.")
        else:
            st.success("Low Risk: Continue standard engagement.")
    except requests.RequestException as exc:
        st.error(f"Prediction service unavailable: {exc}")