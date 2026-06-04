"""
analysis.py
--------------
데이터 분석 엔진 (AI 4번 기능) — 발달 지표 산출.

설계의 5개 핵심 지표를 pandas + scikit-learn 으로 산출한다. 지표 계산·시각화는
시스템이 결정론적으로 수행하고, 해석(자연어)은 report.py 의 LLM 이 담당한다.

  지표 1. 단어 다양성 변화      (Vocabulary Diversity)   — 고유 단어 수 추세
  지표 2. 평균 문장 길이 변화   (Average Sentence Length)
  지표 3. 카테고리별 사용 비율  (Category Distribution)  — high tag 기준
  지표 4. 감정 표현 사용 비율   (Emotion Expression Ratio)
  지표 5. 행동 주제 패턴 분석   (Behavioral Pattern Clustering) — KMeans

데이터가 적어도 깨지지 않도록 모든 지표는 방어적으로 계산한다.
"""

from collections import Counter, defaultdict

import repo

HIGH_TAG_NAMES = {1: "욕구", 2: "감정", 3: "행동", 4: "요청", 5: "사람", 6: "장소", 7: "범용"}
EMOTION_TAG = 2


def _high_tags_of(baby_card_id, card_id) -> set:
    from features import _high_tags
    return _high_tags(baby_card_id, card_id)


# -------------------------------------------------------
# 지표 1. 단어 다양성
# -------------------------------------------------------
def _log_text(l) -> str | None:
    return l.get("text") or l.get("text_snapshot")   # dummy=text, db=text_snapshot


def _word_text(w) -> str:
    return w.get("text") or w.get("text_snapshot") or ""


def vocabulary_diversity(logs) -> dict:
    unique = {_log_text(l) for l in logs if _log_text(l)}
    by_day = defaultdict(set)
    for l in logs:
        used, txt = l.get("used_at"), _log_text(l)
        if used and txt:
            by_day[used.date().isoformat()].add(txt)
    trend = {d: len(s) for d, s in sorted(by_day.items())}
    return {"unique_total": len(unique), "trend_by_day": trend}


# -------------------------------------------------------
# 지표 2. 평균 문장 길이
# -------------------------------------------------------
def avg_sentence_length(sentences) -> dict:
    lengths = [len(s) for s in sentences if s]
    avg = sum(lengths) / len(lengths) if lengths else 0.0
    dist = Counter(lengths)
    return {"avg": round(avg, 2), "n_sentences": len(lengths),
            "length_distribution": dict(sorted(dist.items()))}


# -------------------------------------------------------
# 지표 3. 카테고리별 사용 비율
# -------------------------------------------------------
def category_distribution(logs) -> dict:
    counter = Counter()
    for l in logs:
        for tid in _high_tags_of(l.get("baby_card_id"), l.get("card_id")):
            counter[HIGH_TAG_NAMES.get(tid, str(tid))] += 1
    total = sum(counter.values())
    if total == 0:
        return {}
    return {k: round(100 * v / total, 1) for k, v in counter.most_common()}


# -------------------------------------------------------
# 지표 4. 감정 표현 비율
# -------------------------------------------------------
def emotion_ratio(sentences) -> dict:
    if not sentences:
        return {"ratio": 0.0}
    emo = 0
    for s in sentences:
        if any(EMOTION_TAG in _high_tags_of(w.get("baby_card_id"), w.get("card_id")) for w in s):
            emo += 1
    return {"ratio": round(100 * emo / len(sentences), 1), "emotion_sentences": emo,
            "total_sentences": len(sentences)}


# -------------------------------------------------------
# 지표 5. 행동 주제 패턴 (KMeans 군집)
# -------------------------------------------------------
def behavioral_clusters(sentences, n_clusters: int = 3) -> dict:
    # 각 문장을 카테고리 카운트 벡터로 표현
    cats = list(HIGH_TAG_NAMES.values())
    vectors, labels_text = [], []
    for s in sentences:
        vec = [0] * len(cats)
        for w in s:
            for tid in _high_tags_of(w.get("baby_card_id"), w.get("card_id")):
                name = HIGH_TAG_NAMES.get(tid)
                if name in cats:
                    vec[cats.index(name)] += 1
        vectors.append(vec)
        labels_text.append(" ".join(_word_text(w) for w in s))

    if len(vectors) < n_clusters:
        return {"n_clusters": 0, "note": "데이터 부족"}

    try:
        from sklearn.cluster import KMeans
        km = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = km.fit_predict(vectors)
    except Exception:
        return {"n_clusters": 0, "note": "scikit-learn 미설치"}

    members = defaultdict(list)
    vecsum = defaultdict(lambda: [0] * len(cats))
    for idx, lab in enumerate(labels):
        members[int(lab)].append(labels_text[idx])
        for k in range(len(cats)):
            vecsum[int(lab)][k] += vectors[idx][k]

    summary = {}
    for c in sorted(members):
        v = vecsum[c]
        dom = cats[v.index(max(v))] if max(v) > 0 else "기타"
        summary[f"cluster_{c}"] = {
            "size": len(members[c]),
            "label": f"{dom} 표현",          # 대표 카테고리 기반 의미 라벨
            "examples": members[c][:3],
        }
    return {"n_clusters": n_clusters, "clusters": summary}


# -------------------------------------------------------
# 윈도우(기간) 단위 지표 묶음 — report.py 가 현재/이전 구간에 각각 호출
# -------------------------------------------------------
def bundle(logs, sentences, with_clusters: bool = True) -> dict:
    """주어진 (logs, sentences) 한 구간에 대한 5지표 묶음."""
    return {
        "vocabulary_diversity": vocabulary_diversity(logs),
        "avg_sentence_length": avg_sentence_length(sentences),
        "category_distribution": category_distribution(logs),
        "emotion_ratio": emotion_ratio(sentences),
        "behavioral_clusters": behavioral_clusters(sentences) if with_clusters else None,
        "top5_words": [w for w, _ in Counter(
            _log_text(l) for l in logs if _log_text(l)).most_common(5)],
        "n_logs": len(logs),
        "n_sentences": len([s for s in sentences if s]),
    }


# -------------------------------------------------------
# 통합 지표 산출 (전체 구간, 단일 스냅샷)
# -------------------------------------------------------
def compute_metrics(baby_id: int) -> dict:
    logs = repo.get_vocab_logs(baby_id, limit=100000)
    sentences = repo.get_sentence_word_map(baby_id)
    level = repo.get_level_info(baby_id)

    out = {"baby_id": baby_id}
    out.update(bundle(logs, sentences))
    out["onboarding_context"] = {
        "language_cognitive_level": level.get("language_cognitive_level"),
        "sensory_sensitivity": level.get("sensory_sensitivity"),
    }
    return out
