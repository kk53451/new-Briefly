import os
import boto3
from datetime import datetime

# S3 클라이언트 및 버킷 이름 설정
s3 = boto3.client("s3")
BUCKET_NAME = os.getenv("S3_BUCKET", "briefly-news-audio")

def upload_audio_to_s3(file_bytes: bytes, user_id: str, category: str, date: str) -> str:
    """
    MP3 파일을 S3에 업로드하고 공개 URL 반환 (정적 접근 방식)
    """
    object_key = f"news-audio/{date}/{user_id}/{category}.mp3"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=file_bytes,
        ContentType="audio/mpeg"
    )

    return f"https://{BUCKET_NAME}.s3.amazonaws.com/{object_key}"


def upload_audio_to_s3_presigned(
    file_bytes: bytes,
    user_id: str,
    category: str,
    date: str,
    expires_in_seconds: int = 86400
) -> str:
    """
    MP3 파일 업로드 후, 일정 시간 유효한 presigned URL 반환 (기본 24시간)
    """
    object_key = f"news-audio/{date}/{user_id}/{category}.mp3"

    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=object_key,
        Body=file_bytes,
        ContentType="audio/mpeg"
    )

    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": BUCKET_NAME, "Key": object_key},
        ExpiresIn=expires_in_seconds
    )
