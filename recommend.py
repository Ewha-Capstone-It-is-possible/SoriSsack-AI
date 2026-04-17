"""
recommend.py
--------------
단어 추천 모델 핵심 로직.

흐름:
  1. 선택된 단어의 태그/품사 기반으로 후보 단어 필터링 (DB 기반)
  2. 각 후보에 대해 usage_count / recency / time_diversity / priority feature 계산
  3. scoring_config 가중치를 적용해 system_score 계산 (회귀 기반)
  4. 상위 4~5개 반환

DB 붙일 때: dummy_data.py의 함수들을 db.py의 SQLAlchemy 쿼리로 교체
"""

from datetime import datetime
from typing import Optional
import math

from db import (
    get_candidate_cards,
    get_card_master,
    get_vocab_logs,
    get_scoring_config,
    get_baby_card_tags,
    get_tag,
)

# -------------------------------------------------------
# 품사 전이 규칙
# 선택된 품사 → 다음에 올 수 있는 품사 목록
# 예: 명사(장난감) 선택 → 동사(사주세요), 형용사(갖고싶어요) 우선
# -------------------------------------------------------
POS_TRANSITION = {
    "noun":      ["verb", "adjective"],           # 명사 → 동사, 형용사
    "verb":      ["noun", "verb"],                # 동사 → 명사(목적어), 동사
    "adjective": ["noun", "verb"],                # 형용사 → 명사, 동사
    None:        ["noun", "verb", "adjective"],   # 첫 선택 → 전부 허용
}


# -------------------------------------------------------
# Feature 계산 함수들
# -------------------------------------------------------

def compute_usage_count_feature(baby_card_id: int, logs: list[dict]) -> float:
    """
    feature: usage_count
    전체 로그에서 이 카드의 사용 횟수를 정규화 (0~1)
    """
    total = len(logs)
    if total == 0:
        return 0.0
    count = sum(1 for l in logs if l["baby_card_id"] == baby_card_id)
    return count / total


def compute_recency_feature(last_used_at: Optional[datetime]) -> float:
    """
    feature: recency
    마지막 사용 시각으로부터 경과 시간 → 최근일수록 높은 점수
    감쇠: exp(-경과시간_시간 / 24) (24시간 반감기)
    """
    if last_used_at is None:
        return 0.0
    hours_elapsed = (datetime.now() - last_used_at).total_seconds() / 3600
    return math.exp(-hours_elapsed / 24)


def compute_time_diversity_feature(baby_card_id: int, logs: list[dict]) -> float:
    """
    feature: time_diversity
    하루 중 몇 개의 다른 시간대(시 단위)에서 사용됐는지 → 다양할수록 높은 점수
    정규화: 고유 시간대 수 / 24
    """
    hours_used = {l["used_at"].hour for l in logs if l["baby_card_id"] == baby_card_id}
    return len(hours_used) / 24.0


def compute_priority_feature(priority: Optional[int]) -> float:
    """
    feature: priority
    baby_card.priority 값을 정규화 (낮을수록 중요 → 역수 정규화)
    priority 1 → 1.0, priority 2 → 0.5, priority 3 → 0.33 ...
    """
    if priority is None or priority <= 0:
        return 0.5  # 기본값
    return 1.0 / priority


# -------------------------------------------------------
# Step 1: 태그 기반 의미 필터링
# -------------------------------------------------------

def _get_high_tags(baby_card_id: Optional[int], card_id: Optional[int]) -> set[int]:
    """카드의 high 태그 집합 반환 (개인 카드·기본 카드 모두 지원)"""
    tag_ids = get_baby_card_tags(baby_card_id, card_id)
    high_tags = set()
    for tag_id in tag_ids:
        tag = get_tag(tag_id)
        if tag:
            if tag["tag_level"] == "high":
                high_tags.add(tag_id)
            elif tag["parent_tag_id"]:
                high_tags.add(tag["parent_tag_id"])
    return high_tags


def filter_by_tag_semantic(
    selected_baby_card_id: Optional[int],
    candidate_keys: list[tuple],  # [(baby_card_id | None, card_id | None), ...]
) -> set[tuple]:
    """
    선택된 카드와 동일 high 태그 그룹에 속하는 후보만 필터링.
    반환값: 통과한 (baby_card_id, card_id) 튜플 집합
    → base 카드(baby_card_id=None)도 card_id로 구분 가능
    """
    all_keys = set(candidate_keys)

    if selected_baby_card_id is None:
        return all_keys

    # 선택된 카드의 high 태그
    selected_card_id = next(
        (k[1] for k in candidate_keys if k[0] == selected_baby_card_id), None
    )
    selected_high_tags = _get_high_tags(selected_baby_card_id, selected_card_id)

    if not selected_high_tags:
        return all_keys

    filtered = set()
    for bcid, cid in candidate_keys:
        if bcid == selected_baby_card_id:
            continue
        card_high_tags = _get_high_tags(bcid, cid)
        if card_high_tags & selected_high_tags:
            filtered.add((bcid, cid))

    # 후보가 3개 미만이면 전체 반환
    return filtered if len(filtered) >= 3 else all_keys


# -------------------------------------------------------
# Step 2: 품사 전이 규칙 필터링
# -------------------------------------------------------

def filter_by_pos_transition(selected_pos: Optional[str], candidates: list[dict]) -> list[dict]:
    """
    선택된 단어의 품사 기반으로 다음에 올 수 있는 품사만 필터링.
    예: 명사(장난감) 선택 → 동사(사주세요), 형용사(갖고싶어요) 포함
    """
    allowed_pos = POS_TRANSITION.get(selected_pos, ["Noun", "verb", "adjective"])
    return [c for c in candidates if c.get("pos") in allowed_pos]


# -------------------------------------------------------
# Step 3: scoring_config 기반 system_score 계산
# -------------------------------------------------------

def compute_system_score(
    baby_card_id: int,
    last_used_at: Optional[datetime],
    priority: Optional[int],
    logs: list[dict],
    config: list[dict],
) -> float:
    """
    scoring_config 가중치를 적용해 system_score 계산.

    score = Σ (weight_i * feature_i)

    features:
      - usage_count:    전체 로그 대비 사용 비율
      - recency:        최근 사용일수록 높음 (지수 감쇠)
      - time_diversity: 사용된 시간대 다양성
      - priority:       카드 우선순위 (낮을수록 중요)
    """
    features = {
        "usage_count":    compute_usage_count_feature(baby_card_id, logs),
        "recency":        compute_recency_feature(last_used_at),
        "time_diversity": compute_time_diversity_feature(baby_card_id, logs),
        "priority":       compute_priority_feature(priority),
    }

    score = 0.0
    for cfg in config:
        key = cfg["feature_key"]
        if key in features:
            score += cfg["weight"] * features[key]

    return round(score, 4)


# -------------------------------------------------------
# 메인 추천 함수
# -------------------------------------------------------

def recommend_words(
    baby_id: int,
    selected_baby_card_id: Optional[int],
    top_n: int = 5,
) -> dict:
    """
    단어 추천 메인 함수.

    Args:
        baby_id:               아동 ID
        selected_baby_card_id: 방금 선택한 baby_card_id (첫 선택이면 None)
        top_n:                 추천 단어 수 (기본 5개)

    Returns:
        {
          "baby_id": int,
          "selected_word": Optional[str],
          "recommended_words": [
            {"baby_card_id": int, "text": str, "pos": str, "system_score": float},
            ...
          ]
        }
    """

    # --- 선택된 카드 정보 파악 ---
    selected_pos = None
    selected_text = None

    # 개인 카드 + 기본 카드 전체 후보
    baby_cards_all = get_candidate_cards(baby_id)

    if selected_baby_card_id is not None:
        selected_bc = next(
            (c for c in baby_cards_all if c["baby_card_id"] == selected_baby_card_id),
            None,
        )
        if selected_bc:
            # 텍스트: baby_card.text 우선, 없으면 card_master.base_text
            if selected_bc["text"]:
                selected_text = selected_bc["text"]
            elif selected_bc["card_id"]:
                master = get_card_master(selected_bc["card_id"])
                selected_text = master["base_text"] if master else None

            # 품사: baby_card.type 우선, 없으면 card_master.part_of_speech
            if selected_bc["type"]:
                selected_pos = selected_bc["type"]
            elif selected_bc["card_id"]:
                master = get_card_master(selected_bc["card_id"])
                selected_pos = master["part_of_speech"] if master else None

    # --- 각 카드에 텍스트/품사 붙이기 ---
    enriched = []
    for bc in baby_cards_all:
        if bc["baby_card_id"] == selected_baby_card_id:
            continue  # 방금 선택한 카드 제외

        text = bc["text"]
        pos = bc["type"]
        cid = bc["card_id"]

        if cid:
            master = get_card_master(cid)
            if master:
                if not text:
                    text = master["base_text"]
                if not pos:
                    pos = master["part_of_speech"]

        enriched.append({
            "baby_card_id": bc["baby_card_id"],
            "card_id":      cid,
            "text":         text,
            "pos":          pos,
            "last_used_at": bc["last_used_at"],
            "priority":     bc.get("priority"),
        })

    # --- Step 1: 태그 기반 의미 필터 ---
    # (baby_card_id, card_id) 튜플로 비교 → base 카드(baby_card_id=None)도 card_id로 구분
    candidate_keys = [(c["baby_card_id"], c["card_id"]) for c in enriched]
    filtered_keys = filter_by_tag_semantic(selected_baby_card_id, candidate_keys)

    candidates = [
        c for c in enriched
        if (c["baby_card_id"], c["card_id"]) in filtered_keys
    ]

    # --- Step 2: 품사 전이 규칙 필터 ---
    candidates = filter_by_pos_transition(selected_pos, candidates)

    # 후보가 너무 적으면 fallback (우선순위: 개인카드 → 전체)
    # 이유: base 카드는 usage_count=0이라 score=0.5 동점 → 의미 없는 추천
    if len(candidates) < 3:
        personal_enriched = [c for c in enriched if c["baby_card_id"] is not None]
        personal_pos_filtered = filter_by_pos_transition(selected_pos, personal_enriched)
        if len(personal_pos_filtered) >= 3:
            candidates = personal_pos_filtered   # 개인 카드 + 품사 규칙
        elif len(personal_enriched) >= 3:
            candidates = personal_enriched       # 개인 카드 (품사 무시)
        else:
            candidates = enriched                # 최종 전체 fallback

    # --- Step 3: system_score 계산 ---
    logs = get_vocab_logs(baby_id)
    config = get_scoring_config(baby_id, target_type="card")

    scored = []
    for c in candidates:
        score = compute_system_score(
            baby_card_id=c["baby_card_id"],
            last_used_at=c["last_used_at"],
            priority=c.get("priority"),
            logs=logs,
            config=config,
        )
        scored.append({
            "baby_card_id": c["baby_card_id"],   # None = 아직 baby_card에 없는 기본 카드
            "card_id":      c["card_id"],         # None = 부모가 추가한 커스텀 카드
            "text":         c["text"],
            "pos":          c["pos"],
            "system_score": score,
        })

    # --- Step 4: 점수 내림차순 정렬 후 top_n 반환 ---
    scored.sort(key=lambda x: x["system_score"], reverse=True)

    return {
        "baby_id":           baby_id,
        "selected_word":     selected_text,
        "recommended_words": scored[:top_n],
    }
