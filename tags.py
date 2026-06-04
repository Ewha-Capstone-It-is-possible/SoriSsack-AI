"""
tags.py
--------------
STEP 1 — 태그 기반 의미 필터링.

설계(AI 1번 기능 PDF):
  ① Multi high-tag 매칭 (교집합)   : 선택 카드와 high 태그가 하나라도 겹치면 통과
  ② 브릿지 카드 합류               : '범용' high 태그 카드(주세요/좋아/더/그만/도와줘 등)는 항상 통과
  ③ Fallback 완화                  : 통과 후보 3개 미만이면 전체 후보로 완화 (cold-start 대응)

반환: (통과 후보 리스트, {card_key: filter_stage})
  filter_stage = 1.0 (태그 교집합 통과) | 0.5 (브릿지로만 합류)
"""

import repo
from features import _high_tags, is_bridge


def filter_by_tag(selected: dict, candidates: list):
    """selected 가 None 이면 전체 통과(첫 화면)."""
    stage = {}

    def key(c):
        return repo.card_key(c.get("baby_card_id"), c.get("card_id"), c.get("text"))

    if selected is None:
        for c in candidates:
            stage[key(c)] = 1.0
        return list(candidates), stage

    selected_high = _high_tags(selected.get("baby_card_id"), selected.get("card_id"))

    passed = []
    for c in candidates:
        if key(c) == key(selected):
            continue
        c_high = _high_tags(c.get("baby_card_id"), c.get("card_id"))
        bridge = is_bridge(c)
        if selected_high and (c_high & selected_high):
            stage[key(c)] = 1.0          # ① 교집합 통과
            passed.append(c)
        elif bridge:
            stage[key(c)] = 0.5          # ② 브릿지 합류
            passed.append(c)

    # ③ fallback: 통과 후보가 너무 적으면 전체 완화
    if len(passed) < 3:
        passed = [c for c in candidates if key(c) != key(selected)]
        for c in passed:
            stage.setdefault(key(c), 0.5)
    return passed, stage
