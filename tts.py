"""
tts.py
--------------
멀티모달 — 문장 음성 변환 (Naver Clova Voice TTS).

완성 문장을 자연스러운 한국어 음성으로 변환한다. 아동별 baby_voice_profile
(speaker / speed / pitch / volume)을 반영해 개인화하며, 특히 청각 민감 아동은
volume 을 낮춘다.

CLOVA_CLIENT_ID/SECRET 가 있으면 실제 호출·저장, 없으면 파라미터만 반환(stub).
"""

import os
import hashlib

import config
import repo


def _fname(text: str, baby_id) -> str:
    h = hashlib.sha256(f"{baby_id}:{text}".encode("utf-8")).hexdigest()[:12]
    return f"tts_{baby_id}_{h}.mp3"


def synthesize(text: str, baby_id: int) -> dict:
    profile = repo.get_voice_profile(baby_id)
    params = {
        "speaker": profile.get("speaker", "nara"),
        "speed": profile.get("speed", 0),
        "pitch": profile.get("pitch", 0),
        "volume": profile.get("volume", 0),
        "emotion": profile.get("emotion", 0),
        "format": "mp3",
    }

    if not text:
        return {"audio_url": None, "params": params, "status": "empty text"}

    if not config.has_clova():
        return {"audio_url": None, "params": params,
                "status": "stub (CLOVA_CLIENT_ID/SECRET 미설정)"}

    try:
        import requests
        os.makedirs(config.AUDIO_OUTPUT_DIR, exist_ok=True)
        resp = requests.post(
            config.CLOVA_TTS_URL,
            headers={
                "X-NCP-APIGW-API-KEY-ID": config.CLOVA_CLIENT_ID,
                "X-NCP-APIGW-API-KEY": config.CLOVA_CLIENT_SECRET,
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"text": text, **params},
            timeout=30,
        )
        resp.raise_for_status()
        fname = _fname(text, baby_id)

        # S3 설정이 있으면 S3 업로드(영구), 없으면 로컬 디스크 저장
        if config.has_s3():
            import s3
            audio_url = s3.upload_bytes(resp.content, f"audio/{fname}", "audio/mpeg")
            return {"audio_url": audio_url, "audio_path": f"s3://audio/{fname}",
                    "params": params, "status": "generated"}

        path = os.path.join(config.AUDIO_OUTPUT_DIR, fname)
        with open(path, "wb") as f:
            f.write(resp.content)
        return {"audio_url": config.public_url(path), "audio_path": path,
                "params": params, "status": "generated"}
    except Exception as e:
        return {"audio_url": None, "params": params, "status": f"error: {e}"}
