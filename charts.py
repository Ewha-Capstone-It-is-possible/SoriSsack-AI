"""
charts.py
--------------
리포트 그래프를 PNG 이미지로 렌더해 S3 에 올리고 URL 반환.
(프론트는 차트 라이브러리 없이 이미지로 띄우기만 — '말하기 이미지'와 같은 흐름)

matplotlib + 한글 폰트(NanumGothic). 폰트/라이브러리 없으면 None 반환(차트 생략).
"""

import io
import os
import hashlib

import config
import s3

# 앱 톤(노랑/파스텔)
_PALETTE = ["#FFC93C", "#FF9F68", "#7ED6A5", "#73B6FF", "#C39BD3", "#F1948A"]
_FONT_PATHS = [
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf",
    "/Library/Fonts/AppleGothic.ttf",
]

_plt = None


def _get_plt():
    """matplotlib 준비(한글 폰트 등록). 실패하면 None."""
    global _plt
    if _plt is not None:
        return _plt
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
        for p in _FONT_PATHS:
            if os.path.exists(p):
                fm.fontManager.addfont(p)
                plt.rcParams["font.family"] = fm.FontProperties(fname=p).get_name()
                break
        plt.rcParams["axes.unicode_minus"] = False
        _plt = plt
        return plt
    except Exception:
        return None


def _save(fig, key: str):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)
    data = buf.getvalue()
    if config.has_s3():
        return s3.upload_bytes(data, key, "image/png")
    os.makedirs(config.IMAGE_OUTPUT_DIR, exist_ok=True)
    path = os.path.join(config.IMAGE_OUTPUT_DIR, os.path.basename(key))
    with open(path, "wb") as f:
        f.write(data)
    return config.public_url(path)


def _key(prefix: str, baby_id, payload) -> str:
    h = hashlib.sha256(str(payload).encode("utf-8")).hexdigest()[:10]
    return f"charts/{prefix}_{baby_id}_{h}.png"


def top_words_chart(baby_id, top_words: list) -> str | None:
    """많이 쓴 단어 → 가로 막대그래프."""
    plt = _get_plt()
    if plt is None or not top_words:
        return None
    items = [(w["text"], w["count"]) for w in top_words[:6]][::-1]
    labels = [t for t, _ in items]
    counts = [c for _, c in items]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.barh(labels, counts, color=_PALETTE[0])
    ax.set_title("많이 쓴 단어", fontsize=14, fontweight="bold")
    for i, c in enumerate(counts):
        ax.text(c, i, f" {c}", va="center", fontsize=11)
    ax.set_xlabel("사용 횟수")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    return _save(fig, _key("words", baby_id, items))


def emotion_chart(baby_id, emotion_counts: dict) -> str | None:
    """감정 분포 → 도넛 차트."""
    plt = _get_plt()
    if plt is None or not emotion_counts:
        return None
    labels = list(emotion_counts.keys())
    sizes = list(emotion_counts.values())
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    ax.pie(sizes, labels=labels, autopct="%1.0f%%", colors=_PALETTE,
           wedgeprops={"width": 0.42}, textprops={"fontsize": 11})
    ax.set_title("감정 분포", fontsize=14, fontweight="bold")
    return _save(fig, _key("emotion", baby_id, emotion_counts))


def category_chart(baby_id, category_usage: dict) -> str | None:
    """카테고리 비율 → 도넛 차트. {라벨: 비율/횟수}."""
    plt = _get_plt()
    if plt is None or not category_usage:
        return None
    labels = list(category_usage.keys())
    sizes = list(category_usage.values())
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    ax.pie(sizes, labels=labels, autopct="%1.0f%%", colors=_PALETTE,
           wedgeprops={"width": 0.42}, textprops={"fontsize": 11})
    ax.set_title("카테고리 사용 비율", fontsize=14, fontweight="bold")
    return _save(fig, _key("category", baby_id, category_usage))


def build_report_charts(baby_id, stats: dict) -> dict:
    """리포트 통계 → 차트 이미지 URL 모음(없는 건 생략)."""
    out = {}
    w = top_words_chart(baby_id, stats.get("top_words") or [])
    if w:
        out["words_chart_url"] = w
    e = emotion_chart(baby_id, stats.get("emotion_counts") or {})
    if e:
        out["emotion_chart_url"] = e
    c = category_chart(baby_id, stats.get("category_usage") or {})
    if c:
        out["category_chart_url"] = c
    return out
