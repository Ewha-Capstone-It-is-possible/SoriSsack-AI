"""
features.py
--------------
Layer 1 / Layer 2 회귀 모델용 feature 추출기.

설계(AI 1번 기능 PDF) 기준:
  - Layer 1 (카드 중요도): feature 15개
  - Layer 2 (맥락 랭킹):   feature 20개

모든 feature는 대략 0~1 범위로 정규화되어 회귀 가중치/스코어링이 안정적으로
동작하도록 만든다. 데이터가 없는 경우 합리적 기본값(0 또는 0.5)을 사용한다.

BabyFeatureContext: 한 아동에 대한 로그/문장/공출현 통계를 한 번만 집계해
                    여러 카드의 feature 계산에 재사용한다.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime

import repo

# -------------------------------------------------------
# feature 이름 순서 (회귀 가중치 매핑 기준)
# -------------------------------------------------------
LAYER1_FEATURES = [
    # A. 사용 이력 (5)
    "usage_count_7d", "usage_count_30d", "usage_trend", "recency", "time_diversity_entropy",
    # B. 문장 완성 품질 (2)
    "sentence_completion_rate", "avg_sentence_position",
    # C. 부모·시스템 신호 (3)
    "is_favorite", "source_weight", "priority",
    # D. 의미 풍부도 (3)
    "tag_confidence_avg", "tag_coverage", "co_occurrence_centrality",
    # E. 아동 맥락 (2)
    "onboarding_match_score", "cognitive_difficulty_gap",
]

LAYER2_FEATURES = [
    # A. 후보 자체 (2)
    "cand_system_score", "cand_source_weight",
    # B. 두 카드 관계 (6)
    "co_occurrence_count", "co_occurrence_pmi", "sequential_probability",
    "high_tag_overlap", "low_tag_overlap", "pos_transition_prob",
    # C. 시간·세션 (4)
    "cand_recency_decay", "time_of_day_match", "day_of_week_match", "session_length_so_far",
    # D. 아동 개별 (3)
    "cand_personal_usage", "cand_is_favorite", "child_pos_preference",
    # E. 인지 적합도 (2)
    "cognitive_match", "cand_tag_confidence_avg",
    # F. 구조적 힌트 (3)
    "is_bridge_card", "filter_stage_passed", "max_selectable_position",
]

SOURCE_WEIGHT = {
    "parent_manual": 1.0,
    "onboarding": 0.9,
    "ai_recommend_selected": 0.7,
    "system_default": 0.5,
}

BRIDGE_TAG_ID = 7   # '범용'


def _safe_div(a, b):
    return a / b if b else 0.0


def _norm_pos(pos):
    return pos.lower() if pos else None


# =======================================================
# 아동 단위 통계 집계
# =======================================================
class BabyFeatureContext:
    def __init__(self, baby_id: int, now: datetime | None = None,
                 logs_override: list | None = None):
        self.baby_id = baby_id
        self.now = now or datetime.now()

        import onboarding
        self.logs = logs_override if logs_override is not None else repo.get_vocab_logs(baby_id)
        self.sentences = repo.get_sentence_word_map(baby_id)
        # 선호 키워드 = 즐겨찾기, 인지수준 = 온보딩 인지테스트 채점 결과
        self.onboarding = set(onboarding.get_preferred_keywords(baby_id))
        self.cognitive_level_num = onboarding.get_cognitive_level_num(baby_id)
        self.level = repo.get_level_info(baby_id)

        self._build_log_stats()
        self._build_sentence_stats()

    # ---- 로그 기반 ----
    def _build_log_stats(self):
        self.count_7d = defaultdict(int)
        self.count_30d = defaultdict(int)
        self.total_count = defaultdict(int)
        self.hour_dist = defaultdict(lambda: defaultdict(int))   # bcid -> {hour: n}
        self.weekday_dist = defaultdict(lambda: defaultdict(int))
        self.total_logs = len(self.logs)

        for l in self.logs:
            bcid = l.get("baby_card_id")
            used = l.get("used_at")
            hours = (self.now - used).total_seconds() / 3600 if used else 1e9
            if hours <= 7 * 24:
                self.count_7d[bcid] += 1
            if hours <= 30 * 24:
                self.count_30d[bcid] += 1
            self.total_count[bcid] += 1
            if used:
                self.hour_dist[bcid][used.hour] += 1
                self.weekday_dist[bcid][used.weekday()] += 1

        self.max_7d = max(self.count_7d.values(), default=0)
        self.max_30d = max(self.count_30d.values(), default=0)
        self.max_total = max(self.total_count.values(), default=0)

    # ---- 문장(sentence_word_map) 기반: 공출현/순차/위치 ----
    def _build_sentence_stats(self):
        self.pos_count = defaultdict(int)     # pos -> n (문장 단어 기준)
        self.cooc = defaultdict(int)          # frozenset({key_a,key_b}) -> n
        self.seq = defaultdict(int)           # (prev_key, next_key) -> n
        self.prev_total = defaultdict(int)    # prev_key -> n  (직후 전이 분모)
        self.unigram = defaultdict(int)       # key -> 등장 문장 수
        self.partners = defaultdict(set)      # key -> {함께 등장한 key들}
        self.positions = defaultdict(list)    # key -> [정규화 위치]
        self.in_sentence = defaultdict(int)   # key -> 문장 포함 횟수
        self.pos_transition = defaultdict(int)   # (prev_pos, next_pos) -> n
        self.pos_prev_total = defaultdict(int)
        self.total_sentences = len(self.sentences)
        self.total_words = 0

        for words in self.sentences:
            n = len(words)
            keys = [self._wkey(w) for w in words]
            for i, w in enumerate(words):
                k = keys[i]
                self.unigram[k] += 1
                self.in_sentence[k] += 1
                self.positions[k].append(_safe_div(i, max(1, n - 1)))
                self.total_words += 1
                wpos = _norm_pos(w.get("pos"))
                if wpos:
                    self.pos_count[wpos] += 1
            # 공출현 (무순서 쌍)
            for i in range(n):
                for j in range(i + 1, n):
                    self.cooc[frozenset((keys[i], keys[j]))] += 1
                    self.partners[keys[i]].add(keys[j])
                    self.partners[keys[j]].add(keys[i])
            # 순차 (인접 쌍) + 품사 전이
            for i in range(n - 1):
                self.seq[(keys[i], keys[i + 1])] += 1
                self.prev_total[keys[i]] += 1
                pp, np_ = _norm_pos(words[i].get("pos")), _norm_pos(words[i + 1].get("pos"))
                if pp and np_:
                    self.pos_transition[(pp, np_)] += 1
                    self.pos_prev_total[pp] += 1

        self.distinct_keys = max(1, len(self.unigram))

    @staticmethod
    def _wkey(w):
        return repo.card_key(w.get("baby_card_id"), w.get("card_id"), w.get("text"))

    @staticmethod
    def key_of(card):
        return repo.card_key(card.get("baby_card_id"), card.get("card_id"), card.get("text"))

    # ---------- 공용 helper ----------
    def high_tags(self, card) -> set:
        return _high_tags(card.get("baby_card_id"), card.get("card_id"))

    def all_tags(self, card) -> set:
        return set(repo.get_baby_card_tags(card.get("baby_card_id"), card.get("card_id")))

    def onboarding_match(self, card) -> float:
        text = (card.get("text") or "")
        if text in self.onboarding:
            return 1.0
        if any(kw in text or text in kw for kw in self.onboarding if kw):
            return 0.7
        # 태그 이름 매칭
        for tid in self.all_tags(card):
            t = repo.get_tag(tid)
            if t and t["name"] in self.onboarding:
                return 0.5
        return 0.0

    def cognitive_gap(self, card) -> float:
        priority = card.get("priority") or 2
        difficulty = min(1.0, max(0.0, (priority - 1) / 2.0))     # 1→0(쉬움) .. 3→1(어려움)
        cog = self.cognitive_level_num                           # 온보딩 인지테스트 → 1~5
        capacity = (cog - 1) / 4.0                                # 1→0 .. 5→1
        return abs(difficulty - (1 - capacity))


# =======================================================
# 태그 helper
# =======================================================
def _high_tags(baby_card_id, card_id) -> set:
    """카드의 high 태그 집합 (low 태그는 parent high 로 승격)"""
    tag_ids = repo.get_baby_card_tags(baby_card_id, card_id)
    high = set()
    for tid in tag_ids:
        t = repo.get_tag(tid)
        if not t:
            continue
        if t["tag_level"] == "high":
            high.add(tid)
        elif t.get("parent_tag_id"):
            high.add(t["parent_tag_id"])
    return high


def _low_tags(baby_card_id, card_id) -> set:
    tag_ids = repo.get_baby_card_tags(baby_card_id, card_id)
    return {tid for tid in tag_ids
            if (repo.get_tag(tid) or {}).get("tag_level") == "low"}


def is_bridge(card) -> bool:
    return BRIDGE_TAG_ID in set(repo.get_baby_card_tags(card.get("baby_card_id"), card.get("card_id")))


# =======================================================
# Layer 1 feature 벡터
# =======================================================
def layer1_features(card: dict, ctx: BabyFeatureContext) -> dict:
    bcid = card.get("baby_card_id")
    key = ctx.key_of(card)

    # A. 사용 이력
    c7, c30 = ctx.count_7d.get(bcid, 0), ctx.count_30d.get(bcid, 0)
    f_usage7 = _safe_div(math.log1p(c7), math.log1p(ctx.max_7d) or 1)
    f_usage30 = _safe_div(math.log1p(c30), math.log1p(ctx.max_30d) or 1)
    ratio = _safe_div(c7, c30)
    f_trend = min(1.0, max(0.0, ratio - 0.25 + 0.25))   # 증가 추세일수록 ↑
    last = card.get("last_used_at")
    h = (ctx.now - last).total_seconds() / 3600 if last else 1e9
    f_recency = math.exp(-h / 24)
    f_entropy = _hour_entropy(ctx.hour_dist.get(bcid, {}))

    # B. 문장 완성 품질
    in_sent = ctx.in_sentence.get(key, 0)
    clicks = ctx.total_count.get(bcid, 0)
    f_completion = min(1.0, _safe_div(in_sent, clicks)) if clicks else (1.0 if in_sent else 0.0)
    pos_list = ctx.positions.get(key, [])
    f_avg_pos = _safe_div(sum(pos_list), len(pos_list)) if pos_list else 0.5

    # C. 부모·시스템 신호
    f_fav = 1.0 if card.get("is_favorite") else 0.0
    f_source = SOURCE_WEIGHT.get(card.get("source", "system_default"), 0.5)
    priority = card.get("priority") or 2
    f_priority = 1.0 / priority

    # D. 의미 풍부도
    f_tagconf = repo.get_tag_confidence_avg(bcid, card.get("card_id"))
    high = _high_tags(bcid, card.get("card_id"))
    f_coverage = _safe_div(len(high), 6)   # 전체 high 태그 6종(범용 제외) 기준
    f_centrality = _safe_div(len(ctx.partners.get(key, set())), ctx.distinct_keys - 1)

    # E. 아동 맥락
    f_onboard = ctx.onboarding_match(card)
    f_cog_gap = ctx.cognitive_gap(card)

    return {
        "usage_count_7d": f_usage7, "usage_count_30d": f_usage30, "usage_trend": f_trend,
        "recency": f_recency, "time_diversity_entropy": f_entropy,
        "sentence_completion_rate": f_completion, "avg_sentence_position": f_avg_pos,
        "is_favorite": f_fav, "source_weight": f_source, "priority": f_priority,
        "tag_confidence_avg": f_tagconf, "tag_coverage": f_coverage,
        "co_occurrence_centrality": f_centrality,
        "onboarding_match_score": f_onboard, "cognitive_difficulty_gap": f_cog_gap,
    }


def _hour_entropy(hour_counts: dict) -> float:
    total = sum(hour_counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for n in hour_counts.values():
        p = n / total
        h -= p * math.log(p)
    return h / math.log(24)   # 0~1 정규화


# =======================================================
# Layer 2 feature 벡터  (선택 카드 → 후보 카드)
# =======================================================
def layer2_features(selected: dict, cand: dict, ctx: BabyFeatureContext,
                    runtime: dict | None = None) -> dict:
    runtime = runtime or {}
    skey = ctx.key_of(selected) if selected else None
    ckey = ctx.key_of(cand)
    cbcid = cand.get("baby_card_id")

    # A. 후보 자체
    f_sys = min(1.0, repo.get_system_score(cbcid, cand.get("card_id"), cand.get("text")))
    f_csource = SOURCE_WEIGHT.get(cand.get("source", "system_default"), 0.5)

    # B. 두 카드 관계
    if skey is not None:
        cooc = ctx.cooc.get(frozenset((skey, ckey)), 0)
        f_cooc = _safe_div(math.log1p(cooc), math.log1p(max(ctx.cooc.values(), default=0)) or 1)
        f_pmi = _pmi(ctx, skey, ckey)
        seq = ctx.seq.get((skey, ckey), 0)
        f_seq = _safe_div(seq, ctx.prev_total.get(skey, 0))
        sh, ch = ctx.high_tags(selected), ctx.high_tags(cand)
        sl, cl = _low_tags(selected.get("baby_card_id"), selected.get("card_id")), \
                 _low_tags(cand.get("baby_card_id"), cand.get("card_id"))
        f_high = _safe_div(len(sh & ch), max(1, len(sh | ch)))
        f_low = _safe_div(len(sl & cl), max(1, len(sl | cl)))
        f_postrans = _pos_transition_prob(ctx, _norm_pos(selected.get("pos")), _norm_pos(cand.get("pos")))
    else:
        f_cooc = f_pmi = f_seq = f_high = f_low = 0.0
        f_postrans = 0.5

    # C. 시간·세션
    last = cand.get("last_used_at")
    h = (ctx.now - last).total_seconds() / 3600 if last else 1e9
    f_recency = math.exp(-h / 24)
    f_tod = _slot_match(ctx.hour_dist.get(cbcid, {}), ctx.now.hour)
    f_dow = _slot_match(ctx.weekday_dist.get(cbcid, {}), ctx.now.weekday())
    f_session = min(1.0, runtime.get("session_length", 1) / 5.0)

    # D. 아동 개별
    f_pers = _safe_div(ctx.total_count.get(cbcid, 0), ctx.max_total or 1)
    f_cfav = 1.0 if cand.get("is_favorite") else 0.0
    cpos = _norm_pos(cand.get("pos"))
    f_pospref = _safe_div(ctx.pos_count.get(cpos, 0), ctx.total_words) if cpos else 0.0

    # E. 인지 적합도
    f_cogmatch = 1.0 - ctx.cognitive_gap(cand)
    f_ctagconf = repo.get_tag_confidence_avg(cbcid, cand.get("card_id"))

    # F. 구조적 힌트
    f_bridge = 1.0 if is_bridge(cand) else 0.0
    f_stage = float(runtime.get("filter_stage_passed", 1.0))
    f_maxpos = min(1.0, runtime.get("max_selectable_position", 4) / 4.0)

    return {
        "cand_system_score": f_sys, "cand_source_weight": f_csource,
        "co_occurrence_count": f_cooc, "co_occurrence_pmi": f_pmi,
        "sequential_probability": f_seq, "high_tag_overlap": f_high,
        "low_tag_overlap": f_low, "pos_transition_prob": f_postrans,
        "cand_recency_decay": f_recency, "time_of_day_match": f_tod,
        "day_of_week_match": f_dow, "session_length_so_far": f_session,
        "cand_personal_usage": f_pers, "cand_is_favorite": f_cfav,
        "child_pos_preference": f_pospref,
        "cognitive_match": f_cogmatch, "cand_tag_confidence_avg": f_ctagconf,
        "is_bridge_card": f_bridge, "filter_stage_passed": f_stage,
        "max_selectable_position": f_maxpos,
    }


def _pmi(ctx, a, b):
    cooc = ctx.cooc.get(frozenset((a, b)), 0)
    if cooc == 0 or ctx.total_sentences == 0:
        return 0.0
    p_ab = cooc / ctx.total_sentences
    p_a = ctx.unigram.get(a, 0) / ctx.total_sentences
    p_b = ctx.unigram.get(b, 0) / ctx.total_sentences
    if p_a == 0 or p_b == 0:
        return 0.0
    pmi = math.log(p_ab / (p_a * p_b))
    return min(1.0, max(0.0, pmi / 3.0))   # 정규화


def _pos_transition_prob(ctx, prev_pos, next_pos):
    if not prev_pos or not next_pos:
        return 0.5
    total = ctx.pos_prev_total.get(prev_pos, 0)
    if total == 0:
        return 0.5
    return ctx.pos_transition.get((prev_pos, next_pos), 0) / total


def _slot_match(dist: dict, current_slot: int) -> float:
    total = sum(dist.values())
    if total == 0:
        return 0.0
    return dist.get(current_slot, 0) / total
