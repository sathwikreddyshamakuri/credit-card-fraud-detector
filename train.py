# train.py  — loud & robust
from pathlib import Path
import sys, json, traceback

print("=== train.py starting ===", flush=True)

try:
    import joblib, pandas as pd
    from sklearn.model_selection import train_test_split
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from sklearn.metrics import classification_report, roc_auc_score
except Exception as e:
    print("ERROR: Failed importing libraries:", e, file=sys.stderr, flush=True)
    raise

PROJECT_DIR = Path(__file__).resolve().parent
DATA_PATH = PROJECT_DIR / "data" / "creditcard.csv"
ARTIFACTS_DIR = PROJECT_DIR / "artifacts"
ARTIFACTS_DIR.mkdir(exist_ok=True)

def save_feature_stats(X_train: pd.DataFrame, out_path: Path):
    print(f"[save_feature_stats] columns={len(X_train.columns)}", flush=True)
    num_cols = X_train.columns.tolist()
    stats = {
        "feature_order": num_cols,
        "defaults": X_train[num_cols].median(numeric_only=True).to_dict(),
        "input_ranges": {
            c: [
                float(X_train[c].quantile(0.01)),
                float(X_train[c].quantile(0.99)),
            ] for c in num_cols
        },
    }
    with open(out_path, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"[save_feature_stats] wrote -> {out_path}", flush=True)

def train_with_dataset():
    print(f"[train_with_dataset] reading CSV: {DATA_PATH}", flush=True)
    df = pd.read_csv(DATA_PATH)  # will raise if not found
    print(f"[train_with_dataset] df shape = {df.shape}", flush=True)
    assert "Class" in df.columns, "CSV missing 'Class' label column"
    X = df.drop(columns=["Class"])
    y = df["Class"]

    X_train, X_valid, y_train, y_valid = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    print(f"[split] X_train={X_train.shape}, X_valid={X_valid.shape}", flush=True)

    clf = Pipeline([
        ("model", LogisticRegression(max_iter=2000, class_weight="balanced"))
    ])
    print("[fit] training LogisticRegression...", flush=True)
    clf.fit(X_train, y_train)

    print("[eval] evaluating...", flush=True)
    y_prob = clf.predict_proba(X_valid)[:, 1]
    y_pred = (y_prob >= 0.5).astype(int)
    print("ROC AUC:", roc_auc_score(y_valid, y_prob), flush=True)
    print(classification_report(y_valid, y_pred, digits=4), flush=True)

    model_path = ARTIFACTS_DIR / "model.joblib"
    joblib.dump(clf, model_path)
    print(f"[save] model -> {model_path}", flush=True)

    stats_path = ARTIFACTS_DIR / "feature_stats.json"
    save_feature_stats(X_train, stats_path)

def make_demo_artifacts():
    print("[demo] dataset not found; building DEMO artifacts...", flush=True)
    import numpy as np
    cols = ["Time"] + [f"V{i}" for i in range(1,29)] + ["Amount"]
    n = 5000
    X = pd.DataFrame(np.random.normal(size=(n, len(cols))), columns=cols)
    X["Time"] = np.random.uniform(0, 172800, size=n)
    X["Amount"] = np.abs(np.random.normal(60, 35, size=n))
    y = (X["Amount"] > 120).astype(int)
    clf = LogisticRegression(max_iter=1000)
    clf.fit(X, y)
    joblib.dump(clf, ARTIFACTS_DIR / "model.joblib")
    save_feature_stats(X, ARTIFACTS_DIR / "feature_stats.json")
    print("[demo] wrote demo model + stats", flush=True)

if __name__ == "__main__":
    try:
        print(f"PROJECT_DIR = {PROJECT_DIR}", flush=True)
        print(f"DATA_PATH   = {DATA_PATH}  (exists={DATA_PATH.exists()})", flush=True)
        print(f"ARTIFACTS   = {ARTIFACTS_DIR}", flush=True)

        if DATA_PATH.exists():
            train_with_dataset()
        else:
            make_demo_artifacts()

        print("=== train.py done ===", flush=True)
    except Exception as e:
        print("FATAL:", e, file=sys.stderr, flush=True)
        traceback.print_exc()
        sys.exit(1)
