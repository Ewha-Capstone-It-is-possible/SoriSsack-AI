"""
layer2.py
--------------
Layer 2 — 맥락 랭킹 회귀 (Contextual Ranking).

"방금 선택한 카드 다음에 이 후보가 올 점수" 를 feature 20개로 실시간 산출한다.
입력 = (선택 카드, 후보 카드) 쌍 + Layer1 의 cand_system_score.
저장하지 않고 매 요청마다 계산 → 상위 N개 정렬.

서빙:
  - models/layer2.json 있으면 학습 가중치 사용
  - 없으면 prior 가중치 fallback
"""

from features import BabyFeatureContext, layer2_features, LAYER2_FEATURES
from linmodel import LinearModel, load_or_none

# -------------------------------------------------------
# prior 가중치 (관계 feature 중심)
# -------------------------------------------------------
PRIOR_WEIGHTS = {
    "cand_system_score": 1.0, "cand_source_weight": 0.4,
    "co_occurrence_count": 1.0, "co_occurrence_pmi": 0.8, "sequential_probability": 1.5,
    "high_tag_overlap": 0.7, "low_tag_overlap": 0.5, "pos_transition_prob": 0.6,
    "cand_recency_decay": 0.5, "time_of_day_match": 0.5, "day_of_week_match": 0.2,
    "session_length_so_far": 0.1,
    "cand_personal_usage": 0.6, "cand_is_favorite": 0.5, "child_pos_preference": 0.4,
    "cognitive_match": 0.4, "cand_tag_confidence_avg": 0.2,
    "is_bridge_card": 0.3, "filter_stage_passed": 0.4, "max_selectable_position": 0.1,
}


def _fallback_model() -> LinearModel:
    return LinearModel(LAYER2_FEATURES, PRIOR_WEIGHTS, intercept=0.0, source="prior")


def get_model() -> LinearModel:
    trained = load_or_none("layer2")
    return trained if trained else _fallback_model()


def predict(selected: dict, cand: dict, ctx: BabyFeatureContext,
            runtime: dict = None, model: LinearModel = None) -> float:
    model = model or get_model()
    feats = layer2_features(selected, cand, ctx, runtime)
    return model.score(feats)


def rank_candidates(selected: dict, candidates: list, ctx: BabyFeatureContext,
                    runtime_by_key: dict = None) -> list:
    """
    후보 리스트를 Layer2 점수로 매겨 정렬해 반환.
    runtime_by_key: {card_key: runtime_dict}  (filter_stage_passed 등 후보별 런타임 신호)
    """
    model = get_model()
    runtime_by_key = runtime_by_key or {}
    scored = []
    for cand in candidates:
        key = ctx.key_of(cand)
        rt = runtime_by_key.get(key, {})
        score = predict(selected, cand, ctx, rt, model)
        item = dict(cand)
        item["system_score"] = score
        scored.append(item)
    scored.sort(key=lambda x: x["system_score"], reverse=True)
    return scored
