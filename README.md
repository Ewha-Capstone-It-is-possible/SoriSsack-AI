# SoriSsack-AI (소리쌕 AI)

무발화(minimally verbal) 자폐 아동을 위한 **AI 기반 개인맞춤형 AAC(보완대체의사소통)** 추론 서버.

아동의 사용 이력·개인 특성을 기반으로 다음 단어를 예측·추천하고, 선택한 단어를
**자연스러운 문장 → 이미지 → 음성**의 멀티모달 표현으로 변환하며, 사용 데이터를
분석해 보호자·교사용 발달 리포트를 생성한다.

> 2차 보고서 + "AI 1번 기능" 설계 문서를 그대로 코드로 구현한 버전(v2.0).

---

## 핵심 아키텍처: 2-레이어 회귀 + GPT 보조

```
아동이 카드 선택 ("물")
        │
        ▼
[STEP 1] 태그 의미 필터  (tags.py)
   ① multi high-tag 교집합   ② 브릿지(범용) 카드 합류   ③ 3개 미만 fallback
        │
        ▼
[STEP 2] 품사 전이        → hard-drop 대신 Layer2 feature(pos_transition_prob)로 soft 반영
        │
        ▼
[STEP 3] Layer 2 맥락 회귀 (layer2.py)  ← Layer 1 점수를 feature 로 입력
   (선택카드, 후보카드) 쌍의 feature 20개 → 실시간 점수
        │
        ▼
[STEP 4] GPT selector     (gpt_selector.py)
   상위 후보 중 4~5개 선별·정렬 (새 단어 생성 금지 = 할루시네이션 차단)
        │
        ▼
   추천 단어 4~5개
```

- **Layer 1 (배치/오프라인, `layer1.py`)** — "이 카드가 이 아동에게 얼마나 중요한가"를
  feature **15개**로 회귀. 정답 라벨 = 미래 7일 사용량(time-based split). 결과를
  `baby_card.system_score`에 저장 → Layer 2 입력으로 재사용.
- **Layer 2 (실시간/온라인, `layer2.py`)** — "방금 선택한 카드 다음에 이 후보가 올 점수"를
  feature **20개**로 회귀. 저장하지 않고 매 요청 계산.
- **GPT는 메인이 아니라 보조.** 회귀가 메인, GPT는 결과를 검증·재정렬·보완. 비용/지연 때문에
  역할을 엄격히 제한(selector·문법보정·리포트 해석).

회귀 가중치는 `train.py`로 학습(scikit-learn `LinearRegression`)해 `models/*.json`에 저장하고,
없으면 prior + `scoring_config`(아동별 override) 가중치로 **항상 동작**한다.

---

## 파일 구조

| 파일 | 역할 |
|------|------|
| `main.py` | FastAPI 엔드포인트 |
| `schemas.py` | 요청/응답 Pydantic 스키마 |
| `config.py` | 환경변수 로딩 + 외부 연동 키 유무 판별 |
| `repo.py` | **데이터 파사드** — `DATA_SOURCE`로 dummy↔db 전환 |
| `recommend.py` | 추천 파이프라인 오케스트레이션 |
| `tags.py` | STEP1 태그 필터(교집합 + 브릿지 + fallback) |
| `features.py` | Layer1(15) / Layer2(20) feature 추출 |
| `layer1.py` / `layer2.py` | 카드 중요도 / 맥락 랭킹 회귀 |
| `linmodel.py` | 선형회귀 컨테이너(JSON 저장/로드) |
| `train.py` | 오프라인 회귀 학습(sklearn) |
| `gpt_selector.py` | GPT 단어 selector (새 단어 금지) |
| `grammar.py` | 문법 보정 → 문장 완성 (GPT) |
| `image_gen.py` | Stable Diffusion 이미지 생성 |
| `tts.py` | Naver Clova Voice TTS |
| `analysis.py` | 5개 발달 지표(pandas + sklearn) |
| `report.py` | Plotly 그래프 + LLM 자연어 해석 + PDF |
| `cards.py` | 후보 카드 enrich 유틸 |
| `dummy_data.py` / `dummy_extra.py` | 인메모리 더미 데이터 |
| `db.py` | PostgreSQL 데이터 접근(기본 테이블) |

---

## 멀티모달 (말하기 → 표현)

`POST /sentence` 한 번에:
1. **문법 보정** (`grammar.py`, GPT) — 선택 단어 배열 → 자연스러운 한국어 문장
2. **이미지** (`image_gen.py`, Stable Diffusion) — Scene Description 추출 → 고정 스타일 프롬프트
   (pastel, child-friendly, no background/text) → **seed 고정**으로 같은 문장엔 일관된 이미지,
   `negative_prompt`로 부적합 요소 차단
3. **음성** (`tts.py`, Clova Voice) — `baby_voice_profile`(speaker/speed/pitch/volume) 반영,
   청각 민감 아동은 음량 자동 하향
4. **아바타 감정** + DB 저장(`baby_vocab_log` / `sentence_master` / `sentence_word_map`) → 자기학습 루프

> 외부 키(OpenAI / Stability / Clova)가 없으면 각 단계는 graceful fallback(규칙기반/stub)으로
> 동작하므로 데모는 키 없이도 돌아간다.

---

## 발달 리포트 (closed loop)

`POST /report` → 5개 지표를 결정론적으로 계산하고 LLM이 자연어로 해석:
1. 단어 다양성 변화  2. 평균 문장 길이  3. 카테고리별 사용 비율
4. 감정 표현 비율  5. 행동 패턴 군집(KMeans)

분석 결과는 다시 `scoring_config` 가중치 조정으로 이어지는 폐쇄 루프 설계.

---

## 실행

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# (선택) 회귀 모델 학습 — 없으면 prior 가중치로 동작
python train.py

# 로직만 빠르게 테스트 (서버 불필요)
python test_recommend.py

# 서버 실행
uvicorn main:app --reload --port 8000
# Swagger: http://localhost:8000/docs

# API 호출 예시
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"baby_id": 3, "selected_baby_card_id": 301}'
```

`.env`는 `.env.example`를 복사해 작성. 기본 `DATA_SOURCE=dummy`로 DB 없이 동작한다.

---

## 향후

- `db.py` 확장(`db_extra.py`)로 PostgreSQL 전체 스키마(온보딩/문장/voice 등) 연동
- 품사 전이 가중치를 `sentence_word_map` 실측 전이확률로 학습 전환
- Item2Vec/시퀀셜 모델로 Layer 2 고도화
