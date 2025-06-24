from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.utils.dynamo import (
    get_news_by_category_and_date,
    get_news_card_by_id,
    get_today_news_grouped,
    add_bookmark,
    remove_bookmark
)
from app.utils.jwt_service import get_current_user
from app.constants.category_map import CATEGORY_MAP, REVERSE_CATEGORY_MAP
from typing import List
from datetime import datetime
import pytz
import random

# /api/news 以下のエンドポイントグループ
router = APIRouter(prefix="/api/news", tags=["News"])

# ブックマークリクエストモデル
class BookmarkRequest(BaseModel):
    news_id: str

# [GET] /api/news?category=xxx（trailing slash 有無両方に対応）
@router.get("/")
@router.get("")
def get_news(category: str = Query(..., description="ニュースカテゴリ")):
    """
    特定カテゴリの本日ニュースリストを取得（最大10件）

    - パラメータ: category（例: "政治", "経済", "전체"）
    - ソート基準: 人気順または収集順（現在は上位10件をスライス）
    - 使用例: 「マイニュース」タブなどでカテゴリ別に表示
    """
    print(f" ニュース取得リクエスト - 韓国語カテゴリ: '{category}'")
    
    kst = pytz.timezone("Asia/Seoul")
    today = datetime.now(kst).strftime("%Y-%m-%d")
    print(f" 取得日付: {today}")
    
    # 「전체」カテゴリの場合、すべてのカテゴリのニュースをシャッフル
    if category == "전체":
        print(f" 全カテゴリのニュース取得開始")
        category_news = {}  # カテゴリごとのニュースを格納
        
        # 各カテゴリごとにニュースを取得（カテゴリ順を固定）
        for ko_category, config in CATEGORY_MAP.items():
            en_category = config["api_name"]
            try:
                items = get_news_by_category_and_date(en_category, today)
                if items:
                    # 各カテゴリ内で発行日時順にソート（最新順）
                    sorted_items = sorted(items, key=lambda x: x.get("published_at", ""), reverse=True)
                    # 各カテゴリから最大8件ずつ取得（多様性確保）
                    selected_items = sorted_items[:8]
                    category_news[ko_category] = selected_items
                else:
                    category_news[ko_category] = []
            except Exception as e:
                category_news[ko_category] = []
        
        # カテゴリごとにラウンドロビン方式で均等に混ぜる
        mixed_news = []
        max_rounds = max(len(news_list) for news_list in category_news.values()) if category_news.values() else 0
        
        # カテゴリ順を固定（毎回同じ順序を保証）
        categories = list(CATEGORY_MAP.keys())
        
        for round_num in range(max_rounds):
            for category_name in categories:
                news_list = category_news[category_name]
                if round_num < len(news_list):
                    news_item = news_list[round_num]
                    # 重複チェック
                    if not any(existing.get("news_id") == news_item.get("news_id") for existing in mixed_news):
                        mixed_news.append(news_item)
        
        # 最大30件に制限
        result = mixed_news[:30]
        
        print(f" 全体ニュース {len(result)}件返却完了")
        
        return result
    
    # 特定カテゴリの場合の既存ロジック
    # 韓国語カテゴリを英語に変換
    if category in CATEGORY_MAP:
        en_category = CATEGORY_MAP[category]["api_name"]
        print(f" 変換された英語カテゴリ: '{en_category}'")
    else:
        print(f" 未対応カテゴリ: '{category}'")
        print(f" サポートカテゴリ一覧: {list(CATEGORY_MAP.keys())} + ['전체']")
        raise HTTPException(status_code=400, detail=f"サポートされていないカテゴリです: {category}")
    
    items = get_news_by_category_and_date(en_category, today)
    
    print(f" 取得ニュース件数: {len(items) if items else 0}")
    
    if not items:
        print(f" '{en_category}' カテゴリに {today} のニュースがありません")
        return []
    
    result = items[:10]
    print(f" 返却するニュース件数: {len(result)}")
    
    return result

# [GET] /api/news/today
@router.get("/today")
def get_today_news():
    """
    今日のニュースタブ：カテゴリごとに代表ニュースを6件ずつグループ化して返却

    - 内部でDynamoDBからカテゴリごとに6件ずつ取得
    - 使用例：「今日のニュース」タブでのカードスライド表示
    - 返却例: { "政治": [...6件], "経済": [...6件], ... }
    """
    return get_today_news_grouped()

# [GET] /api/news/{news_id}
@router.get("/{news_id}")
def get_news_detail(news_id: str):
    """
    個別ニュースカードの詳細情報を取得

    - ニュースIDを元に詳細データを返却
    - content, publisher, summary などを含む
    - 存在しない場合は404を返す
    """
    item =  get_news_card_by_id(news_id)
    if not item:
        raise HTTPException(status_code=404, detail="ニュースが見つかりません。")
    return item

# [POST] /api/news/bookmark
@router.post("/bookmark")
def bookmark_news(request: BookmarkRequest, user=Depends(get_current_user)):
    """
    ニュースをブックマークに追加

    - 認証が必要
    - ブックマークされたニュースはユーザーのブックマークリストで確認可能
    - 使用例: ニュースカードのブックマークボタンをクリック時
    """
    print(f" ブックマーク追加リクエスト - ユーザー: {user['user_id']}, ニュース: {request.news_id}")
    add_bookmark(user_id=user["user_id"], news_id=request.news_id)
    return {"message": "ブックマークが完了しました"}

# [DELETE] /api/news/bookmark/{news_id}
@router.delete("/bookmark/{news_id}")
def delete_bookmark(news_id: str, user=Depends(get_current_user)):
    """
    ニュースのブックマークを削除

    - 認証が必要
    - 使用例: ブックマークタブやニュースカードでのブックマーク解除時
    """
    print(f" ブックマーク削除リクエスト - ユーザー: {user['user_id']}, ニュース: {news_id}")
    remove_bookmark(user_id=user["user_id"], news_id=news_id)
    return {"message": "ブックマークが削除されました"}
