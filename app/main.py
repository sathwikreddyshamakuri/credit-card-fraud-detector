from fastapi import FastAPI
from pydantic import BaseModel, Field
import joblib, os, uuid, time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = FastAPI(title="Fraud Inference", version="v1")
MODEL_PATH = os.getenv("MODEL_PATH", "artifacts/model.joblib")
model = joblib.load(MODEL_PATH)

PRED_COUNT = Counter("predict_requests_total", "Predict requests")
PRED_ERR   = Counter("predict_errors_total", "Predict errors")
PRED_LAT   = Histogram("predict_latency_seconds", "Predict latency seconds")

class PredictIn(BaseModel):
    features: list[float] = Field(..., description="Feature vector matching training schema")
    threshold: float = 0.5

class PredictOut(BaseModel):
    request_id: str
    model_version: str
    prob: float
    label: int

@app.get("/healthz")
def healthz():
    return {"ok": True, "version": "v1", "has_model": model is not None}

@app.get("/readyz")
def readyz():
    return {"ready": True}

@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}

@app.post("/predict", response_model=PredictOut)
def predict(body: PredictIn):
    start = time.time()
    PRED_COUNT.inc()
    try:
        prob = float(model.predict_proba([body.features])[0][1])
        label = int(prob >= body.threshold)
        return {
            "request_id": str(uuid.uuid4()),
            "model_version": "v1",
            "prob": prob,
            "label": label,
        }
    except Exception:
        PRED_ERR.inc()
        raise
    finally:
        PRED_LAT.observe(time.time() - start)
