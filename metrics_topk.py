# metrics_topk.py
import pandas as pd
from pathlib import Path

P = Path(__file__).resolve().parent
truth = pd.read_csv(P / "data" / "creditcard.csv", usecols=["Class"])
preds = pd.read_csv(P / "fraud_scores.csv", usecols=["fraud_probability"])

df = pd.concat([truth, preds], axis=1)
df = df.sort_values("fraud_probability", ascending=False).reset_index(drop=True)

K = 1000   # <-- set the number of cases you want to flag
df["is_fraud_pred"] = 0
df.loc[:K-1, "is_fraud_pred"] = 1

tp = ((df.Class==1) & (df.is_fraud_pred==1)).sum()
fp = ((df.Class==0) & (df.is_fraud_pred==1)).sum()
precision = tp / K if K else 0.0
recall = tp / (df.Class==1).sum()

print(f"Top-{K} precision: {precision:.4f}  (TP={tp}, FP={fp})")
print(f"Top-{K} recall:    {recall:.4f}")
print(f"Implied threshold ≈ {float(df.loc[K-1, 'fraud_probability']):.6f}")
