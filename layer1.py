"""
layer1.py
--------------
Layer 1 — 카드 중요도 회귀 (Card Importance).

"이 아동에게 이 카드가 얼마나 중요한가" 를 feature 15개로 회귀 예측한다.
정답 라벨 = 미래 7일 사용 횟수(train.py 에서 time-based split). 배치(주 1회)로
계산해 baby_card.system_score 에 저장 → Layer 2 의 입력 feature 로 재사용.

서빙:
  - models/layer1.json (학습 결과)이 있으면 그 가중치 사용
  - 없으면 scoring_config + prior 가중치로 fallback (항상 동작)
"""

import repo
import cards
from features import BabyFeatureContext, layer1_features, LAYER1_FEATURES
from linmodel import LinearModel, load_or_none

# -------------------------------------------------------
# prior 가중치 (학습 모델 없을 때 fallback)
# -------------------------------------------------------
PRIOR_WEIGHTS = {
    "usage_count_7d": 1.0, "usage_count_30d": 0.6, "usage_trend": 0.4,
    "recency": 1.2, "time_diversity_entropy": 0.3,
    "sentence_completion_rate": 1.5, "avg_sentence_position": 0.2,
    "is_favorite": 0.8, "source_weight": 0.7, "priority": 0.5,
    "tag_confidence_avg": 0.3, "tag_coverage": 0.3, "co_occurrence_centrality": 0.6,
    "onboarding_match_score": 0.6, "cognitive_difficulty_gap": -0.5,
}

# scoring_config(feature_key) → Layer1 feature 매핑 (아동별 개인화 가중치 반영)
_CONFIG_MAP = {
    "usage_count": "usage_count_7d",
    "recency": "recency",
    "time_diversity": "time_diversity_entropy",
    "priority": "priority",
}


def _fallback_model(baby_id: int) -> LinearModel:
    weights = dict(PRIOR_WEIGHTS)
    for cfg in repo.get_scoring_config(baby_id, target_type="card"):
        mapped = _CONFIG_MAP.get(cfg["feature_key"])
        if mapped:
            weights[mapped] = cfg["weight"]   # 아동별 override
    return LinearModel(LAYER1_FEATURES, weights, intercept=0.0, source="prior")


def get_model(baby_id: int) -> LinearModel:
    trained = load_or_none("layer1")
    return trained if trained else _fallback_model(baby_id)


def predict(card: dict, ctx: BabyFeatureContext, model: LinearModel = None) -> float:
    model = model or get_model(ctx.baby_id)
    feats = layer1_features(card, ctx)
    return model.score(feats)


# -------------------------------------------------------
# 배치: 아동의 모든 후보 카드 중요도 계산 → 저장
# -------------------------------------------------------
def compute_importance(baby_id: int) -> dict:
    """{card_key: system_score} 반환 (저장은 하지 않음)"""
    ctx = BabyFeatureContext(baby_id)
    model = get_model(baby_id)
    scores = {}
    for card in cards.get_enriched_candidates(baby_id):
        key = repo.card_key(card.get("baby_card_id"), card.get("card_id"), card.get("text"))
        scores[key] = predict(card, ctx, model)
    return scores


def update_scores(baby_id: int) -> int:
    """배치 실행: system_score 계산 후 저장. 갱신된 카드 수 반환."""
    scores = compute_importance(baby_id)
    repo.set_system_scores(scores)
    return len(scores)
