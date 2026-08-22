import math
import os

import mlflow
import mlflow.sklearn
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Churn Prediction API")
MODEL_URI = os.getenv("MODEL_URI", "models:/ChurnModel@Production")
MODEL_FEATURES = [
    "total_orders",
    "country_encoded",
    "signup_year",
    "signup_month",
    "marketing_opt_in",
]
model = None
model_error = None
model_features = MODEL_FEATURES


@app.on_event("startup")
def load_prediction_model():
    global model, model_error, model_features
    try:
        model = mlflow.sklearn.load_model(MODEL_URI)
        model_features = list(getattr(model, "feature_names_in_", MODEL_FEATURES))
        model_error = None
    except Exception as exc:
        model = None
        model_error = str(exc)

class PredictionRequest(BaseModel):
    total_orders: float = Field(ge=0)
    country_encoded: int = Field(ge=0)
    signup_year: int = Field(default=2020, ge=1900, le=2100)
    signup_month: int = Field(default=1, ge=1, le=12)
    marketing_opt_in: bool = False

@app.get("/health")
def health_check():
    if model is None:
        return {
            "status": "degraded",
            "model_loaded": False,
            "model_uri": MODEL_URI,
            "model_error": model_error,
        }
    return {"status": "healthy", "model_loaded": True, "model_uri": MODEL_URI}

@app.post("/predict")
def predict(req: PredictionRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Prediction model is unavailable")

    raw_features = {
        "total_orders": math.log1p(req.total_orders),
        "country_encoded": req.country_encoded,
        "signup_year": req.signup_year,
        "signup_month": req.signup_month,
        "marketing_opt_in": req.marketing_opt_in,
    }
    data = pd.DataFrame([{feature: raw_features[feature] for feature in model_features}], columns=model_features)
    try:
        prediction = int(model.predict(data)[0])
        if hasattr(model, "predict_proba"):
            probability = float(model.predict_proba(data)[0][1])
        elif hasattr(model, "decision_function"):
            score = float(model.decision_function(data)[0])
            probability = 1.0 / (1.0 + math.exp(-score))
        else:
            probability = float(prediction)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Model prediction failed: {exc}") from exc

    return {"churn_risk": prediction, "probability": max(0.0, min(1.0, probability))}