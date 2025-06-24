"""
ニュースカテゴリのマッピング情報を管理するモジュールです。

韓国語のカテゴリ名を、DeepSearch APIなどで使用する英語名に変換するための
定数を定義しています。
"""

# app/constants/category_map.py

# ユーザーに表示される韓国語カテゴリ名と、API連携のための英語カテゴリ名＋セクション情報をマッピング
# - 'api_name': APIリクエスト時に使用される英語のカテゴリ名
# - 'section': DeepSearch APIのセクション区分（'domestic' または 'international'）
CATEGORY_MAP = {
    "정치": {"api_name": "politics", "section": "domestic"},
    "경제": {"api_name": "economy", "section": "domestic"},
    "사회": {"api_name": "society", "section": "domestic"},
    "생활/문화": {"api_name": "culture", "section": "domestic"},
    "IT/과학": {"api_name": "tech", "section": "domestic"},
    "연예": {"api_name": "entertainment", "section": "domestic"},
    # "세계": {"api_name": "world", "section": "international"},  ← 削除済み
    # "스포츠": {"api_name": "sports", "section": "international"},  ← 削除済み
}

# 韓国語のカテゴリ名リスト（例: ["정치", "경제", ...]）
CATEGORY_KO_LIST = list(CATEGORY_MAP.keys())

# 英語のカテゴリ名リスト（例: ["politics", "economy", ...]）
CATEGORY_EN_LIST = [v["api_name"] for v in CATEGORY_MAP.values()]

# 英語カテゴリ名 → 韓国語カテゴリ名への逆マッピング辞書
# 例: {"politics": "정치", "economy": "경제", ...}
REVERSE_CATEGORY_MAP = {v["api_name"]: k for k, v in CATEGORY_MAP.items()}
