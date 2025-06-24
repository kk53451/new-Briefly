import os
from fastapi import FastAPI
from mangum import Mangum
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# .envファイルの環境変数を読み込む
load_dotenv()

# ルーターのインポート
from app.routes import (
    auth,
    category,
    frequency,
    news,
    user
)

# カテゴリーマップのインポート
from app.constants.category_map import CATEGORY_KO_LIST

# FastAPIインスタンスの作成
app = FastAPI(
    title="Briefly API",
    redirect_slashes=False  # URL末尾のスラッシュによる自動リダイレクトを防ぐ
)

# ルーターの登録
app.include_router(auth.router)
app.include_router(category.router)
app.include_router(frequency.router)
app.include_router(news.router)
app.include_router(user.router)

# CORSミドルウェアの設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のドメインに制限することを推奨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# AWS Lambda対応のMangumハンドラー
handler = Mangum(app)

# ルートのヘルスチェックエンドポイント
@app.get("/")
def read_root():
    return {"message": "Welcome to Briefly API"}

# オンボーディングページのエンドポイント（フロントエンドの要求に対応）
@app.get("/onboarding")
def get_onboarding_info():
    """
    オンボーディングページ情報を提供（認証不要）

    - フロントエンドが /onboarding パスにアクセスした際のレスポンス
    """
    return {
        "message": "온보딩 페이지입니다",  # オンボーディングページです
        "available_categories": CATEGORY_KO_LIST  # 利用可能なカテゴリ一覧
    }
