# Briefly バックエンド

**FastAPIベースのAIニュースポッドキャストバックエンドシステム**

---

## 概要

Brieflyバックエンドは、毎日ニュースを収集し、AIで要約し、TTSで音声を生成する自動化システムです。

### 主要機能
- **AIニュース要約**: GPT-4o-mini + 二重クラスタリング
- **TTS変換**: ElevenLabs 高品質音声生成
- **スケジューリング**: 毎日6時に自動実行
- **認証**: カカオログイン + JWT
- **データ**: DynamoDB + S3

---

## システムアーキテクチャ

```
 External APIs           Backend Services          Data Storage
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────────┐
│ • OpenAI GPT    │────▶│   FastAPI Lambda    │────▶│   DynamoDB      │
│ • ElevenLabs    │     │                     │     │   - NewsCards   │
│ • DeepSearch    │     │ • API Routes        │     │   - Frequencies │
│ • カカオログイン  │     │ • Services          │     │   - Users       │
└─────────────────┘     │ • Tasks             │     │   - Bookmarks   │
                        └─────────────────────┘     └─────────────────┘
                                   │                          │
                        ┌─────────────────────┐     ┌─────────────────┐
                        │ Scheduler Lambda    │     │   S3 Storage    │
                        │ (Daily 6AM KST)     │     │   - Audio Files │
                        └─────────────────────┘     └─────────────────┘
```

---

## プロジェクト構造

```
backend/
├── app/
│   ├── main.py                     # FastAPIメインアプリケーション
│   ├── constants/
│   │   └── category_map.py         # カテゴリマッピング (韓国語↔英語)
│   ├── services/                   # 主要サービス
│   │   ├── openai_service.py       # GPT要約 + 二重クラスタリング
│   │   ├── deepsearch_service.py   # ニュース収集 + 本文抽出
│   │   └── tts_service.py          # ElevenLabs TTS変換
│   ├── utils/                      # ユーティリティ
│   │   ├── dynamo.py              # DynamoDB接続
│   │   ├── s3.py                  # S3ファイルアップロード
│   │   ├── jwt_service.py         # JWTトークン管理
│   │   └── date.py                # 日付処理 (KST)
│   ├── routes/                     # APIルーター
│   │   ├── auth.py               # カカオログイン
│   │   ├── user.py               # ユーザー管理
│   │   ├── news.py               # ニュース照会
│   │   ├── frequency.py          # 周波数管理
│   │   └── category.py           # カテゴリ照会
│   └── tasks/                     # バッチ処理
│       ├── scheduler.py          # 毎日6時スケジューラー
│       ├── collect_news.py       # ニュース収集
│       └── generate_frequency.py # 音声生成
├── test/                          # ユニットテスト (100% 合格)
│   ├── run_all_tests.py          # 統合テストランナー
│   ├── test_frequency_unit.py    # 主要機能テスト
│   ├── test_clustering.py        # クラスタリングテスト
│   └── ...                       # その他テストファイル
├── template.yaml                  # AWS SAMデプロイ設定
├── requirements.txt               # Python依存関係
└── README.md                      # このファイル
```

---

## 使用方法

### 1. 環境設定

```bash
# 仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt
```

### 2. 環境変数設定

`.env` ファイルを作成:
```env
# AIサービス
OPENAI_API_KEY=sk-proj-...
ELEVENLABS_API_KEY=sk_...
ELEVENLABS_VOICE_ID=TX3LPaxmHKxFdv7VOQHJ

# ニュース収集
DEEPSEARCH_API_KEY=...

# ソーシャルログイン
KAKAO_CLIENT_ID=...

# AWSリソース
DDB_NEWS_TABLE=NewsCards
DDB_FREQ_TABLE=Frequencies
DDB_USERS_TABLE=Users
DDB_BOOKMARKS_TABLE=Bookmarks
S3_BUCKET=briefly-news-audio
```

### 3. ローカル実行

```bash
# FastAPI開発サーバーの実行
uvicorn app.main:app --reload --port 8000

# APIドキュメントの確認
# http://localhost:8000/docs
```

---

## テスト実行

### 全体テスト
```bash
cd test
python run_all_tests.py
```

### 個別テスト (Windows)
```bash
cd test
$env:PYTHONIOENCODING='utf-8'; python test_frequency_unit.py
$env:PYTHONIOENCODING='utf-8'; python test_clustering.py
```

### テスト状況
- **成功率**: 100% (6/6)
- **カバレッジ**: 主要ビジネスロジック 100%
- **実行時間**: 約30秒

---

## 主要機能

### AIニュース要約システム

**二重クラスタリング戦略**
```python
# 1次: 元記事の物理的な重複を除去 (しきい値 0.80)
groups = cluster_similar_texts(full_contents, threshold=0.80)

# 2次: GPT要約文の意味的な重複を除去 (しきい値 0.75)  
final_groups = cluster_similar_texts(summaries, threshold=0.75)
```

**トークン最適化**
- 記事本文: 1500字に制限
- クラスタリング埋め込み: 1000字に制限
- グループ要約: 各記事800字に制限
- 最終台本: 1800-2500字

### TTS変換

**ElevenLabs設定**
```python
voice_settings = {
    "stability": 0.5,
    "similarity_boost": 0.8,
    "style": 0.2,
    "use_speaker_boost": True
}
```

### 自動化スケジューラー

**毎日午前6時 (KST) 実行**
1. ニュース収集 (カテゴリ別30件)
2. 本文の精製とノイズ除去
3. 二重クラスタリングで重複除去
4. GPTでポッドキャスト台本を生成
5. TTSで音声に変換
6. S3に音声ファイルをアップロード
7. DynamoDBにメタデータを保存

---

## APIエンドポイント

### 認証 `/api/auth`
| メソッド | エンドポイント | 説明 |
|--------|------------|------|
| `GET` | `/kakao/login` | カカオログイン開始 |
| `GET` | `/kakao/callback` | ログインコールバック |
| `GET` | `/me` | 自分の情報を照会 |
| `POST` | `/logout` | ログアウト |

### ユーザー `/api/user`
| メソッド | エンドポイント | 説明 |
|--------|------------|------|
| `GET` | `/profile` | プロフィール照会 |
| `PUT` | `/profile` | プロフィール修正 |
| `GET` | `/categories` | 関心カテゴリ照会 |
| `PUT` | `/categories` | 関心カテゴリ修正 |
| `POST` | `/onboarding` | オンボーディング完了 |
| `GET` | `/onboarding/status` | オンボーディング状態確認 |
| `GET` | `/bookmarks` | ブックマーク一覧 |
| `GET` | `/frequencies` | 自分の周波数一覧 |

### ニュース `/api/news`
| メソッド | エンドポイント | 説明 |
|--------|------------|------|
| `GET` | `/?category={category}` | カテゴリ別ニュース |
| `GET` | `/{news_id}` | ニュース詳細 |
| `GET` | `/today` | 今日のカテゴリ別ニュース |
| `POST` | `/bookmark` | ブックマーク追加 |
| `DELETE` | `/bookmark/{news_id}` | ブックマーク削除 |

### 周波数 `/api/frequencies`
| メソッド | エンドポイント | 説明 |
|--------|------------|------|
| `GET` | `/` | 自分の関心カテゴリの周波数 |
| `GET` | `/history` | 周波数履歴 |
| `GET` | `/{category}` | 特定カテゴリの周波数詳細 |

### カテゴリ `/api/categories`
| メソッド | エンドポイント | 説明 |
|--------|------------|------|
| `GET` | `/` | 全カテゴリ一覧 |

---

## データベース構造

### NewsCards
```json
{
  "news_id": "news_12345",
  "category_date": "politics#2025-06-03",
  "category": "politics",
  "title": "ニュースタイトル",
  "content": "記事本文",
  "published_at": "2025-06-03T12:00:00",
  "...": "..."
}
```

### Frequencies
```json
{
  "frequency_id": "politics#2025-06-03",
  "category": "politics",
  "date": "2025-06-03",
  "script": "ポッドキャスト台本",
  "audio_url": "https://s3.../politics_20250603.mp3",
  "created_at": "2025-06-03T06:00:00"
}
```

### Users
```json
{
  "user_id": "kakao_1234567890",
  "nickname": "山田太郎",
  "interests": ["政治", "経済"],
  "onboarding_completed": true,
  "created_at": "2025-05-01T00:00:00"
}
```

---

## セキュリティ考慮事項

### APIキー管理
- 環境変数で管理
- AWS Parameter Store連携準備
- 現在はハードコーディング (開発の便宜のため)

### JWTトークン
```python
# トークン生成
token = create_access_token(data={"sub": user_id})

# トークン検証
payload = verify_token(token)
```

### CORS設定
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 運用時は具体的なドメイン設定を推奨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## デプロイ

### AWS SAMデプロイ
```bash
# ビルド
sam build

# デプロイ (初回)
sam deploy --guided

# デプロイ (以降)
sam deploy
```

### Lambda関数
1. **BrieflyApi**: FastAPIメインAPIサーバー
2. **DailyBrieflyTask**: 毎日6時スケジューラー

### AWSリソース
- **DynamoDB**: 4つのテーブル (NewsCards, Frequencies, Users, Bookmarks)
- **S3**: 音声ファイル保存
- **EventBridge**: Cronスケジューリング
- **IAM**: 適切な権限設定

---

## パフォーマンス最適化

### トークン使用量を50%削減
- **以前**: 90,000字 → **現在**: 45,000字
- **月間予想費用**: 50%削減

### メモリ最適化
- **Lambdaメモリ**: 1024MB (クラスタリング作業)
- **バッチ処理**: 段階的なメモリ効率化

### ロギングシステム
```python
import logging
logger = logging.getLogger(__name__)

logger.info("情報ログ")
logger.warning("警告ログ") 
logger.error("エラーログ")
```

---

## 問題解決

### よくある問題

**1. UTF-8エンコーディングエラー**
```bash
# Windows PowerShell
$env:PYTHONIOENCODING='utf-8'
```

**2. APIキーエラー**
```python
# .env ファイルを確認
OPENAI_API_KEY=sk-proj-...
```

**3. DynamoDB接続エラー**
```bash
# AWS認証情報を確認
aws configure list
```

### ログ確認
```bash
# Lambdaログ (CloudWatch)
sam logs -n BrieflyApi --stack-name briefly-backend

# ローカルログ
tail -f logs/app.log
```

---

## モニタリング

### 主要指標
- **API応答時間**: 平均200ms以下
- **日次処理量**: カテゴリ別30件の記事
- **成功率**: 99%以上
- **トークン使用量**: 月間45,000字

### CloudWatchメトリクス
- Lambda実行時間
- DynamoDB読み取り/書き込みユニット
- S3アップロード成功率
- API Gateway呼び出し数

---

## 開発ガイド

### 新しいAPIの追加
1. `routes/` フォルダにルーターファイルを作成
2. `main.py` にルーターを登録
3. テストファイルを作成
4. APIドキュメントを更新

### 新しいサービスの追加
1. `services/` フォルダにサービスファイルを作成
2. 環境変数を設定
3. ユニットテストを作成
4. 統合テストに含める

### コーディング規約
- **関数名**: snake_case
- **クラス名**: PascalCase
- **定数名**: UPPER_CASE
- **docstring**: すべての関数に追加
- **型ヒント**: 可能な限りすべての場所で使用


---


---

# Backend API Server

## 環境変数設定

### TTSサービス最適化 (NEW)

自然なポッドキャストのためのElevenLabs設定:

```bash
# ElevenLabs TTS設定
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_VOICE_ID=your_voice_id_here


## 既存の設定

### OpenAI設定
```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini  # または gpt-4o
```

### AWS設定  
```bash
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=ap-northeast-2
AWS_DYNAMODB_TABLE_NAME=briefly-news
AWS_S3_BUCKET_NAME=briefly-audio
```

### DeepSearch API
```bash
DEEPSEARCH_API_KEY=your_deepsearch_api_key
```

## 実行方法

```bash
# 仮想環境の有効化
source venv/Scripts/activate  # Windows
source venv/bin/activate      # Mac/Linux

# 依存関係のインストール
pip install -r requirements.txt

# サーバー実行
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## APIドキュメント

サーバー実行後、次のURLでAPIドキュメントを確認:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)
