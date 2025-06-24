from fastapi import APIRouter, Depends, HTTPException
from app.utils.jwt_service import get_current_user
from app.utils.dynamo import (
    get_user,
    save_user,
    get_user_bookmarks,
    get_frequency_by_category_and_date  #  共有スクリプトベース
)
from app.utils.date import get_today_kst

# /api/user 以下のエンドポイントグループ
router = APIRouter(prefix="/api/user", tags=["User"])

# [GET] /api/user/profile
@router.get("/profile")
def get_profile(user: dict = Depends(get_current_user)):
    """
    ログイン中のユーザープロフィール情報を取得

    - 応答項目: user_id, nickname, profile_image, interests, onboarding_completed など
    - 使用例: マイページ表示時のプロフィール描画
    """
    return user

# [PUT] /api/user/profile
@router.put("/profile")
def update_profile(
    nickname: str = None,
    default_length: int = None,
    profile_image: str = None,
    user: dict = Depends(get_current_user)
):
    """
    ユーザープロフィール情報を更新

    - パラメータは任意（nickname, default_length, profile_image）
    - 指定された値のみを更新
    - 使用例: プロフィール編集画面での保存操作
    """
    if nickname:
        user["nickname"] = nickname
    if default_length:
        user["default_length"] = default_length
    if profile_image:
        user["profile_image"] = profile_image

    save_user(user)
    return {"message": "プロフィールが更新されました。"}

# [GET] /api/user/bookmarks
@router.get("/bookmarks")
def get_bookmarks(user: dict = Depends(get_current_user)):
    """
    ユーザーがブックマークしたニュース一覧を取得

    - 応答: ブックマークされたニュースカードの配列
    - 使用例: ブックマークタブやプロフィール「マイニュース」セクション
    """
    return get_user_bookmarks(user["user_id"])

# [GET] /api/user/frequencies
@router.get("/frequencies")
def get_my_frequencies(user: dict = Depends(get_current_user)):
    """
    ユーザーの関心カテゴリごとの共有周波数要約（TTSスクリプトと音声）を取得

    - 本日の日付を基準に取得
    - 使用例: 「マイ周波数」タブアクセス時に自動取得
    """
    today = get_today_kst()
    results = []

    for category in user.get("interests", []):
        item = get_frequency_by_category_and_date(category, today)
        if item:
            results.append(item)

    return results

# [GET] /api/user/categories
@router.get("/categories")
def get_my_categories(user: dict = Depends(get_current_user)):
    """
    ユーザーの関心カテゴリリストを取得

    - 使用例: オンボーディング画面やマイページ→カテゴリ設定時
    """
    return {"interests": user.get("interests", [])}

# [PUT] /api/user/categories
@router.put("/categories")
def update_my_categories(interests: list[str], user: dict = Depends(get_current_user)):
    """
    ユーザーの関心カテゴリを更新

    - パラメータ: interests（韓国語カテゴリ名のリスト）
    - 使用例: オンボーディング完了時、マイページでのカテゴリ変更時
    """
    user["interests"] = interests
    save_user(user)
    return {"message": "関心カテゴリが更新されました。"}

# [POST] /api/user/onboarding
@router.post("/onboarding")
def complete_onboarding(user: dict = Depends(get_current_user)):
    """
    オンボーディング完了処理（初期設定完了後に呼び出される）

    - user["onboarding_completed"] = True フラグを設定
    """
    user["onboarding_completed"] = True
    save_user(user)
    return {"message": "オンボーディングが完了しました。"}

# [GET] /api/user/onboarding/status
@router.get("/onboarding/status")
def onboarding_status(user: dict = Depends(get_current_user)):
    """
    オンボーディングの完了状況を確認

    - 応答: { onboarded: True/False }
    - 使用例: 初回アクセス時にオンボーディング画面を表示するか判断
    """
    return {"onboarded": user.get("onboarding_completed", False)}

# [GET] /onboarding - フロントエンドからのリクエストに対応
@router.get("/onboarding")
def get_onboarding_page(user: dict = Depends(get_current_user)):
    """
    オンボーディングページ用の情報を提供

    - オンボーディング完了状況とユーザー基本情報を返す
    - 使用例: フロントエンドが /onboarding ページを表示する際
    """
    return {
        "user_id": user["user_id"],
        "nickname": user.get("nickname", ""),
        "onboarding_completed": user.get("onboarding_completed", False),
        "interests": user.get("interests", [])
    }
