"""
image_gen.py
--------------
자폐 아동 AAC용 문장 기반 이미지 생성 (Stable Diffusion).

설계 원칙(자폐 아동 친화):
  - **아이별 고정 캐릭터**: seed = hash(baby_id) → 같은 아이는 늘 같은 외모의 캐릭터.
  - **성별 반영**: DB(baby_basic_information.sex) → boy / girl.
  - **동작 명확화**: GPT 로 한국어 문장 → 영어 시각 장면(분명한 제스처/표정).
    Stable Diffusion 은 영어만 이해하므로 한국어 동작을 그대로 넣으면 무시된다.
  - **저자극·단순·일관**: 단일 주체, 단색 파스텔 배경, 부드러운 색, 굵은 외곽선,
    텍스트/잡음/복잡 배경 차단 → 시각 과부하 최소화 + 의미 전달 명확.

STABILITY_API_KEY 가 있으면 실제 생성·S3(또는 로컬) 저장, 없으면 프롬프트만 반환(stub).
"""

import os
import hashlib

import config
import repo
import s3

# 자폐 아동 친화 고정 스타일 — 명확/저자극/일관
STYLE_PROMPT = (
    "simple flat 2D cartoon illustration, one single child character, centered, full body, "
    "clear and obvious friendly gesture, plain solid soft pastel background, "
    "calm muted colors, gentle happy expression, clean bold outlines, simple rounded shapes, "
    "no text, children's AAC communication pictogram style"
)
NEGATIVE_PROMPT = (
    "standing still, idle pose, hands at sides, stiff portrait, motionless, "
    "text, letters, words, numbers, watermark, signature, logo, "
    "two people, multiple children, crowd, extra person, "
    "realistic, photo, 3d render, photorealistic, "
    "dark, scary, angry, gloomy, creepy, "
    "blurry, cluttered, busy background, detailed background, "
    "extra limbs, extra fingers, deformed hands, distorted face, mutated, "
    "low quality, oversaturated, neon"
)


def _baby_seed(baby_id) -> int:
    """아이별 고정 seed → 같은 아이는 늘 같은 캐릭터 외모(일관성)."""
    h = hashlib.sha256(f"baby-{baby_id}".encode("utf-8")).hexdigest()
    return int(h[:8], 16) % (2**31)


def _stable_seed(sentence: str) -> int:
    """baby_id 가 없을 때 폴백: 문장 기반 seed."""
    h = hashlib.sha256((sentence or "x").encode("utf-8")).hexdigest()
    return int(h[:8], 16) % (2**31)


# FE 좋아하는 색 값 → 영어 색 (프롬프트용)
_COLOR_MAP = {
    "pink": "pink", "purple": "purple", "blue": "blue",
    "green": "green", "yellow": "yellow", "orange": "orange",
}


def _shirt_color(favorite_color) -> str:
    """좋아하는 색을 셔츠 색으로(없으면 기본 노랑)."""
    return _COLOR_MAP.get((favorite_color or "").lower(), "light yellow")


def _child_descriptor(sex, favorite_color=None) -> str:
    """성별 + 좋아하는 색 반영 '고정 외모' 캐릭터 묘사 → 일관성."""
    s = (sex or "").upper()
    shirt = _shirt_color(favorite_color)
    if s.startswith("M") or s in ("남", "남자", "1"):
        return (f"a cheerful little boy, short black hair, round face, big kind eyes, "
                f"wearing a {shirt} t-shirt and blue overalls")
    if s.startswith("F") or s in ("여", "여자", "2"):
        return (f"a cheerful little girl, short black bob hair, round face, big kind eyes, "
                f"wearing a {shirt} t-shirt and a blue jumper dress")
    return (f"a cheerful little child, short black hair, round face, big kind eyes, "
            f"wearing a {shirt} t-shirt")


# 자폐 아동 AAC 핵심 의도 → 명확하고 과장된 전신 포즈(검증된 템플릿).
# 의도가 유한하므로 freeform 보다 안정적 → "모든 문장"이 또렷한 동작으로 나옴.
INTENT_POSES = {
    "eat":     "sitting, holding a spoon raised up to the wide-open mouth, a bowl of food in the other hand, eating happily",
    "drink":   "holding a cup with both hands raised up to the mouth, drinking, looking refreshed and happy",
    "hungry":  "both hands patting an empty tummy, mouth open, looking hungry and asking for food",
    "toilet":  "one hand pointing toward a door, knees pressed together, leaning forward, looking a little urgent",
    "hug":     "both arms stretched wide open to the sides, reaching forward for a big hug, warm happy smile",
    "sleep":   "one hand rubbing an eye, head tilted, mouth open in a yawn, looking very sleepy",
    "play":    "jumping up with both arms raised high above the head, big excited open-mouth smile",
    "hurt":    "one hand pressing on the tummy, eyebrows raised, looking like it hurts a little",
    "give":    "both hands open and stretched forward, asking to receive something, hopeful face",
    "greet":   "raising one hand high in the air and waving, big friendly smile",
    "yes":     "standing with both thumbs up, nodding, big approving smile",
    "no":      "both hands raised in a gentle stop gesture, head turned aside, unsure face",
    "call":    "both arms reaching forward calling for a parent, looking up wanting attention",
    "happy":   "jumping with joy, both arms thrown up, huge happy open-mouth smile",
    "sad":     "both hands rubbing the eyes, mouth turned down, one small teardrop, looking sad",
    "scared":  "both hands raised near the face, shoulders pulled up, looking a little worried",
    "more":    "holding up one open hand and pointing at it with the other, asking for more",
    "thanks":  "both hands pressed together at the chest, head bowed slightly, grateful smile",
    "wash":    "rubbing both hands together as if washing them, looking focused and happy",
    "go":      "one hand pointing forward, one foot stepping ahead, walking, looking eager",
}

_INTENT_SYSTEM = (
    "You label a short Korean sentence from a toddler's AAC speaking app with ONE intent key.\n"
    "Allowed keys: " + ", ".join(INTENT_POSES.keys()) + ", other.\n"
    "Pick the key whose ACTION best shows what the child means visually. "
    "If a sentence mixes things (e.g. '엄마 밥 줘'), pick the most visual action ('eat'). "
    "Reply with ONLY the key, nothing else."
)

_FREEFORM_SYSTEM = (
    "Convert a Korean toddler AAC sentence into a SHORT explicit English full-body POSE "
    "for a single child cartoon (8-14 words). Start with arms/hands/legs position so the "
    "gesture is obvious and exaggerated. No other people, no background, no art style words."
)


def _gpt(system: str, user: str, max_tokens: int = 40) -> str | None:
    if not config.has_openai() or not user:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=config.OPENAI_API_KEY)
        resp = client.chat.completions.create(
            model=config.OPENAI_MODEL_GRAMMAR, temperature=0, max_tokens=max_tokens,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content.strip().strip('"').strip()
    except Exception:
        return None


def _scene_pose(sentence: str) -> str:
    """문장 → 명확한 영어 포즈. 알려진 의도는 검증 템플릿, 아니면 GPT freeform."""
    intent = (_gpt(_INTENT_SYSTEM, sentence, max_tokens=4) or "").lower().strip(". ")
    if intent in INTENT_POSES:
        return INTENT_POSES[intent]
    # 'other' or 분류 실패 → freeform 포즈
    return _gpt(_FREEFORM_SYSTEM, sentence) or "waving one hand with a big happy smile"


# 단어카드용 스타일/네거티브 — 사람 없이 '물체/개념' 아이콘만(자폐 친화 픽토그램)
WORD_STYLE = (
    "simple flat 2D cartoon icon, one single clear object centered, plain solid pastel background, "
    "soft calm colors, bold clean outlines, minimal, no text, AAC pictogram for children"
)
WORD_NEGATIVE = (
    "person, people, child, kid, human, hands, face, body, "
    "text, letters, watermark, multiple objects, clutter, busy background, "
    "realistic, photo, 3d, dark, scary, blurry, low quality"
)

# 단어 → '그 물체/개념 자체'의 영어 묘사 (사람 등장 X)
_WORD_SYSTEM = (
    "Convert a Korean word from a toddler's AAC word card into a SHORT English description of "
    "the OBJECT or CONCEPT ITSELF for a simple clean icon (4-10 words). NO person, no child, no hands. "
    "For a thing: describe the single object. For an action verb: describe a simple representative object/scene. "
    "No background, no art-style words.\n"
    "Examples:\n"
    "'사과' -> 'a single big red shiny apple'\n"
    "'물' -> 'a clear glass cup full of water'\n"
    "'양치' -> 'a toothbrush with white toothpaste on it'\n"
    "'먹다' -> 'a bowl of food with a spoon'\n"
    "'자동차' -> 'a cute small red toy car'"
)


def _word_object(word: str) -> str:
    return _gpt(_WORD_SYSTEM, word) or f"a simple cute icon of {word}"


def extract_scene(sentence: str, words: list | None = None, sex=None,
                  favorite_color=None) -> dict:
    """말하기용 scene 메타 + 명확한 영어 동작(의도 기반)."""
    return {"object": sentence, "action": _scene_pose(sentence),
            "actor": _child_descriptor(sex, favorite_color)}


def build_prompt(scene: dict) -> str:
    # 동작을 맨 앞 = 가중치 ↑, 'standing' 기본값 억제 → 모션이 살아남
    return (
        f"a child {scene['action']}, dynamic full body action pose, "
        f"{scene['actor']}, {STYLE_PROMPT}"
    )


def _image_key(baby_id, sentence: str, color, kind: str = "sentence") -> str:
    """캐시 키 = (종류 + 아이 + 문장/단어 + 색). 같은 조합이면 같은 파일 → 재사용."""
    h = _stable_seed(f"{kind}|{baby_id}|{sentence}|{color or ''}")
    prefix = "cards" if kind == "word" else "images"
    return f"{prefix}/img_{baby_id or 'x'}_{h}.png"


def generate_image(sentence: str, words: list | None = None, baby_id: int | None = None,
                   favorite_color: str | None = None, kind: str = "sentence") -> dict:
    is_word = (kind == "word")

    # 말하기 전용: 아이 성별/색/외모. 단어카드는 사람 없음 → 불필요.
    sex = None
    color = favorite_color
    stored = {}
    if not is_word:
        baby = repo.get_baby_basic(baby_id) if baby_id is not None else {}
        sex = baby.get("sex")
        if baby_id is not None:
            try:
                stored = repo.get_avatar_config(baby_id) or {}
            except Exception:
                stored = {}
        color = favorite_color or stored.get("favorite_color")

    key = _image_key(baby_id, sentence, color, kind)
    seed = _stable_seed(f"{kind}|{baby_id}|{sentence}|{color or ''}")

    # 프롬프트/네거티브/scene — 말하기(아이 동작) vs 단어카드(물체만)
    if is_word:
        obj = _word_object(sentence)
        prompt = f"{obj}, {WORD_STYLE}"
        negative = WORD_NEGATIVE
        scene = {"object": sentence, "action": None, "actor": obj}
    else:
        scene = extract_scene(sentence, words, sex, color)
        prompt = build_prompt(scene)
        negative = NEGATIVE_PROMPT

    # ── 캐싱: 이미 만든 (종류+아이+문장+색) 이미지면 GPT/SD 건너뛰고 즉시 반환 ──
    if config.has_stability() and config.has_s3() and s3.object_exists(key):
        return {
            "image_url": s3.public_url(key), "image_path": f"s3://{key}",
            "prompt": None, "negative_prompt": negative, "seed": seed,
            "scene": scene, "status": "cached",
        }

    # 외모 설정 영속화(말하기 전용, best-effort)
    if not is_word and baby_id is not None and (
        stored.get("favorite_color") != color or not stored.get("descriptor")
    ):
        try:
            repo.upsert_avatar_config(baby_id, {
                "sex": sex, "favorite_color": color, "descriptor": scene["actor"],
            })
        except Exception:
            pass

    if not config.has_stability():
        return {
            "image_url": None, "prompt": prompt, "negative_prompt": negative,
            "seed": seed, "scene": scene, "status": "stub (STABILITY_API_KEY 미설정)",
        }

    try:
        import requests
        resp = requests.post(
            config.STABILITY_API_URL,
            headers={"Authorization": f"Bearer {config.STABILITY_API_KEY}", "Accept": "image/*"},
            files={"none": ""},
            data={
                "prompt": prompt, "negative_prompt": negative, "seed": seed,
                "output_format": "png", "aspect_ratio": "1:1",
            },
            timeout=60,
        )
        resp.raise_for_status()

        if config.has_s3():
            image_url = s3.upload_bytes(resp.content, key, "image/png")
            return {
                "image_url": image_url, "image_path": f"s3://{key}",
                "prompt": prompt, "negative_prompt": negative,
                "seed": seed, "scene": scene, "status": "generated",
            }

        os.makedirs(config.IMAGE_OUTPUT_DIR, exist_ok=True)
        path = os.path.join(config.IMAGE_OUTPUT_DIR, os.path.basename(key))
        with open(path, "wb") as f:
            f.write(resp.content)
        return {
            "image_url": config.public_url(path), "image_path": path,
            "prompt": prompt, "negative_prompt": negative,
            "seed": seed, "scene": scene, "status": "generated",
        }
    except Exception as e:
        return {
            "image_url": None, "prompt": prompt, "negative_prompt": negative,
            "seed": seed, "scene": scene, "status": f"error: {e}",
        }
