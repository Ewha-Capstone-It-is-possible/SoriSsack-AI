"""
main.py
--------------
FastAPI 엔드포인트.
Spring 서버에서 POST /recommend 호출하면 추천 단어 반환.

실행 방법:
    pip install fastapi uvicorn
    uvicorn main:app --reload --port 8000

Spring 서버 연동:
    POST http://localhost:8000/recommend
    Body: {"baby_id": 3, "selected_baby_card_id": 501}
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from recommend import recommend_words

app = FastAPI(
    title="소리싹 단어 추천 API",
    description="무발화 자폐 아동을 위한 AI 기반 개인맞춤형 단어 추천 시스템",
    version="1.0.0",
)


# -------------------------------------------------------
# Request / Response 스키마
# -------------------------------------------------------

class RecommendRequest(BaseModel):
    baby_id: int
    selected_baby_card_id: Optional[int] = None  # 첫 선택이면 None

    class Config:
        json_schema_extra = {
            "example": {
                "baby_id": 3,
                "selected_baby_card_id": 501  # "물" 카드 선택
            }
        }


class RecommendedWord(BaseModel):
    baby_card_id: Optional[int]   # None이면 아직 baby_card에 없는 card_master 기본 카드
    card_id: Optional[int]        # card_master의 card_id. None이면 부모가 추가한 커스텀 카드
    text: str
    pos: Optional[str]
    system_score: float


class RecommendResponse(BaseModel):
    baby_id: int
    selected_word: Optional[str]
    recommended_words: list[RecommendedWord]

    class Config:
        json_schema_extra = {
            "example": {
                "baby_id": 3,
                "selected_word": "장난감",
                "recommended_words": [
                    {"baby_card_id": 302, "card_id": 40,   "text": "사주세요",   "pos": "verb",      "system_score": 1.63},
                    {"baby_card_id": 303, "card_id": 41,   "text": "갖고싶어요", "pos": "adjective", "system_score": 1.57},
                    {"baby_card_id": 304, "card_id": 42,   "text": "놀고싶어요", "pos": "verb",      "system_score": 1.52},
                    {"baby_card_id": None, "card_id": 36,  "text": "블록",       "pos": "Noun",      "system_score": 0.50},
                    {"baby_card_id": None, "card_id": 38,  "text": "공",         "pos": "Noun",      "system_score": 0.50},
                ]
            }
        }


# -------------------------------------------------------
# 엔드포인트
# -------------------------------------------------------

@app.get("/")
def health_check():
    return {"status": "ok", "service": "소리싹 단어 추천 API"}


@app.post("/recommend", response_model=RecommendResponse)
def get_recommendations(request: RecommendRequest):
    """
    단어 추천 API.

    - **baby_id**: 아동 ID
    - **selected_baby_card_id**: 방금 선택한 카드 ID (첫 선택이면 생략)

    Returns: 추천 단어 4~5개 (system_score 내림차순)
    """
    try:
        result = recommend_words(
            baby_id=request.baby_id,
            selected_baby_card_id=request.selected_baby_card_id,
            top_n=5,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/score/update")
def update_scores(baby_id: int):
    """
    (예정) 아동의 모든 카드 system_score를 재계산하여 baby_card 테이블에 반영.
    현재는 stub - DB 연결 후 구현 예정.
    """
    # TODO: DB 연결 후
    # 1. get_vocab_logs(baby_id) 로 로그 가져오기
    # 2. 각 baby_card에 대해 compute_system_score() 실행
    # 3. baby_card.system_score UPDATE 쿼리 실행
    return {"message": f"baby_id={baby_id} score update 예정 (DB 연결 후 구현)"}