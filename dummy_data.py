"""
dummy_data.py
--------------
RDS 연결 전 테스트용 더미 데이터.
실제 DB 연결 시 각 함수를 SQLAlchemy 쿼리로 바꾸면 됩니다.

[시스템 구조]
  card_master  : 서비스 전체가 공유하는 기본 단어 사전 (관리자가 관리)
  baby_card    : 아이가 실제로 사용했거나 부모가 추가/수정한 카드만 저장
                 card_id=None  → 부모가 새로 추가한 커스텀 카드
                 card_id=있음  → card_master 기반이지만 개인 기록이 생긴 카드

[추천 후보 구성]
  = baby_card(개인 사용·추가 카드) + card_master(아직 baby_card에 없는 기본 카드)

아동 프로필:
  baby_id=1  민준 (6세 남아) — 음식·요청 중심 / 밥·물·과자 집착, 식사 시간대 집중 사용
  baby_id=2  서아 (4세 여아) — 감정·놀이·미디어 중심 / 인형·TV·감정 표현 풍부
  baby_id=3  지호 (5세 남아) — 장난감·야외활동 중심 / 사주세요·놀이터·뛰기 좋아함
  baby_id=4  하은 (7세 여아) — 학교·일상·사람 중심 / 언어 발달 진행 중, 다양한 시간대 사용
  baby_id=5  준서 (3세 남아) — 기초 단어 위주 / 아직 초기 단계, 기본 단어 반복 사용
"""

from datetime import datetime, timedelta
import random

random.seed(42)
now = datetime.now()


# ================================================================
# card_master  ── 서비스 전체 공유 기본 단어 사전 (95개)
# ================================================================
CARD_MASTER = [
    # ── 음식·음료 (1~10) ──────────────────────────────────────
    {"card_id": 1,  "base_text": "물",          "normalized_text": "물",          "part_of_speech": "Noun",      "is_active": True, "priority": 1},
    {"card_id": 2,  "base_text": "밥",          "normalized_text": "밥",          "part_of_speech": "Noun",      "is_active": True, "priority": 1},
    {"card_id": 3,  "base_text": "우유",        "normalized_text": "우유",        "part_of_speech": "Noun",      "is_active": True, "priority": 1},
    {"card_id": 4,  "base_text": "빵",          "normalized_text": "빵",          "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 5,  "base_text": "과자",        "normalized_text": "과자",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 6,  "base_text": "사과",        "normalized_text": "사과",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 7,  "base_text": "바나나",      "normalized_text": "바나나",      "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 8,  "base_text": "아이스크림",  "normalized_text": "아이스크림",  "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 9,  "base_text": "주스",        "normalized_text": "주스",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 10, "base_text": "라면",        "normalized_text": "라면",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    # ── 식사 동사 (11~12) ──────────────────────────────────────
    {"card_id": 11, "base_text": "먹다",        "normalized_text": "먹다",        "part_of_speech": "verb",      "is_active": True, "priority": 1},
    {"card_id": 12, "base_text": "마시다",      "normalized_text": "마시다",      "part_of_speech": "verb",      "is_active": True, "priority": 1},
    # ── 신체·건강 (13~20) ──────────────────────────────────────
    {"card_id": 13, "base_text": "배고파",      "normalized_text": "배고파",      "part_of_speech": "adjective", "is_active": True, "priority": 1},
    {"card_id": 14, "base_text": "목말라",      "normalized_text": "목말라",      "part_of_speech": "adjective", "is_active": True, "priority": 1},
    {"card_id": 15, "base_text": "아파",        "normalized_text": "아파",        "part_of_speech": "adjective", "is_active": True, "priority": 1},
    {"card_id": 16, "base_text": "피곤해",      "normalized_text": "피곤해",      "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 17, "base_text": "졸려",        "normalized_text": "졸려",        "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 18, "base_text": "더워",        "normalized_text": "더워",        "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 19, "base_text": "추워",        "normalized_text": "추워",        "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 20, "base_text": "가려워",      "normalized_text": "가려워",      "part_of_speech": "adjective", "is_active": True, "priority": 3},
    # ── 감정 (21~27) ───────────────────────────────────────────
    {"card_id": 21, "base_text": "좋아",        "normalized_text": "좋아",        "part_of_speech": "adjective", "is_active": True, "priority": 1},
    {"card_id": 22, "base_text": "싫어",        "normalized_text": "싫어",        "part_of_speech": "adjective", "is_active": True, "priority": 1},
    {"card_id": 23, "base_text": "슬퍼",        "normalized_text": "슬퍼",        "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 24, "base_text": "무서워",      "normalized_text": "무서워",      "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 25, "base_text": "행복해",      "normalized_text": "행복해",      "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 26, "base_text": "화나",        "normalized_text": "화나",        "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 27, "base_text": "신나",        "normalized_text": "신나",        "part_of_speech": "adjective", "is_active": True, "priority": 2},
    # ── 요청·의사표현 (28~34) ──────────────────────────────────
    {"card_id": 28, "base_text": "주세요",      "normalized_text": "주세요",      "part_of_speech": "verb",      "is_active": True, "priority": 1},
    {"card_id": 29, "base_text": "도와줘",      "normalized_text": "도와줘",      "part_of_speech": "verb",      "is_active": True, "priority": 1},
    {"card_id": 30, "base_text": "그만",        "normalized_text": "그만",        "part_of_speech": "verb",      "is_active": True, "priority": 1},
    {"card_id": 31, "base_text": "더",          "normalized_text": "더",          "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 32, "base_text": "같이",        "normalized_text": "같이",        "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 33, "base_text": "안해",        "normalized_text": "안해",        "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 34, "base_text": "틀어줘",      "normalized_text": "틀어줘",      "part_of_speech": "verb",      "is_active": True, "priority": 2},
    # ── 장난감·놀이 (35~43) ────────────────────────────────────
    {"card_id": 35, "base_text": "장난감",      "normalized_text": "장난감",      "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 36, "base_text": "블록",        "normalized_text": "블록",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 37, "base_text": "인형",        "normalized_text": "인형",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 38, "base_text": "공",          "normalized_text": "공",          "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 39, "base_text": "그림책",      "normalized_text": "그림책",      "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 40, "base_text": "사주세요",    "normalized_text": "사주세요",    "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 41, "base_text": "갖고싶어요",  "normalized_text": "갖고싶어요",  "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 42, "base_text": "놀고싶어요",  "normalized_text": "놀고싶어요",  "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 43, "base_text": "놀다",        "normalized_text": "놀다",        "part_of_speech": "verb",      "is_active": True, "priority": 2},
    # ── TV·미디어 (44~47) ──────────────────────────────────────
    {"card_id": 44, "base_text": "TV",          "normalized_text": "tv",          "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 45, "base_text": "뽀로로",      "normalized_text": "뽀로로",      "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 46, "base_text": "유튜브",      "normalized_text": "유튜브",      "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 47, "base_text": "보다",        "normalized_text": "보다",        "part_of_speech": "verb",      "is_active": True, "priority": 2},
    # ── 장소 (48~52) ───────────────────────────────────────────
    {"card_id": 48, "base_text": "화장실",      "normalized_text": "화장실",      "part_of_speech": "Noun",      "is_active": True, "priority": 1},
    {"card_id": 49, "base_text": "방",          "normalized_text": "방",          "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 50, "base_text": "놀이터",      "normalized_text": "놀이터",      "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 51, "base_text": "학교",        "normalized_text": "학교",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 52, "base_text": "집",          "normalized_text": "집",          "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    # ── 이동 동사 (53~54) ──────────────────────────────────────
    {"card_id": 53, "base_text": "가다",        "normalized_text": "가다",        "part_of_speech": "verb",      "is_active": True, "priority": 1},
    {"card_id": 54, "base_text": "오다",        "normalized_text": "오다",        "part_of_speech": "verb",      "is_active": True, "priority": 2},
    # ── 일상 활동 (55~58) ──────────────────────────────────────
    {"card_id": 55, "base_text": "자다",        "normalized_text": "자다",        "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 56, "base_text": "일어나",      "normalized_text": "일어나",      "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 57, "base_text": "씻다",        "normalized_text": "씻다",        "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 58, "base_text": "입다",        "normalized_text": "입다",        "part_of_speech": "verb",      "is_active": True, "priority": 3},
    # ── 사람 (59~62) ───────────────────────────────────────────
    {"card_id": 59, "base_text": "엄마",        "normalized_text": "엄마",        "part_of_speech": "Noun",      "is_active": True, "priority": 1},
    {"card_id": 60, "base_text": "아빠",        "normalized_text": "아빠",        "part_of_speech": "Noun",      "is_active": True, "priority": 1},
    {"card_id": 61, "base_text": "선생님",      "normalized_text": "선생님",      "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 62, "base_text": "친구",        "normalized_text": "친구",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    # ── 도구·사물 (63~65) ──────────────────────────────────────
    {"card_id": 63, "base_text": "컵",          "normalized_text": "컵",          "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 64, "base_text": "이불",        "normalized_text": "이불",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 65, "base_text": "약",          "normalized_text": "약",          "part_of_speech": "Noun",      "is_active": True, "priority": 2},

    # ── 추가 음식 (66~70) ──────────────────────────────────────
    {"card_id": 66, "base_text": "치킨",        "normalized_text": "치킨",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 67, "base_text": "피자",        "normalized_text": "피자",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 68, "base_text": "김밥",        "normalized_text": "김밥",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 69, "base_text": "케이크",      "normalized_text": "케이크",      "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 70, "base_text": "딸기",        "normalized_text": "딸기",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    # ── 추가 장난감 (71~74) ────────────────────────────────────
    {"card_id": 71, "base_text": "레고",        "normalized_text": "레고",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 72, "base_text": "자동차",      "normalized_text": "자동차",      "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 73, "base_text": "기차",        "normalized_text": "기차",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    {"card_id": 74, "base_text": "퍼즐",        "normalized_text": "퍼즐",        "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    # ── 도구·학용품 (75) ───────────────────────────────────────
    {"card_id": 75, "base_text": "색연필",      "normalized_text": "색연필",      "part_of_speech": "Noun",      "is_active": True, "priority": 3},
    # ── 추가 감정 (76~80) ──────────────────────────────────────
    {"card_id": 76, "base_text": "맛있어",      "normalized_text": "맛있어",      "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 77, "base_text": "맛없어",      "normalized_text": "맛없어",      "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 78, "base_text": "부끄러워",    "normalized_text": "부끄러워",    "part_of_speech": "adjective", "is_active": True, "priority": 3},
    {"card_id": 79, "base_text": "억울해",      "normalized_text": "억울해",      "part_of_speech": "adjective", "is_active": True, "priority": 3},
    {"card_id": 80, "base_text": "신기해",      "normalized_text": "신기해",      "part_of_speech": "adjective", "is_active": True, "priority": 3},
    # ── 추가 장소 (81~84) ──────────────────────────────────────
    {"card_id": 81, "base_text": "공원",        "normalized_text": "공원",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 82, "base_text": "마트",        "normalized_text": "마트",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 83, "base_text": "병원",        "normalized_text": "병원",        "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    {"card_id": 84, "base_text": "유치원",      "normalized_text": "유치원",      "part_of_speech": "Noun",      "is_active": True, "priority": 2},
    # ── 추가 행동 (85~88) ──────────────────────────────────────
    {"card_id": 85, "base_text": "달리다",      "normalized_text": "달리다",      "part_of_speech": "verb",      "is_active": True, "priority": 3},
    {"card_id": 86, "base_text": "그리다",      "normalized_text": "그리다",      "part_of_speech": "verb",      "is_active": True, "priority": 3},
    {"card_id": 87, "base_text": "읽다",        "normalized_text": "읽다",        "part_of_speech": "verb",      "is_active": True, "priority": 3},
    {"card_id": 88, "base_text": "쓰다",        "normalized_text": "쓰다",        "part_of_speech": "verb",      "is_active": True, "priority": 3},
    # ── 추가 요청 (89~92) ──────────────────────────────────────
    {"card_id": 89, "base_text": "안아줘",      "normalized_text": "안아줘",      "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 90, "base_text": "칭찬해줘",    "normalized_text": "칭찬해줘",    "part_of_speech": "verb",      "is_active": True, "priority": 3},
    {"card_id": 91, "base_text": "같이해요",    "normalized_text": "같이해요",    "part_of_speech": "verb",      "is_active": True, "priority": 2},
    {"card_id": 92, "base_text": "기다려",      "normalized_text": "기다려",      "part_of_speech": "verb",      "is_active": True, "priority": 2},
    # ── 추가 신체 상태 (93~95) ─────────────────────────────────
    {"card_id": 93, "base_text": "힘들어",      "normalized_text": "힘들어",      "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 94, "base_text": "배불러",      "normalized_text": "배불러",      "part_of_speech": "adjective", "is_active": True, "priority": 2},
    {"card_id": 95, "base_text": "어지러워",    "normalized_text": "어지러워",    "part_of_speech": "adjective", "is_active": True, "priority": 3},
]


# ================================================================
# tag_master
# ================================================================
TAG_MASTER = [
    {"tag_id": 1,  "name": "욕구",     "normalized_name": "욕구",     "tag_level": "high", "parent_tag_id": None},
    {"tag_id": 2,  "name": "감정",     "normalized_name": "감정",     "tag_level": "high", "parent_tag_id": None},
    {"tag_id": 3,  "name": "행동",     "normalized_name": "행동",     "tag_level": "high", "parent_tag_id": None},
    {"tag_id": 4,  "name": "요청",     "normalized_name": "요청",     "tag_level": "high", "parent_tag_id": None},
    {"tag_id": 5,  "name": "사람",     "normalized_name": "사람",     "tag_level": "high", "parent_tag_id": None},
    {"tag_id": 6,  "name": "장소",     "normalized_name": "장소",     "tag_level": "high", "parent_tag_id": None},
    {"tag_id": 7,  "name": "범용",     "normalized_name": "범용",     "tag_level": "high", "parent_tag_id": None},  # 브릿지 카드: 주제 무관 항상 후보

    {"tag_id": 10, "name": "기본욕구", "normalized_name": "기본욕구", "tag_level": "low",  "parent_tag_id": 1},
    {"tag_id": 11, "name": "소유욕구", "normalized_name": "소유욕구", "tag_level": "low",  "parent_tag_id": 1},
    {"tag_id": 12, "name": "신체욕구", "normalized_name": "신체욕구", "tag_level": "low",  "parent_tag_id": 1},
    {"tag_id": 13, "name": "수면욕구", "normalized_name": "수면욕구", "tag_level": "low",  "parent_tag_id": 1},

    {"tag_id": 20, "name": "긍정감정", "normalized_name": "긍정감정", "tag_level": "low",  "parent_tag_id": 2},
    {"tag_id": 21, "name": "부정감정", "normalized_name": "부정감정", "tag_level": "low",  "parent_tag_id": 2},
    {"tag_id": 22, "name": "통증",     "normalized_name": "통증",     "tag_level": "low",  "parent_tag_id": 2},

    {"tag_id": 30, "name": "식사행동", "normalized_name": "식사행동", "tag_level": "low",  "parent_tag_id": 3},
    {"tag_id": 31, "name": "이동행동", "normalized_name": "이동행동", "tag_level": "low",  "parent_tag_id": 3},
    {"tag_id": 32, "name": "놀이행동", "normalized_name": "놀이행동", "tag_level": "low",  "parent_tag_id": 3},
    {"tag_id": 33, "name": "일상행동", "normalized_name": "일상행동", "tag_level": "low",  "parent_tag_id": 3},
    {"tag_id": 34, "name": "미디어",   "normalized_name": "미디어",   "tag_level": "low",  "parent_tag_id": 3},
    {"tag_id": 35, "name": "학습행동", "normalized_name": "학습행동", "tag_level": "low",  "parent_tag_id": 3},

    {"tag_id": 40, "name": "구매요청", "normalized_name": "구매요청", "tag_level": "low",  "parent_tag_id": 4},
    {"tag_id": 41, "name": "도움요청", "normalized_name": "도움요청", "tag_level": "low",  "parent_tag_id": 4},
    {"tag_id": 42, "name": "거부",     "normalized_name": "거부",     "tag_level": "low",  "parent_tag_id": 4},
    {"tag_id": 43, "name": "애정요청", "normalized_name": "애정요청", "tag_level": "low",  "parent_tag_id": 4},
]

# card_id → 태그 목록 (card_master 공용 태그 기준)
CARD_MASTER_TAGS = {
    # 음식·음료 → 욕구(1), 기본욕구(10)
    1:  [1, 10], 2:  [1, 10], 3:  [1, 10], 4:  [1, 10], 5:  [1, 10],
    6:  [1, 10], 7:  [1, 10], 8:  [1, 10], 9:  [1, 10], 10: [1, 10],
    # 식사 동사 → 행동(3), 식사행동(30), 기본욕구(10)
    11: [3, 30, 10], 12: [3, 30, 10],
    # 신체·건강
    13: [1, 10], 14: [1, 10],                               # 배고파, 목말라
    15: [2, 22], 16: [1, 12], 17: [1, 13],                  # 아파, 피곤해, 졸려
    18: [1, 12], 19: [1, 12], 20: [2, 22],                  # 더워, 추워, 가려워
    # 감정
    21: [2, 20, 7], 22: [2, 21, 7], 23: [2, 21],            # 좋아(범용), 싫어(범용), 슬퍼
    24: [2, 21], 25: [2, 20], 26: [2, 21], 27: [2, 20],     # 무서워, 행복해, 화나, 신나
    # 요청·의사표현
    28: [4, 10, 7], 29: [4, 41, 7], 30: [4, 42, 7],         # 주세요·도와줘·그만 (모두 범용 브릿지)
    31: [4, 10, 7], 32: [4, 32], 33: [4, 42], 34: [4, 34],  # 더(범용), 같이, 안해, 틀어줘
    # 장난감·놀이
    35: [1, 11], 36: [1, 11], 37: [1, 11], 38: [1, 11], 39: [1, 11],
    40: [4, 40, 1], 41: [1, 11], 42: [1, 3, 32], 43: [3, 32],
    # TV·미디어
    44: [1, 34], 45: [1, 34], 46: [1, 34], 47: [3, 34],
    # 장소
    48: [1, 6], 49: [6], 50: [6, 32], 51: [6], 52: [6],
    # 이동 동사
    53: [3, 31], 54: [3, 31],
    # 일상 활동
    55: [3, 13], 56: [3, 33], 57: [3, 33], 58: [3, 33],
    # 사람
    59: [5], 60: [5], 61: [5], 62: [5],
    # 도구·사물
    63: [3, 30], 64: [1, 13], 65: [4, 41],
    # 추가 음식
    66: [1, 10], 67: [1, 10], 68: [1, 10], 69: [1, 10], 70: [1, 10],
    # 추가 장난감
    71: [1, 11], 72: [1, 11], 73: [1, 11], 74: [1, 11],
    # 학용품
    75: [3, 35],
    # 추가 감정
    76: [2, 20], 77: [2, 21], 78: [2, 21], 79: [2, 21], 80: [2, 20],
    # 추가 장소
    81: [6, 32], 82: [6], 83: [6, 22], 84: [6],
    # 추가 행동
    85: [3, 32], 86: [3, 35], 87: [3, 35], 88: [3, 35],
    # 추가 요청
    89: [4, 43], 90: [4, 43], 91: [4, 32], 92: [4, 41],
    # 추가 신체
    93: [2, 22], 94: [1, 10], 95: [2, 22],
}


# ================================================================
# baby_card  ── 아이가 실제 사용했거나 부모가 추가/수정한 카드만
#
# ※ card_master에 있는 카드라도 아이가 한 번도 안 썼으면 여기 없음
#   → 추천 시 card_master에서 기본 후보로 자동 포함됨
# ================================================================

def _bc(baby_card_id, baby_id, card_id,
        usage_count, hours_ago,
        text=None, pos=None,
        status="default", is_favorite=False, priority=None,
        source=None):
    cm_priority = priority
    if cm_priority is None and card_id is not None:
        cm_priority = next(
            (c["priority"] for c in CARD_MASTER if c["card_id"] == card_id), 2)
    # source 추론: 부모 커스텀(card_id 없음/status=add) → parent_manual, 그 외 system_default
    if source is None:
        source = "parent_manual" if (card_id is None or status == "add") else "system_default"
    return {
        "baby_card_id": baby_card_id,
        "baby_id":      baby_id,
        "card_id":      card_id,
        "text":         text,       # None → card_master.base_text 사용
        "type":         pos,        # None → card_master.part_of_speech 사용
        "status":       status,
        "source":       source,     # parent_manual | onboarding | ai_recommend_selected | system_default
        "is_active":    True,
        "is_favorite":  is_favorite,
        "usage_count":  usage_count,
        "last_used_at": now - timedelta(hours=hours_ago),
        "system_score": 0.0,
        "priority":     cm_priority,
        "manual_order": None,
    }


# ── baby_id=1  민준 (6세 남아) ─────────────────────────────────
# 음식/요청 중심. 밥·과자·라면을 자주 요청. 식사 시간대 집중.
# 커스텀: 부모가 한식 특화 카드 추가
BABY_CARDS_1 = [
    _bc(101, 1, 2,  usage_count=42, hours_ago=1,   is_favorite=True),   # 밥
    _bc(102, 1, 1,  usage_count=38, hours_ago=2,   is_favorite=True),   # 물
    _bc(103, 1, 3,  usage_count=25, hours_ago=4),                        # 우유
    _bc(104, 1, 11, usage_count=30, hours_ago=1),                        # 먹다
    _bc(105, 1, 28, usage_count=45, hours_ago=0.5, is_favorite=True),   # 주세요
    _bc(106, 1, 13, usage_count=20, hours_ago=3,   is_favorite=True),   # 배고파
    _bc(107, 1, 59, usage_count=28, hours_ago=1,   is_favorite=True),   # 엄마
    _bc(108, 1, 22, usage_count=12, hours_ago=8),                        # 싫어
    _bc(109, 1, 15, usage_count=8,  hours_ago=14),                       # 아파
    _bc(110, 1, 48, usage_count=15, hours_ago=3),                        # 화장실
    _bc(111, 1, 31, usage_count=18, hours_ago=2),                        # 더
    _bc(112, 1, 33, usage_count=10, hours_ago=10),                       # 안해
    _bc(113, 1, 12, usage_count=22, hours_ago=2),                        # 마시다
    _bc(114, 1, 5,  usage_count=20, hours_ago=5),                        # 과자
    _bc(115, 1, 10, usage_count=15, hours_ago=6),                        # 라면
    _bc(116, 1, 76, usage_count=14, hours_ago=2),                        # 맛있어
    _bc(117, 1, 4,  usage_count=12, hours_ago=8),                        # 빵
    _bc(118, 1, 63, usage_count=8,  hours_ago=6),                        # 컵
    # 부모가 추가한 커스텀 카드 (card_id=None)
    _bc(119, 1, None, usage_count=10, hours_ago=2,
        text="김치찌개", pos="Noun", status="add"),
    _bc(120, 1, None, usage_count=7,  hours_ago=5,
        text="떡볶이",   pos="Noun", status="add"),
    _bc(121, 1, None, usage_count=5,  hours_ago=12,
        text="된장국",   pos="Noun", status="add"),
]

# ── baby_id=2  서아 (4세 여아) ─────────────────────────────────
# 감정/놀이/미디어 중심. 인형·TV·캐릭터 집착. 감정 표현 풍부.
# 커스텀: 좋아하는 캐릭터 추가
BABY_CARDS_2 = [
    _bc(201, 2, 37, usage_count=30, hours_ago=1,   is_favorite=True),   # 인형
    _bc(202, 2, 41, usage_count=25, hours_ago=2,   is_favorite=True),   # 갖고싶어요
    _bc(203, 2, 21, usage_count=22, hours_ago=1),                        # 좋아
    _bc(204, 2, 45, usage_count=28, hours_ago=2,   is_favorite=True),   # 뽀로로
    _bc(205, 2, 47, usage_count=26, hours_ago=2),                        # 보다
    _bc(206, 2, 43, usage_count=20, hours_ago=3),                        # 놀다
    _bc(207, 2, 28, usage_count=22, hours_ago=1,   is_favorite=True),   # 주세요
    _bc(208, 2, 59, usage_count=30, hours_ago=1,   is_favorite=True),   # 엄마
    _bc(209, 2, 23, usage_count=12, hours_ago=5),                        # 슬퍼
    _bc(210, 2, 22, usage_count=14, hours_ago=4),                        # 싫어
    _bc(211, 2, 25, usage_count=18, hours_ago=2),                        # 행복해
    _bc(212, 2, 24, usage_count=10, hours_ago=8),                        # 무서워
    _bc(213, 2, 44, usage_count=20, hours_ago=3),                        # TV
    _bc(214, 2, 32, usage_count=16, hours_ago=2),                        # 같이
    _bc(215, 2, 60, usage_count=18, hours_ago=3),                        # 아빠
    _bc(216, 2, 36, usage_count=14, hours_ago=4),                        # 블록
    _bc(217, 2, 27, usage_count=16, hours_ago=2),                        # 신나
    _bc(218, 2, 34, usage_count=12, hours_ago=3),                        # 틀어줘
    # 부모가 추가한 커스텀 카드
    _bc(219, 2, None, usage_count=22, hours_ago=1,
        text="핑크퐁",   pos="Noun", status="add", is_favorite=True),
    _bc(220, 2, None, usage_count=15, hours_ago=2,
        text="티니핑",   pos="Noun", status="add", is_favorite=True),
    _bc(221, 2, None, usage_count=10, hours_ago=6,
        text="보고싶어", pos="adjective", status="add"),
    _bc(222, 2, None, usage_count=6,  hours_ago=10,
        text="예뻐",     pos="adjective", status="add"),
]

# ── baby_id=3  지호 (5세 남아) ─────────────────────────────────
# 장난감/야외활동 중심. 사주세요·놀이터·달리기 좋아함.
# 커스텀: 운동 관련 단어 추가
BABY_CARDS_3 = [
    _bc(301, 3, 35, usage_count=25, hours_ago=1.5, is_favorite=True),   # 장난감
    _bc(302, 3, 40, usage_count=30, hours_ago=0.7, is_favorite=True),   # 사주세요
    _bc(303, 3, 41, usage_count=22, hours_ago=1,   is_favorite=True),   # 갖고싶어요
    _bc(304, 3, 42, usage_count=18, hours_ago=2),                        # 놀고싶어요
    _bc(305, 3, 50, usage_count=20, hours_ago=3),                        # 놀이터
    _bc(306, 3, 53, usage_count=16, hours_ago=2),                        # 가다
    _bc(307, 3, 28, usage_count=25, hours_ago=1,   is_favorite=True),   # 주세요
    _bc(308, 3, 59, usage_count=22, hours_ago=1,   is_favorite=True),   # 엄마
    _bc(309, 3, 22, usage_count=10, hours_ago=7),                        # 싫어
    _bc(310, 3, 15, usage_count=6,  hours_ago=15),                       # 아파
    _bc(311, 3, 38, usage_count=18, hours_ago=2),                        # 공
    _bc(312, 3, 62, usage_count=14, hours_ago=4),                        # 친구
    _bc(313, 3, 85, usage_count=12, hours_ago=3),                        # 달리다
    _bc(314, 3, 71, usage_count=16, hours_ago=2),                        # 레고
    _bc(315, 3, 43, usage_count=14, hours_ago=3),                        # 놀다
    _bc(316, 3, 60, usage_count=12, hours_ago=5),                        # 아빠
    # 부모가 추가한 커스텀 카드
    _bc(317, 3, None, usage_count=12, hours_ago=3,
        text="축구공",    pos="Noun", status="add"),
    _bc(318, 3, None, usage_count=8,  hours_ago=5,
        text="더뛰고싶어", pos="verb", status="add"),
    _bc(319, 3, None, usage_count=6,  hours_ago=8,
        text="같이놀자",  pos="verb", status="add"),
]

# ── baby_id=4  하은 (7세 여아) ─────────────────────────────────
# 학교/일상/사람 중심. 언어 발달이 진행 중. 학교 생활 관련 표현 풍부.
# 다양한 시간대(아침/학교/저녁)에 고르게 사용.
# 커스텀: 학교 생활 특화 단어
BABY_CARDS_4 = [
    _bc(401, 4, 51, usage_count=25, hours_ago=6,   is_favorite=True),   # 학교
    _bc(402, 4, 61, usage_count=20, hours_ago=7,   is_favorite=True),   # 선생님
    _bc(403, 4, 62, usage_count=22, hours_ago=5),                        # 친구
    _bc(404, 4, 53, usage_count=18, hours_ago=6),                        # 가다
    _bc(405, 4, 21, usage_count=20, hours_ago=4),                        # 좋아
    _bc(406, 4, 22, usage_count=15, hours_ago=5),                        # 싫어
    _bc(407, 4, 87, usage_count=14, hours_ago=8),                        # 읽다
    _bc(408, 4, 86, usage_count=12, hours_ago=9),                        # 그리다
    _bc(409, 4, 11, usage_count=18, hours_ago=2),                        # 먹다
    _bc(410, 4, 15, usage_count=8,  hours_ago=20),                       # 아파
    _bc(411, 4, 76, usage_count=16, hours_ago=3),                        # 맛있어
    _bc(412, 4, 93, usage_count=14, hours_ago=7),                        # 힘들어
    _bc(413, 4, 32, usage_count=18, hours_ago=4),                        # 같이
    _bc(414, 4, 2,  usage_count=20, hours_ago=2),                        # 밥
    _bc(415, 4, 1,  usage_count=16, hours_ago=3),                        # 물
    _bc(416, 4, 16, usage_count=12, hours_ago=10),                       # 피곤해
    _bc(417, 4, 59, usage_count=22, hours_ago=2,   is_favorite=True),   # 엄마
    _bc(418, 4, 60, usage_count=16, hours_ago=5),                        # 아빠
    _bc(419, 4, 29, usage_count=10, hours_ago=12),                       # 도와줘
    _bc(420, 4, 89, usage_count=8,  hours_ago=6),                        # 안아줘
    # 부모가 추가한 커스텀 카드
    _bc(421, 4, None, usage_count=14, hours_ago=8,
        text="숙제",     pos="Noun",      status="add"),
    _bc(422, 4, None, usage_count=8,  hours_ago=15,
        text="발표",     pos="Noun",      status="add"),
    _bc(423, 4, None, usage_count=6,  hours_ago=20,
        text="칭찬받고싶어", pos="adjective", status="add"),
]

# ── baby_id=5  준서 (3세 남아) ─────────────────────────────────
# 기초 단어 위주. 아직 초기 단계라 단어 수가 적음.
# 기본 욕구·감정 단어를 매우 높은 빈도로 반복 사용.
# 커스텀: 부모가 아이 특성에 맞는 기초 단어 추가
BABY_CARDS_5 = [
    _bc(501, 5, 59, usage_count=50, hours_ago=0.5, is_favorite=True),   # 엄마
    _bc(502, 5, 60, usage_count=40, hours_ago=1,   is_favorite=True),   # 아빠
    _bc(503, 5, 2,  usage_count=45, hours_ago=1,   is_favorite=True),   # 밥
    _bc(504, 5, 1,  usage_count=38, hours_ago=1,   is_favorite=True),   # 물
    _bc(505, 5, 28, usage_count=42, hours_ago=0.5, is_favorite=True),   # 주세요
    _bc(506, 5, 22, usage_count=20, hours_ago=3),                        # 싫어
    _bc(507, 5, 15, usage_count=14, hours_ago=8),                        # 아파
    _bc(508, 5, 21, usage_count=18, hours_ago=2),                        # 좋아
    _bc(509, 5, 48, usage_count=16, hours_ago=3),                        # 화장실
    _bc(510, 5, 29, usage_count=12, hours_ago=5),                        # 도와줘
    _bc(511, 5, 24, usage_count=10, hours_ago=6),                        # 무서워
    _bc(512, 5, 3,  usage_count=20, hours_ago=2),                        # 우유
    # 부모가 추가한 커스텀 카드
    _bc(513, 5, None, usage_count=8,  hours_ago=4,
        text="무서워요", pos="adjective", status="add"),
    _bc(514, 5, None, usage_count=6,  hours_ago=6,
        text="같이놀자", pos="verb",      status="add"),
    _bc(515, 5, None, usage_count=10, hours_ago=2,
        text="뽀뽀",    pos="Noun",      status="add", is_favorite=True),
]

BABY_CARDS = BABY_CARDS_1 + BABY_CARDS_2 + BABY_CARDS_3 + BABY_CARDS_4 + BABY_CARDS_5


# ================================================================
# baby_card_tag_map  (baby_card_id → [tag_id, ...])
# 커스텀 카드(card_id=None)는 텍스트 기반으로 태그 추정
# ================================================================
def _build_tag_map():
    tag_map = {}
    for bc in BABY_CARDS:
        bcid = bc["baby_card_id"]
        cid  = bc["card_id"]
        if cid is not None:
            tag_map[bcid] = CARD_MASTER_TAGS.get(cid, [])
        else:
            text = (bc["text"] or "").lower()
            # 음식류
            if any(k in text for k in ["찌개", "볶이", "라면", "밥", "빵", "국", "치킨", "피자", "김밥", "케이크", "딸기", "된장"]):
                tag_map[bcid] = [1, 10]
            # 장난감·소유
            elif any(k in text for k in ["공", "블록", "장난감", "인형", "레고", "기차", "퍼즐", "자동차", "축구"]):
                tag_map[bcid] = [1, 11]
            # 미디어·캐릭터
            elif any(k in text for k in ["퐁", "로로", "티니핑", "ping", "tv", "유튜브"]):
                tag_map[bcid] = [1, 34]
            # 소유욕구 (갖고싶다 계열)
            elif any(k in text for k in ["갖고싶", "사주", "갖고 싶"]):
                tag_map[bcid] = [1, 11]
            # 놀이·운동
            elif any(k in text for k in ["뛰", "달리", "운동", "놀자", "같이놀", "뛰고싶"]):
                tag_map[bcid] = [3, 32]
            # 학교·학습
            elif any(k in text for k in ["숙제", "발표", "학교", "공부", "읽", "쓰"]):
                tag_map[bcid] = [3, 35, 6]
            # 부정감정
            elif any(k in text for k in ["무서", "슬퍼", "억울", "싫어"]):
                tag_map[bcid] = [2, 21]
            # 긍정감정
            elif any(k in text for k in ["좋아", "행복", "신나", "예뻐", "칭찬"]):
                tag_map[bcid] = [2, 20]
            # 애정·그리움
            elif any(k in text for k in ["보고싶", "안아", "뽀뽀"]):
                tag_map[bcid] = [4, 43]
            else:
                tag_map[bcid] = [1]
    return tag_map

BABY_CARD_TAG_MAP = _build_tag_map()


# ================================================================
# baby_vocab_log  ── 각 아동의 실제 사용 기록 (시간대 패턴 반영)
# ================================================================
def _make_logs():
    logs = []
    log_id = 1

    def add_logs(baby_cards_subset, count, peak_hours=None, max_days=7):
        """
        peak_hours: 집중 사용 시간대 목록 (예: [7,8,12,13,18,19] = 식사 시간)
        None이면 완전 랜덤
        """
        nonlocal log_id
        pool = []
        for bc in baby_cards_subset:
            weight = max(1, bc["usage_count"] // 5)
            pool.extend([(bc["baby_card_id"], bc["card_id"], bc["text"])] * weight)

        baby_id = baby_cards_subset[0]["baby_id"]
        for _ in range(count):
            bcid, cid, custom_text = random.choice(pool)
            if custom_text:
                text = custom_text
            elif cid:
                m = next((c for c in CARD_MASTER if c["card_id"] == cid), None)
                text = m["base_text"] if m else "?"
            else:
                text = "?"

            # 시간대 패턴 반영
            days_ago = random.randint(0, max_days)
            if peak_hours and random.random() < 0.7:  # 70% 확률로 peak 시간에 사용
                hour = random.choice(peak_hours)
            else:
                hour = random.randint(7, 21)  # 기상~취침 사이
            minute = random.randint(0, 59)

            used_at = now - timedelta(
                days=days_ago,
                hours=now.hour - hour if now.hour >= hour else 0,
                minutes=minute,
            )
            # 단순화: days + random minutes
            used_at = now - timedelta(
                days=days_ago,
                minutes=random.randint(0, 23*60)
            )

            logs.append({
                "log_id":       log_id,
                "baby_id":      baby_id,
                "baby_card_id": bcid,
                "card_id":      cid,
                "text":         text,
                "used_at":      used_at,
                "created_at":   used_at,
            })
            log_id += 1

    # 민준: 식사 시간대 집중 (아침 7~8, 점심 12~13, 저녁 18~19)
    add_logs(BABY_CARDS_1, count=150, peak_hours=[7, 8, 12, 13, 18, 19])
    # 서아: 오후 낮잠 후~저녁 (14~20) 집중
    add_logs(BABY_CARDS_2, count=130, peak_hours=[14, 15, 16, 17, 18, 19, 20])
    # 지호: 하원 후 야외 (15~19) 집중
    add_logs(BABY_CARDS_3, count=140, peak_hours=[15, 16, 17, 18, 19])
    # 하은: 등하교 전후 + 저녁 (7~8, 14~15, 18~20) 다양한 시간대
    add_logs(BABY_CARDS_4, count=160, peak_hours=[7, 8, 14, 15, 18, 19, 20])
    # 준서: 하루 종일 분산 (배고프면 언제든)
    add_logs(BABY_CARDS_5, count=120, peak_hours=[8, 9, 12, 13, 17, 18, 19, 20])

    return logs

BABY_VOCAB_LOGS = _make_logs()


# ================================================================
# scoring_config  ── 가중치 설정 (global 기본 + 아동별 override)
# ================================================================
SCORING_CONFIG = [
    # ── global 기본값 ───────────────────────────────────────────
    {"config_id": 1, "target_type": "card", "scope": "global", "baby_id": None, "feature_key": "usage_count",    "weight": 0.7,  "enabled": True,  "version": 1},
    {"config_id": 2, "target_type": "card", "scope": "global", "baby_id": None, "feature_key": "recency",        "weight": 1.2,  "enabled": True,  "version": 1},
    {"config_id": 3, "target_type": "card", "scope": "global", "baby_id": None, "feature_key": "time_diversity", "weight": 0.3,  "enabled": True,  "version": 1},
    {"config_id": 4, "target_type": "card", "scope": "global", "baby_id": None, "feature_key": "priority",       "weight": 0.5,  "enabled": True,  "version": 1},

    # ── 민준(1): 식사 반복 패턴 → usage_count 더 높임 ──────────
    {"config_id": 5, "target_type": "card", "scope": "baby",   "baby_id": 1,   "feature_key": "usage_count",    "weight": 1.2,  "enabled": True,  "version": 1},

    # ── 서아(2): 최근 감정 표현 중시 → recency 더 높임 ──────────
    {"config_id": 6, "target_type": "card", "scope": "baby",   "baby_id": 2,   "feature_key": "recency",        "weight": 1.8,  "enabled": True,  "version": 1},

    # ── 지호(3): 장난감 요청 패턴 → usage_count + priority 높임 ─
    {"config_id": 7, "target_type": "card", "scope": "baby",   "baby_id": 3,   "feature_key": "usage_count",    "weight": 1.0,  "enabled": True,  "version": 1},
    {"config_id": 8, "target_type": "card", "scope": "baby",   "baby_id": 3,   "feature_key": "priority",       "weight": 0.8,  "enabled": True,  "version": 1},

    # ── 하은(4): 다양한 시간대 학습 → time_diversity 높임 ────────
    {"config_id": 9, "target_type": "card", "scope": "baby",   "baby_id": 4,   "feature_key": "time_diversity", "weight": 0.6,  "enabled": True,  "version": 1},

    # ── 준서(5): 기초 단어 반복 → usage_count + priority 높임 ───
    {"config_id": 10, "target_type": "card", "scope": "baby",  "baby_id": 5,   "feature_key": "usage_count",    "weight": 1.5,  "enabled": True,  "version": 1},
    {"config_id": 11, "target_type": "card", "scope": "baby",  "baby_id": 5,   "feature_key": "priority",       "weight": 1.0,  "enabled": True,  "version": 1},
]


# ================================================================
# 데이터 접근 함수  ── DB 연결 시 SQLAlchemy 쿼리로 교체 대상
# ================================================================

def get_baby_cards(baby_id: int) -> list[dict]:
    """아이가 실제 사용했거나 부모가 추가한 카드 (개인 DB)"""
    return [
        c for c in BABY_CARDS
        if c["baby_id"] == baby_id
        and c["is_active"]
        and c["status"] != "off"
    ]


def get_card_master(card_id: int) -> dict | None:
    for c in CARD_MASTER:
        if c["card_id"] == card_id and c["is_active"]:
            return c
    return None


def get_all_card_masters() -> list[dict]:
    return [c for c in CARD_MASTER if c["is_active"]]


def get_candidate_cards(baby_id: int) -> list[dict]:
    """
    추천 후보 전체 목록을 반환.

    = baby_card (개인 사용·추가 카드)
    + card_master 중 이 아이의 baby_card에 없는 기본 카드

    baby_card에 없는 기본 카드는:
      - baby_card_id = None (아직 개인화 안 됨)
      - usage_count = 0, last_used_at = None
      → 점수가 낮게 계산되어 자연스럽게 하위 추천
    """
    personal_cards = get_baby_cards(baby_id)
    used_card_ids  = {bc["card_id"] for bc in personal_cards if bc["card_id"] is not None}

    base_cards = []
    for cm in get_all_card_masters():
        if cm["card_id"] not in used_card_ids:
            base_cards.append({
                "baby_card_id": None,
                "baby_id":      baby_id,
                "card_id":      cm["card_id"],
                "text":         None,
                "type":         None,
                "status":       "default",
                "source":       "system_default",
                "is_active":    True,
                "is_favorite":  False,
                "usage_count":  0,
                "last_used_at": None,
                "system_score": 0.0,
                "priority":     cm["priority"],
                "manual_order": None,
            })

    return personal_cards + base_cards


def get_vocab_logs(baby_id: int, limit: int = 200) -> list[dict]:
    logs = [l for l in BABY_VOCAB_LOGS if l["baby_id"] == baby_id]
    return sorted(logs, key=lambda x: x["used_at"], reverse=True)[:limit]


def get_scoring_config(baby_id: int | None = None, target_type: str = "card") -> list[dict]:
    merged = {
        c["feature_key"]: c
        for c in SCORING_CONFIG
        if c["target_type"] == target_type
        and c["scope"] == "global"
        and c["enabled"]
    }
    if baby_id is not None:
        for c in SCORING_CONFIG:
            if (c["target_type"] == target_type
                    and c["scope"] == "baby"
                    and c["baby_id"] == baby_id
                    and c["enabled"]):
                merged[c["feature_key"]] = c
    return list(merged.values())


def get_baby_card_tags(baby_card_id: int | None, card_id: int | None = None) -> list[int]:
    """
    태그 조회.
    - baby_card_id 있음 → BABY_CARD_TAG_MAP (개인 카드)
    - baby_card_id 없음 (기본 카드) → CARD_MASTER_TAGS (card_id 기준)
    """
    if baby_card_id is not None:
        return BABY_CARD_TAG_MAP.get(baby_card_id, [])
    if card_id is not None:
        return CARD_MASTER_TAGS.get(card_id, [])
    return []


def get_tag(tag_id: int) -> dict | None:
    for t in TAG_MASTER:
        if t["tag_id"] == tag_id:
            return t
    return None
