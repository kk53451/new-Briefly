from fastapi import APIRouter, Depends, HTTPException
from app.utils.jwt_service import get_current_user
from app.utils.dynamo import get_user, save_user
from app.constants.category_map import CATEGORY_KO_LIST

# カテゴリ関連のルーター設定（prefix: /api）
router = APIRouter(prefix="/api", tags=["Categories"])

# [GET] /api/categories
@router.get("/categories")
def get_all_categories():
    """
    全カテゴリのリストを返します。
    - フロントエンドのオンボーディング/プロフィール設定画面で使用
    """
    return {"categories": CATEGORY_KO_LIST}

# [GET] /api/user/categories
@router.get("/user/categories")
def get_user_categories(user: dict = Depends(get_current_user)):
    """
    ログイン中のユーザーの関心カテゴリを返します。
    - JWT認証によりユーザー情報を取得
    - ユーザーは複数のカテゴリを選択可能
    """
    interests = user.get("interests", [])
    return {"user_id": user["user_id"], "interests": interests}

# [PUT] /api/user/categories
@router.put("/user/categories")
def update_user_categories(data: dict, user: dict = Depends(get_current_user)):
    """
    ログイン中のユーザーの関心カテゴリを更新します。
    - リクエストBody例: {"interests": ["정치", "경제", "IT/과학"]}
    - 関心カテゴリはDynamoDBのUsersテーブルに保存されます
    """
    selected = data.get("interests", [])
    if not isinstance(selected, list):
        raise HTTPException(status_code=400, detail="interestsはリストである必要があります")
    
    # 有効なカテゴリかどうかを検証
    invalid_categories = [cat for cat in selected if cat not in CATEGORY_KO_LIST]
    if invalid_categories:
        raise HTTPException(
            status_code=400, 
            detail=f"サポートされていないカテゴリです: {invalid_categories}"
        )

    user["interests"] = selected
    save_user(user)
    return {"message": "関心カテゴリが更新されました", "interests": selected}
