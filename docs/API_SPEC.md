# 소리싹 AI API 명세서 (v2.0)

> **Base URL**: `http://localhost:8000`
> **Version**: 2.0.0

2-레이어 회귀 추천 + GPT selector + Stable Diffusion + Clova TTS + 발달 리포트.

---

## 목차
1. [헬스 체크](#1-헬스-체크)
2. [단어 추천](#2-단어-추천)
3. [말하기: 문장+멀티모달](#3-말하기-문장멀티모달)
4. [이미지 생성](#4-이미지-생성)
5. [TTS 음성](#5-tts-음성)
6. [스코어 재계산(Layer1 배치)](#6-스코어-재계산-layer1-배치)
7. [발달 리포트](#7-발달-리포트)
8. [공통 에러](#8-공통-에러)

---

## 1. 헬스 체크

`GET /` → 서버 상태 + 데이터 소스 + 외부 연동 활성화 여부

```json
{
  "status": "ok",
  "service": "소리싹 단어 추천 API",
  "data_source": "dummy",
  "integrations": {"openai": false, "stable_diffusion": false, "clova_tts": false}
}
```

---

## 2. 단어 추천

`POST /recommend`

### Request
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `baby_id` | int | O | 아동 ID |
| `selected_baby_card_id` | int \| null | X | 방금 선택한 카드. 첫 화면이면 생략/null |
| `session_length` | int | X | 현재 세션 선택 카드 수 (기본 1) |
| `use_gpt` | bool | X | GPT selector 사용 (기본 true, 키 없으면 자동 회귀순서) |

```json
{ "baby_id": 3, "selected_baby_card_id": 301, "session_length": 1 }
```

### Response
```json
{
  "baby_id": 3,
  "selected_word": "장난감",
  "recommended_words": [
    {"baby_card_id": 302, "card_id": 40, "text": "사주세요", "pos": "verb", "system_score": 1.12},
    {"baby_card_id": 303, "card_id": 41, "text": "갖고싶어요", "pos": "adjective", "system_score": 0.75}
  ]
}
```

`recommended_words[]`: `baby_card_id`(null=미할당 기본카드), `card_id`(null=부모 커스텀),
`text`, `pos`, `system_score`(Layer2 맥락 점수).

---

## 3. 말하기: 문장+멀티모달

`POST /sentence` — 선택 단어 배열 → 문장 → 이미지 → 음성 → 저장 (한 번에)

### Request
```json
{
  "baby_id": 5,
  "words": [
    {"text": "물", "pos": "noun", "baby_card_id": 504, "card_id": 1},
    {"text": "마시다", "pos": "verb", "baby_card_id": 513, "card_id": 12}
  ],
  "emotion": "happy"
}
```

### Response
```json
{
  "baby_id": 5,
  "sentence": "물을 마시고 싶어요.",
  "image": {"image_url": "generated/images/img_123.png", "prompt": "...", "seed": 123, "status": "generated"},
  "audio": {"audio_url": "generated/audio/tts_5_ab.mp3", "params": {"speaker":"ndain","volume":-2}, "status": "generated"},
  "avatar": {"emotion": "happy", "image_url": "avatars/baby_5_happy.png"},
  "saved": true
}
```
> 외부 키가 없으면 `sentence`는 규칙기반, `image`/`audio`는 `status: "stub ..."`로 반환.

---

## 4. 이미지 생성

`POST /image`
```json
{ "sentence": "물을 마시고 싶어요", "words": [{"text":"물","pos":"noun"}], "baby_id": 5 }
```
→ `{ "image_url", "prompt", "negative_prompt", "seed", "scene": {object, action, actor}, "status" }`

---

## 5. TTS 음성

`POST /tts`
```json
{ "text": "물을 마시고 싶어요", "baby_id": 5 }
```
→ `{ "audio_url", "params": {speaker, speed, pitch, volume}, "status" }`

---

## 6. 스코어 재계산 (Layer1 배치)

`POST /score/update?baby_id={id}` — Layer1 회귀로 모든 카드 `system_score` 재계산·저장
```json
{ "baby_id": 1, "updated_cards": 98, "status": "ok" }
```

---

## 7. 발달 리포트

`POST /report`
```json
{ "baby_id": 3, "period": "2026-04-01 ~ 2026-04-30" }
```

### Response
```json
{
  "baby_id": 3,
  "period": "2026-04-01 ~ 2026-04-30",
  "metrics": {
    "vocabulary_diversity": {"unique_total": 22, "trend_by_day": {}},
    "avg_sentence_length": {"avg": 2.3, "n_sentences": 50},
    "category_distribution": {"욕구": 45.0, "감정": 15.0},
    "emotion_ratio": {"ratio": 15.0},
    "behavioral_clusters": {"n_clusters": 3, "clusters": {}},
    "top5_words": ["사주세요", "장난감", "..."]
  },
  "interpretation": "이번 기간 동안 ... (LLM 또는 규칙기반 자연어 해석)",
  "charts": {"category_distribution": { /* Plotly JSON */ }}
}
```

`GET /report/{baby_id}/pdf` → `{ "path": "generated/reports/report_3.pdf", "status": "generated" }`
(reportlab 미설치 시 stub)

---

## 8. 공통 에러

| 코드 | 의미 |
|------|------|
| 400 / 422 | 요청 필드 누락·타입 오류 (FastAPI 검증) |
| 500 | `{"detail": "에러 메시지"}` |

---

## Swagger / ReDoc
- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`
