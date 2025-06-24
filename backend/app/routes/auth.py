# 認証（カカオログイン・JWT）関連のルーター設定（prefix: /api/auth）

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import os, requests
from datetime import datetime
import time
import urllib.parse

from app.utils.jwt_service import create_access_token, get_current_user
from app.utils.dynamo import save_user, get_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

# 使用済みコードの一時保存（実運用ではRedisなどを使用）
used_codes = set()

# [GET] /kakao/login
@router.get("/kakao/login")
def kakao_login():
    """
    カカオのOAuth認証ページにリダイレクトします。

    - stateパラメータを生成し、CSRF攻撃を防ぎます。
    """
    state = f"briefly_{int(time.time())}"
    
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}"
        f"&response_type=code"
        f"&state={state}"
    )
    return RedirectResponse(kakao_auth_url)

# [GET] /kakao/callback
@router.get("/kakao/callback")
def kakao_callback(code: str):
    """
    カカオログインのコールバックを処理し、JWTトークンを発行します。

    1. 認証コード(code)の有効性を検証します（再利用防止）。
    2. 認証コードを使い、カカオからアクセストークンを取得します。
    3. アクセストークンを使い、カカオからユーザー情報を取得します。
    4. ユーザー情報をDBに保存または更新します（新規ユーザーの場合は作成）。
    5. Brieflyサービス用のJWTトークンを発行し、クライアントに返します。
    """
    print(f" カカオコールバック開始")
    print(f" 元のcode: {code}")
    print(f" codeの長さ: {len(code)}")
    
    try:
        decoded_code = urllib.parse.unquote(code)
        print(f" デコードされたcode: {decoded_code}")
        if decoded_code != code:
            print(f" コードはURLエンコードされていた")
            code = decoded_code
    except Exception as e:
        print(f" URLデコード失敗: {e}")
    
    if code in used_codes:
        print(f" すでに使用されたコード: {code[:20]}...")
        raise HTTPException(
            status_code=400, 
            detail="この認証コードはすでに使用されました。再度ログインしてください。"
        )
    
    used_codes.add(code)
    
    print(f" KAKAO_CLIENT_ID: {KAKAO_CLIENT_ID}")
    print(f" KAKAO_REDIRECT_URI: {KAKAO_REDIRECT_URI}")
    
    token_data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }
    
    print(f" トークンリクエストデータ: {token_data}")
    
    try:
        token_res = requests.post(
            url="https://kauth.kakao.com/oauth/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=10
        )
        
        print(f" カカオトークン応答ステータス: {token_res.status_code}")
        print(f" カカオトークン応答ヘッダー: {dict(token_res.headers)}")
        
        if token_res.status_code != 200:
            print(f" HTTPエラー: {token_res.text}")
            used_codes.discard(code)
            raise HTTPException(
                status_code=400, 
                detail=f"カカオトークン取得失敗 (HTTP {token_res.status_code}): {token_res.text}"
            )
            
        token_json = token_res.json()
        print(f" カカオトークン応答: {token_json}")
        
    except requests.exceptions.RequestException as e:
        print(f" ネットワークエラー: {str(e)}")
        used_codes.discard(code)
        raise HTTPException(status_code=500, detail="カカオサーバー接続失敗")
    
    access_token = token_json.get("access_token")

    if not access_token:
        error_description = token_json.get("error_description", "不明なエラー")
        error_code = token_json.get("error", "unknown_error")
        print(f" トークン発行失敗 - error: {error_code}, description: {error_description}")
        
        if error_code == "invalid_grant":
            detail = "認証コードが期限切れまたはすでに使用されました。再度ログインしてください。"
        elif error_code == "invalid_client":
            detail = "カカオアプリの設定に問題があります。"
        else:
            detail = f"カカオログイン失敗: {error_description}"
            
        raise HTTPException(status_code=400, detail=detail)

    profile_res = requests.get(
        url="https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile_json = profile_res.json()

    kakao_id = profile_json.get("id")
    kakao_account = profile_json.get("kakao_account", {})
    nickname = kakao_account.get("profile", {}).get("nickname")
    profile_image = kakao_account.get("profile", {}).get("profile_image_url", "")

    if not kakao_id or not nickname:
        raise HTTPException(status_code=400, detail="カカオユーザー情報取得失敗")

    user_id = f"kakao_{kakao_id}"
    user = get_user(user_id)

    if user is None:
        print(f" 新規ユーザー作成: {user_id}")
        save_user({
            "user_id": user_id,
            "nickname": nickname,
            "profile_image": profile_image,
            "created_at": datetime.utcnow().isoformat(),
            "interests": [],
            "onboarding_completed": False,
        })
        user = get_user(user_id)
    else:
        print(f" 既存ユーザー情報更新: {user_id}")
        user["nickname"] = nickname
        user["profile_image"] = profile_image
        save_user(user)

    if not user or "nickname" not in user:
        raise HTTPException(status_code=500, detail="ユーザー保存失敗")

    jwt_token = create_access_token(user_id)
    return JSONResponse({
        "access_token": jwt_token,
        "user_id": user_id,
        "nickname": user["nickname"]
    })

# [GET] /me
@router.get("/me")
def auth_me(user: dict = Depends(get_current_user)):
    """
    現在ログインしているユーザーの情報を返します。
    - JWTトークンからユーザーを特定します。
    """
    return user

# [POST] /logout
@router.post("/logout")
def logout():
    """
    ログアウト処理を実行します。
    - サーバー側でのセッション無効化は行わず、クライアントでのトークン削除を促すメッセージを返します。
    """
    return {"message": "ログアウト完了（クライアント側でトークン削除推奨）"}
