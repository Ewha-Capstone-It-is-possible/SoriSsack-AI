# 소리싹 AI 단어 추천 API 명세서

> **Base URL**: `http://localhost:8000`
> **Version**: 1.0.0
> **Last Updated**: 2026-04-17

---

## 목차

1. [헬스 체크](#1-헬스-체크)
2. [단어 추천](#2-단어-추천)
3. [스코어 재계산 (예정)](#3-스코어-재계산-예정)
4. [공통 에러 응답](#4-공통-에러-응답)
5. [데이터 타입 설명](#5-데이터-타입-설명)

---

## 1. 헬스 체크

서버 상태 확인용 엔드포인트

| 항목 | 값 |
|------|------|
| **Method** | `GET` |
| **URL** | `/` |
| **인증** | 없음 |

### Response

```
Status: 200 OK
```

```json
{
  "status": "ok",
  "service": "소리싹 단어 추천 API"
}
```

---

## 2. 단어 추천

아동이 카드를 선택했을 때, AI 기반으로 다음에 추천할 단어 4~5개를 반환합니다.

| 항목 | 값 |
|------|------|
| **Method** | `POST` |
| **URL** | `/recommend` |
| **Content-Type** | `application/json` |
| **인증** | 없음 (Spring 서버 내부 호출) |

### Request Body

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `baby_id` | `int` | O | 아동 ID |
| `selected_baby_card_id` | `int \| null` | X | 방금 선택한 카드의 baby_card_id. 첫 선택(아무것도 선택 안 한 상태)이면 `null` 또는 필드 생략 |

### Request 예시

**카드 선택 후 추천 요청:**

```json
{
  "baby_id": 3,
  "selected_baby_card_id": 501
}
```

**첫 진입 (선택 없이 초기 추천):**

```json
{
  "baby_id": 3,
  "selected_baby_card_id": null
}
```

또는

```json
{
  "baby_id": 3
}
```

### Response

```
Status: 200 OK
```

```json
{
  "baby_id": 3,
  "selected_word": "장난감",
  "recommended_words": [
    {
      "baby_card_id": 302,
      "card_id": 40,
      "text": "사주세요",
      "pos": "verb",
      "system_score": 1.63
    },
    {
      "baby_card_id": 303,
      "card_id": 41,
      "text": "갖고싶어요",
      "pos": "adjective",
      "system_score": 1.57
    },
    {
      "baby_card_id": 304,
      "card_id": 42,
      "text": "놀고싶어요",
      "pos": "verb",
      "system_score": 1.52
    },
    {
      "baby_card_id": null,
      "card_id": 36,
      "text": "블록",
      "pos": "noun",
      "system_score": 0.50
    },
    {
      "baby_card_id": null,
      "card_id": 38,
      "text": "공",
      "pos": "noun",
      "system_score": 0.50
    }
  ]
}
```

### Response 필드 설명

| 필드 | 타입 | 설명 |
|------|------|------|
| `baby_id` | `int` | 요청한 아동 ID |
| `selected_word` | `string \| null` | 선택된 카드의 텍스트. 첫 진입이면 `null` |
| `recommended_words` | `array` | 추천 단어 목록 (system_score 내림차순, 최대 5개) |

#### `recommended_words[]` 각 항목

| 필드 | 타입 | 설명 |
|------|------|------|
| `baby_card_id` | `int \| null` | 아동 개인 카드 ID. **`null`이면 아직 아동에게 할당되지 않은 기본 카드** |
| `card_id` | `int \| null` | card_master 기본 카드 ID. **`null`이면 부모가 직접 추가한 커스텀 카드** |
| `text` | `string` | 카드에 표시할 단어 텍스트 |
| `pos` | `string \| null` | 품사 (`"noun"`, `"verb"`, `"adjective"`) |
| `system_score` | `float` | AI 추천 점수 (높을수록 추천도 높음) |

### 카드 타입 판별 가이드

프론트에서 카드 종류를 구분할 때 아래 조합으로 판단하세요:

| `baby_card_id` | `card_id` | 의미 |
|---|----|------|
| 값 있음 | 값 있음 | 아동에게 이미 할당된 기본 카드 |
| 값 있음 | `null` | 부모가 직접 추가한 커스텀 카드 |
| `null` | 값 있음 | 아직 할당 안 된 기본 카드 (신규 추천) |

---

## 3. 스코어 재계산 (예정)

> **현재 미구현** - DB 연결 후 구현 예정

아동의 모든 카드에 대해 system_score를 일괄 재계산합니다.

| 항목 | 값 |
|------|------|
| **Method** | `POST` |
| **URL** | `/score/update?baby_id={baby_id}` |
| **인증** | 없음 |

### Query Parameters

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `baby_id` | `int` | O | 아동 ID |

### Response (현재 Stub)

```
Status: 200 OK
```

```json
{
  "message": "baby_id=3 score update 예정 (DB 연결 후 구현)"
}
```

---

## 4. 공통 에러 응답

### 400 Bad Request - 잘못된 요청

필수 필드 누락 또는 타입 불일치 시

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "baby_id"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

### 422 Unprocessable Entity - 유효성 검증 실패

```json
{
  "detail": [
    {
      "type": "int_parsing",
      "loc": ["body", "baby_id"],
      "msg": "Input should be a valid integer",
      "input": "abc"
    }
  ]
}
```

### 500 Internal Server Error - 서버 내부 오류

```json
{
  "detail": "에러 메시지 문자열"
}
```

---

## 5. 데이터 타입 설명

### 품사 (pos) 값

| 값 | 의미 | 예시 |
|------|------|------|
| `"noun"` | 명사 | 물, 장난감, 블록 |
| `"verb"` | 동사 | 사주세요, 놀고싶어요 |
| `"adjective"` | 형용사 | 갖고싶어요 |

### 추천 알고리즘 흐름 (참고)

```
1. 아동의 선택 카드 품사/태그 파악
2. 태그 기반 의미 필터링 (같은 상위 태그 그룹)
3. 품사 전이 규칙 필터링 (명사→동사/형용사 등)
4. system_score 계산 (usage_count, recency, time_diversity, priority)
5. 점수 내림차순으로 상위 5개 반환
```

---

## Swagger (자동 문서)

FastAPI 서버 실행 후 아래 URL에서 인터랙티브 API 문서 확인 가능:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
