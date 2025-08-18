# metrics_sweep.py
import pandas as pd
import numpy as np
from pathlib import Path

P = Path(__file__).resolve().parent
truth = pd.read_csv(P / "data" / "creditcard.csv", usecols=["Class"]).Class.to_numpy()
preds = pd.read_csv(P / "fraud_scores.csv", usecols=["fraud_probability","is_fraud_pred"])

probs = preds["fraud_probability"].to_numpy()

def metrics_at(th):
    pred = (probs >= th).astype(int)
    tp = ((truth==1) & (pred==1)).sum()
    fp = ((truth==0) & (pred==1)).sum()
    tn = ((truth==0) & (pred==0)).sum()
    fn = ((truth==1) & (pred==0)).sum()
    precision = tp / (tp+fp) if (tp+fp) else 0.0
    recall    = tp / (tp+fn) if (tp+fn) else 0.0
    f1        = (2*precision*recall)/(precision+recall) if (precision+recall) else 0.0
    flagged   = (pred==1).sum()
    return tp, fp, tn, fn, precision, recall, f1, flagged

ths = np.concatenate([
    np.linspace(0.01, 0.99, 99),  # coarse
    np.percentile(probs, np.linspace(90, 100, 101))  # finer near the top
])
rows = []
seen = set()
for th in np.clip(ths, 0, 1):
    th = float(round(th, 6))
    if th in seen: 
        continue
    seen.add(th)
    tp, fp, tn, fn, p, r, f1, flagged = metrics_at(th)
    rows.append({"threshold": th, "precision": p, "recall": r, "f1": f1, "flagged": flagged})

df = pd.DataFrame(rows).sort_values("threshold")
df.to_csv("threshold_sweep.csv", index=False)
print("Wrote threshold_sweep.csv")
print(df.sort_values("f1", ascending=False).head(10))         # best F1
print("\nPrecise operating points (examples):")
for target_p in [0.2, 0.5, 0.8]:
    near = df.iloc[(df["precision"]-target_p).abs().argsort()[:1]]
    print(f"~Precision {target_p:.0%} -> threshold≈{float(near.threshold):.3f}, "
          f"recall={float(near.recall):.3f}, flagged={int(near.flagged)}")
