import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.constants.category_map import CATEGORY_MAP, REVERSE_CATEGORY_MAP

# ================================
# Decimal 変換ユーティリティ関数
# ================================
def deep_convert(obj: Any) -> Any:
    """
    float → Decimal 変換（DynamoDB 保存時のエラー防止用）
    """
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, list):
        return [deep_convert(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: deep_convert(v) for k, v in obj.items()}
    return obj

# ================================
# DynamoDB 接続およびテーブルオブジェクト
# ================================
dynamodb = boto3.resource("dynamodb")

news_table = dynamodb.Table(os.getenv("DDB_NEWS_TABLE", "NewsCards"))
freq_table = dynamodb.Table(os.getenv("DDB_FREQ_TABLE", "Frequencies"))
users_table = dynamodb.Table(os.getenv("DDB_USERS_TABLE", "Users"))
bookmark_table = dynamodb.Table(os.getenv("DDB_BOOKMARKS_TABLE", "Bookmarks"))

# ============================================
# 1. NewsCards 関連関数
# ============================================

def save_news_card(category: str, article: dict, date_str: str):
    """
    ニュース記事1件をNewsCardsテーブルに保存
    """
    item = {
        "news_id": article["id"],
        "category_date": f"{category}#{date_str}",  # GSI 用の複合キー
        "category": category,
        "section": article.get("sections", [])[0] if article.get("sections") else "domestic",
        "rank": article.get("rank"),
        "title": article.get("title"),
        "title_ko": article.get("title_ko"),
        "summary": article.get("summary"),
        "summary_ko": article.get("summary_ko"),
        "image_url": article.get("image_url"),
        "thumbnail_url": article.get("thumbnail_url") or article.get("thumbnail"),
        "content_url": article.get("content_url"),
        "publisher": article.get("publisher"),
        "author": article.get("author"),
        "published_at": article.get("published_at"),
        "collected_at": datetime.utcnow().isoformat(),
        "companies": article.get("companies", []),
        "esg": article.get("esg", []),
        "content": article.get("content", "")
    }

    try:
        news_table.put_item(Item=deep_convert(item))
    except ClientError as e:
        raise Exception(f"[NewsCards 저장 실패] {e.response['Error']['Message']}")
        # [NewsCards 保存失敗]

def get_news_by_category_and_date(category: str, date: str):
    """
    category と date に基づいてニュースリストを取得（最新 30〜60 件）
    """
    key = f"{category}#{date}"
    try:
        response = news_table.query(
            IndexName="category_date-index",
            KeyConditionExpression="category_date = :key",
            ExpressionAttributeValues={":key": key}
        )
        return response.get("Items", [])
    except ClientError as e:
        raise Exception(f"[NewsCards 조회 실패] {e.response['Error']['Message']}")
        # [NewsCards 取得失敗]

def get_news_card_by_id(news_id: str):
    """
    news_id に基づいてニュース詳細を取得
    """
    try:
        response = news_table.get_item(Key={"news_id": news_id})
        return response.get("Item")
    except ClientError as e:
        raise Exception(f"[뉴스 상세 조회 실패] {e.response['Error']['Message']}")
        # [ニュース詳細取得失敗]

def get_news_card_by_content_url(content_url: str):
    """
    content_url に基づいてニュースを取得（重複確認用）
    """
    try:
        response = news_table.scan(
            FilterExpression="content_url = :url",
            ExpressionAttributeValues={":url": content_url}
        )
        items = response.get("Items", [])
        return items[0] if items else None
    except ClientError as e:
        raise Exception(f"[URL로 뉴스 조회 실패] {e.response['Error']['Message']}")
        # [URL によるニュース取得失敗]

def get_today_news_grouped():
    """
    今日の日付を基準に、カテゴリ別にニュースを6件ずつまとめて返す
    """
    today = datetime.now().strftime("%Y-%m-%d")
    result = {}
    for ko_category, en_category in CATEGORY_MAP.items():
        items = get_news_by_category_and_date(en_category["api_name"], today)
        result[ko_category] = items[:6]
    return result

def update_news_card_content(news_id: str, content: str):
    """
    news_id に基づいて本文（content）を更新
    """
    try:
        news_table.update_item(
            Key={"news_id": news_id},
            UpdateExpression="SET content = :c",
            ExpressionAttributeValues={":c": content}
        )
    except ClientError as e:
        raise Exception(f"[본문 업데이트 실패] {e.response['Error']['Message']}")
        # [本文更新失敗]

def update_news_card_content_by_url(content_url: str, content: str):
    """
    content_url に基づいてニュースを探して本文を更新
    （news_id が不明な場合に使用）
    """
    try:
        response = news_table.scan(
            FilterExpression="content_url = :url",
            ExpressionAttributeValues={":url": content_url}
        )
        items = response.get("Items", [])
        if not items:
            raise Exception(f"[본문 업데이트 실패] URL로 해당 뉴스 없음 → {content_url}")
            # [本文更新失敗] URL に該当するニュースが存在しません

        news_id = items[0]["news_id"]
        update_news_card_content(news_id, content)
    except ClientError as e:
        raise Exception(f"[URL로 본문 업데이트 실패] {e.response['Error']['Message']}")
        # [URL による本文更新失敗]

# ============================================
# 2. Frequencies 関連関数
# ============================================

def save_frequency_summary(item: dict):
    """
    共有要約スクリプトおよび音声情報を保存
    """
    try:
        freq_table.put_item(Item=deep_convert(item))
    except ClientError as e:
        raise Exception(f"[Frequencies 저장 실패] {e.response['Error']['Message']}")

def get_frequency_by_category_and_date(category: str, date: str):
    """
    カテゴリ/日付に基づく共有要約スクリプトの取得
    """
    frequency_id = f"{category}#{date}"
    try:
        response = freq_table.get_item(Key={"frequency_id": frequency_id})
        return response.get("Item")
    except ClientError as e:
        raise Exception(f"[Frequencies 조회 실패] {e.response['Error']['Message']}")

def get_frequency_history_by_categories(categories: list, limit: int = 30):
    """
    ユーザーの関心カテゴリ別の周波数履歴を取得（直近N日）
    """
    try:
        all_frequencies = []
        
        # 各カテゴリごとにデータを収集
        for category in categories:
            # category で始まるすべての frequency_id を取得（category#YYYY-MM-DD 形式）
            response = freq_table.scan(
                FilterExpression="begins_with(frequency_id, :category)",
                ExpressionAttributeValues={
                    ":category": f"{category}#"
                }
            )
            
            items = response.get("Items", [])
            all_frequencies.extend(items)
        
        # 日付順にソート（新しい順）
        all_frequencies.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # 指定数だけ返す
        return all_frequencies[:limit]
        
    except ClientError as e:
        raise Exception(f"[Frequency History 조회 실패] {e.response['Error']['Message']}")
        # [Frequency 履歴取得失敗]

# ============================================
# 3. Users 関連関数
# ============================================

def save_user(user: dict):
    """
    ユーザー情報の保存（新規または更新）
    - created_at, profile_image はデフォルト値を自動設定
    """
    if "created_at" not in user:
        user["created_at"] = datetime.utcnow().isoformat()
    if "profile_image" not in user:
        user["profile_image"] = ""

    try:
        users_table.put_item(Item=deep_convert(user))
    except ClientError as e:
        raise Exception(f"[Users 저장 실패] {e.response['Error']['Message']}")
        # [Users 保存失敗]

def get_user(user_id: str):
    """
    user_id に基づくユーザー情報の取得
    - nickname, profile_image, interests などのデフォルト値を自動設定
    """
    try:
        response = users_table.get_item(Key={"user_id": user_id})
        item = response.get("Item")
        if not item:
            return None

        # デフォルト値の設定
        item.setdefault("nickname", "")
        item.setdefault("profile_image", "")
        item.setdefault("created_at", "")
        item.setdefault("interests", [])
        item.setdefault("onboarding_completed", False)

        return item
    except ClientError as e:
        raise Exception(f"[Users 조회 실패] {e.response['Error']['Message']}")
        # [Users 取得失敗]

# ============================================
# 4. Bookmarks 関連関数
# ============================================

def add_bookmark(user_id: str, news_id: str):
    """
    ブックマーク追加（user_id + news_id の組み合わせ）
    """
    item = {
        "user_id": user_id,
        "news_id": news_id,
        "bookmarked_at": datetime.utcnow().isoformat()
    }
    try:
        bookmark_table.put_item(Item=item)
    except ClientError as e:
        raise Exception(f"[Bookmark 추가 실패] {e.response['Error']['Message']}")
        # [ブックマーク追加失敗]

def get_user_bookmarks(user_id: str):
    """
    user_id に基づいてブックマークリストを取得し、ニュース詳細を含む
    """
    try:
        # ブックマーク一覧の取得
        response = bookmark_table.query(
            KeyConditionExpression="user_id = :uid",
            ExpressionAttributeValues={":uid": user_id},
            ScanIndexForward=False  # 新しい順にソート
        )
        bookmark_items = response.get("Items", [])
        
        # 各ブックマークについてニュース詳細を取得
        bookmarked_news = []
        for bookmark in bookmark_items:
            news_id = bookmark.get("news_id")
            if news_id:
                try:
                    # ニュース詳細の取得
                    news_response = news_table.get_item(Key={"news_id": news_id})
                    news_item = news_response.get("Item")
                    if news_item:
                        # ブックマーク時間を追加
                        news_item["bookmarked_at"] = bookmark.get("bookmarked_at")
                        bookmarked_news.append(news_item)
                except ClientError as e:
                    print(f"뉴스 상세 조회 실패 (news_id: {news_id}): {e}")
                    # ニュース詳細取得失敗
                    continue
        
        return bookmarked_news
    except ClientError as e:
        raise Exception(f"[Bookmark 조회 실패] {e.response['Error']['Message']}")
        # [ブックマーク取得失敗]

def remove_bookmark(user_id: str, news_id: str):
    """
    ブックマーク削除（user_id + news_id のキー）
    """
    try:
        bookmark_table.delete_item(Key={"user_id": user_id, "news_id": news_id})
    except ClientError as e:
        raise Exception(f"[Bookmark 삭제 실패] {e.response['Error']['Message']}")
        # [ブックマーク削除失敗]