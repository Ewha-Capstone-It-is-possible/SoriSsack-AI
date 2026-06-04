"""
recommend.py
--------------
단어 추천 오케스트레이션 (AI 1번 기능).

파이프라인:
  0. Layer 1 배치 점수 보장 (baby_card.system_score)
  1. 후보 enrich + 선택 카드 파악
  2. STEP 1 — 태그 기반 의미 필터 (multi high-tag 교집합 + 브릿지 + fallback)  [tags.py]
  3. STEP 2 — 품사 전이는 hard-drop 하지 않고 Layer2 feature(pos_transition_prob)로 soft 반영
  4. STEP 3 — Layer 2 맥락 회귀로 후보 점수화·정렬                              [layer2.py]
  5. STEP 4 — GPT selector 로 상위 4~5개 선별·정렬 (새 단어 생성 금지)          [gpt_selector.py]

회귀(Layer1/2)가 메인, GPT 는 보조(검증·재정렬). GPT 키 없으면 회귀 순서 그대로.
"""

from typing import Optional

import repo
import cards
import tags
import layer1
import layer2
import gpt_selector
import onboarding
from features import BabyFeatureContext, _high_tags

SHORTLIST_MULT = 3          # GPT 에 넘길 후보 수 = top_n * 배수
MAX_SELECTABLE_POSITION = 4
COGNITIVE_BOOST = 0.15      # 약한 인지 영역 태그 카드 점수 가산율 (폐쇄루프)


def _key(c):
    return repo.card_key(c.get("baby_card_id"), c.get("card_id"), c.get("text"))


def recommend_words(
    baby_id: int,
    selected_baby_card_id: Optional[int] = None,
    top_n: int = 5,
    session_length: int = 1,
    use_gpt: bool = True,
) -> dict:
    # 0. Layer1 점수 보장 (cand_system_score feature 입력)
    layer1.update_scores(baby_id)

    ctx = BabyFeatureContext(baby_id)
    all_cards = cards.get_enriched_candidates(baby_id)

    # 1. 선택 카드 파악
    selected = None
    if selected_baby_card_id is not None:
        selected = next(
            (c for c in all_cards if c["baby_card_id"] == selected_baby_card_id), None)
    selected_text = selected["text"] if selected else None
    sel_key = _key(selected) if selected else None

    candidates = [c for c in all_cards if _key(c) != sel_key]

    # 2. STEP 1 — 태그 의미 필터 (+ 브릿지 + fallback)
    filtered, stage = tags.filter_by_tag(selected, candidates)

    # 후보별 런타임 신호
    runtime_by_key = {
        _key(c): {
            "filter_stage_passed": stage.get(_key(c), 1.0),
            "session_length": session_length,
            "max_selectable_position": MAX_SELECTABLE_POSITION,
        }
        for c in filtered
    }

    # 3~4. STEP 3 — Layer2 맥락 회귀 점수화·정렬
    ranked = layer2.rank_candidates(selected, filtered, ctx, runtime_by_key)

    # 4.5 폐쇄루프 — 약한 인지 영역 태그 카드 점수 가산 (약점 강화)
    weak_tags = onboarding.get_weak_dimension_tags(baby_id)
    if weak_tags:
        for c in ranked:
            if weak_tags & _high_tags(c.get("baby_card_id"), c.get("card_id")):
                c["system_score"] = round(c["system_score"] * (1 + COGNITIVE_BOOST), 4)
                c["cognitive_boost"] = True
        ranked.sort(key=lambda x: x["system_score"], reverse=True)

    # 5. STEP 4 — GPT selector (상위 shortlist → 4~5개 선별)
    shortlist = ranked[: max(top_n * SHORTLIST_MULT, 10)]
    final = gpt_selector.select(selected_text, shortlist, top_n) if use_gpt else shortlist[:top_n]

    recommended = [
        {
            "baby_card_id": c.get("baby_card_id"),
            "card_id":      c.get("card_id"),
            "text":         c.get("text"),
            "pos":          c.get("pos"),
            "system_score": c.get("system_score", 0.0),
        }
        for c in final
    ]

    return {
        "baby_id":           baby_id,
        "selected_word":     selected_text,
        "recommended_words": recommended,
    }
