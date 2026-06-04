"""
related.py
--------------
부모 모드 '단어 추가'용 관련 단어 생성.

아이 추천(recommend.py)은 DB 후보 안에서만 고르지만, 부모가 카드를 추가할 때는
'DB 에 아직 없는' 관련 단어를 제안해야 한다 → 본질적으로 생성형이라 GPT 로 만든다.

  - 입력(단어/문장)과 의미적으로 관련된, 카드로 추가하면 좋을 쉬운 한국어 단어 제안
  - 입력에 이미 나온 단어 / exclude(이미 DB 에 있는 단어)는 제외
  - OPENAI_API_KEY 없으면 빈 목록 반환(생성형이라 fallback 으론 의미있는 새 단어 불가)
"""

import json

import config

SYSTEM_PROMPT = (
    "너는 무발화 자폐 아동을 위한 AAC(보완대체의사소통) 카드 보조 시스템이다.\n"
    "부모가 입력한 단어/문장과 의미적으로 관련 있어, 카드로 추가하면 좋을 단어를 제안하라.\n\n"
    "조건:\n"
    "- 입력에 이미 나온 단어는 제외할 것\n"
    "- 아동이 이해하기 쉬운 짧은 한국어 단어(명사/동사/형용사)일 것\n"
    "- 일상 의사소통에서 자주 쓰는 단어 위주로 고를 것\n"
    "- part_of_speech 는 noun / verb / adjective 중 하나\n"
    '- 반드시 JSON 으로만 답할 것: '
    '{"related_words": [{"text": "단어", "pos": "noun"}]}'
)


def suggest_related(text: str, count: int = 6, exclude=None) -> list:
    """입력 텍스트와 관련된 새 단어 후보 리스트 [{text, pos}] 반환."""
    text = (text or "").strip()
    exclude_set = {x.strip() for x in (exclude or []) if x and x.strip()}
    if not text or not config.has_openai():
        return []

    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        user = (
            f'입력: "{text}"\n'
            f"이와 관련해 카드로 추가하면 좋을 단어 {count}개를 제안하라."
        )
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL_GRAMMAR,
            temperature=0.6,
            max_tokens=250,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        out, seen = [], set()
        for w in data.get("related_words", []):
            if isinstance(w, dict):
                t = (w.get("text") or "").strip()
                pos = (w.get("pos") or None)
            else:
                t = str(w).strip()
                pos = None
            if not t or t in seen or t in exclude_set or t in text:
                continue
            pos = pos.lower() if isinstance(pos, str) else None
            seen.add(t)
            out.append({"text": t, "pos": pos})
            if len(out) >= count:
                break
        return out
    except Exception:
        return []
