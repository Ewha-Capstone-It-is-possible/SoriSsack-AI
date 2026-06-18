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
    selected_baby_card_id: Optional[int] = None   # 첫 화면이면 None (개인 카드)
    selected_card_id: Optional[int] = None         # 공용(마스터) 카드 선택 시 (baby_card_id 없음)
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


class SceneInfo(BaseModel):
    """이미지 생성을 위해 문장에서 추출한 장면 요소."""
    object: Optional[str] = None
    action: Optional[str] = None
    actor: Optional[str] = None


class ImageResult(BaseModel):
    """Stable Diffusion 이미지 생성 결과. 키 미설정 시 image_url=null (stub)."""
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    prompt: Optional[str] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    scene: Optional[SceneInfo] = None
    status: str


class AudioResult(BaseModel):
    """Clova Voice TTS 결과. 키 미설정 시 audio_url=null (stub)."""
    audio_url: Optional[str] = None
    audio_path: Optional[str] = None
    params: Optional[dict] = None
    status: str


class AvatarResult(BaseModel):
    """아바타 감정 표현."""
    emotion: Optional[str] = None
    image_url: Optional[str] = None


class SentenceResponse(BaseModel):
    baby_id: int
    sentence: str
    image: ImageResult
    audio: AudioResult
    avatar: AvatarResult
    saved: bool

    model_config = {
        "json_schema_extra": {
            "example": {
                "baby_id": 5,
                "sentence": "물을 마시고 싶어요.",
                "image": {
                    "image_url": "http://127.0.0.1:8001/generated/images/img_123.png",
                    "prompt": "cute cartoon illustration ...",
                    "negative_prompt": "text, letters, watermark ...",
                    "seed": 123,
                    "scene": {"object": "물", "action": "마시다", "actor": "a friendly child character"},
                    "status": "generated",
                },
                "audio": {
                    "audio_url": "http://127.0.0.1:8001/generated/audio/tts_5_ab.mp3",
                    "params": {"speaker": "ndain", "speed": 0, "pitch": 0, "volume": -2},
                    "status": "generated",
                },
                "avatar": {"emotion": "happy", "image_url": "avatars/baby_5_happy.png"},
                "saved": True,
            }
        }
    }


class ImageRequest(BaseModel):
    sentence: str
    words: Optional[list[WordItem]] = None
    baby_id: Optional[int] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "sentence": "물을 마시고 싶어요",
                "words": [{"text": "물", "pos": "noun"}],
                "baby_id": 5,
            }
        }
    }


class TTSRequest(BaseModel):
    text: str
    baby_id: int

    model_config = {
        "json_schema_extra": {"example": {"text": "물을 마시고 싶어요", "baby_id": 5}}
    }


# -------------------------------------------------------
# 리포트
# -------------------------------------------------------
class ReportRequest(BaseModel):
    baby_id: int
    period_days: Optional[int] = None   # None=AUTO(가용 로그 절반 분할), 예: 30 → 최근 30일 vs 이전 30일

    model_config = {
        "json_schema_extra": {"example": {"baby_id": 3, "period_days": 30}}
    }


# -------------------------------------------------------
# 관련 단어 (부모 단어추가용 — DB 에 없는 새 단어 생성)
# -------------------------------------------------------
class RelatedWordsRequest(BaseModel):
    text: str
    count: int = 6
    exclude: list[str] = []   # 이미 DB 에 있는 단어(중복 제외용)

    model_config = {
        "json_schema_extra": {"example": {"text": "주먹밥", "count": 6}}
    }


class RelatedWord(BaseModel):
    text: str
    pos: Optional[str] = None


class RelatedWordsResponse(BaseModel):
    text: str
    related_words: list[RelatedWord]


# -------------------------------------------------------
# 단순 응답 (헬스 / 이미지 / TTS / 스코어 / 리포트 / 온보딩)
# -------------------------------------------------------
class IntegrationStatus(BaseModel):
    openai: bool
    stable_diffusion: bool
    clova_tts: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    data_source: str
    integrations: IntegrationStatus


class ScoreUpdateResponse(BaseModel):
    baby_id: int
    updated_cards: int
    status: str


class ReportResponse(BaseModel):
    """발달 리포트. summary/current_metrics 는 분석 결과(동적 구조)라 dict 로 둔다."""
    baby_id: int
    period: str
    summary: dict        # 기간 대비 5지표 비교
    current_metrics: dict  # 현재 구간 상세 5지표
    interpretation: str
    charts: Optional[dict] = None  # Plotly JSON (with_charts 시)

    model_config = {
        "json_schema_extra": {
            "example": {
                "baby_id": 3,
                "period": "2026-04-01 ~ 2026-04-30",
                "summary": {"vocabulary_diversity": "+12%", "avg_sentence_length": "+0.3"},
                "current_metrics": {"unique_total": 22, "avg": 2.3, "top5_words": ["사주세요", "장난감"]},
                "interpretation": "이번 기간 동안 단어 다양성이 늘었고 ...",
                "charts": {"category_distribution": {"_plotly_": "..."}},
            }
        }
    }


class OnboardingResponse(BaseModel):
    """온보딩 인지 평가: profile(영역별 채점) + assessment(GPT 자연어 해석)."""
    profile: dict
    assessment: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "profile": {
                    "baby_id": 3,
                    "correct": 4,
                    "total": 5,
                    "overall_level": 4,
                    "weak_dimensions": ["분류"],
                    "strong_dimensions": ["색 인지", "수 인지"],
                },
                "assessment": "강한 영역은 색·수 인지입니다. 분류 영역은 연습이 도움 될 수 있습니다 ...",
            }
        }
    }


class ErrorResponse(BaseModel):
    detail: str
