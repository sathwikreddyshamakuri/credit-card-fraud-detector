from app.dummy_model import DummyModel
import joblib, os
os.makedirs("artifacts", exist_ok=True)
joblib.dump(DummyModel(), "artifacts/model.joblib")
print("Wrote artifacts/model.joblib (module = app.dummy_model.DummyModel)")
