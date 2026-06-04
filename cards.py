"""
cards.py
--------------
후보 카드 enrich 유틸. baby_card 의 비어있는 text/pos 를 card_master 기본값으로
채워, 추천/학습 양쪽에서 동일한 카드 표현을 쓰도록 한다.
"""

import repo


def _norm_pos(pos):
    return pos.lower() if pos else None


def enrich_card(bc: dict) -> dict:
    text, pos, cid = bc.get("text"), bc.get("type"), bc.get("card_id")
    if cid and (not text or not pos):
        master = repo.get_card_master(cid)
        if master:
            text = text or master.get("base_text")
            pos = pos or master.get("part_of_speech")
    return {
        "baby_card_id": bc.get("baby_card_id"),
        "card_id":      cid,
        "text":         text,
        "pos":          _norm_pos(pos),
        "last_used_at": bc.get("last_used_at"),
        "priority":     bc.get("priority"),
        "is_favorite":  bc.get("is_favorite", False),
        "source":       bc.get("source", "system_default"),
        "usage_count":  bc.get("usage_count", 0),
    }


def get_enriched_candidates(baby_id: int) -> list:
    return [enrich_card(bc) for bc in repo.get_candidate_cards(baby_id)]


def card_lookup(baby_id: int) -> dict:
    """{card_key: enriched_card}"""
    out = {}
    for c in get_enriched_candidates(baby_id):
        out[repo.card_key(c["baby_card_id"], c["card_id"], c["text"])] = c
    return out
