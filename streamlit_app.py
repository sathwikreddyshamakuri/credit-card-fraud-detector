# app.py — simplified, tabbed UI with saved threshold default
import json
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

try:
    import joblib
except Exception:
    joblib = None

st.set_page_config(page_title="Credit Card Fraud Detector", page_icon="💳", layout="wide")

ARTIFACTS_DIR = Path("artifacts")
CONF_PATH = ARTIFACTS_DIR / "config.json"


#Config helpers (default threshold) 
def get_default_threshold() -> float:
    try:
        if CONF_PATH.exists():
            data = json.loads(CONF_PATH.read_text())
            v = float(data.get("threshold", 0.5))
            return float(min(max(v, 0.0), 1.0))
    except Exception:
        pass
    return 0.5


def save_default_threshold(v: float) -> None:
    try:
        ARTIFACTS_DIR.mkdir(exist_ok=True)
        data = {}
        if CONF_PATH.exists():
            try:
                data = json.loads(CONF_PATH.read_text())
            except Exception:
                data = {}
        data["threshold"] = float(min(max(v, 0.0), 1.0))
        CONF_PATH.write_text(json.dumps(data, indent=2))
    except Exception as e:
        st.warning(f"Could not save default threshold: {e}")


# ---------- Load model & stats ----------
@st.cache_resource(show_spinner=False)
def load_model():
    model_path = Path("artifacts/model.joblib")
    if model_path.exists() and joblib is not None:
        try:
            model = joblib.load(model_path)
            return model, True, "✅ Loaded model.joblib"
        except Exception as e:
            return None, False, f"⚠️ Could not load model.joblib: {e}"
    # Fallback so the UI still works without a model
    class _DemoModel:
        def predict_proba(self, X):
            amt = X["Amount"].values if "Amount" in X.columns else np.zeros(len(X))
            p = 0.15 * (amt / (amt.max() + 1e-9)) if amt.max() > 0 else np.zeros_like(amt, dtype=float)
            p = np.clip(p, 0.0, 0.15)
            return np.c_[1 - p, p]

        @property
        def classes_(self):
            return np.array([0, 1])

    return _DemoModel(), False, "🧪 Demo model active (put your trained model at artifacts/model.joblib)"


@st.cache_resource(show_spinner=False)
def load_feature_stats():
    stats_path = Path("artifacts/feature_stats.json")
    if stats_path.exists():
        try:
            with open(stats_path, "r") as f:
                return json.load(f), True, "✅ Loaded feature_stats.json"
        except Exception as e:
            return None, False, f"⚠️ Could not read feature_stats.json: {e}"
    return None, False, "ℹ️ No feature_stats.json (we’ll fill missing features with 0.0)."


model, model_is_real, model_msg = load_model()
feature_stats, has_stats, stats_msg = load_feature_stats()


def expected_features():
    feats = None
    if hasattr(model, "feature_names_in_"):
        try:
            feats = list(model.feature_names_in_)
        except Exception:
            feats = None
    if feats is None and has_stats and "feature_order" in feature_stats:
        feats = list(feature_stats["feature_order"])
    if feats is None:
        feats = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]
    return feats


FEATURES = expected_features()


def coerce(df: pd.DataFrame) -> pd.DataFrame:
    cols = FEATURES
    df = df.copy()
    defaults = (feature_stats or {}).get("defaults", {})
    for c in cols:
        if c not in df.columns:
            df[c] = float(defaults.get(c, 0.0))
    df = df[cols]
    for c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    return df


def score(df: pd.DataFrame, threshold: float) -> pd.DataFrame:
    X = coerce(df)
    proba = None
    if hasattr(model, "predict_proba"):
        try:
            proba = model.predict_proba(X)[:, -1]
        except Exception:
            proba = None
    if proba is None and hasattr(model, "decision_function"):
        try:
            raw = model.decision_function(X)
            proba = 1 / (1 + np.exp(-raw))
        except Exception:
            proba = None
    if proba is None and hasattr(model, "predict"):
        proba = model.predict(X).astype(float)
    out = X.copy()
    out["fraud_probability"] = proba
    out["is_fraud_pred"] = (out["fraud_probability"] >= threshold).astype(int)
    return out


#  Header & controls 
st.markdown("## 💳 Credit Card Fraud Detector")

with st.container():
    c1, c2, c3 = st.columns([1, 1, 2])

    # Slider uses saved default; step to 0.001 and full 0..1 range
    default_th = get_default_threshold()
    threshold = c1.slider("Decision threshold", 0.0, 1.0, default_th, 0.001, help="Scores ≥ threshold are flagged as fraud.")

    # Save the current slider value as default
    if c1.button("Save as default", use_container_width=True):
        save_default_threshold(threshold)
        st.success(f"Saved default threshold = {threshold:.3f} → artifacts/config.json")

    c2.number_input("Show top-K rows (Batch tab)", 1, 5000, 20, 1, key="topk")

    # status strip
    ok_style = "✅" if model_is_real else "🧪"
    st.caption(f"{ok_style} {model_msg}  •  {stats_msg}")

tabs = st.tabs(["Quick Predict", "Batch CSV", "JSON Row"])

# - Tab 1: Quick Predict 
with tabs[0]:
    st.markdown("### Quick Predict")
    st.write(
        "Enter **Amount** (and optionally **Time**). "
        "All other features will be filled from defaults"
        + (" in your feature stats." if has_stats else " (0.0 if no stats).")
    )
    q1, q2, q3 = st.columns([1, 1, 2])
    amt = q1.number_input("Amount", min_value=0.0, value=50.0, step=1.0)
    time = q2.number_input("Time (seconds since first txn)", min_value=0.0, value=10_000.0, step=100.0)

    # Build a single-row frame using defaults
    base = {c: (feature_stats["defaults"].get(c, 0.0) if has_stats else 0.0) for c in FEATURES}
    base["Amount"] = float(amt)
    if "Time" in base:
        base["Time"] = float(time)
    single_df = pd.DataFrame([base])

    if st.button("Predict", type="primary"):
        res = score(single_df, threshold)
        prob = float(res.loc[0, "fraud_probability"])
        label = int(res.loc[0, "is_fraud_pred"])
        st.success(f"Fraud probability: **{prob:.3f}**  •  Prediction: {'🚩 FRAUD' if label==1 else '✅ LEGIT'}")

        st.markdown("**Scored row (features shown after coercion):**")
        st.dataframe(res[FEATURES + ["fraud_probability", "is_fraud_pred"]], use_container_width=True)

    with st.expander("Need full control? (advanced form)"):
        st.write("This builds inputs for **all features** from your `feature_stats.json` ranges.")
        if not has_stats:
            st.info("Full form requires `artifacts/feature_stats.json`. Use the Batch CSV or JSON tabs instead.")
        else:
            defaults = feature_stats.get("defaults", {})
            ranges = feature_stats.get("input_ranges", {})
            mcol1, mcol2 = st.columns(2)
            values = {}
            for i, feat in enumerate(FEATURES):
                default = float(defaults.get(feat, 0.0))
                r = ranges.get(feat, None)
                kwargs = {"value": default}
                if r and isinstance(r, (list, tuple)) and len(r) == 2:
                    lo, hi = float(r[0]), float(r[1])
                    if lo > hi:
                        lo, hi = hi, lo
                    step = (hi - lo) / 100.0 if hi > lo else 0.01
                    kwargs.update({"min_value": lo, "max_value": hi, "step": max(step, 1e-4)})
                v = (mcol1 if i % 2 == 0 else mcol2).number_input(feat, **kwargs)
                values[feat] = v
            if st.button("Predict (advanced)"):
                adv_df = pd.DataFrame([values])
                res = score(adv_df, threshold)
                prob = float(res.loc[0, "fraud_probability"])
                label = int(res.loc[0, "is_fraud_pred"])
                st.success(f"Fraud probability: **{prob:.3f}**  •  Prediction: {'🚩 FRAUD' if label==1 else '✅ LEGIT'}")
                st.dataframe(res[FEATURES + ["fraud_probability", "is_fraud_pred"]], use_container_width=True)

#  Batch CSV
with tabs[1]:
    st.markdown("### Batch CSV")
    st.write(
        "Upload a CSV with columns matching your model’s input schema (e.g., Time, V1..V28, Amount). "
        "Extras are dropped; missing numeric columns are filled from defaults or 0.0."
    )
    csv = st.file_uploader("Upload CSV", type=["csv"])
    if st.button("Run Prediction on CSV"):
        if not csv:
            st.warning("Please upload a CSV first.")
        else:
            try:
                df = pd.read_csv(csv)
                scored = score(df, threshold)
                flagged = int((scored["fraud_probability"] >= threshold).sum())
                st.metric("Flagged (≥ threshold)", value=flagged)
                topk = int(st.session_state.get("topk", 20))
                st.dataframe(
                    scored.sort_values("fraud_probability", ascending=False).head(topk),
                    use_container_width=True,
                )
                st.download_button(
                    "⬇️ Download all results (CSV)",
                    data=scored.to_csv(index=False).encode("utf-8"),
                    file_name="fraud_scores.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(f"Could not score CSV: {e}")

# JSON Row 
with tabs[2]:
    st.markdown("### JSON Row")
    st.write("Paste a single JSON object (one transaction). Only provide fields you know; we’ll fill the rest.")
    example = '{"Time": 10000, "Amount": 250.75}'
    jtxt = st.text_area("JSON input", value=example, height=120)
    if st.button("Predict from JSON"):
        try:
            obj = json.loads(jtxt)
            scored = score(pd.DataFrame([obj]), threshold)
            st.dataframe(scored[FEATURES + ["fraud_probability", "is_fraud_pred"]], use_container_width=True)
        except Exception as e:
            st.error(f"Invalid JSON: {e}")
