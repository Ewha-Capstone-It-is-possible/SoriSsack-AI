"""
report.py
--------------
발달 리포트 생성 (AI 4번 기능).

핵심 설계: "온보딩 → 표현 → 데이터 축적 → 분석 → 공유" 폐쇄 루프의 분석 단계.

  1. analysis.bundle 로 현재 구간 / 이전 구간 5지표를 각각 산출
  2. 두 구간을 비교해 기간 대비 변화(증감) 도출
        vocab_growth        : 고유 단어 수 증감(%)
        avg_sentence_length : "3.2 → 4.6" (이전→현재)
        emotion_ratio       : "8% → 15%"
        category_distribution / behavioral_clusters / top5_words
  3. LLM(gpt-4o-mini)이 정량 지표만 근거로 자연어 해석 (수치 생성 금지)
  4. Plotly 시각화 JSON + PDF 변환 (선택)

LLM·시각화·PDF 라이브러리가 없어도 항상 동작(graceful)한다.
"""

import json
from datetime import datetime, timedelta

import config
import repo
import analysis
import onboarding

LLM_SYSTEM = (
    "너는 무발화 자폐 아동의 의사소통 발달 리포트를 보호자와 교사에게 설명하는 분석가다.\n"
    "시스템이 계산한 정량적 지표만을 근거로, 다음 원칙에 따라 자연어 리포트를 작성하라.\n\n"
    "원칙:\n"
    "- 새로운 수치를 생성하거나 추정하지 말 것\n"
    "- 주어진 지표 값만을 정확히 인용할 것\n"
    "- 보호자가 이해하기 쉬운 비전문적 언어로 작성할 것\n"
    "- 긍정적 변화를 먼저 언급하고, 개선이 필요한 부분은 제안 형태로 제시할 것\n"
    "- 온보딩 정보(인지 수준, 감각 예민도)를 고려해 해석할 것"
)


# =======================================================
# 구간 분할 (현재 vs 이전)
# =======================================================
def _sentence_time(sentence):
    """문장의 시각(첫 단어 created_at). dummy 는 없을 수 있음."""
    if sentence and isinstance(sentence, list) and sentence:
        return sentence[0].get("created_at")
    return None


def _split_windows(logs, sentences, period_days=None, now=None):
    """
    (현재 logs, 이전 logs, 현재 sentences, 이전 sentences, 기간 라벨) 반환.

    - period_days 지정 시: now 기준 [now-P, now] = 현재, [now-2P, now-P] = 이전
    - 미지정(AUTO): 로그 used_at 범위의 중간점으로 절반 분할(데모용). 문장은
      created_at 이 있으면 같은 기준, 없으면 인덱스 절반 분할.
    """
    now = now or datetime.now()
    times = [l["used_at"] for l in logs if l.get("used_at")]

    if period_days:
        cur_start = now - timedelta(days=period_days)
        prev_start = now - timedelta(days=2 * period_days)
        cur_logs = [l for l in logs if l.get("used_at") and l["used_at"] >= cur_start]
        prev_logs = [l for l in logs if l.get("used_at") and prev_start <= l["used_at"] < cur_start]
        label = f"최근 {period_days}일"
        mid = cur_start
    elif times:
        lo, hi = min(times), max(times)
        mid = lo + (hi - lo) / 2
        cur_logs = [l for l in logs if l.get("used_at") and l["used_at"] >= mid]
        prev_logs = [l for l in logs if l.get("used_at") and l["used_at"] < mid]
        label = f"{lo.date().isoformat()} ~ {hi.date().isoformat()}"
    else:
        cur_logs, prev_logs, mid, label = logs, [], None, "전체"

    # 문장 분할
    if any(_sentence_time(s) for s in sentences) and mid is not None:
        cur_sents = [s for s in sentences if (_sentence_time(s) or mid) >= mid]
        prev_sents = [s for s in sentences if (_sentence_time(s) or mid) < mid]
    else:
        half = len(sentences) // 2
        prev_sents, cur_sents = sentences[:half], sentences[half:]

    return cur_logs, prev_logs, cur_sents, prev_sents, label


# =======================================================
# 비교 지표 구성 (LLM 입력 + 응답 표시용)
# =======================================================
def _pct_change(cur, prev):
    if prev == 0:
        return "신규" if cur > 0 else "0%"
    pct = round(100 * (cur - prev) / prev)
    return f"{'+' if pct >= 0 else ''}{pct}%"


def _cluster_labels(clusters: dict):
    if not clusters or not clusters.get("clusters"):
        return []
    # 대표 카테고리 의미 라벨 우선, 없으면 예시 문구로 fallback
    return [v.get("label") or (v["examples"][0] if v.get("examples") else "")
            for v in clusters["clusters"].values()]


def _build_comparison(cur: dict, prev: dict, level: dict, baby_id: int = None) -> dict:
    cur_uniq = cur["vocabulary_diversity"]["unique_total"]
    prev_uniq = prev["vocabulary_diversity"]["unique_total"]
    cur_len = cur["avg_sentence_length"]["avg"]
    prev_len = prev["avg_sentence_length"]["avg"]
    cur_emo = cur["emotion_ratio"].get("ratio", 0)
    prev_emo = prev["emotion_ratio"].get("ratio", 0)
    return {
        "vocab_growth": _pct_change(cur_uniq, prev_uniq),
        "vocab_unique": {"prev": prev_uniq, "cur": cur_uniq},
        "avg_sentence_length": f"{prev_len} → {cur_len}",
        "category_distribution": cur["category_distribution"],
        "emotion_ratio": f"{prev_emo}% → {cur_emo}%",
        "behavioral_clusters": _cluster_labels(cur.get("behavioral_clusters")),
        "top5_words": cur["top5_words"],
        "onboarding_context": {
            "cognitive_level": onboarding.get_cognitive_level_num(baby_id) if baby_id else None,
            "language_cognitive_level": level.get("language_cognitive_level"),
            "sensory_sensitivity": level.get("sensory_sensitivity"),
        },
    }


# =======================================================
# LLM 자연어 해석
# =======================================================
def _fallback_interpretation(c: dict) -> str:
    cat = c.get("category_distribution", {})
    top_cat = next(iter(cat), None)
    top5 = ", ".join(c.get("top5_words", [])) or "(데이터 없음)"
    lines = [
        f"이번 기간 동안 사용한 고유 단어 수는 이전 대비 {c['vocab_growth']} 변화했습니다.",
        f"평균 문장 길이는 {c['avg_sentence_length']} 단어로 변화했습니다.",
        f"자주 사용한 단어는 {top5} 입니다.",
    ]
    if top_cat:
        lines.append(f"'{top_cat}' 표현({cat[top_cat]}%)의 비중이 가장 높습니다.")
    lines.append(f"감정 표현이 포함된 문장 비율은 {c['emotion_ratio']} 로 변화했습니다.")
    lines.append("사회적 표현(인사·감사·거절)과 감정 단어 노출을 점진적으로 늘려가는 것을 권장합니다.")
    return "\n".join(lines)


def _llm_interpretation(comparison: dict) -> str:
    if not config.has_openai():
        return _fallback_interpretation(comparison)
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL_REPORT,
            temperature=0.3,
            max_tokens=500,
            messages=[
                {"role": "system", "content": LLM_SYSTEM},
                {"role": "user", "content": json.dumps(comparison, ensure_ascii=False)},
            ],
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return _fallback_interpretation(comparison)


# =======================================================
# Plotly 시각화
# =======================================================
def build_charts(cur: dict, comparison: dict) -> dict:
    try:
        import plotly.graph_objects as go
    except ImportError:
        return {}

    charts = {}
    cat = cur.get("category_distribution", {})
    if cat:
        fig = go.Figure([go.Bar(x=list(cat.keys()), y=list(cat.values()))])
        fig.update_layout(title="카테고리별 사용 비율 (%)")
        charts["category_distribution"] = json.loads(fig.to_json())

    trend = cur.get("vocabulary_diversity", {}).get("trend_by_day", {})
    if trend:
        fig = go.Figure([go.Scatter(x=list(trend.keys()), y=list(trend.values()),
                                    mode="lines+markers")])
        fig.update_layout(title="단어 다양성 추세 (일별 고유 단어 수)")
        charts["vocabulary_diversity"] = json.loads(fig.to_json())

    dist = cur.get("avg_sentence_length", {}).get("length_distribution", {})
    if dist:
        fig = go.Figure([go.Bar(x=[str(k) for k in dist.keys()], y=list(dist.values()))])
        fig.update_layout(title="문장 길이 분포 (단어 수)")
        charts["sentence_length"] = json.loads(fig.to_json())

    return charts


# =======================================================
# 리포트 생성 (메인)
# =======================================================
def generate_report(baby_id: int, period_days: int = None, with_charts: bool = True) -> dict:
    logs = repo.get_vocab_logs(baby_id, limit=100000)
    sentences = repo.get_sentence_word_map(baby_id)
    level = repo.get_level_info(baby_id)

    cur_logs, prev_logs, cur_sents, prev_sents, label = _split_windows(logs, sentences, period_days)

    cur = analysis.bundle(cur_logs, cur_sents, with_clusters=True)
    prev = analysis.bundle(prev_logs, prev_sents, with_clusters=False)
    comparison = _build_comparison(cur, prev, level, baby_id)

    # LLM INPUT (슬라이드 구조): baby_id + period + 5지표 정량값만
    llm_input = {"baby_id": baby_id, "period": label, **comparison}

    report = {
        "baby_id": baby_id,
        "period": label,
        "summary": comparison,            # 기간 대비 요약
        "current_metrics": cur,           # 현재 구간 상세 5지표
        "interpretation": _llm_interpretation(llm_input),
    }
    if with_charts:
        report["charts"] = build_charts(cur, comparison)
    return report


# =======================================================
# PDF 변환
# =======================================================
def export_pdf(baby_id: int, path: str, period_days: int = None) -> dict:
    rep = generate_report(baby_id, period_days, with_charts=False)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import cm
    except ImportError:
        return {"path": None, "report": rep,
                "status": "stub (reportlab 미설치) — JSON 리포트만 제공"}

    import os
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    y = height - 2 * cm
    c.setFont("Helvetica-Bold", 15)
    c.drawString(2 * cm, y, f"SoriSsak Development Report (baby_id={baby_id})")
    y -= 0.8 * cm
    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, f"period: {rep['period']}")
    y -= 0.8 * cm

    s = rep["summary"]
    rows = [
        f"vocab growth: {s['vocab_growth']}  ({s['vocab_unique']['prev']} -> {s['vocab_unique']['cur']})",
        f"avg sentence length: {s['avg_sentence_length']}",
        f"emotion ratio: {s['emotion_ratio']}",
        f"top5: {', '.join(s['top5_words'])}",
        f"category: {s['category_distribution']}",
    ]
    for r in rows:
        c.drawString(2 * cm, y, r[:100]); y -= 0.55 * cm

    y -= 0.4 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Interpretation"); y -= 0.6 * cm
    c.setFont("Helvetica", 9)
    for line in rep["interpretation"].splitlines():
        if y < 2 * cm:
            c.showPage(); y = height - 2 * cm; c.setFont("Helvetica", 9)
        c.drawString(2 * cm, y, line[:110]); y -= 0.45 * cm

    c.save()
    return {"path": path, "report": rep, "status": "generated"}
