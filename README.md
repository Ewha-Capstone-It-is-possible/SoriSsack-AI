# SoriSsack-AI (소리쌕 AI)

AI model training and inference code for the It-is-possible AAC system — personalization, prediction, and language support.

비언어 자폐 아동을 위한 AAC(보완대체의사소통) 시스템의 AI 추천 서버
아동의 사용 이력과 개인 특성을 기반으로 다음에 선택할 단어를 예측·추천

---

## 프로젝트 구조

```
sorisak-ai/
├── main.py            # FastAPI 서버 및 API 엔드포인트
├── recommend.py       # 핵심 추천 알고리즘
├── dummy_data.py      # 임시 인메모리 데이터 (DB 연동 전)
└── test_recommend.py  # 통합 테스트 (5명 아동 시나리오)
```

---

## 파일별 설명

### `main.py` — FastAPI 서버

Spring 백엔드에서 POST 요청을 받아 추천 결과를 반환하는 REST API 서버

**엔드포인트:**

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/` | 헬스 체크 |
| `POST` | `/recommend` | 단어 추천 (핵심 기능) |
| `POST` | `/score/update` | 점수 재계산 (추후 구현 예정) |

**요청/응답 형식:**

```json
// POST /recommend 요청
{
  "baby_id": 3,
  "selected_baby_card_id": 301
}

// 응답
{
  "baby_id": 3,
  "selected_word": "장난감",
  "recommended_words": [
    {
      "baby_card_id": 302,
      "card_id": 40,
      "text": "사주세요",
      "pos": "verb",
      "system_score": 1.90
    },
    ...
  ]
}
```

---

### `recommend.py` — 추천 알고리즘

추천의 핵심 로직이 담긴 파일. 4단계 필터링 및 점수화 과정을 수행

#### 추천 4단계 흐름

```
선택한 카드
    ↓
[1단계] 태그 기반 의미 필터링
    ↓
[2단계] 품사 전이 규칙 필터링
    ↓
[3단계] 개인화 점수 계산
    ↓
[4단계] 상위 5개 반환
```

#### 1단계: 태그 기반 의미 필터링 (`filter_by_tag_semantic`)

선택한 단어의 상위 카테고리 태그와 같은 그룹의 단어만 후보로 남기기
예: "장난감"을 선택하면 "욕구" 카테고리 단어만 추천 (병원 단어는 제외)

#### 2단계: 품사 전이 규칙 (`filter_by_pos_transition`)

문법적으로 자연스러운 단어 순서가 되도록 품사를 기반으로 필터링

```python
POS_TRANSITION = {
    "Noun":      ["verb", "adjective"],   # 명사 → 동사/형용사
    "verb":      ["Noun", "verb"],        # 동사 → 명사/동사
    "adjective": ["Noun", "verb"],        # 형용사 → 명사/동사
    None:        ["Noun", "verb", "adjective"],  # 첫 선택 → 전부 허용
}
```

#### 3단계: 개인화 점수 계산 (`compute_system_score`)

4가지 특성(feature)을 가중합산하여 점수를 계산

| 특성 | 함수 | 설명 |
|------|------|------|
| `usage_count` | `compute_usage_count_feature()` | 사용 빈도 정규화 (0~1) |
| `recency` | `compute_recency_feature()` | 최근 사용 시간 감쇠 (24시간 반감기) |
| `time_diversity` | `compute_time_diversity_feature()` | 하루 중 다양한 시간대 사용 여부 |
| `priority` | `compute_priority_feature()` | 카드 중요도 (1=높음, 3=낮음) |

가중치는 아동별로 개인화 설정 가능합니다 (`SCORING_CONFIG`).

#### 폴백(fallback) 로직

후보가 3개 미만일 경우 순차적으로 조건을 완화
1. 개인 카드 + 품사 규칙 적용
2. 개인 카드만 (품사 규칙 제거)
3. 전체 후보 반환

---

### `dummy_data.py` — 임시 데이터 레이어

RDS 연동 전까지 사용하는 인메모리 목 데이터
함수 시그니처는 그대로 유지하여, 실제 DB 연동 시 내부 구현만 교체하면 됨

**주요 데이터:**

| 데이터 | 설명 | 규모 |
|--------|------|------|
| `CARD_MASTER` | 시스템 공통 단어 사전 | 95개 카드 |
| `TAG_MASTER` | 2계층 의미 카테고리 | 상위 6개 / 하위 17개 |
| `BABY_CARDS` | 아동별 개인 카드 | 5명 × ~20개 |
| `BABY_VOCAB_LOGS` | 사용 이력 로그 | ~700건 |
| `SCORING_CONFIG` | 특성 가중치 (전역 + 아동별 오버라이드) | 11개 설정 |

**태그 계층 구조 (예시):**

```
욕구 (Desires)
  ├─ 기본욕구 (배고파, 목마르다...)
  ├─ 소유욕구 (사주세요, 갖고싶다...)
  └─ 신체욕구 (아파요, 졸려요...)

감정 (Emotions)
  ├─ 긍정감정 (좋아, 행복해...)
  ├─ 부정감정 (싫어, 무서워...)
  └─ 통증 (머리 아파, 배 아파...)
```

**테스트용 아동 프로필 (5명):**

| baby_id | 이름 | 나이 | 특징 |
|---------|------|------|------|
| 1 | 민준 | 6세 | 음식/요청 중심, 반복 사용 패턴 |
| 2 | 서아 | 4세 | 감정/놀이/미디어 위주 |
| 3 | 지호 | 5세 | 장난감/야외활동, "사주세요" 선호 |
| 4 | 하은 | 7세 | 학교/일상/사람 관련, 시간대 다양 |
| 5 | 준서 | 3세 | 초기 단계, 기본 단어 반복 |

**주요 함수:**

| 함수 | 설명 |
|------|------|
| `get_baby_cards(baby_id)` | 아동의 활성 카드 목록 반환 |
| `get_candidate_cards(baby_id)` | 개인 카드 + 미사용 공통 카드 반환 |
| `get_vocab_logs(baby_id)` | 최근 200건 사용 이력 반환 |
| `get_scoring_config(baby_id)` | 전역 + 아동별 가중치 병합 반환 |

---

### `test_recommend.py` — 통합 테스트

5명 아동의 22개 이상 시나리오를 통해 추천 결과를 검증

```python
# 예시: 민준이 "배고파"를 선택한 경우
recommend_words(baby_id=1, selected_baby_card_id=106)
# 예상 결과: 밥, 먹다, 주세요 등 식사 관련 단어 추천
```

---

## 실행 방법

```bash
# 가상환경 활성화
source venv/bin/activate

# 서버 실행
uvicorn main:app --reload --port 8000

# 테스트 실행
python test_recommend.py

# API 테스트 (curl)
curl -X POST http://localhost:8000/recommend \
  -H "Content-Type: application/json" \
  -d '{"baby_id": 3, "selected_baby_card_id": 301}'
```

---

## 의존성

```
fastapi
uvicorn
pydantic
```

---

## 향후 연동 계획

- `dummy_data.py` 함수들을 SQLAlchemy ORM 쿼리로 교체 (RDS 연동)
- `/score/update` 엔드포인트 구현
- Spring 백엔드와 실제 연동 테스트
