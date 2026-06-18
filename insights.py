"""
insights.py
--------------
GPT 기반 자연어 생성 2종:
  1) report_insight  — 발달 리포트 해석(보호자용, 통계 → 따뜻한 한국어 설명)
  2) emotion_diary   — 감정일기(그날 쓴 단어/문장 → 아이의 하루·감정 서술)

OPENAI_API_KEY 가 없으면 규칙기반 fallback 으로 동작(데모 항상 가능).
"""

import json

import config


def _chat(system: str, user: str, max_tokens: int = 400, temperature: float = 0.4) -> str | None:
    if not config.has_openai():
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL_REPORT,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


# =======================================================
# 1) 발달 리포트 해석 (보호자용)
# =======================================================
_REPORT_SYSTEM = (
    "너는 무발화·자폐 아동의 의사소통 발달을 보호자에게 따뜻하고 쉽게 설명하는 발달 전문가다.\n"
    "주어진 통계(JSON: 기간, 총 선택 수, 고유 단어 수, 문장 수, 평균 문장 길이(어절), "
    "많이 쓴 단어 top, 감정 분포, 최근 문장)를 근거로 보호자용 리포트를 쓴다.\n"
    "원칙:\n"
    "- 따뜻하고 긍정적으로 시작한다.\n"
    "- 통계에 있는 실제 단어/문장을 구체적으로 인용한다.\n"
    "- 주어진 수치 외에 새로운 숫자를 지어내지 않는다.\n"
    "- 마지막에 '다음에 함께 해보면 좋은 것' 한 가지를 부드럽게 제안한다.\n"
    "- 3~4문장, 비전문적이고 다정한 한국어."
)


def _report_fallback(stats: dict) -> str:
    tw = stats.get("top_words") or []
    lead = (tw[0]["text"] if tw and isinstance(tw[0], dict) else (tw[0] if tw else "단어"))
    n = stats.get("total_selections", 0)
    if not n:
        return "아직 기록이 충분하지 않아요. 아이와 함께 카드를 조금 더 사용해보면 다음 리포트가 풍성해질 거예요."
    return (f"이번 기간 동안 아이가 '{lead}'을(를) 가장 자주 사용했어요. "
            f"총 {n}번의 표현을 시도했고 꾸준히 소통하고 있어요. "
            "다음에는 좋아하는 단어에 새로운 단어를 하나씩 이어 말하기를 함께 해보면 좋아요.")


def report_insight(stats: dict) -> str:
    return _chat(_REPORT_SYSTEM, json.dumps(stats, ensure_ascii=False), max_tokens=400) \
        or _report_fallback(stats)


# =======================================================
# 2) 감정일기 (오늘 하루)
# =======================================================
_DIARY_SYSTEM = (
    "너는 무발화·자폐 아동의 하루 의사소통 기록을 보고 '오늘의 감정일기'를 쓰는 따뜻한 작가다.\n"
    "입력 JSON: 날짜, 아이가 오늘 사용한 문장 목록, 자주 쓴 단어, (있다면)감정 태그.\n"
    "아이가 오늘 무엇을 표현했고 어떤 마음이었을지 보호자에게 들려주듯 다정하게 쓴다.\n"
    "원칙:\n"
    "- 실제 사용한 문장을 1~2개 자연스럽게 인용한다.\n"
    "- 단정적 진단 대신 '~한 것 같아요' 처럼 부드럽게.\n"
    "- 기록이 없으면 억지로 지어내지 말고 조용한 하루였다고 따뜻하게 적는다.\n"
    "반드시 아래 JSON 형식으로만 답한다(다른 말 금지):\n"
    '{"mood": "차분|기쁨|신남|속상|편안 중 하나", "diary": "3~4문장 한국어 일기"}'
)


def _diary_fallback(day: dict) -> dict:
    sents = day.get("sentences") or []
    if not sents:
        return {"mood": "편안", "diary": "오늘은 조용한 하루였어요. 아이가 편안하게 보낸 것 같아요."}
    quote = sents[0]
    return {"mood": "차분",
            "diary": f"오늘 아이는 '{quote}' 같은 말로 마음을 표현했어요. "
                     "하고 싶은 것을 또렷이 전하려고 노력한 하루였던 것 같아요."}


def emotion_diary(day: dict) -> dict:
    raw = _chat(_DIARY_SYSTEM, json.dumps(day, ensure_ascii=False), max_tokens=350, temperature=0.6)
    if not raw:
        return _diary_fallback(day)
    try:
        # 코드블록/잡텍스트 방어
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start:end + 1])
        return {"mood": str(data.get("mood") or "차분"),
                "diary": str(data.get("diary") or _diary_fallback(day)["diary"])}
    except Exception:
        return _diary_fallback(day)
