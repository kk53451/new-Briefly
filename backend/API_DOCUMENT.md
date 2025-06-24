#  Briefly バックエンドAPI ドキュメント

##  プロジェクト概要

**Briefly**は、AI基盤のニュースポッドキャストバックエンドシステムで、毎日ニュースを収集してGPT-4o-miniで要約し、ElevenLabs TTSで音声を生成する自動化サービスです。

###  主要機能
-  **AIニュース要約**: GPT-4o-mini + 二重クラスタリングで重複除去
-  **TTS変換**: ElevenLabs 高品質音声生成
-  **スケジューリング**: 毎日午前6時(KST) 自動実行
-  **認証**: カカオログイン + JWTトークン
-  **データ**: AWS DynamoDB + S3ストレージ

###  **実装済みユースケース**
- **合計13個の主要ユースケース** 実装完了
- **UC-001~003**: ユーザー認証とオンボーディング (3個)
- **UC-004~006**: ニュース閲覧と探索 (3個)
- **UC-007~008**: ポッドキャストと音声サービス (2個)
- **UC-009~011**: パーソナライゼーションと設定 (3個)
- **UC-012~013**: 自動化システム (2個)

###  システムアーキテクチャ

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

###  デプロイ情報

- **Base URL**: `https://your-api-gateway-url/`
- **デプロイツール**: AWS SAM
- **実行環境**: AWS Lambda (Python 3.12)
- **スケジューラー**: EventBridge (毎日午前6時 KST)

---

##  認証システム

### JWTトークンの使用方法

すべての保護されたエンドポイントには、以下のようなヘッダーが必要です：

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 認証フロー

1. **カカオログイン開始** → `/api/auth/kakao/login`
2. **ユーザーカカオ認証** → カカオサーバー
3. **コールバック処理** → `/api/auth/kakao/callback`
4. **JWTトークン発行** → クライアントに配信
5. **API呼び出し時のトークン使用** → `Authorization` ヘッダー

---

## 📚 APIエンドポイント

### 🔑 1. 認証API (`/api/auth`)

#### 1-1. カカオログイン開始

```http
GET /api/auth/kakao/login
```

**説明**: カカオ OAuth ログインページにリダイレクト

**パラメータ**: なし

**レスポンス**: カカオ認証ページにリダイレクト

**使用例**:
```javascript
// フロントエンドでの使用
window.location.href = 'https://api.briefly.com/api/auth/kakao/login';
```

---

#### 1-2. カカオログインコールバック

```http
GET /api/auth/kakao/callback?code={authorization_code}
```

**説明**: カカオログイン完了後のJWTトークン発行

**パラメータ**:
- `code` (query, required): カカオから渡される認証コード

**レスポンス** (200):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user_id": "kakao_123456789",
  "nickname": "홍길동"
}
```

**エラーレスポンス**:
- `400`: 認証コード期限切れ/再使用
  ```json
  {
    "detail": "이 인증 코드는 이미 사용되었습니다. 다시 로그인해주세요."
  }
  ```
- `500`: カカオサーバー接続失敗
  ```json
  {
    "detail": "카카오 서버 연결 실패"
  }
  ```

---

#### 1-3. ユーザー情報取得

```http
GET /api/auth/me
Authorization: Bearer {token}
```

**説明**: 現在ログインしているユーザー情報取得

**レスポンス** (200):
```json
{
  "user_id": "kakao_123456789",
  "nickname": "홍길동",
  "profile_image": "https://k.kakaocdn.net/dn/profile.jpg",
  "interests": ["정치", "경제"],
  "onboarding_completed": true,
  "created_at": "2025-01-01T00:00:00",
  "default_length": 3
}
```

**エラーレスポンス**:
- `401`: トークンなし/期限切れ
  ```json
  {
    "detail": "토큰이 필요합니다"
  }
  ```

---

#### 1-4. ログアウト

```http
POST /api/auth/logout
Authorization: Bearer {token}
```

**説明**: ログアウト処理 (クライアントからトークン削除を推奨)

**レスポンス** (200):
```json
{
  "message": "로그아웃 완료 (클라이언트 토큰 삭제 권장)"
}
```

---

### 👤 2. ユーザーAPI (`/api/user`)

#### 2-1. プロフィール取得

```http
GET /api/user/profile
Authorization: Bearer {token}
```

**説明**: ログインしているユーザーのプロフィール情報取得

**レスポンス** (200):
```json
{
  "user_id": "kakao_123456789",
  "nickname": "홍길동",
  "profile_image": "https://k.kakaocdn.net/dn/profile.jpg",
  "interests": ["정치", "경제"],
  "onboarding_completed": true,
  "default_length": 3,
  "created_at": "2025-01-01T00:00:00"
}
```

---

#### 2-2. ブックマークリスト取得

```http
GET /api/user/bookmarks
Authorization: Bearer {token}
```

**説明**: ユーザーがブックマークしたニュースリスト取得

**レスポンス** (200):
```json
[
  {
    "news_id": "news_123",
    "title": "뉴스 제목",
    "summary": "뉴스 요약",
    "bookmark_date": "2025-01-27T10:00:00"
  }
]
```

---

#### 2-3. ユーザー周波数取得

```http
GET /api/user/frequencies
Authorization: Bearer {token}
```

**説明**: ユーザーの関心カテゴリ別共有周波数要約取得 (今日日付ベース)

**レスポンス** (200):
```json
[
  {
    "frequency_id": "politics#2025-01-27",
    "category": "politics",
    "script": "오늘의 정치 뉴스 요약...",
    "audio_url": "https://s3.amazonaws.com/briefly-news-audio/politics-2025-01-27.mp3",
    "date": "2025-01-27"
  }
]
```

---

#### 2-4. 関心カテゴリ取得

```http
GET /api/user/categories
Authorization: Bearer {token}
```

**説明**: ユーザーの関心カテゴリリスト取得

**レスポンス** (200):
```json
{
  "interests": ["정치", "경제"]
}
```

---

#### 2-5. 関心カテゴリ修正

```http
PUT /api/user/categories
Authorization: Bearer {token}
```

**説明**: ユーザーの関心カテゴリリスト修正

**リクエスト Body**:
```json
{
  "interests": ["정치", "경제", "IT/과학"]
}
```

**レスポンス** (200):
```json
{
  "message": "관심 카테고리가 업데이트되었습니다."
}
```

---

#### 2-6. オンボーディング完了

```http
POST /api/user/onboarding
Authorization: Bearer {token}
```

**説明**: オンボーディング完了処理

**レスポンス** (200):
```json
{
  "message": "온보딩 완료"
}
```

---

#### 2-7. オンボーディングステータス確認

```http
GET /api/user/onboarding/status
Authorization: Bearer {token}
```

**説明**: オンボーディング完了確認

**レスポンス** (200):
```json
{
  "onboarded": true
}
```

---

#### 2-8. オンボーディングページ情報

```http
GET /api/user/onboarding
Authorization: Bearer {token}
```

**説明**: オンボーディングページ情報提供

**レスポンス** (200):
```json
{
  "user_id": "kakao_123456789",
  "nickname": "홍길동",
  "onboarding_completed": false,
  "interests": []
}
```

---

### 📰 3. ニュースAPI (`/api/news`)

#### 3-1. カテゴリ別ニュース取得

```http
GET /api/news?category={category}
```

**説明**: 特定カテゴリの今日ニュースリスト取得

**パラメータ**:
- `category` (query, required): ニュースカテゴリ
  - サポートカテゴリ: `정치`, `경제`, `사회`, `생활/문화`, `IT/과학`, `연예`, `전체`

**レスポンス** (200):
```json
[
  {
    "news_id": "news_123",
    "title": "뉴스 제목",
    "summary": "뉴스 요약",
    "image_url": "https://example.com/image.jpg",
    "content_url": "https://example.com/news",
    "publisher": "언론사",
    "published_at": "2025-01-27T09:00:00",
    "sections": ["politics"],
    "rank": 1
  }
]
```

**エラーレスポンス**:
- `400`: サポートしないカテゴリ
  ```json
  {
    "detail": "지원하지 않는 카테고리입니다: 스포츠"
  }
  ```

---

#### 3-2. 今日のニュースグループ化

```http
GET /api/news/today
```

**説明**: 今日のニュースをカテゴリ別でグループ化して返す

**レスポンス** (200):
```json
{
  "정치": [
    {
      "news_id": "news_123",
      "title": "정치 뉴스 제목",
      "summary": "정치 뉴스 요약"
    }
  ],
  "경제": [
    {
      "news_id": "news_456",
      "title": "경제 뉴스 제목",
      "summary": "경제 뉴스 요약"
    }
  ]
}
```

---

#### 3-3. ニュース詳細取得

```http
GET /api/news/{news_id}
```

**説明**: 個別ニュースカード詳細内容取得

**レスポンス** (200):
```json
{
  "news_id": "news_123",
  "title": "뉴스 제목",
  "summary": "뉴스 요약",
  "content": "뉴스 본문 전체...",
  "image_url": "https://example.com/image.jpg",
  "content_url": "https://example.com/news",
  "publisher": "언론사",
  "author": "기자명",
  "published_at": "2025-01-27T09:00:00",
  "companies": ["삼성", "LG"],
  "esg": []
}
```

**エラーレスポンス**:
- `404`: ニュースを見つけることができません
  ```json
  {
    "detail": "뉴스를 찾을 수 없습니다."
  }
  ```

---

#### 3-4. ニュースブックマーク追加

```http
POST /api/news/bookmark
Authorization: Bearer {token}
```

**説明**: ニュースブックマーク追加

**リクエスト Body**:
```json
{
  "news_id": "news_123"
}
```

**レスポンス** (200):
```json
{
  "message": "북마크 완료"
}
```

---

#### 3-5. ニュースブックマーク削除

```http
DELETE /api/news/bookmark/{news_id}
Authorization: Bearer {token}
```

**説明**: ニュースブックマーク削除

**レスポンス** (200):
```json
{
  "message": "북마크 삭제됨"
}
```

---

###  4. 周波数API (`/api/frequencies`)

#### 4-1. ユーザー周波数リスト

```http
GET /api/frequencies
Authorization: Bearer {token}
```

**説明**: ユーザーの関心カテゴリ別共有周波数リスト (今日日付ベース)

**レスポンス** (200):
```json
[
  {
    "frequency_id": "politics#2025-01-27",
    "category": "politics",
    "script": "오늘의 정치 뉴스 요약...",
    "audio_url": "https://s3.amazonaws.com/briefly-news-audio/politics-2025-01-27.mp3",
    "date": "2025-01-27",
    "created_at": "2025-01-27T06:30:00"
  }
]
```

---

#### 4-2. 周波数ヒストリー

```http
GET /api/frequencies/history?limit={limit}
Authorization: Bearer {token}
```

**説明**: ユーザーの関心カテゴリ別周波数ヒストリー (過去データ)

**パラメータ**:
- `limit` (query, optional): 取得数 (デフォルト: 30, 最大: 100)

**レスポンス** (200):
```json
[
  {
    "frequency_id": "politics#2025-01-26",
    "category": "politics",
    "script": "어제의 정치 뉴스 요약...",
    "audio_url": "https://s3.amazonaws.com/briefly-news-audio/politics-2025-01-26.mp3",
    "date": "2025-01-26",
    "created_at": "2025-01-26T06:30:00"
  }
]
```

---

#### 4-3. カテゴリ別周波数詳細

```http
GET /api/frequencies/{category}
Authorization: Bearer {token}
```

**説明**: 特定カテゴリの周波数詳細情報取得

**レスポンス** (200):
```json
{
  "frequency_id": "politics#2025-01-27",
  "category": "politics",
  "script": "오늘의 정치 뉴스 요약...",
  "audio_url": "https://s3.amazonaws.com/briefly-news-audio/politics-2025-01-27.mp3",
  "date": "2025-01-27",
  "created_at": "2025-01-27T06:30:00"
}
```

**エラーレスポンス**:
- `404`: 該当周波数がありません
  ```json
  {
    "detail": "해당 주파수가 없습니다."
  }
  ```

---

### 📂 5. カテゴリAPI (`/api`)

#### 5-1. 全カテゴリリスト取得

```http
GET /api/categories
```

**説明**: 全カテゴリリスト返却 (認証不要)

**レスポンス** (200):
```json
{
  "categories": ["정치", "경제", "사회", "생활/문화", "IT/과학", "연예"]
}
```

---

#### 5-2. ユーザーカテゴリ取得

```http
GET /api/user/categories
Authorization: Bearer {token}
```

**説明**: ログインしているユーザーの関心カテゴリ取得

**レスポンス** (200):
```json
{
  "user_id": "kakao_123456789",
  "interests": ["정치", "경제"]
}
```

---

#### 5-3. ユーザーカテゴリ修正

```http
PUT /api/user/categories
Authorization: Bearer {token}
```

**説明**: ログインしているユーザーの関心カテゴリ修正

**リクエスト Body**:
```json
{
  "interests": ["정치", "경제", "IT/과학"]
}
```

**レスポンス** (200):
```json
{
  "message": "관심 카테고리 업데이트 완료",
  "interests": ["정치", "경제", "IT/과학"]
}
```

**エラーレスポンス**:
- `400`: 不正なカテゴリ
  ```json
  {
    "detail": "지원하지 않는 카테고리입니다: ['스포츠']"
  }
  ```

---

###  6. 他エンドポイント

#### 6-1. ルートヘルスチェック

```http
GET /
```

**説明**: APIサーバー状態確認

**レスポンス** (200):
```json
{
  "message": "Welcome to Briefly API"
}
```

---

#### 6-2. オンボーディングページ情報

```http
GET /onboarding
```

**説明**: オンボーディングページ情報提供 (認証不要)

**レスポンス** (200):
```json
{
  "message": "온보딩 페이지입니다",
  "available_categories": ["정치", "경제", "사회", "생활/문화", "IT/과학", "연예"]
}
```

---

##  共通エラーレスポンス

### 認証エラー
- `401 Unauthorized`: JWTトークンなし/期限切れ
- `403 Forbidden`: 権限なし

### リクエストエラー
- `400 Bad Request`: 不正なリクエストパラメータ
- `404 Not Found`: リソースを見つけることができません
- `422 Validation Error`: リクエスト形式エラー

### サーバーエラー
- `500 Internal Server Error`: サーバー内部エラー

---

##  API使用例

### 1. ユーザー認証フロー
```javascript
// 1. カカオログイン
window.location.href = '/api/auth/kakao/login';

// 2. コールバックからトークン取得
const response = await fetch('/api/auth/kakao/callback?code=AUTH_CODE');
const { access_token } = await response.json();

// 3. トークンでAPI呼び出し
const userInfo = await fetch('/api/auth/me', {
  headers: { 'Authorization': `Bearer ${access_token}` }
});
```

### 2. ニュース取得フロー
```javascript
// 1. 全ニュース取得
const allNews = await fetch('/api/news?category=전체');

// 2. 特定カテゴリニュース
const politicsNews = await fetch('/api/news?category=정치');

// 3. ニュース詳細取得
const newsDetail = await fetch('/api/news/news_123');
```

### 3. 周波数取得フロー
```javascript
// 1. ユーザー関心周波数取得
const myFrequencies = await fetch('/api/frequencies', {
  headers: { 'Authorization': `Bearer ${token}` }
});

// 2. 周波数ヒストリー取得
const history = await fetch('/api/frequencies/history?limit=10', {
  headers: { 'Authorization': `Bearer ${token}` }
});
```

---

##  環境変数

```bash
# カカオログイン
KAKAO_CLIENT_ID=your_kakao_client_id
KAKAO_REDIRECT_URI=your_redirect_uri

# AIサービス
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id

# ニュースAPI
DEEPSEARCH_API_KEY=your_deepsearch_key

# AWSリソース
DDB_NEWS_TABLE=NewsCards
DDB_FREQ_TABLE=Frequencies
DDB_USERS_TABLE=Users
DDB_BOOKMARKS_TABLE=Bookmarks
S3_BUCKET=briefly-news-audio
```

---

##  開発ロードマップ

###  完了した機能
- カカオログインとJWT認証
- ニュース収集と要約システム
- TTS音声変換とS3保存
- ユーザープロフィルとブックマーク管理
- 周波数生成と取得

###  今後拡張可能な機能
- プッシュ通知システム
- ニュース検索機能  
- 音声再生分析
- リアルタイムニュースストリーミング

---