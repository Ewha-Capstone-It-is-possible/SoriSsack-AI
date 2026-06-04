"""
train.py
--------------
Layer 1 / Layer 2 회귀 모델 오프라인 학습 (배치).

  python train.py

Layer 1 (카드 중요도):
  - time-based split: 과거 로그로 feature, 미래 로그 사용횟수(log1p)를 라벨로 학습
  - 데이터 누수 없이 "미래 7일 사용량 예측" 구조

Layer 2 (맥락 랭킹):
  - sentence_word_map 의 인접 쌍(prev→next)을 positive(1),
    같은 문맥의 비인접 후보를 negative(0)로 샘플링해 학습

학습 결과는 models/layer1.json, models/layer2.json 으로 저장된다.
scikit-learn 이 없으면 학습을 건너뛰고 서빙은 prior 가중치로 동작한다.
"""

import math
import random
from collections import Counter
from datetime import datetime, timedelta

import repo
import cards
from features import (
    BabyFeatureContext, layer1_features, layer2_features,
    LAYER1_FEATURES, LAYER2_FEATURES,
)
from linmodel import LinearModel, model_path

BABIES = [1, 2, 3, 4, 5]
SPLIT_DAYS = 3.5     # 더미 로그가 ~7일 범위 → 절반 지점으로 분할


def _try_sklearn():
    try:
        from sklearn.linear_model import LinearRegression
        return LinearRegression
    except ImportError:
        return None


# =======================================================
# Layer 1 데이터셋
# =======================================================
def build_layer1_dataset():
    X, y = [], []
    now = datetime.now()
    cutoff = now - timedelta(days=SPLIT_DAYS)
    for baby_id in BABIES:
        all_logs = repo.get_vocab_logs(baby_id, limit=100000)
        past_logs = [l for l in all_logs if l.get("used_at") and l["used_at"] <= cutoff]
        future = Counter(
            l.get("baby_card_id") for l in all_logs
            if l.get("used_at") and l["used_at"] > cutoff
        )
        ctx = BabyFeatureContext(baby_id, now=cutoff, logs_override=past_logs)
        for card in cards.get_enriched_candidates(baby_id):
            feats = layer1_features(card, ctx)
            X.append([feats[f] for f in LAYER1_FEATURES])
            y.append(math.log1p(future.get(card["baby_card_id"], 0)))
    return X, y


# =======================================================
# Layer 2 데이터셋
# =======================================================
def build_layer2_dataset():
    X, y = [], []
    rng = random.Random(7)
    # 학습 전 Layer1 점수를 채워둬야 cand_system_score feature 가 유효
    import layer1
    for baby_id in BABIES:
        layer1.update_scores(baby_id)

    for baby_id in BABIES:
        ctx = BabyFeatureContext(baby_id)
        lookup = cards.card_lookup(baby_id)
        all_cands = list(lookup.values())
        for sentence in repo.get_sentence_word_map(baby_id):
            keys = [repo.card_key(w.get("baby_card_id"), w.get("card_id"), w.get("text"))
                    for w in sentence]
            for i in range(len(sentence) - 1):
                sel = lookup.get(keys[i])
                pos_cand = lookup.get(keys[i + 1])
                if not sel or not pos_cand:
                    continue
                # positive
                X.append([layer2_features(sel, pos_cand, ctx)[f] for f in LAYER2_FEATURES])
                y.append(1.0)
                # negative: 같은 후보군에서 무관한 카드 2개
                for _ in range(2):
                    neg = rng.choice(all_cands)
                    if repo.card_key(neg["baby_card_id"], neg["card_id"], neg["text"]) in keys:
                        continue
                    X.append([layer2_features(sel, neg, ctx)[f] for f in LAYER2_FEATURES])
                    y.append(0.0)
    return X, y


# =======================================================
# 학습 실행
# =======================================================
def _fit_and_save(name, feature_order, X, y):
    LinearRegression = _try_sklearn()
    if LinearRegression is None:
        print(f"  [skip] scikit-learn 미설치 → {name} 은 prior 가중치로 서빙됩니다.")
        return None
    if not X:
        print(f"  [skip] {name} 학습 데이터 없음")
        return None
    reg = LinearRegression()
    reg.fit(X, y)
    coef = {f: float(w) for f, w in zip(feature_order, reg.coef_)}
    model = LinearModel(feature_order, coef, intercept=float(reg.intercept_), source="trained")
    model.save(model_path(name))
    r2 = reg.score(X, y)
    print(f"  [ok] {name}: {len(X)} samples, R²={r2:.3f} → {model_path(name)}")
    return model


def main():
    print("Layer 1 학습 (카드 중요도, 미래 7일 사용량 회귀)")
    X1, y1 = build_layer1_dataset()
    _fit_and_save("layer1", LAYER1_FEATURES, X1, y1)

    print("Layer 2 학습 (맥락 랭킹, 다음 단어 확률 회귀)")
    X2, y2 = build_layer2_dataset()
    _fit_and_save("layer2", LAYER2_FEATURES, X2, y2)

    print("완료.")


if __name__ == "__main__":
    main()
