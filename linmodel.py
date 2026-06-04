"""
linmodel.py
--------------
경량 선형 회귀 모델 컨테이너 + JSON 저장/로드.

  score = intercept + Σ coef[feature] * x[feature]

train.py 가 scikit-learn 으로 학습한 가중치를 JSON 으로 저장하고,
서빙 시 layer1/layer2 가 이 클래스로 로드한다. 학습 결과 파일이 없으면
각 레이어의 config 기반 prior 가중치로 fallback 한다.
"""

import json
import os

import config


class LinearModel:
    def __init__(self, feature_order, coef, intercept=0.0, source="prior"):
        self.feature_order = list(feature_order)
        self.coef = dict(coef)
        self.intercept = float(intercept)
        self.source = source   # "trained" | "prior"

    def score(self, feats: dict) -> float:
        s = self.intercept
        for f in self.feature_order:
            s += self.coef.get(f, 0.0) * feats.get(f, 0.0)
        return round(s, 4)

    # ---------- 직렬화 ----------
    def to_dict(self):
        return {
            "feature_order": self.feature_order,
            "coef": self.coef,
            "intercept": self.intercept,
            "source": "trained",
        }

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return cls(d["feature_order"], d["coef"], d.get("intercept", 0.0),
                   source=d.get("source", "trained"))


def model_path(name: str) -> str:
    return os.path.join(config.MODEL_DIR, f"{name}.json")


def load_or_none(name: str):
    path = model_path(name)
    if os.path.exists(path):
        try:
            return LinearModel.load(path)
        except Exception:
            return None
    return None
