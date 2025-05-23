import os
import requests
from app.utils.s3 import upload_audio_to_s3

# 환경 변수에서 ElevenLabs API 키와 음성 ID 불러오기
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

def text_to_speech(text: str) -> bytes:
    # 텍스트를 ElevenLabs TTS API로 음성(MP3) 변환
    if not text or len(text.strip()) < 100:
        raise ValueError("TTS 변환 실패: 입력 텍스트가 너무 짧습니다")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.4,           # 발음 안정성 조절
            "similarity_boost": 0.75    # 화자의 특성 유지 정도
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"ElevenLabs TTS 실패: {response.status_code} {response.text}")

    return response.content  # MP3 파일 바이너리 반환

def text_to_speech_and_store(text: str, user_id: str, category: str, date: str) -> str:
    # 텍스트 → 음성 변환 → S3 업로드 → Presigned URL 반환
    audio_bytes = text_to_speech(text)
    return upload_audio_to_s3(audio_bytes, user_id, category, date)
