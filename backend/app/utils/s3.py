import os
import boto3
from datetime import datetime

# S3クライアントとバケット名の設定
s3 = boto3.client("s3")
BUCKET_NAME = os.getenv("S3_BUCKET", "briefly-news-audio")

def upload_audio_to_s3(file_bytes: bytes, user_id: str, category: str, date: str) -> str:
    """
    MP3ファイルをS3にアップロードし、公開URLを返す（静的アクセス方式）
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
    MP3ファイルをアップロード後、指定時間有効なpresigned URLを返す（デフォルトは24時間）
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
