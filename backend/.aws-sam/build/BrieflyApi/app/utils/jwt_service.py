# app/utils/jwt_service.py

import os
import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt as jose_jwt  # jose 사용 시

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60))

# OAuth2PasswordBearer는 token을 Header에서 추출하는 역할만 함
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # 실제 토큰 발급 엔드포인트는 Kakao 인증 기반이므로 사용 X, 형식용

def create_access_token(user_id: str) -> str:
    """
    주어진 user_id를 기반으로 JWT 액세스 토큰을 생성하여 반환
    """
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    HTTP Authorization 헤더에서 JWT 토큰을 읽어 현재 로그인된 사용자 ID를 추출
    """
    try:
        payload = jose_jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="토큰에서 사용자 ID를 찾을 수 없습니다.")
        return {"user_id": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 정보입니다 (JWT 디코딩 실패).",
        )
