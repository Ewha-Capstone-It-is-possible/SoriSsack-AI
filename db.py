"""
db.py
--------------
실제 PostgreSQL 연결 및 데이터 조회.
dummy_data.py의 함수 시그니처를 그대로 유지하므로
recommend.py에서 import 경로만 바꾸면 됨.

환경변수: .env 파일에 DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD 설정
"""

import os
from datetime import datetime
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool
from dotenv import load_dotenv

load_dotenv()

# -------------------------------------------------------
# 연결 풀
# -------------------------------------------------------

_pool: Optional[SimpleConnectionPool] = None


def _get_pool() -> SimpleConnectionPool:
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            dbname=os.getenv("DB_NAME", "sorisak"),
            user=os.getenv("DB_USER", "sorisak_user"),
            password=os.getenv("DB_PASSWORD", ""),
        )
    return _pool


def _conn():
    return _get_pool().getconn()


def _release(conn):
    _get_pool().putconn(conn)


# -------------------------------------------------------
# 내부 헬퍼
# -------------------------------------------------------

# DB의 part_of_speech는 모두 소문자('noun','verb','adjective')
# recommend.py의 POS_TRANSITION도 소문자를 사용하므로 그대로 반환
def _normalize_pos(pos: Optional[str]) -> Optional[str]:
    return pos.lower() if pos else None


# scoring_config의 feature_key를 recommend.py가 아는 이름으로 매핑
_FEATURE_KEY_MAP = {
    "usage_count_7d": "usage_count",
    "recency_days":   "recency",
    "time_diversity": "time_diversity",
    # 아직 미구현 feature는 매핑하지 않음 → compute_system_score에서 자동 스킵
}


# -------------------------------------------------------
# get_candidate_cards
# -------------------------------------------------------

def get_candidate_cards(baby_id: int) -> list[dict]:
    """
    아동의 추천 후보 카드 목록 반환.
    = 활성 baby_card + 아직 baby_card에 없는 card_master 기본 카드

    반환 형식 (dummy_data와 동일):
      {baby_card_id, baby_id, card_id, text, type(=part_of_speech),
       last_used_at, priority, is_active}
    """
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            # 1) 활성 baby_card
            cur.execute("""
                SELECT
                    bc.baby_card_id,
                    bc.baby_id,
                    bc.card_id,
                    bc.text,
                    bc.part_of_speech AS type,
                    bc.last_used_at,
                    bc.priority,
                    bc.is_active
                FROM baby_card bc
                WHERE bc.baby_id = %s
                  AND bc.is_active = TRUE
                  AND bc.status   != 'off'
            """, (baby_id,))
            baby_cards = [dict(r) for r in cur.fetchall()]

            # 이미 baby_card에 연결된 card_id 집합
            linked_card_ids = {
                r["card_id"] for r in baby_cards if r["card_id"] is not None
            }

            # 2) 아직 baby_card에 없는 card_master 기본 카드
            cur.execute("""
                SELECT
                    NULL::INT     AS baby_card_id,
                    %s::INT       AS baby_id,
                    cm.card_id,
                    cm.base_text  AS text,
                    cm.part_of_speech AS type,
                    NULL::TIMESTAMP AS last_used_at,
                    cm.priority,
                    cm.is_active
                FROM card_master cm
                WHERE cm.is_active = TRUE
                  AND cm.card_id NOT IN (
                      SELECT card_id
                      FROM baby_card
                      WHERE baby_id = %s
                        AND card_id IS NOT NULL
                  )
            """, (baby_id, baby_id))
            base_cards = [dict(r) for r in cur.fetchall()]

        result = baby_cards + base_cards
        # part_of_speech 소문자 정규화
        for c in result:
            c["type"] = _normalize_pos(c["type"])
        return result

    finally:
        _release(conn)


# -------------------------------------------------------
# get_baby_basic — 아동 기본정보(성별) : 이미지 개인화용
# -------------------------------------------------------

def get_baby_basic(baby_id: int) -> dict:
    """아동 기본 정보(성별 등). 이미지 캐릭터 개인화(성별·고정 시드)에 사용."""
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT baby_id, baby_name, sex, birth "
                "FROM baby_basic_information WHERE baby_id = %s",
                (baby_id,),
            )
            row = cur.fetchone()
            return dict(row) if row else {}
    finally:
        _release(conn)


# -------------------------------------------------------
# 아바타 외모 설정 (baby_avatar_profile.config_json) — 이미지 개인화 영속화
# -------------------------------------------------------

def get_avatar_config(baby_id: int) -> dict:
    """저장된 외모 설정(config_json). 없으면 {}."""
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT config_json FROM baby_avatar_profile "
                "WHERE baby_id = %s AND is_active = TRUE ORDER BY avatar_id DESC LIMIT 1",
                (baby_id,),
            )
            row = cur.fetchone()
            cfg = row["config_json"] if row else None
            return cfg if isinstance(cfg, dict) else {}
    finally:
        _release(conn)


def upsert_avatar_config(baby_id: int, config_json: dict) -> None:
    """외모 설정 저장(없으면 생성). base_avatar_image_url 은 NOT NULL → 빈값."""
    conn = _conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT avatar_id FROM baby_avatar_profile "
                "WHERE baby_id = %s AND is_active = TRUE ORDER BY avatar_id DESC LIMIT 1",
                (baby_id,),
            )
            row = cur.fetchone()
            payload = psycopg2.extras.Json(config_json)
            # avatar_type 은 CHECK 제약: default_male | default_female | custom_photo
            sex = str(config_json.get("sex") or "").upper()
            avatar_type = "default_female" if sex.startswith("F") else "default_male"
            if row:
                cur.execute(
                    "UPDATE baby_avatar_profile "
                    "SET config_json = %s, avatar_type = %s, updated_at = now() "
                    "WHERE avatar_id = %s",
                    (payload, avatar_type, row[0]),
                )
            else:
                cur.execute(
                    "INSERT INTO baby_avatar_profile "
                    "(baby_id, avatar_type, base_avatar_image_url, config_json, is_active) "
                    "VALUES (%s, %s, %s, %s, TRUE)",
                    (baby_id, avatar_type, "", payload),
                )
            conn.commit()
    finally:
        _release(conn)


# -------------------------------------------------------
# get_card_master
# -------------------------------------------------------

def get_card_master(card_id: int) -> Optional[dict]:
    """card_master 단건 조회"""
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT card_id, base_text, part_of_speech, is_active, priority
                FROM card_master
                WHERE card_id = %s
            """, (card_id,))
            row = cur.fetchone()
            if row is None:
                return None
            r = dict(row)
            r["part_of_speech"] = _normalize_pos(r["part_of_speech"])
            return r
    finally:
        _release(conn)


# -------------------------------------------------------
# get_vocab_logs
# -------------------------------------------------------

def get_vocab_logs(baby_id: int, limit: int = 200) -> list[dict]:
    """
    최근 vocab log 조회.
    반환 형식: {baby_card_id, card_id, text_snapshot, used_at}
    """
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT baby_card_id, card_id, text_snapshot, used_at
                FROM baby_vocab_log
                WHERE baby_id = %s
                ORDER BY used_at DESC
                LIMIT %s
            """, (baby_id, limit))
            return [dict(r) for r in cur.fetchall()]
    finally:
        _release(conn)


# -------------------------------------------------------
# get_scoring_config
# -------------------------------------------------------

def get_scoring_config(baby_id: int, target_type: str = "card") -> list[dict]:
    """
    scoring_config 조회 (전역 + 아동별 오버라이드 병합).
    반환 형식: [{feature_key, weight}, ...]
    feature_key는 recommend.py가 아는 이름으로 매핑됨.
    """
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # 전역 설정
            cur.execute("""
                SELECT feature_key, weight
                FROM scoring_config
                WHERE target_type = %s
                  AND scope = 'global'
                  AND enabled = TRUE
            """, (target_type,))
            global_cfg = {r["feature_key"]: r["weight"] for r in cur.fetchall()}

            # 아동별 오버라이드
            cur.execute("""
                SELECT feature_key, weight
                FROM scoring_config
                WHERE target_type = %s
                  AND scope = 'baby'
                  AND baby_id = %s
                  AND enabled = TRUE
            """, (target_type, baby_id))
            for r in cur.fetchall():
                global_cfg[r["feature_key"]] = r["weight"]  # 오버라이드

        # feature_key 매핑 후 반환
        result = []
        for db_key, weight in global_cfg.items():
            mapped_key = _FEATURE_KEY_MAP.get(db_key)
            if mapped_key:
                result.append({"feature_key": mapped_key, "weight": weight})

        return result
    finally:
        _release(conn)


# -------------------------------------------------------
# get_baby_card_tags
# -------------------------------------------------------

def get_baby_card_tags(baby_card_id: Optional[int], card_id: Optional[int]) -> list[int]:
    """
    카드에 연결된 tag_id 목록 반환.
    - baby_card_id가 있으면 baby_card_tag_map 우선 조회
    - 없으면 card_master_tag_map 조회 (card_id 기준)
    """
    conn = _conn()
    try:
        with conn.cursor() as cur:
            if baby_card_id is not None:
                cur.execute("""
                    SELECT tag_id
                    FROM baby_card_tag_map
                    WHERE baby_card_id = %s AND is_active = TRUE
                """, (baby_card_id,))
                rows = cur.fetchall()
                if rows:
                    return [r[0] for r in rows]

            # baby_card에 태그가 없거나 base 카드인 경우 card_master_tag_map 사용
            if card_id is not None:
                cur.execute("""
                    SELECT tag_id
                    FROM card_master_tag_map
                    WHERE card_id = %s AND is_active = TRUE
                """, (card_id,))
                return [r[0] for r in cur.fetchall()]

            return []
    finally:
        _release(conn)


# -------------------------------------------------------
# get_tag
# -------------------------------------------------------

def get_tag(tag_id: int) -> Optional[dict]:
    """tag_master 단건 조회"""
    conn = _conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT tag_id, name, tag_level, parent_tag_id
                FROM tag_master
                WHERE tag_id = %s AND is_active = TRUE
            """, (tag_id,))
            row = cur.fetchone()
            return dict(row) if row else None
    finally:
        _release(conn)
