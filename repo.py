"""
repo.py
--------------
데이터 접근 파사드(facade).

config.DATA_SOURCE 값("dummy" | "db")에 따라 dummy_data/dummy_extra 또는
db.py 를 단일 인터페이스로 노출한다. 추천/feature/멀티모달 모듈은 항상
repo 만 import 하므로, 데이터 소스를 바꿔도 로직 코드는 손대지 않는다.

노출 함수:
  get_candidate_cards, get_card_master, get_all_card_masters,
  get_vocab_logs, get_scoring_config, get_baby_card_tags, get_tag,
  get_onboarding_keywords, get_level_info, get_voice_profile,
  get_avatar_profile, get_sentence_word_map, get_tag_confidence_avg,
  get_system_score, set_system_scores, card_key,
  append_vocab_log, save_sentence
"""

import config

if config.DATA_SOURCE == "db":
    import db as _base          # PostgreSQL (db.py)
    try:
        import db_extra as _extra
    except ImportError:
        _extra = None
else:
    import dummy_data as _base   # 인메모리 더미
    import dummy_extra as _extra


def _b(name):
    return getattr(_base, name)


def _x(name, fallback=None):
    if _extra is not None and hasattr(_extra, name):
        return getattr(_extra, name)
    return fallback


# -------------------------------------------------------
# 기본 카드/로그/태그/스코어링 (dummy_data ↔ db)
# -------------------------------------------------------
get_candidate_cards = _b("get_candidate_cards")
get_card_master     = _b("get_card_master")
get_vocab_logs      = _b("get_vocab_logs")
get_scoring_config  = _b("get_scoring_config")
get_baby_card_tags  = _b("get_baby_card_tags")
get_tag             = _b("get_tag")

# db.py 에는 get_all_card_masters 가 없을 수 있음 → candidate 기반 대체
get_all_card_masters = getattr(_base, "get_all_card_masters", None)


# -------------------------------------------------------
# 확장 테이블 (dummy_extra ↔ db_extra)
# -------------------------------------------------------
get_onboarding_keywords = _x("get_onboarding_keywords", lambda baby_id: [])
get_level_info          = _x("get_level_info", lambda baby_id: {
    "language_cognitive_level": 3, "language_expression_level": 3,
    "disability_level": "moderate", "sensory_sensitivity": "neutral",
    "favorite_visual_type": "cartoon"})
get_voice_profile       = _x("get_voice_profile", lambda baby_id: {
    "speaker": "nara", "speed": 0, "pitch": 0, "volume": 0, "emotion": 0})
get_cognitive_test_result = _x("get_cognitive_test_result",
                               lambda baby_id: {"correct": 3, "total": 5})
get_onboarding_test       = _x("get_onboarding_test", lambda baby_id: [])
get_avatar_profile      = _x("get_avatar_profile", lambda baby_id, emotion="neutral": {
    "baby_id": baby_id, "emotion": emotion, "image_url": None})
get_sentence_word_map   = _x("get_sentence_word_map", lambda baby_id: [])
get_tag_confidence_avg  = _x("get_tag_confidence_avg", lambda bcid, cid: 0.9)
get_system_score        = _x("get_system_score", lambda bcid, cid, text=None: 0.0)
set_system_scores       = _x("set_system_scores", lambda scores: None)
card_key                = _x("card_key",
                             lambda bcid, cid, text=None: ("bc", bcid) if bcid else ("cm", cid))
append_vocab_log        = _x("append_vocab_log",
                             lambda *a, **k: None)
save_sentence           = _x("save_sentence", lambda *a, **k: None)
