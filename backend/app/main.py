# app/main.py

import os
from fastapi import FastAPI
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv  # ✅ dotenv 로드 추가

# ✅ .env 환경변수 불러오기
load_dotenv()

# ✅ 라우터 임포트
from app.routes import (
    auth,
    category,
    frequency,
    news,
    user
)

# ✅ FastAPI 인스턴스 생성
app = FastAPI(title="Briefly API")

# ✅ 라우터 등록
app.include_router(auth.router)
app.include_router(category.router)
app.include_router(frequency.router)
app.include_router(news.router)
app.include_router(user.router)

# ✅ CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 구체적인 도메인으로 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ AWS Lambda용 Mangum 핸들러
handler = Mangum(app)

# ✅ 루트 헬스 체크
@app.get("/")
def read_root():
    return {"message": "Welcome to Briefly API"}
