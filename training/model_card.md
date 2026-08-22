
# Model Card: Customer Churn Predictor

- **Features Used**: country_encoded, total_orders, days_since_last_order, avg_order_value.
- **Validation Strategy**: 80/20 Train/Test split, 3-fold Cross-Validation.
- **Key Metric**: Accuracy (Baseline: 0.82, Best RF: 0.89), Recall (Critical for churn).
- **Known Limitations**: Assumes historical order patterns predict future behavior; does not account for external market shocks.
