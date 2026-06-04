"""
grammar.py
--------------
STEP 3 — 문법 보정 ('말하기' 버튼).

아동이 선택한 단어 배열을 자연스러운 한국어 문장으로 변환한다.
예: ["물", "마시다"] → "물을 마시고 싶어요."

  - GPT(gpt-4o-mini)로 조사 추가/어미 활용/어순 정렬 (단어 자체는 바꾸지 않음)
  - 아동의 인지 수준(level)에 따라 문장 길이/구체성 조절
  - OPENAI_API_KEY 없으면 규칙 기반 fallback
"""

import config

SYSTEM_PROMPT = (
    "너는 무발화 자폐 아동의 단어 선택을 자연스러운 한국어 문장으로 바꾸는 도우미다.\n"
    "주어진 단어들의 의미와 순서를 유지하되, 조사와 어미만 보정해 한 문장으로 만들어라.\n"
    "새로운 의미의 단어를 추가하지 말고, 공손하고 짧은 구어체로 만들어라.\n"
    "문장 하나만 출력하라. 따옴표나 설명 없이 문장만."
)


def _level_hint(level: dict | None) -> str:
    if not level:
        return ""
    cog = level.get("language_cognitive_level", 3)
    if cog <= 2:
        return "아동의 인지 수준이 초기 단계이므로 아주 짧고 직관적인 문장으로 만들어라."
    if cog >= 4:
        return "아동의 표현 수준이 높으므로 조금 더 자연스럽고 구체적인 문장으로 만들어라."
    return ""


def _fallback(words: list) -> str:
    """규칙 기반 단순 보정 (GPT 미사용 시): 단어를 공백으로 이어 붙인다."""
    texts = [w for w in words if w]
    return " ".join(texts)


def complete_sentence(words: list, level: dict | None = None) -> str:
    """words: 선택 단어 텍스트 리스트. 반환: 완성 문장."""
    texts = [w for w in words if w]
    if not texts:
        return ""

    if not config.has_openai():
        return _fallback(texts)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        user = "단어: " + ", ".join(texts)
        hint = _level_hint(level)
        if hint:
            user += "\n" + hint
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL_GRAMMAR,
            temperature=0.2,
            max_tokens=60,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content.strip().strip('"').strip()
        return text or _fallback(texts)
    except Exception:
        return _fallback(texts)
