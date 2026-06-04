"""
dummy_extra.py
--------------
2차 보고서 설계에 맞춰 추가된 더미 테이블 + 파생 데이터.

dummy_data.py(기존 카드/로그/태그/스코어링)에 더해, 신규 feature 계산에 필요한:
  - baby_onboarding_answers  (온보딩 키워드)        → onboarding_relevance / onboarding_match_score
  - baby_level_information   (인지·발화·감각 수준)   → cognitive_level_match / cognitive_difficulty_gap
  - baby_voice_profile       (TTS 음성 설정)          → tts.py
  - baby_avatar_profile      (아바타/감정 이미지)     → image_gen.py 발화 모션
  - sentence_word_map        (문장 내 단어 순서)      → co_occurrence / sequential_probability / position
  - SYSTEM_SCORES (mutable)  (Layer1 배치 결과 저장소) → baby_card.system_score 대체

실제 DB 연결 시 db.py가 같은 시그니처의 함수를 제공한다.
"""

import random
from datetime import timedelta

from dummy_data import (
    BABY_CARDS,
    CARD_MASTER,
    CARD_MASTER_TAGS,
    BABY_CARD_TAG_MAP,
    now,
)


def _norm_pos(pos):
    return pos.lower() if pos else None


def _enrich(bc: dict) -> dict:
    """baby_card에 card_master 기본값을 채워 text/pos 확정"""
    text, pos, cid = bc.get("text"), bc.get("type"), bc.get("card_id")
    if cid:
        m = next((c for c in CARD_MASTER if c["card_id"] == cid), None)
        if m:
            text = text or m["base_text"]
            pos = pos or m["part_of_speech"]
    return {
        "baby_card_id": bc["baby_card_id"],
        "card_id":      cid,
        "text":         text,
        "pos":          _norm_pos(pos),
        "usage_count":  bc.get("usage_count", 0),
        "tags":         _card_tags(bc["baby_card_id"], cid),
    }


def _card_tags(baby_card_id, card_id) -> list:
    if baby_card_id is not None and baby_card_id in BABY_CARD_TAG_MAP:
        return BABY_CARD_TAG_MAP[baby_card_id]
    if card_id is not None:
        return CARD_MASTER_TAGS.get(card_id, [])
    return []


# ================================================================
# baby_onboarding_answers  ── 온보딩 선호 키워드
# ================================================================
ONBOARDING_KEYWORDS = {
    1: ["밥", "과자", "라면", "김치찌개", "떡볶이", "먹다"],          # 민준 — 음식
    2: ["인형", "뽀로로", "핑크퐁", "티니핑", "TV", "놀다"],          # 서아 — 놀이·미디어
    3: ["장난감", "축구공", "레고", "놀이터", "공", "달리다"],         # 지호 — 장난감·야외
    4: ["학교", "숙제", "친구", "그림책", "읽다", "선생님"],          # 하은 — 학교·일상
    5: ["엄마", "아빠", "밥", "물", "뽀뽀", "주세요"],               # 준서 — 기초
}


# ================================================================
# baby_level_information  ── 인지/발화/감각 수준
#   language_cognitive_level: 1(초기) ~ 5(높음)
# ================================================================
LEVEL_INFO = {
    1: {"language_cognitive_level": 3, "language_expression_level": 3,
        "disability_level": "moderate", "sensory_sensitivity": "neutral",  "favorite_visual_type": "cartoon"},
    2: {"language_cognitive_level": 3, "language_expression_level": 3,
        "disability_level": "moderate", "sensory_sensitivity": "neutral",  "favorite_visual_type": "cartoon"},
    3: {"language_cognitive_level": 3, "language_expression_level": 2,
        "disability_level": "moderate", "sensory_sensitivity": "neutral",  "favorite_visual_type": "cartoon"},
    4: {"language_cognitive_level": 4, "language_expression_level": 4,
        "disability_level": "mild",     "sensory_sensitivity": "neutral",  "favorite_visual_type": "illustration"},
    5: {"language_cognitive_level": 1, "language_expression_level": 1,
        "disability_level": "severe",   "sensory_sensitivity": "auditory", "favorite_visual_type": "cartoon"},
}


# ================================================================
# 온보딩 인지 테스트  ── 문항마다 측정하는 인지 영역(dimension)이 다름
#   예) quantity: "사과 8개 중 3개 찾기" / emotion: "우는 아이 → 우는 카드"
#   각 문항 통과(정답) 여부 → 영역별 프로파일 → 약한 영역 탐지 → GPT 해석
#   (실제로는 baby_onboarding_answers 를 영역별 정답키로 채점)
# ================================================================
COGNITIVE_DIMENSIONS = {
    "quantity":    "수·수량 인지",        # 사과 8개 중 3개 찾기
    "emotion":     "감정 인지",           # 우는 아이 보고 '우는' 카드 고르기
    "color_shape": "색·형태 인지",        # 같은 색/모양 찾기
    "category":    "범주·분류",           # 같은 무리(과일/탈것) 묶기
    "language":    "언어 이해·지시 수행",  # 지시대로 카드 고르기
}

# 아동별 문항 통과 여부 (True=정답). 실제론 정답키로 채점한 결과로 대체.
ONBOARDING_TEST = {
    1: {"quantity": True,  "emotion": True,  "color_shape": True,  "category": False, "language": False},  # 민준
    2: {"quantity": False, "emotion": True,  "color_shape": True,  "category": True,  "language": False},  # 서아
    3: {"quantity": True,  "emotion": False, "color_shape": False, "category": True,  "language": True},   # 지호
    4: {"quantity": True,  "emotion": True,  "color_shape": True,  "category": True,  "language": False},  # 하은
    5: {"quantity": False, "emotion": False, "color_shape": False, "category": False, "language": False},  # 준서(초기)
}


def get_onboarding_test(baby_id: int) -> list:
    """문항(인지 영역)별 통과 여부 리스트."""
    res = ONBOARDING_TEST.get(baby_id, {})
    return [{"dimension": d, "label": COGNITIVE_DIMENSIONS[d], "correct": bool(res.get(d, False))}
            for d in COGNITIVE_DIMENSIONS]


def get_cognitive_test_result(baby_id: int) -> dict:
    """영역별 결과 → (정답 수/전체) 요약 (레벨 산출 호환용)."""
    res = ONBOARDING_TEST.get(baby_id, {})
    return {"correct": sum(1 for v in res.values() if v),
            "total": len(COGNITIVE_DIMENSIONS)}


# ================================================================
# baby_voice_profile  ── TTS 음성 설정 (Clova Voice 파라미터)
#   청각 민감(준서) → volume 낮춤
# ================================================================
VOICE_PROFILE = {
    1: {"speaker": "nara",  "speed": 0,  "pitch": 0, "volume": 0,  "emotion": 0},
    2: {"speaker": "nara",  "speed": 1,  "pitch": 1, "volume": 0,  "emotion": 1},
    3: {"speaker": "njihun", "speed": 0, "pitch": 0, "volume": 0,  "emotion": 0},
    4: {"speaker": "nara",  "speed": 0,  "pitch": 0, "volume": 0,  "emotion": 0},
    5: {"speaker": "ndain", "speed": 1,  "pitch": 0, "volume": -2, "emotion": 0},  # 청각 민감 → 음량↓
}


# ================================================================
# baby_avatar_profile / baby_avatar_emotion
#   감정별 아바타 이미지 (happy/sad/angry/neutral/surprised)
# ================================================================
def get_avatar_profile(baby_id: int, emotion: str = "neutral") -> dict:
    emotion = emotion if emotion in {"happy", "sad", "angry", "neutral", "surprised"} else "neutral"
    return {
        "baby_id": baby_id,
        "emotion": emotion,
        "image_url": f"avatars/baby_{baby_id}_{emotion}.png",
    }


# ================================================================
# sentence_word_map  ── 합성 문장(단어 순서) 데이터
#   co_occurrence / sequential_probability / position_index 학습 기반
# ================================================================
def _build_sentence_word_map():
    rng = random.Random(123)
    smap = {}
    sentence_id = 1
    for baby_id in (1, 2, 3, 4, 5):
        cards = [_enrich(bc) for bc in BABY_CARDS if bc["baby_id"] == baby_id]
        nouns = [c for c in cards if c["pos"] == "noun"]
        verbs = [c for c in cards if c["pos"] == "verb"]
        adjs  = [c for c in cards if c["pos"] == "adjective"]
        bridges = [c for c in cards if 7 in c["tags"]]

        def pick(pool):
            if not pool:
                return None
            weights = [max(1, c["usage_count"]) for c in pool]
            return rng.choices(pool, weights=weights, k=1)[0]

        sentences = []
        for _ in range(50):
            seq = []
            head = pick(nouns) or pick(cards)
            if head:
                seq.append(head)
            # 명사 → 동사/형용사 (자연스러운 전이)
            tail_pool = verbs + adjs
            tail = pick(tail_pool)
            if tail and tail is not head:
                seq.append(tail)
            # 30% 확률로 브릿지(주세요/더 등) 말미 합류
            if bridges and rng.random() < 0.35:
                br = pick(bridges)
                if br and br not in seq:
                    seq.append(br)
            if len(seq) < 2:
                continue
            words = [
                {
                    "sentence_id":  sentence_id,
                    "position_index": i,
                    "baby_card_id": c["baby_card_id"],
                    "card_id":      c["card_id"],
                    "text":         c["text"],
                    "pos":          c["pos"],
                }
                for i, c in enumerate(seq)
            ]
            sentences.append(words)
            sentence_id += 1
        smap[baby_id] = sentences
    return smap


SENTENCE_WORD_MAP = _build_sentence_word_map()


# ================================================================
# Layer1 배치 결과 저장소 (baby_card.system_score 대체)
#   key: ("bc", baby_card_id) | ("cm", card_id) | ("t", text)
# ================================================================
SYSTEM_SCORES = {}


def card_key(baby_card_id, card_id, text=None):
    if baby_card_id is not None:
        return ("bc", baby_card_id)
    if card_id is not None:
        return ("cm", card_id)
    return ("t", text)


# ================================================================
# 접근 함수  ── repo.py가 호출
# ================================================================
def get_onboarding_keywords(baby_id: int) -> list:
    return ONBOARDING_KEYWORDS.get(baby_id, [])


def get_level_info(baby_id: int) -> dict:
    return LEVEL_INFO.get(baby_id, {
        "language_cognitive_level": 3, "language_expression_level": 3,
        "disability_level": "moderate", "sensory_sensitivity": "neutral",
        "favorite_visual_type": "cartoon",
    })


def get_voice_profile(baby_id: int) -> dict:
    return VOICE_PROFILE.get(baby_id, {"speaker": "nara", "speed": 0, "pitch": 0, "volume": 0, "emotion": 0})


def get_sentence_word_map(baby_id: int) -> list:
    """문장 리스트. 각 문장은 position_index 순서의 단어 dict 리스트."""
    return SENTENCE_WORD_MAP.get(baby_id, [])


def get_tag_confidence_avg(baby_card_id, card_id) -> float:
    """카드 태그 평균 confidence. master 연결=1.0, 커스텀(룰 추정)=0.7"""
    if card_id is not None:
        return 1.0
    return 0.7


def get_system_score(baby_card_id, card_id, text=None) -> float:
    return SYSTEM_SCORES.get(card_key(baby_card_id, card_id, text), 0.0)


def set_system_scores(scores: dict):
    """{card_key: score} 일괄 저장 (Layer1 배치 결과 반영)"""
    SYSTEM_SCORES.update(scores)


# ----- write-side (엔드포인트용 인메모리 append) -----
_VOCAB_LOG_SEQ = [10_000]
_SENTENCE_SEQ = [1_000]


def append_vocab_log(baby_id, baby_card_id, card_id, text, context=None):
    from dummy_data import BABY_VOCAB_LOGS
    _VOCAB_LOG_SEQ[0] += 1
    entry = {
        "log_id": _VOCAB_LOG_SEQ[0], "baby_id": baby_id,
        "baby_card_id": baby_card_id, "card_id": card_id,
        "text": text, "used_at": now, "created_at": now,
        "context_json": context,
    }
    BABY_VOCAB_LOGS.insert(0, entry)
    return entry


def save_sentence(baby_id, words, sentence_text, image_url=None, audio_url=None):
    _SENTENCE_SEQ[0] += 1
    sid = _SENTENCE_SEQ[0]
    record = {
        "sentence_id": sid, "baby_id": baby_id, "sentence_text": sentence_text,
        "avatar_image_url": image_url, "avatar_audio_url": audio_url,
        "played_tts": audio_url is not None,
        "words": [
            {"position_index": i, "baby_card_id": w.get("baby_card_id"),
             "card_id": w.get("card_id"), "text": w.get("text")}
            for i, w in enumerate(words)
        ],
    }
    # 자기학습 루프: 합성 sentence_word_map 에도 즉시 반영
    SENTENCE_WORD_MAP.setdefault(baby_id, []).append([
        {"sentence_id": sid, "position_index": i,
         "baby_card_id": w.get("baby_card_id"), "card_id": w.get("card_id"),
         "text": w.get("text"), "pos": w.get("pos")}
        for i, w in enumerate(words)
    ])
    return record
