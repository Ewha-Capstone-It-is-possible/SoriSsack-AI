"""
config.py
--------------
환경변수 기반 설정 로딩 (.env).

핵심 스위치:
  DATA_SOURCE = "dummy" | "db"   → repo.py가 어느 데이터 레이어를 쓸지 결정
  OPENAI_API_KEY                 → GPT selector / 문법보정 / 리포트 해석
  STABILITY_API_KEY              → Stable Diffusion 이미지 생성
  CLOVA_*                        → Naver Clova Voice TTS

외부 키가 없으면 각 모듈은 graceful fallback으로 동작 → 데모는 항상 돌아감.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# -------------------------------------------------------
# 데이터 소스
# -------------------------------------------------------
DATA_SOURCE = _get("DATA_SOURCE", "dummy").lower()   # dummy | db

# -------------------------------------------------------
# OpenAI (GPT selector / grammar / report 해석)
# -------------------------------------------------------
OPENAI_API_KEY = _get("OPENAI_API_KEY")
OPENAI_MODEL_SELECTOR = _get("OPENAI_MODEL_SELECTOR", "gpt-4o-mini")
OPENAI_MODEL_GRAMMAR = _get("OPENAI_MODEL_GRAMMAR", "gpt-4o-mini")
OPENAI_MODEL_REPORT = _get("OPENAI_MODEL_REPORT", "gpt-4o-mini")

# -------------------------------------------------------
# Stable Diffusion (Stability AI 호환)
# -------------------------------------------------------
STABILITY_API_KEY = _get("STABILITY_API_KEY")
STABILITY_API_URL = _get(
    "STABILITY_API_URL",
    "https://api.stability.ai/v2beta/stable-image/generate/core",
)
IMAGE_OUTPUT_DIR = _get("IMAGE_OUTPUT_DIR", "generated/images")

# -------------------------------------------------------
# Naver Clova Voice (TTS)
# -------------------------------------------------------
CLOVA_CLIENT_ID = _get("CLOVA_CLIENT_ID")
CLOVA_CLIENT_SECRET = _get("CLOVA_CLIENT_SECRET")
CLOVA_TTS_URL = _get(
    "CLOVA_TTS_URL",
    "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts",
)
AUDIO_OUTPUT_DIR = _get("AUDIO_OUTPUT_DIR", "generated/audio")

# -------------------------------------------------------
# 모델 가중치 저장 경로 (Layer1/Layer2 학습 결과)
# -------------------------------------------------------
MODEL_DIR = _get("MODEL_DIR", "models")

# -------------------------------------------------------
# 생성 미디어(이미지/음성) 정적 서빙 base URL
#   image_gen / tts 가 저장한 파일을 프론트가 로드할 수 있도록 절대 URL 로 변환한다.
#   /generated 경로가 generated/ 디렉터리에 매핑된다(main.py StaticFiles).
#   실기기 데모 시 LAN IP 로 바꾼다. 예: http://192.168.0.10:8001
# -------------------------------------------------------
PUBLIC_BASE_URL = _get("AI_PUBLIC_BASE_URL", "http://127.0.0.1:8001").rstrip("/")


def public_url(path: str) -> str:
    """로컬 저장 경로(generated/...)를 정적 서빙 절대 URL 로 변환."""
    rel = str(path).lstrip("./").lstrip("/")
    return f"{PUBLIC_BASE_URL}/{rel}"


def has_openai() -> bool:
    return bool(OPENAI_API_KEY)


def has_stability() -> bool:
    return bool(STABILITY_API_KEY)


def has_clova() -> bool:
    return bool(CLOVA_CLIENT_ID and CLOVA_CLIENT_SECRET)
