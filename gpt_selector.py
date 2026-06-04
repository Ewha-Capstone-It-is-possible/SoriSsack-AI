"""
gpt_selector.py
--------------
STEP 2 — GPT 기반 후보 정렬 및 축소 (보조 역할).

회귀(Layer2)가 매긴 상위 후보 중에서, OpenAI GPT 를 selector 로 사용해
아동에게 실제 제시할 4~5개를 선별·정렬한다.

핵심 제약(설계):
  - GPT 는 새 단어를 생성하지 않는다 (DB 후보 중에서만 선택) → 할루시네이션 차단
  - 의미적으로 자연스럽고 아동이 선택하기 쉬운 순서로 정렬
  - model=gpt-4o-mini, temperature=0.2, max_tokens=150, response_format=JSON

OPENAI_API_KEY 가 없으면 회귀 점수 순서를 그대로 반환(graceful fallback).
"""

import json

import config

SYSTEM_PROMPT = (
    "너는 무발화 자폐 아동을 위한 의사소통 보조 시스템이다.\n"
    "아이가 방금 선택한 단어와, 시스템이 제공한 단어 후보 목록을 참고하여,\n"
    "다음에 올 가능성이 높은 단어 후보를 정확히 4~5개만 선택하라.\n\n"
    "조건:\n"
    "- 새로운 단어를 생성하지 말 것 (반드시 후보 목록 안에서만 선택)\n"
    "- 의미적으로 자연스러운 단어만 선택할 것\n"
    "- 아동이 선택하기 쉬운 순서로 정렬할 것\n"
    '- 반드시 JSON 으로만 답할 것: {"recommended_words": ["...", "..."]}'
)


def _build_user_prompt(selected_word, candidates):
    lines = [f'선택 단어: "{selected_word or "(첫 화면)"}"', "후보 단어 목록:"]
    for c in candidates:
        lines.append(
            f'- {c["text"]} (score={c.get("system_score", 0):.2f}, '
            f'pos={c.get("pos")}, priority={c.get("priority")})'
        )
    return "\n".join(lines)


def select(selected_word, candidates: list, top_n: int = 5) -> list:
    """
    candidates: Layer2 점수 내림차순 정렬된 후보(dict, 'text' 포함).
    반환: GPT(또는 fallback)가 고른 후보 dict 리스트 (순서 유지, 최대 top_n).
    """
    if not candidates:
        return []

    if not config.has_openai():
        return candidates[:top_n]            # fallback: 회귀 점수 순서

    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL_SELECTOR,
            temperature=0.2,
            max_tokens=150,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(selected_word, candidates)},
            ],
        )
        data = json.loads(resp.choices[0].message.content)
        chosen_texts = data.get("recommended_words", [])
        # 새 단어 생성 방지: 후보에 실제 존재하는 텍스트만 채택, GPT 순서 유지
        by_text = {c["text"]: c for c in candidates}
        ordered = [by_text[t] for t in chosen_texts if t in by_text]
        # GPT 응답이 비거나 매칭 실패 시 회귀 순서로 보강
        if len(ordered) < min(top_n, len(candidates)):
            for c in candidates:
                if c not in ordered:
                    ordered.append(c)
                if len(ordered) >= top_n:
                    break
        return ordered[:top_n]
    except Exception:
        # 네트워크/쿼터/파싱 오류 → 회귀 순서 fallback
        return candidates[:top_n]
