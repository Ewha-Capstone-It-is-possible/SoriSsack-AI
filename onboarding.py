"""
onboarding.py
--------------
온보딩 데이터 → 정규화 신호 어댑터.

온보딩 정보는 DB 여러 테이블에 흩어져 있고(자유 텍스트 포함), 그대로는 추천/멀티모달/
리포트에 쓰기 어렵다. 이 모듈이 단일 진입점으로 정규화한다.

  - cognitive_level_num : 온보딩 인지 테스트(5문항) 정답 수 → 1~5 레벨
                          (DB 미구축 단계: repo.get_cognitive_test_result 사용,
                           실제론 baby_onboarding_answers 를 정답키로 채점)
  - preferred_keywords  : 아이의 즐겨찾기 카드(baby_card.is_favorite) 텍스트
  - sensory / visual    : baby_onboarding_information 의 감각예민도·선호시각(자유텍스트) 파싱

추천 feature(onboarding_relevance, cognitive_level_match), TTS 음량, SD 스타일,
리포트 onboarding_context 가 모두 이 신호를 공유한다.
"""

import json

import config
import repo
import cards


# -------------------------------------------------------
# 인지 수준: 테스트 정답 수 → 레벨
# -------------------------------------------------------
def cognitive_score_to_level(correct: int, total: int = 5) -> int:
    """정답 0~total → 레벨 1~5 (0개=1, 만점=5)."""
    if not total or total <= 0:
        return 3
    ratio = max(0.0, min(1.0, correct / total))
    return max(1, min(5, 1 + round(ratio * 4)))


# language_cognitive_level 텍스트 → 숫자 (테스트 결과가 없을 때 fallback)
_LEVEL_TEXT_MAP = {
    "초기": 1, "기초": 2, "발달": 3, "확장": 4, "유창": 5, "높음": 5,
}


def _level_text_to_num(text) -> int:
    if isinstance(text, (int, float)):
        return int(text)
    if not text:
        return 3
    for key, val in _LEVEL_TEXT_MAP.items():
        if key in str(text):
            return val
    return 3


def get_cognitive_level_num(baby_id: int) -> int:
    profile = get_cognitive_profile(baby_id)
    if profile["total"]:
        return profile["overall_level"]
    # 테스트 결과 없으면 레벨 텍스트로 추정
    return _level_text_to_num(repo.get_level_info(baby_id).get("language_cognitive_level"))


# 인지 영역 → 강화할 high 태그 매핑 (폐쇄루프: 약점 강화)
#   감정 인지가 약하면 '감정' 태그 카드를 추천에서 더 노출 → 반복 학습 유도
#   ※ 수·수량/색·형태/언어 영역은 현재 단어 태그 체계에 대응 카테고리가 없어 비움.
#     태그 체계가 확장되면 여기만 늘리면 됨.
DIMENSION_TAG_MAP = {
    "emotion":  [2],   # 감정
    # "quantity": [...], "color_shape": [...], "category": [...], "language": [...],
}


def get_weak_dimension_tags(baby_id: int) -> set:
    """약한 인지 영역에 해당하는 강화 대상 high 태그 집합."""
    profile = get_cognitive_profile(baby_id)
    weak = {t["dimension"] for t in profile["dimensions"] if not t.get("correct")}
    tags = set()
    for d in weak:
        tags.update(DIMENSION_TAG_MAP.get(d, []))
    return tags


# -------------------------------------------------------
# 영역별 인지 프로파일 (문항마다 측정 영역이 다름)
# -------------------------------------------------------
def get_cognitive_profile(baby_id: int) -> dict:
    """
    온보딩 인지 테스트의 영역별 통과 여부를 채점해 프로파일로 반환.
    시스템이 결정론적으로 채점만 하고, 해석은 assess_cognition(GPT)이 담당.
    """
    tests = repo.get_onboarding_test(baby_id)
    correct = sum(1 for t in tests if t.get("correct"))
    total = len(tests)
    return {
        "baby_id": baby_id,
        "dimensions": tests,                                  # [{dimension,label,correct}]
        "correct": correct,
        "total": total,
        "overall_level": cognitive_score_to_level(correct, total) if total else 3,
        "weak_dimensions": [t["label"] for t in tests if not t.get("correct")],
        "strong_dimensions": [t["label"] for t in tests if t.get("correct")],
    }


# -------------------------------------------------------
# 인지 평가 결과 — GPT 해석 (시스템 채점 결과만 근거)
# -------------------------------------------------------
_ASSESS_SYSTEM = (
    "너는 무발화 자폐 아동의 온보딩 인지 평가 결과를 보호자에게 설명하는 발달 전문가다.\n"
    "시스템이 영역별로 채점한 결과(통과/미통과)만을 근거로 해석하라.\n\n"
    "원칙:\n"
    "- 새로운 점수나 수치를 만들지 말 것\n"
    "- 약한 영역은 단정적 진단이 아니라 '연습이 도움 될 수 있는 영역'으로 표현할 것\n"
    "- 강한 영역을 먼저 언급해 긍정적으로 시작할 것\n"
    "- 보호자가 이해하기 쉬운 비전문적 언어로, 3~5문장으로 작성할 것\n"
    "- 각 약한 영역에 맞는 단어 카드 활용 방향을 1가지씩 제안할 것"
)


def _fallback_assessment(profile: dict) -> str:
    strong = ", ".join(profile["strong_dimensions"]) or "없음"
    weak = ", ".join(profile["weak_dimensions"]) or "없음"
    lines = [
        f"인지 테스트 결과 {profile['correct']}/{profile['total']} 영역을 통과했습니다 "
        f"(추정 수준 {profile['overall_level']}/5).",
        f"강한 영역: {strong}.",
        f"연습이 도움 될 수 있는 영역: {weak}.",
    ]
    if profile["weak_dimensions"]:
        lines.append("약한 영역과 관련된 단어 카드를 추천에서 조금 더 자주 노출해 반복 학습을 권장합니다.")
    return "\n".join(lines)


def assess_cognition(baby_id: int) -> dict:
    """{profile, assessment(자연어)} 반환."""
    profile = get_cognitive_profile(baby_id)
    if not config.has_openai():
        return {"profile": profile, "assessment": _fallback_assessment(profile)}
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL_REPORT,
            temperature=0.3,
            max_tokens=400,
            messages=[
                {"role": "system", "content": _ASSESS_SYSTEM},
                {"role": "user", "content": json.dumps(profile, ensure_ascii=False)},
            ],
        )
        return {"profile": profile, "assessment": resp.choices[0].message.content.strip()}
    except Exception:
        return {"profile": profile, "assessment": _fallback_assessment(profile)}


# -------------------------------------------------------
# 선호 키워드: 즐겨찾기 카드 텍스트
# -------------------------------------------------------
def get_preferred_keywords(baby_id: int) -> list:
    return [c["text"] for c in cards.get_enriched_candidates(baby_id)
            if c.get("is_favorite") and c.get("text")]


# -------------------------------------------------------
# 감각 예민도 / 선호 시각 (자유 텍스트 파싱)
# -------------------------------------------------------
def get_sensory_flags(baby_id: int) -> dict:
    text = str(repo.get_level_info(baby_id).get("sensory_sensitivity") or "").lower()
    return {
        "auditory": any(k in text for k in ["청각", "소리", "audi", "sound"]),
        "visual":   any(k in text for k in ["시각", "빛", "visual", "light"]),
        "tactile":  any(k in text for k in ["촉각", "tactile"]),
    }


def get_favorite_visual_type(baby_id: int) -> str:
    return repo.get_level_info(baby_id).get("favorite_visual_type") or "cartoon"


# -------------------------------------------------------
# 통합 신호 (추천·멀티모달·리포트 공용)
# -------------------------------------------------------
def get_signals(baby_id: int) -> dict:
    return {
        "cognitive_level_num": get_cognitive_level_num(baby_id),
        "preferred_keywords": get_preferred_keywords(baby_id),
        "sensory": get_sensory_flags(baby_id),
        "favorite_visual_type": get_favorite_visual_type(baby_id),
    }
