from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
import os, requests
from datetime import datetime

from app.utils.jwt_service import create_access_token, get_current_user
from app.utils.dynamo import save_user, get_user

# ✅ 인증 관련 라우터 (prefix: /api/auth)
router = APIRouter(prefix="/api/auth", tags=["Auth"])

# ✅ .env 파일에서 카카오 OAuth 정보 불러오기
KAKAO_CLIENT_ID = os.getenv("KAKAO_CLIENT_ID")
KAKAO_REDIRECT_URI = os.getenv("KAKAO_REDIRECT_URI")

# ✅ 1. 카카오 로그인 페이지로 리다이렉트
@router.get("/kakao/login")
def kakao_login():
    """
    카카오 로그인 URL로 리다이렉트합니다.
    프론트에서 해당 API 호출 시, 카카오 로그인 페이지로 이동합니다.
    """
    kakao_auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_CLIENT_ID}&redirect_uri={KAKAO_REDIRECT_URI}&response_type=code"
    )
    return RedirectResponse(kakao_auth_url)

# ✅ 2. 카카오 로그인 콜백 → 토큰 발급 + 사용자 정보 저장 + JWT 발급
@router.get("/kakao/callback")
def kakao_callback(code: str):
    """
    카카오 OAuth 콜백 처리:
    - 인가 코드(code)를 받아 카카오 access_token 발급
    - 사용자 정보 조회
    - DB에 사용자 저장 (신규 시)
    - JWT access_token 발급 및 반환
    """

    # 🔹 2-1. 인가 코드로 access token 요청
    token_url = "https://kauth.kakao.com/oauth/token"
    token_data = {
        "grant_type": "authorization_code",
        "client_id": KAKAO_CLIENT_ID,
        "redirect_uri": KAKAO_REDIRECT_URI,
        "code": code,
    }
    token_headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_res = requests.post(token_url, data=token_data, headers=token_headers)
    token_json = token_res.json()

    if "access_token" not in token_json:
        raise HTTPException(status_code=400, detail="카카오 토큰 발급 실패")

    access_token = token_json["access_token"]

    # 🔹 2-2. 카카오 사용자 정보 요청
    profile_url = "https://kapi.kakao.com/v2/user/me"
    profile_headers = {"Authorization": f"Bearer {access_token}"}
    profile_res = requests.get(profile_url, headers=profile_headers)
    profile_json = profile_res.json()

    kakao_id = profile_json.get("id")
    kakao_account = profile_json.get("kakao_account", {})
    nickname = kakao_account.get("profile", {}).get("nickname", "익명")
    profile_image = kakao_account.get("profile", {}).get("profile_image_url", "")

    if not kakao_id:
        raise HTTPException(status_code=400, detail="카카오 사용자 정보 조회 실패")

    # 🔹 2-3. 유저 정보 DB에 저장 (이미 존재하지 않는 경우에만)
    user_id = f"kakao_{kakao_id}"
    user = get_user(user_id)
    if not user:
        user = {
            "user_id": user_id,
            "nickname": nickname,
            "profile_image": profile_image,
            "created_at": datetime.utcnow().isoformat(),
            "interests": [],
            "onboarding_completed": False,
        }
        save_user(user)

    # 🔹 2-4. JWT access token 발급 및 반환
    jwt_token = create_access_token(user_id)
    return JSONResponse({
        "access_token": jwt_token,
        "user_id": user_id,
        "nickname": user["nickname"]
    })

# ✅ 3. 현재 로그인된 사용자 정보 조회
@router.get("/me")
def auth_me(user: dict = Depends(get_current_user)):
    """
    JWT 토큰을 통해 인증된 사용자의 정보를 반환합니다.
    """
    return user

# ✅ 4. 로그아웃 처리 (실제 동작은 클라이언트에서 토큰 제거)
@router.post("/logout")
def logout():
    """
    클라이언트가 JWT 토큰을 삭제하도록 안내합니다.
    (서버는 세션을 따로 관리하지 않음)
    """
    return {"message": "로그아웃 완료 (클라이언트 토큰 삭제 권장)"}
