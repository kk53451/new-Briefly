from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import os, requests
from datetime import datetime

from app.utils.jwt_service import create_access_token, get_current_user
from app.utils.dynamo import save_user, get_user

router = APIRouter(prefix="/api/auth", tags=["Auth"])

KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

# ✅ 1. 카카오 로그인 URL 리다이렉트
@router.get("/kakao/login")
def kakao_login():
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code"
    )
    return RedirectResponse(kakao_auth_url)

# ✅ 2. 콜백 처리
@router.get("/kakao/callback")
def kakao_callback(code: str):
    # 2-1. 토큰 요청
    token_res = requests.post(
        url="https://kauth.kakao.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": KAKAO_CLIENT_ID,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": code,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_json = token_res.json()
    access_token = token_json.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="카카오 access_token 발급 실패")

    # 2-2. 사용자 정보 요청
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
        raise HTTPException(status_code=400, detail="카카오 사용자 정보 조회 실패")

    # 2-3. DB 저장
    user_id = f"kakao_{kakao_id}"
    user = get_user(user_id)  # ✅ get_user가 None 반환하도록 구성 필요

    if user is None:
        print(f"✅ 신규 사용자 생성: {user_id}")
        save_user({
            "user_id": user_id,
            "nickname": nickname,
            "profile_image": profile_image,
            "created_at": datetime.utcnow().isoformat(),
            "interests": [],
            "onboarding_completed": False,
        })
        user = get_user(user_id)

    if not user or "nickname" not in user:
        raise HTTPException(status_code=500, detail="사용자 저장 실패")

    # 2-4. JWT 토큰 발급
    jwt_token = create_access_token(user_id)
    return JSONResponse({
        "access_token": jwt_token,
        "user_id": user_id,
        "nickname": user["nickname"]
    })

# ✅ 3. 사용자 정보 조회
@router.get("/me")
def auth_me(user: dict = Depends(get_current_user)):
    return user

# ✅ 4. 로그아웃
@router.post("/logout")
def logout():
    return {"message": "로그아웃 완료 (클라이언트 토큰 삭제 권장)"}
