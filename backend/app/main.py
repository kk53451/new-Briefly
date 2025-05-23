# app/main.py

from fastapi import FastAPI
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware

from app.routes import (
    auth,
    category,
    frequency,
    news,
    user
)

app = FastAPI(title="Briefly API")

# ✅ 라우터 등록
app.include_router(auth.router)
app.include_router(category.router)
app.include_router(frequency.router)
app.include_router(news.router)
app.include_router(user.router)

# ✅ CORS 미들웨어
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 운영 환경에서는 보안상 도메인 제한 권장
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Lambda 핸들러용 Wrapping
handler = Mangum(app)

# ✅ 루트 헬스 체크
@app.get("/")
def read_root():
    return {"message": "Welcome to Briefly API"}
