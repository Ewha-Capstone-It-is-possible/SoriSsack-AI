"""
main.py
--------------
FastAPI 엔드포인트 — Spring 서버(Backend)에서 호출하는 AI 추론 API.

실행:
    pip install -r requirements.txt
    uvicorn main:app --reload --port 8000

엔드포인트:
    GET  /                      헬스 체크
    POST /recommend            단어 추천 (Layer1+Layer2 회귀 → GPT selector)
    POST /sentence             '말하기': 문법 보정 → 이미지 → 음성 → 저장 (멀티모달)
    POST /image                문장 → Stable Diffusion 이미지
    POST /tts                  문장 → Clova Voice 음성
    POST /score/update         Layer1 배치 재계산 (system_score 갱신)
    POST /report               발달 리포트 (5지표 + LLM 해석)
    GET  /report/{baby_id}/pdf 리포트 PDF 다운로드 정보
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

import config
import recommend
import related
import grammar
import image_gen
import tts
import layer1
import report
import onboarding
import repo
import schemas

TAGS_METADATA = [
    {"name": "health", "description": "서버 상태 + 외부 연동(OpenAI/Stable Diffusion/Clova) 활성화 여부"},
    {"name": "recommend", "description": "2-레이어 회귀 + GPT selector 기반 다음 단어 추천"},
    {"name": "multimodal", "description": "‘말하기’ — 선택 단어 → 문장 → 이미지(Stable Diffusion) → 음성(Clova)"},
    {"name": "score", "description": "Layer1 배치 점수(system_score) 재계산"},
    {"name": "report", "description": "발달 리포트(5지표) + 온보딩 인지 평가"},
]

app = FastAPI(
    title="소리싹 AI 추론 API",
    description=(
        "무발화 자폐 아동을 위한 AI 기반 개인맞춤형 의사소통 추론 서버.\n\n"
        "백엔드(SoriSsack-Back, FastAPI :8000)가 `httpx` 로 호출하는 내부 AI 서버다. "
        "프론트(React Native)는 이 서버를 직접 호출하지 않고, 응답에 담긴 "
        "`image_url`/`audio_url`(정적 미디어)만 `/generated/...` 에서 직접 로드한다.\n\n"
        "구성: 2-레이어 회귀 추천 + GPT selector + Stable Diffusion + Clova TTS + 발달 리포트.\n"
        "외부 키가 없으면 각 단계는 graceful fallback(규칙기반/stub)으로 동작한다."
    ),
    version="2.0.0",
    openapi_tags=TAGS_METADATA,
    contact={"name": "SoriSsack (이화여대 캡스톤)", "url": "http://localhost:8001/docs"},
)

# 생성 미디어(이미지/음성) 정적 서빙: image_gen/tts 가 generated/ 아래에 저장 →
# /generated/... URL 로 프론트가 직접 로드 (config.public_url 이 절대 URL 생성)
os.makedirs(config.IMAGE_OUTPUT_DIR, exist_ok=True)
os.makedirs(config.AUDIO_OUTPUT_DIR, exist_ok=True)
app.mount("/generated", StaticFiles(directory="generated"), name="generated")


@app.get(
    "/",
    response_model=schemas.HealthResponse,
    tags=["health"],
    summary="헬스 체크 + 연동 상태",
    description="서버 상태와 외부 연동 활성화 여부를 반환. 모두 true 여야 실제 GPT/이미지/음성이 동작한다(아니면 stub).",
)
def health_check():
    return {
        "status": "ok",
        "service": "소리싹 단어 추천 API",
        "data_source": config.DATA_SOURCE,
        "integrations": {
            "openai": config.has_openai(),
            "stable_diffusion": config.has_stability(),
            "clova_tts": config.has_clova(),
        },
    }


# -------------------------------------------------------
# 단어 추천
# -------------------------------------------------------
@app.post(
    "/recommend",
    response_model=schemas.RecommendResponse,
    tags=["recommend"],
    summary="다음 단어 추천",
    responses={500: {"model": schemas.ErrorResponse}},
)
def get_recommendations(request: schemas.RecommendRequest):
    """
    선택 카드 기반 다음 단어 추천 (system_score 내림차순, 최대 5개).
    파이프라인: 태그필터(+브릿지) → Layer2 맥락회귀 → GPT selector.
    """
    try:
        return recommend.recommend_words(
            baby_id=request.baby_id,
            selected_baby_card_id=request.selected_baby_card_id,
            selected_card_id=request.selected_card_id,
            top_n=5,
            session_length=request.session_length,
            use_gpt=request.use_gpt,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------
# 관련 단어 (부모 단어추가용 — DB 에 없는 새 단어 GPT 생성)
# -------------------------------------------------------
@app.post(
    "/related-words",
    response_model=schemas.RelatedWordsResponse,
    tags=["recommend"],
    summary="관련 단어 생성 (부모 단어추가용)",
    responses={500: {"model": schemas.ErrorResponse}},
)
def related_words(request: schemas.RelatedWordsRequest):
    """입력 단어/문장과 관련된, DB 에 없는 새 단어 후보를 제안 (GPT)."""
    try:
        items = related.suggest_related(request.text, request.count, request.exclude)
        return {"text": request.text, "related_words": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------
# 문장 완성 + 멀티모달 ('말하기')
# -------------------------------------------------------
@app.post(
    "/sentence",
    response_model=schemas.SentenceResponse,
    tags=["multimodal"],
    summary="말하기: 문장 + 이미지 + 음성",
    description="선택 단어 배열 → 자연스러운 문장 → Stable Diffusion 이미지 + Clova 음성 동시 생성 → DB 저장.",
    responses={500: {"model": schemas.ErrorResponse}},
)
def speak_sentence(request: schemas.SentenceRequest):
    """
    선택 단어 배열 → 자연스러운 문장 → 이미지·음성 동시 생성 → DB 저장.
    """
    try:
        words = [w.model_dump() for w in request.words]
        texts = [w["text"] for w in words]
        level = repo.get_level_info(request.baby_id)

        sentence = grammar.complete_sentence(texts, level)
        image = image_gen.generate_image(sentence, words, request.baby_id)
        audio = tts.synthesize(sentence, request.baby_id)
        avatar = repo.get_avatar_profile(request.baby_id, request.emotion)

        # 자기학습 루프: 로그 + 문장 저장
        for w in words:
            repo.append_vocab_log(request.baby_id, w.get("baby_card_id"),
                                  w.get("card_id"), w.get("text"))
        repo.save_sentence(request.baby_id, words, sentence,
                           image.get("image_url"), audio.get("audio_url"))

        return {
            "baby_id": request.baby_id, "sentence": sentence,
            "image": image, "audio": audio, "avatar": avatar, "saved": True,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/image",
    response_model=schemas.ImageResult,
    tags=["multimodal"],
    summary="이미지만 생성 (Stable Diffusion)",
    responses={500: {"model": schemas.ErrorResponse}},
)
def generate_image(request: schemas.ImageRequest):
    try:
        words = [w.model_dump() for w in request.words] if request.words else None
        return image_gen.generate_image(request.sentence, words, request.baby_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post(
    "/tts",
    response_model=schemas.AudioResult,
    tags=["multimodal"],
    summary="음성만 생성 (Clova Voice)",
    responses={500: {"model": schemas.ErrorResponse}},
)
def generate_tts(request: schemas.TTSRequest):
    try:
        return tts.synthesize(request.text, request.baby_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------
# Layer1 배치 재계산
# -------------------------------------------------------
@app.post(
    "/score/update",
    response_model=schemas.ScoreUpdateResponse,
    tags=["score"],
    summary="Layer1 배치 점수 재계산",
    responses={500: {"model": schemas.ErrorResponse}},
)
def update_scores(baby_id: int):
    """아동의 모든 카드 system_score(Layer1 중요도)를 재계산·저장 (baby_id 는 쿼리 파라미터)."""
    try:
        n = layer1.update_scores(baby_id)
        return {"baby_id": baby_id, "updated_cards": n, "status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------------
# 발달 리포트
# -------------------------------------------------------
@app.post(
    "/report",
    response_model=schemas.ReportResponse,
    tags=["report"],
    summary="발달 리포트 (5지표 + LLM 해석)",
    responses={500: {"model": schemas.ErrorResponse}},
)
def get_report(request: schemas.ReportRequest):
    """발달 리포트: 기간 대비 5지표 변화 + LLM 자연어 해석 + Plotly 차트."""
    try:
        return report.generate_report(request.baby_id, request.period_days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/onboarding/{baby_id}/assessment",
    response_model=schemas.OnboardingResponse,
    tags=["report"],
    summary="온보딩 인지 평가",
    responses={500: {"model": schemas.ErrorResponse}},
)
def get_cognitive_assessment(baby_id: int):
    """온보딩 인지 테스트 영역별 채점 프로파일 + GPT 자연어 평가."""
    try:
        return onboarding.assess_cognition(baby_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/report/{baby_id}/pdf",
    tags=["report"],
    summary="리포트 PDF 다운로드",
    description="reportlab 설치 시 application/pdf 파일 다운로드, 미설치 시 JSON 리포트 반환.",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF 파일 또는 JSON 리포트"},
        500: {"model": schemas.ErrorResponse},
    },
)
def get_report_pdf(baby_id: int, period_days: int = None):
    """리포트 PDF 생성. reportlab 설치 시 파일 다운로드, 미설치 시 JSON 리포트 반환."""
    try:
        result = report.export_pdf(
            baby_id, f"generated/reports/report_{baby_id}.pdf", period_days)
        if result.get("path"):
            from fastapi.responses import FileResponse
            return FileResponse(result["path"], media_type="application/pdf",
                                filename=f"report_{baby_id}.pdf")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
