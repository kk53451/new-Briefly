from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.jwt_service import get_current_user
from app.utils.dynamo import get_frequency_by_category_and_date, get_frequency_history_by_categories, save_frequency_summary
from app.utils.date import get_today_kst
from app.constants.category_map import CATEGORY_MAP
import requests
import boto3
import os
from urllib.parse import urlparse

# S3クライアントの初期化
s3 = boto3.client("s3")
BUCKET_NAME = os.getenv("S3_BUCKET", "briefly-news-audio")

def regenerate_presigned_url(audio_url: str, expires_in_seconds: int = 604800) -> str:
    """
    既存のS3オブジェクトに対して新しいpresigned URLを生成
    """
    try:
        # URLからS3オブジェクトキーを抽出
        parsed_url = urlparse(audio_url)
        if "amazonaws.com" in parsed_url.netloc:
            # https://bucket.s3.amazonaws.com/path または https://s3.amazonaws.com/bucket/path 形式
            if parsed_url.netloc.startswith(BUCKET_NAME):
                object_key = parsed_url.path.lstrip('/')
            else:
                # s3.amazonaws.com/bucket/path 形式
                path_parts = parsed_url.path.lstrip('/').split('/', 1)
                if len(path_parts) > 1:
                    object_key = path_parts[1]
                else:
                    return audio_url
        else:
            return audio_url
            
        # 新しいpresigned URLを生成
        new_url = s3.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": BUCKET_NAME, "Key": object_key},
            ExpiresIn=expires_in_seconds
        )
        
        return new_url
        
    except Exception as e:
        print(f" Presigned URLの再生成に失敗: {str(e)}")
        return audio_url

def validate_and_refresh_audio_urls(frequencies: list) -> list:
    """
    周波数リストのaudio_urlを検証し、必要に応じて新しいpresigned URLに置き換え
    """
    updated_frequencies = []
    
    for freq in frequencies:
        if not freq.get("audio_url"):
            updated_frequencies.append(freq)
            continue
            
        # URLの有効性を簡易チェック（HEADリクエスト）
        try:
            response = requests.head(freq["audio_url"], timeout=3)
            if response.status_code == 200:
                # URLが有効
                updated_frequencies.append(freq)
            else:
                # URLが期限切れ、再生成
                print(f"期限切れのaudio_urlを再生成: {freq.get('frequency_id')}")
                new_audio_url = regenerate_presigned_url(freq["audio_url"])
                
                freq_copy = freq.copy()
                freq_copy["audio_url"] = new_audio_url
                
                # DynamoDBを更新
                save_frequency_summary(freq_copy)
                updated_frequencies.append(freq_copy)
                
        except Exception as e:
            # ネットワークエラーなどで検証失敗時も再生成を試みる
            print(f" URL検証失敗、再生成試行: {str(e)}")
            new_audio_url = regenerate_presigned_url(freq["audio_url"])
            freq_copy = freq.copy()
            freq_copy["audio_url"] = new_audio_url
            updated_frequencies.append(freq_copy)
    
    return updated_frequencies

# /api/frequencies エンドポイントグループ
router = APIRouter(prefix="/api/frequencies", tags=["Frequency"])

# [GET] /api/frequencies
@router.get("")
def get_frequencies(user: dict = Depends(get_current_user)):
    """
    本日の日付を基準に、ユーザーの関心カテゴリごとの共有要約（TTSスクリプトと音声）を返します。

    - 各カテゴリに対し、事前に生成された共有周波数をDynamoDBから取得
    - フロントではユーザーの関心ベースでの音声リスト表示に使用
    - 戻り値: [{category, script, audio_url, ...}, ...]
    """
    date = get_today_kst()
    results = []

    for korean_category in user.get("interests", []):
        # 韓国語カテゴリを英語カテゴリに変換
        if korean_category in CATEGORY_MAP:
            english_category = CATEGORY_MAP[korean_category]["api_name"]
            item = get_frequency_by_category_and_date(english_category, date)
            if item:
                results.append(item)

    # audio_url の検証および再生成
    validated_results = validate_and_refresh_audio_urls(results)
    
    return validated_results

# [GET] /api/frequencies/history
@router.get("/history")
def get_frequency_history(
    user: dict = Depends(get_current_user),
    limit: int = Query(default=30, ge=1, le=100, description="取得する履歴の件数（最大100）")
):
    """
    ユーザーの関心カテゴリに対応する周波数の履歴を返します。

    - ユーザーの関心カテゴリに関連する過去の周波数データを日付順で返却
    - 本日分は除外し、過去のみ返す
    - 戻り値: [{frequency_id, category, script, audio_url, date, created_at}, ...]
    """
    user_interests = user.get("interests", [])
    if not user_interests:
        return []
    
    # 韓国語カテゴリを英語に変換
    english_categories = []
    for korean_category in user_interests:
        if korean_category in CATEGORY_MAP:
            english_categories.append(CATEGORY_MAP[korean_category]["api_name"])
    
    if not english_categories:
        return []
    
    # 全履歴取得（余分に取得しておく）
    all_history = get_frequency_history_by_categories(english_categories, limit + 10)
    
    # 本日の日付を除外
    today = get_today_kst()
    past_history = [item for item in all_history if item.get("date") != today]
    
    # 件数制限を適用
    limited_history = past_history[:limit]
    
    # audio_url の検証および再生成
    validated_history = validate_and_refresh_audio_urls(limited_history)
    
    return validated_history

# [GET] /api/frequencies/{category}
@router.get("/{category}")
def get_frequency_detail(category: str, user: dict = Depends(get_current_user)):
    """
    特定カテゴリの共有周波数の詳細情報を取得します。

    - ユーザーの関心とは無関係に直接アクセス可能
    - 共有された script（要約テキスト）と audio_url（MP3）を返却
    - 該当カテゴリに本日のデータがない場合は404
    """
    date = get_today_kst()
    
    # カテゴリが韓国語なら英語に変換
    if category in CATEGORY_MAP:
        english_category = CATEGORY_MAP[category]["api_name"]
    else:
        # すでに英語カテゴリならそのまま使用
        english_category = category
    
    result = get_frequency_by_category_and_date(english_category, date)
    if not result:
        raise HTTPException(status_code=404, detail="該当する周波数が存在しません。")
    return result
