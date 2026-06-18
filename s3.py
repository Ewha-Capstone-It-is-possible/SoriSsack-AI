"""
s3.py
--------------
생성 미디어(이미지/음성)를 S3에 업로드하고 공개 URL을 반환한다.

config.has_s3() 가 True 일 때만 사용. 업로드 실패 시 예외를 올리고,
호출측(image_gen/tts)이 로컬 저장으로 graceful fallback 한다.
"""

import config

_client = None


def _get_client():
    global _client
    if _client is None:
        import boto3
        _client = boto3.client(
            "s3",
            region_name=config.S3_REGION,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
        )
    return _client


def public_url(key: str) -> str:
    return f"https://{config.S3_BUCKET}.s3.{config.S3_REGION}.amazonaws.com/{key}"


def object_exists(key: str) -> bool:
    """S3 에 해당 key 가 이미 있는지(캐싱용)."""
    try:
        _get_client().head_object(Bucket=config.S3_BUCKET, Key=key)
        return True
    except Exception:
        return False


def upload_bytes(data: bytes, key: str, content_type: str) -> str:
    """data 를 s3://{bucket}/{key} 로 업로드하고 공개 URL 을 반환."""
    _get_client().put_object(
        Bucket=config.S3_BUCKET,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    return public_url(key)
