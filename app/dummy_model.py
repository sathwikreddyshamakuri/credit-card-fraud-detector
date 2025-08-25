import math

class DummyModel:
    def predict_proba(self, X):
        out = []
        for row in X:
            s = sum(float(v) for v in row)
            p = 1 / (1 + math.exp(-s / 10))
            out.append([1 - p, p])  # [neg, pos]
        return out
