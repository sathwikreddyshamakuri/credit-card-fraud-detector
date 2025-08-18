import pandas as pd, numpy as np
from pathlib import Path
P = Path(__file__).resolve().parent
truth = pd.read_csv(P / "data" / "creditcard.csv", usecols=["Class"]).Class.to_numpy()
preds = pd.read_csv(P / "fraud_scores.csv", usecols=["fraud_probability"])
probs = preds["fraud_probability"].to_numpy()

def metrics_at(th):
    pred = (probs >= th).astype(int)
    tp = ((truth==1) & (pred==1)).sum()
    fp = ((truth==0) & (pred==1)).sum()
    tn = ((truth==0) & (pred==0)).sum()
    fn = ((truth==1) & (pred==0)).sum()
    prec = tp / (tp+fp) if (tp+fp) else 0.0
    rec  = tp / (tp+fn) if (tp+fn) else 0.0
    f1   = (2*prec*rec)/(prec+rec) if (prec+rec) else 0.0
    flagged = (pred==1).sum()
    return prec, rec, f1, flagged

ths = np.linspace(0, 1, 1000)
rows = [{"threshold": float(th), **dict(zip(
    ["precision","recall","f1","flagged"], metrics_at(th)))} for th in ths]
df = pd.DataFrame(rows)
df.to_csv("threshold_sweep.csv", index=False)
print("Wrote threshold_sweep.csv")
print(df.sort_values("f1", ascending=False).head(10))
