"""
image_gen.py
--------------
멀티모달 — 문장 기반 이미지 생성 (Stable Diffusion).

처리 흐름(설계):
  (a) 내부 의미 해석 → Scene Description 추출 (object / action / actor)
  (b) 고정 스타일 프롬프트 템플릿 생성 (pastel, child-friendly, no background, no text)
  (c) seed 고정 → 같은 문장엔 일관된 이미지
  (d) negative_prompt 로 자폐 아동에게 부적합한 요소 차단

STABILITY_API_KEY 가 있으면 Stability AI 로 실제 생성·저장,
없으면 프롬프트만 구성해 반환(graceful stub) → 데모는 항상 동작.
"""

import os
import hashlib

import config

# 고정 스타일 (시각적 일관성 + 자폐 아동 자극 최소화)
STYLE_PROMPT = (
    "cute cartoon illustration, child-friendly style, simple shapes, "
    "pastel colors, soft lighting, no background, no text"
)
NEGATIVE_PROMPT = (
    "text, letters, watermark, dark, scary, realistic photo, complex background, "
    "violence, blood, multiple objects, clutter"
)


def _stable_seed(sentence: str) -> int:
    """같은 문장 → 같은 seed (일관된 이미지)."""
    h = hashlib.sha256(sentence.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % (2**31)


def extract_scene(sentence: str, words: list | None = None) -> dict:
    """
    Scene Description 추출. words(품사 포함)가 있으면 그것으로, 없으면 휴리스틱.
    actor 는 항상 아동 아바타(고정 캐릭터).
    """
    obj, action = None, None
    if words:
        for w in words:
            pos = (w.get("pos") or "").lower()
            if pos == "noun" and obj is None:
                obj = w.get("text")
            elif pos in ("verb", "adjective") and action is None:
                action = w.get("text")
    if obj is None and sentence:
        obj = sentence.split()[0]
    return {"object": obj, "action": action, "actor": "a friendly child character"}


def build_prompt(scene: dict) -> str:
    parts = [STYLE_PROMPT]
    desc = scene.get("actor", "a friendly child character")
    if scene.get("action"):
        desc += f" {scene['action']}"
    if scene.get("object"):
        desc += f" with {scene['object']}"
    parts.append(desc)
    return ", ".join(parts)


def generate_image(sentence: str, words: list | None = None, baby_id: int | None = None) -> dict:
    scene = extract_scene(sentence, words)
    prompt = build_prompt(scene)
    seed = _stable_seed(sentence)

    if not config.has_stability():
        return {
            "image_url": None, "prompt": prompt, "negative_prompt": NEGATIVE_PROMPT,
            "seed": seed, "scene": scene, "status": "stub (STABILITY_API_KEY 미설정)",
        }

    try:
        import requests
        os.makedirs(config.IMAGE_OUTPUT_DIR, exist_ok=True)
        resp = requests.post(
            config.STABILITY_API_URL,
            headers={
                "Authorization": f"Bearer {config.STABILITY_API_KEY}",
                "Accept": "image/*",
            },
            files={"none": ""},
            data={
                "prompt": prompt,
                "negative_prompt": NEGATIVE_PROMPT,
                "seed": seed,
                "output_format": "png",
                "aspect_ratio": "1:1",
            },
            timeout=60,
        )
        resp.raise_for_status()
        fname = f"img_{seed}.png"
        path = os.path.join(config.IMAGE_OUTPUT_DIR, fname)
        with open(path, "wb") as f:
            f.write(resp.content)
        return {
            "image_url": config.public_url(path), "image_path": path,
            "prompt": prompt, "negative_prompt": NEGATIVE_PROMPT,
            "seed": seed, "scene": scene, "status": "generated",
        }
    except Exception as e:
        return {
            "image_url": None, "prompt": prompt, "negative_prompt": NEGATIVE_PROMPT,
            "seed": seed, "scene": scene, "status": f"error: {e}",
        }
