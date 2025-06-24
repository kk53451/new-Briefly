# app/utils/jwt_service.py

import os
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# PyJWTライブラリを直接インポート
try:
    import jwt
except ImportError:
    raise ImportError("PyJWT 라이브러리가 설치되어 있지 않습니다. 'pip install PyJWT'를 실행하세요.")
    # PyJWTライブラリがインストールされていません。「pip install PyJWT」を実行してください。

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256") 
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", 60))

# OAuth2PasswordBearerはトークンをヘッダーから抽出する役割のみを果たす
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # 実際のトークン発行エンドポイントはKakao認証ベースなので使用しない。形式用。


def create_access_token(user_id: str) -> str:
    """
    指定されたuser_idを元にJWTアクセストークンを生成して返す
    """
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    }
    try:
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"JWT 토큰 생성 실패: {str(e)}")
        # JWTトークンの生成に失敗しました


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    HTTP AuthorizationヘッダーからJWTトークンを読み取り、現在ログイン中のユーザーの全情報を返す
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="토큰에서 사용자 ID를 찾을 수 없습니다.")
            # トークンからユーザーIDを見つけることができません

        # DynamoDBからユーザーの全情報を取得
        from app.utils.dynamo import get_user
        user = get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
            # ユーザーが見つかりません

        return user
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 정보입니다 (JWT 디코딩 실패).",
            # 無効な認証情報です（JWTのデコードに失敗しました）
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT 토큰 처리 중 오류: {str(e)}",
            # JWTトークン処理中にエラーが発生しました
        )
