# SoriSsack-AI (소리쌕 AI 추론 서버)

무발화(minimally verbal) 자폐 아동을 위한 **AI 기반 개인맞춤형 AAC(보완대체의사소통)** 추론 서버.

아동의 사용 이력·개인 특성을 기반으로 다음 단어를 예측·추천하고, 선택한 단어를
**자연스러운 문장 → 이미지 → 음성**의 멀티모달 표현으로 변환하며, 사용 데이터를
분석해 보호자용 발달 리포트·감정일기를 생성한다.

> 소리쌕 프로젝트는 3개 저장소로 구성된다.
> - **SoriSsack-AI** (본 저장소) — AI 추론 서버 (FastAPI, 포트 8001)
> - **SoriSsack-Back** — 백엔드 API 서버 (FastAPI, 포트 8000). 본 AI 서버를 호출한다.
> - **SoriSsak-FE** — 프론트엔드 앱 (React Native / Expo)
>
> 프론트는 백엔드만 호출하고, 백엔드가 본 AI 서버를 내부 호출한다.

---

## 1. 프로젝트 설명

핵심은 **2-레이어 선형회귀 추천 + GPT 보조**이다.

```
아동이 카드 선택 ("물")
        │
[STEP 1] 태그 의미 필터 (tags.py)        — 의미 연관 후보 추출
[STEP 2] 품사 전이                       — Layer2 feature 로 반영
[STEP 3] Layer 2 맥락 회귀 (layer2.py)   — (선택카드, 후보카드) 실시간 점수
[STEP 4] GPT selector (gpt_selector.py)  — 상위 후보 4~5개 선별(새 단어 생성 금지)
        │
   추천 단어 4~5개
```

- **Layer 1** (`layer1.py`, 오프라인) — 카드 중요도를 feature 15개로 회귀. 결과를 `baby_card.system_score`에 저장.
- **Layer 2** (`layer2.py`, 실시간) — 다음 후보 점수를 feature 20개로 회귀.
- **GPT는 보조** — 회귀가 메인, GPT는 selector·문법보정·리포트/일기 해석에만 제한적으로 사용.
- 회귀 가중치는 `train.py`로 학습(scikit-learn)해 `models/*.json`에 저장하고, 없으면 prior 가중치로 **항상 동작**한다.

### 멀티모달 (말하기)

`POST /sentence` 한 번에: ① 문법 보정(GPT) → ② 이미지(Stable Diffusion) → ③ 음성(Clova Voice).

이미지 개인화(`image_gen.py`):
- **아동별 고정 외형**(성별·선호 색상·외형 묘사)을 DB(`baby_avatar_profile`)에 저장해 모든 문장에서 동일 캐릭터로 표현.
- **seed를 (아동·문장·색) 기준으로 결정론적 고정** → 동일 문장은 항상 동일 이미지 재현(시각 일관성) + S3 캐싱으로 재사용.
- **GPT 의도 분류 → 동작 포즈 매핑**으로 문장 의미에 맞는 동작 생성. 자폐 친화 스타일(단순·명확·저자극), AAC 픽토그램 자료 **ARASAAC** 참고.

### 발달 리포트 / 감정일기

- `POST /report/insight` — 통계(많이 쓴 단어·문장·감정) → GPT 자연어 해석.
- `POST /report/charts` — 통계를 막대/도넛 **PNG 그래프**로 렌더(matplotlib) → S3.
- `POST /emotion-diary` — 그날 사용 문장 → 아이의 하루·감정 일기 생성(GPT).

> 외부 키(OpenAI / Stability / Clova / AWS)가 없으면 각 단계는 graceful fallback(규칙기반/stub)으로
> 동작하므로 **키 없이도 데모가 가능**하다.

---

## 2. 소스코드 설명

| 파일 | 역할 |
|------|------|
| `main.py` | FastAPI 엔드포인트(추천/말하기/이미지/음성/리포트/감정일기/온보딩) |
| `schemas.py` | 요청/응답 Pydantic 스키마 |
| `config.py` | 환경변수 로딩 + 외부 연동 키 유무 판별 |
| `repo.py` | **데이터 파사드** — `DATA_SOURCE`로 dummy↔db 전환 |
| `db.py` | PostgreSQL 데이터 접근 |
| `dummy_data.py` / `dummy_extra.py` | 인메모리 더미(샘플) 데이터 |
| `recommend.py` | 추천 파이프라인 오케스트레이션 |
| `tags.py` | STEP1 태그 필터 |
| `features.py` | Layer1(15)/Layer2(20) feature 추출 |
| `layer1.py` / `layer2.py` | 카드 중요도 / 맥락 랭킹 회귀 |
| `linmodel.py` | 선형회귀 컨테이너(JSON 저장/로드) |
| `train.py` | 오프라인 회귀 학습(scikit-learn) |
| `gpt_selector.py` / `grammar.py` | GPT 단어 selector / 문법 보정 |
| `image_gen.py` | Stable Diffusion 이미지 생성(개인화·캐싱) |
| `tts.py` | Naver Clova Voice TTS |
| `s3.py` | 생성 미디어 S3 업로드 |
| `charts.py` | 리포트 그래프 PNG 렌더(matplotlib) |
| `insights.py` | 리포트 GPT 해석 + 감정일기 |
| `analysis.py` / `report.py` | 발달 지표 분석(pandas/sklearn) / 리포트 |
| `onboarding.py` | 온보딩 인지 평가 |
| `cards.py` | 후보 카드 enrich 유틸 |
| `test_recommend.py` | 서버 없이 추천 로직 단위 테스트 |

---

## 3. How to build / install

전제: **Python 3.11+**

```bash
# 1) 저장소 클론
git clone https://github.com/Ewha-Capstone-It-is-possible/SoriSsack-AI.git
cd SoriSsack-AI

# 2) 가상환경 + 의존성 설치
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

# 3) 환경변수 파일 작성 (.env.example 복사)
cp .env.example .env
#   - 기본값 DATA_SOURCE=dummy 이면 DB·외부키 없이 바로 동작
#   - 실제 추천/멀티모달을 쓰려면 .env 에 DB / OPENAI / STABILITY / CLOVA / S3 값 입력

# 4) (선택) 회귀 모델 학습 — 없으면 prior 가중치로 동작
python train.py
```

### 실행

```bash
uvicorn main:app --host 0.0.0.0 --port 8001
# Swagger UI:  http://localhost:8001/docs
```

---

## 4. How to test

```bash
# (1) 서버 없이 추천 로직 단위 테스트
python test_recommend.py

# (2) 서버 실행 후 API 호출 테스트
uvicorn main:app --port 8001
curl http://localhost:8001/            # 헬스체크 + 외부 연동 활성화 여부

# 단어 추천
curl -X POST http://localhost:8001/recommend \
  -H "Content-Type: application/json" \
  -d '{"baby_id": 3, "selected_baby_card_id": 301}'

# 말하기(문장+이미지+음성)
curl -X POST http://localhost:8001/sentence \
  -H "Content-Type: application/json" \
  -d '{"baby_id": 3, "words": [{"text":"물","pos":"noun"}], "emotion":"happy"}'
```

- `GET /docs`(Swagger)에서 모든 엔드포인트를 직접 실행·검증할 수 있다.
- 외부 키가 없으면 이미지/음성은 stub(또는 fallback)으로 응답하므로 테스트 자체는 항상 통과한다.

---

## 5. 샘플 데이터 (Sample / proto data)

- **`dummy_data.py`, `dummy_extra.py`** — DB 없이 동작하기 위한 인메모리 샘플 데이터(아동·카드·로그·태그·음성/아바타 프로필 등). `DATA_SOURCE=dummy`(기본값)에서 사용된다. → **별도 DB 설치 없이 clone 후 바로 재현 가능**.
- **`models/layer1.json`, `models/layer2.json`** — 사전 학습된 회귀 가중치(실험 결과물). 없어도 prior 가중치로 동작한다.
- 생성 결과 예시(이미지/음성)는 실행 시 `generated/`(로컬) 또는 S3에 저장된다.

---

## 6. Database / 사용 데이터

- **PostgreSQL** (`DATA_SOURCE=db`) — 운영 시 사용. 접속 정보는 `.env`(DB_HOST/PORT/NAME/USER/PASSWORD).
  주요 테이블: `baby_basic_information`, `baby_card`, `card_master`, `baby_vocab_log`,
  `sentence_master`, `scoring_config`, `tag_master`, `baby_avatar_profile` 등.
- 데모/개발 시에는 위 샘플 데이터(`DATA_SOURCE=dummy`)로 DB 없이 동작한다.
- 생성 미디어(이미지·음성)는 `S3_BUCKET` 설정 시 **AWS S3**에 저장(공개 읽기), 미설정 시 로컬 `generated/`에 저장.

---

## 7. 사용한 오픈소스 / 외부 서비스

| 구분 | 사용 |
|------|------|
| 웹 프레임워크 | FastAPI, Uvicorn, Pydantic |
| 머신러닝/분석 | scikit-learn, NumPy, pandas |
| 시각화 | matplotlib, plotly, reportlab |
| DB | psycopg2 (PostgreSQL) |
| 스토리지 | boto3 (AWS S3) |
| 생성형 AI | OpenAI API(GPT), Stability AI(Stable Diffusion), Naver Clova Voice(TTS) |
| 참고 자료 | ARASAAC (AAC 공개 픽토그램, 이미지 스타일 레퍼런스) |

---

## 라이선스 / 비고

- 이화여자대학교 캡스톤디자인 프로젝트.
- 외부 API 키는 저장소에 포함되지 않는다(`.env`는 `.gitignore` 처리). `.env.example` 참고.
