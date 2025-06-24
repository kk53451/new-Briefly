import os
import requests
from app.utils.s3 import upload_audio_to_s3

# 環境変数から ElevenLabs の APIキーと音声ID を取得
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

def text_to_speech(text: str) -> bytes:
    """
    テキストを ElevenLabs の TTS API により音声（MP3）に変換します。
    APIドキュメントに基づいた安全な設定。
    """
    if not text or len(text.strip()) < 100:
        raise ValueError("TTS 변환 실패: 입력 텍스트가 너무 짧습니다")
        # TTS変換失敗：入力テキストが短すぎます

    # APIドキュメントに準拠した正しいURLとパラメータ構造
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=mp3_44100_128"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    
    # 検証済みの安全な設定（APIドキュメント基準）
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.45,          # 自然な変化を許容
            "similarity_boost": 0.85,   # 音声の個性を強調
            "style": 0.15,              # 少しのスタイル変化を許容
        }
    }

    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise Exception(f"ElevenLabs TTS 실패: {response.status_code} {response.text}")
        # ElevenLabs TTS失敗時のエラーハンドリング

    return response.content

def text_to_speech_with_prosody(text: str) -> bytes:
    """
    自然なイントネーションと感情表現のための強化TTS変換。
    """
    # 自然なイントネーションのためのテキスト前処理
    enhanced_text = enhance_text_for_natural_speech(text)
    return text_to_speech(enhanced_text)

def enhance_text_for_natural_speech(text: str) -> str:
    """
    自然な音声出力のための高級テキスト強化。
    韓国語TTS最適化と自然なイントネーションの実現。
    """
    import re
    
    # 1. 句読点の整理と呼吸ポイントの調整
    text = re.sub(r'\.(?!\s*$)', '. ', text)
    text = re.sub(r'\!(?!\s*$)', '! ', text)
    text = re.sub(r'\?(?!\s*$)', '? ', text)
    text = re.sub(r'\,(?!\s)', ', ', text)
    
    # 2. 自然なイントネーションのための間投詞とあいづちの強化
    text = re.sub(r'그런데(?!\s)', '그런데... ', text)
    text = re.sub(r'하지만(?!\s)', '하지만... ', text)
    text = re.sub(r'그리고(?!\s)', '그리고, ', text)
    text = re.sub(r'또한(?!\s)', '또한, ', text)
    text = re.sub(r'특히(?!\s)', '특히... ', text)
    text = re.sub(r'정말(?!\s)', '정말로 ', text)
    
    # 3. 数字と単位表現の自然な調整
    text = re.sub(r'(\d+)%', r'\1 퍼센트', text)
    text = re.sub(r'(\d+)억', r'\1억', text)
    text = re.sub(r'(\d+)만', r'\1만', text)
    text = re.sub(r'(\d{1,3})(,\d{3})+', lambda m: m.group().replace(',', ''), text)
    
    # 4. 専門用語や固有名詞の前後に余白を追加
    text = re.sub(r'([A-Z]{2,})', r' \1 ', text)
    text = re.sub(r'(\w+API|\w+AI)', r' \1 ', text)
    
    # 5. 強調表現の改善
    text = re.sub(r'중요한(?!\s)', '정말 중요한 ', text)
    text = re.sub(r'놀라운(?!\s)', '정말 놀라운 ', text)
    text = re.sub(r'흥미로운(?!\s)', '매우 흥미로운 ', text)
    
    # 6. 自然なリズムと呼吸のための文分割
    sentences = text.split('. ')
    enhanced_sentences = []
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        # 長い文を自然に分割（100文字以上）
        if len(sentence) > 100:
            # 接続詞やカンマで分割
            connectors = ['그런데', '하지만', '또한', '그리고', '특히', '즉', '다시 말해']
            for connector in connectors:
                if connector in sentence:
                    parts = sentence.split(connector, 1)
                    if len(parts) == 2:
                        sentence = parts[0].strip() + '. ' + connector + ' ' + parts[1].strip()
                        break
            # カンマ基準の分割（まだ長ければ）
            if len(sentence) > 120:
                comma_parts = sentence.split(', ')
                if len(comma_parts) > 2:
                    mid_point = len(comma_parts) // 2
                    sentence = ', '.join(comma_parts[:mid_point]) + '. ' + ', '.join(comma_parts[mid_point:])
        enhanced_sentences.append(sentence)
    # 7. 最終整理と不要な空白削除
    result = '. '.join(enhanced_sentences)
    result = re.sub(r'\s+', ' ', result)
    result = re.sub(r'\s+([,.!?])', r'\1', result)
    return result.strip()

def text_to_speech_and_store(text: str, user_id: str, category: str, date: str) -> str:
    """
    高度なTTS変換 → S3アップロード → Presigned URL返却
    """
    audio_bytes = text_to_speech_with_prosody(text)
    return upload_audio_to_s3(audio_bytes, user_id, category, date)
