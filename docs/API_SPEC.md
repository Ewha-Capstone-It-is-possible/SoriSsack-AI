# 소리싹 AI API 명세서 (v2.0)

> **AI 서버 Base URL**: `http://localhost:8000` (개발) / 실기기 데모 시 LAN IP
> **Version**: 2.0.0
> 2-레이어 회귀 추천 + GPT selector + Stable Diffusion + Clova TTS + 발달 리포트

---

## 0. 호출 구조 (누가 누구를 부르나)

```
[FRONT: React Native]  ──①──>  [BACK: FastAPI :8000 /api/v1]  ──②──>  [AI: FastAPI :8001 (이 문서)]  ──>  OpenAI / Stability / Clova
   │                                                                          │
   │                                                                          └─ 생성된 이미지/음성을 generated/ 에 저장
   └─────────────────────③ 정적 미디어 직접 GET ─────────────────────────────> /generated/...  (image_url / audio_url)
```

- **① Front → Back**: 프론트는 백엔드(`http://localhost:8000/api/v1/...`)만 호출. 명세는 백엔드 Swagger(`http://localhost:8000/docs`).
- **② Back → AI**: 백엔드가 `httpx` 로 아래 AI 엔드포인트를 프록시. **프론트가 직접 부르지 않음.**
- **③ Front → AI 정적 서버**: 프론트가 AI 서버를 **직접 쓰는 건 이것뿐** — 응답의 `image_url`·`audio_url`을 `<img>`/`<audio>`로 로드. (키·로직 일절 불필요)

> 📌 두 서버 모두 FastAPI라 Swagger 자동 제공: 백엔드 `http://localhost:8000/docs`, AI `http://localhost:8001/docs`.
> 프론트엔 이 두 링크를 넘기면 된다(특히 백엔드 `/docs`가 프론트가 실제 호출하는 API).

### 프론트가 실제로 받아서 쓰는 필드 (핵심 요약)

| 화면 동작 | 어느 API 응답에서 | 쓰는 필드 |
|-----------|------------------|-----------|
| 추천 단어 4~5개 표시 | `/recommend` | `recommended_words[].text` / `pos` |
| "말하기" → 문장 표시 | `/sentence` | `sentence` |
| "말하기" → 이미지 표시 | `/sentence` | `image.image_url` |
| "말하기" → 음성 재생 | `/sentence` | `audio.audio_url` |
| 아바타 표정 | `/sentence` | `avatar.emotion` |
| 리포트 화면 | `/report` | `metrics`, `interpretation`, `charts` |

> ⚠️ 키 미설정(데모 stub) 시 `image_url`/`audio_url`은 **`null`** → 프론트는 null 가드 필요.
> ⚠️ 실기기에서 이미지/음성이 안 뜨면 AI 서버 `.env`의 `AI_PUBLIC_BASE_URL`을 LAN IP로 바꿔야 함 (`127.0.0.1` → `192.168.x.x`).

---

## 엔드포인트 목록

| # | Method | Path | 용도 | 호출 주체 |
|---|--------|------|------|-----------|
| 1 | GET  | `/` | 헬스 체크 + 연동 활성화 여부 | Back |
| 2 | POST | `/recommend` | 다음 단어 추천 | Back |
| 3 | POST | `/related-words` | 부모 단어추가용 관련단어 생성 | Back |
| 4 | POST | `/sentence` | **말하기**: 문장+이미지+음성 한 번에 | Back |
| 5 | POST | `/image` | 문장 → 이미지만 | Back |
| 6 | POST | `/tts` | 문장 → 음성만 | Back |
| 7 | POST | `/score/update` | Layer1 배치 점수 재계산 | Back(배치) |
| 8 | POST | `/report` | 발달 리포트 | Back |
| 9 | GET  | `/onboarding/{baby_id}/assessment` | 온보딩 인지테스트 채점 | Back |
| 10| GET  | `/report/{baby_id}/pdf` | 리포트 PDF 다운로드 | Back |
| — | GET  | `/generated/...` | 생성 이미지·음성 정적 서빙 | **Front 직접** |

---

## 1. 헬스 체크

`GET /`
```json
{
  "status": "ok",
  "service": "소리싹 단어 추천 API",
  "data_source": "dummy",
  "integrations": {"openai": false, "stable_diffusion": false, "clova_tts": false}
}
```
> `integrations` 가 모두 `true` 여야 실제 GPT/이미지/음성이 나옴. `false` = stub 모드.

---

## 2. 단어 추천

`POST /recommend`

### Request
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `baby_id` | int | O | 아동 ID |
| `selected_baby_card_id` | int \| null | X | 방금 선택한 개인 카드. 첫 화면이면 null |
| `selected_card_id` | int \| null | X | 공용(마스터) 카드 선택 시 (개인카드 id 없을 때) |
| `session_length` | int | X | 현재 세션 선택 카드 수 (기본 1) |
| `use_gpt` | bool | X | GPT selector 사용 (기본 true, 키 없으면 회귀순서로 자동 fallback) |

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
- `baby_card_id` null = 미할당 기본카드 / `card_id` null = 부모 커스텀 단어
- `system_score` = Layer2 맥락 점수 (내림차순 정렬됨)

---

## 3. 관련 단어 (부모 단어추가용)

`POST /related-words` — DB에 없는 새 단어를 GPT가 제안 (부모가 단어 직접 추가할 때)

### Request
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `text` | str | O | 기준 단어/문장 (예: "주먹밥") |
| `count` | int | X | 제안 개수 (기본 6) |
| `exclude` | string[] | X | 이미 DB에 있어 제외할 단어들 |

```json
{ "text": "주먹밥", "count": 6, "exclude": ["밥", "김"] }
```

### Response
```json
{ "text": "주먹밥", "related_words": [ { "text": "도시락", "pos": "noun" }, ... ] }
```

---

## 4. 말하기: 문장 + 멀티모달  ⭐ 핵심

`POST /sentence` — 선택 단어 배열 → 문장 → **이미지 + 음성** → DB 저장 (한 번에)

### Request
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `baby_id` | int | O | 아동 ID |
| `words` | WordItem[] | O | 선택한 단어 배열 (순서대로) |
| `emotion` | str | X | 아바타 감정: happy/sad/angry/neutral/surprised (기본 neutral) |

**WordItem**: `{ "text": str, "pos": str?, "baby_card_id": int?, "card_id": int? }`

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
  "image": {
    "image_url": "http://127.0.0.1:8001/generated/images/img_123.png",
    "prompt": "...", "negative_prompt": "...", "seed": 123,
    "scene": {"object": "물", "action": "마시다", "actor": "a friendly child character"},
    "status": "generated"
  },
  "audio": {
    "audio_url": "http://127.0.0.1:8001/generated/audio/tts_5_ab.mp3",
    "params": {"speaker": "ndain", "speed": 0, "pitch": 0, "volume": -2},
    "status": "generated"
  },
  "avatar": {"emotion": "happy", "image_url": "avatars/baby_5_happy.png"},
  "saved": true
}
```
> 키 없으면: `sentence`는 규칙기반, `image.image_url`/`audio.audio_url` = **null**, `status: "stub ..."`.
> **프론트는 `image.image_url`을 `<img src>`, `audio.audio_url`을 `<audio src>`로 사용.**

---

## 5. 이미지만 생성

`POST /image`
```json
{ "sentence": "물을 마시고 싶어요", "words": [{"text":"물","pos":"noun"}], "baby_id": 5 }
```
### Response
```json
{ "image_url": "http://.../generated/images/img_123.png", "prompt": "...",
  "negative_prompt": "...", "seed": 123,
  "scene": {"object": "물", "action": null, "actor": "..."}, "status": "generated" }
```

---

## 6. 음성만 생성 (TTS)

`POST /tts`
```json
{ "text": "물을 마시고 싶어요", "baby_id": 5 }
```
### Response
```json
{ "audio_url": "http://.../generated/audio/tts_5_ab.mp3",
  "params": {"speaker": "ndain", "speed": 0, "pitch": 0, "volume": -2}, "status": "generated" }
```

---

## 7. 스코어 재계산 (Layer1 배치)

`POST /score/update?baby_id={id}` — 쿼리 파라미터로 baby_id 전달. 모든 카드 `system_score` 재계산·저장 (배치/주기 작업, 화면과 무관)
```json
{ "baby_id": 1, "updated_cards": 98, "status": "ok" }
```

---

## 8. 발달 리포트

`POST /report`
### Request
| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `baby_id` | int | O | 아동 ID |
| `period_days` | int \| null | X | null=AUTO(가용 로그 절반 분할), 30 → 최근 30일 vs 이전 30일 |

```json
{ "baby_id": 3, "period_days": 30 }
```
### Response
```json
{
  "baby_id": 3,
  "period": "2026-04-01 ~ 2026-04-30",
  "summary": { "vocabulary_diversity": "+12%", "avg_sentence_length": "+0.3" },
  "current_metrics": {
    "vocabulary_diversity": {"unique_total": 22},
    "avg_sentence_length": {"avg": 2.3, "n_sentences": 50},
    "category_distribution": {"욕구": 45.0, "감정": 15.0},
    "emotion_ratio": {"ratio": 15.0},
    "behavioral_clusters": {"n_clusters": 3},
    "top5_words": ["사주세요", "장난감", "..."]
  },
  "interpretation": "이번 기간 동안 ... (LLM 또는 규칙기반 자연어 해석)",
  "charts": {"category_distribution": { "_plotly_": "..." }}
}
```
> `summary`=기간 대비 비교, `current_metrics`=현재 구간 상세 5지표. 둘 다 분석 결과라 내부 구조는 동적.
> `charts`는 Plotly JSON. 프론트가 plotly.js로 렌더하거나 무시 가능.

`GET /report/{baby_id}/pdf?period_days=30` → reportlab 설치 시 **PDF 파일 다운로드**(application/pdf), 미설치 시 JSON 리포트 반환.

---

## 9. 온보딩 인지 평가

`GET /onboarding/{baby_id}/assessment` — 온보딩 인지테스트 영역별 채점 + GPT 자연어 평가
```json
{
  "baby_id": 3,
  "scores": { "...영역별 점수..." },
  "assessment": "...GPT 자연어 평가..."
}
```

---

## 10. 공통 에러

| 코드 | 의미 | 바디 |
|------|------|------|
| 400 / 422 | 요청 필드 누락·타입 오류 (FastAPI 검증) | FastAPI 기본 형식 |
| 500 | 서버 내부 오류 | `{ "detail": "에러 메시지" }` |

---

## Swagger / ReDoc (자동 생성 문서)
- `http://localhost:8000/docs`  ← 프론트/백 모두 여기서 직접 테스트 가능
- `http://localhost:8000/redoc`
