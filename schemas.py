"""
schemas.py
--------------
FastAPI 요청/응답 Pydantic 스키마.
"""

from typing import Optional
from pydantic import BaseModel


# -------------------------------------------------------
# 추천
# -------------------------------------------------------
class RecommendRequest(BaseModel):
    baby_id: int
    selected_baby_card_id: Optional[int] = None   # 첫 화면이면 None
    session_length: int = 1                        # 현재 세션에서 선택한 카드 수
    use_gpt: bool = True                            # GPT selector 사용 여부

    model_config = {
        "json_schema_extra": {
            "example": {"baby_id": 3, "selected_baby_card_id": 301, "session_length": 1}
        }
    }


class RecommendedWord(BaseModel):
    baby_card_id: Optional[int]
    card_id: Optional[int]
    text: str
    pos: Optional[str]
    system_score: float


class RecommendResponse(BaseModel):
    baby_id: int
    selected_word: Optional[str]
    recommended_words: list[RecommendedWord]


# -------------------------------------------------------
# 문장 완성 / 멀티모달
# -------------------------------------------------------
class WordItem(BaseModel):
    text: str
    pos: Optional[str] = None
    baby_card_id: Optional[int] = None
    card_id: Optional[int] = None


class SentenceRequest(BaseModel):
    baby_id: int
    words: list[WordItem]
    emotion: Optional[str] = "neutral"      # 아바타 감정 (happy/sad/angry/neutral/surprised)

    model_config = {
        "json_schema_extra": {
            "example": {
                "baby_id": 5,
                "words": [{"text": "물", "pos": "noun"}, {"text": "마시다", "pos": "verb"}],
                "emotion": "happy",
            }
        }
    }


class SentenceResponse(BaseModel):
    baby_id: int
    sentence: str
    image: dict
    audio: dict
    avatar: dict
    saved: bool


class ImageRequest(BaseModel):
    sentence: str
    words: Optional[list[WordItem]] = None
    baby_id: Optional[int] = None


class TTSRequest(BaseModel):
    text: str
    baby_id: int


# -------------------------------------------------------
# 리포트
# -------------------------------------------------------
class ReportRequest(BaseModel):
    baby_id: int
    period_days: Optional[int] = None   # None=AUTO(가용 로그 절반 분할), 예: 30 → 최근 30일 vs 이전 30일

    model_config = {
        "json_schema_extra": {"example": {"baby_id": 3, "period_days": 30}}
    }
