import os
import httpx
from typing import List, Literal
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import trafilatura
import re

from app.utils.dynamo import get_news_by_category_and_date, get_news_card_by_id, get_news_card_by_content_url
from app.constants.category_map import CATEGORY_MAP

# 環境変数からAPIキーと基本設定を読み込み
DEEPSEARCH_API_KEY = os.getenv("DEEPSEARCH_API_KEY")
DEEPSEARCH_BASE_URL = "https://api-v2.deepsearch.com/v1"
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
)
HEADERS = {
    "Authorization": f"Bearer {DEEPSEARCH_API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": USER_AGENT
}

# 主要メディアごとのドメインと本文セレクターの指定
ARTICLE_SELECTORS = {
    "newsis.com": "div.view_text",
    "news1.kr": "div#articleBody",
    "yna.co.kr": "div#articleBody, div#articleView",
    "heraldcorp.com": "div.view_con_t",
    "biz.heraldcorp.com": "div.view_con_t",
    "kbs.co.kr": "div#cont_newstext",
    "sisajournal.com": "div.view_con",
    "asiatoday.co.kr": "div#articleBody",
    "koreaherald.com": "div.article-text",
    "sedaily.com": "div#v_article",
    "donga.com": "div.article_txt",
    "hankyung.com": "div#articletxt",
    "joongang.co.kr": "div#article_body",
    "ohmynews.com": "div#article_view",
    "pressian.com": "div.view_con_tx",
    "mt.co.kr": "div#textBody",
    "edaily.co.kr": "div.news_body",
    "mk.co.kr": "div#article_body",
    "fnnews.com": "div.articleCont",
    "busan.com": "div#news_body_area",
}

# 本文内の「韓国語比率」をチェック（70%以上で有効な本文と判定）
def is_korean_text(text: str, threshold: float = 0.7) -> bool:
    """
    テキスト内の韓国語比率を判定（韓国ニュースかどうかを判別）
    """
    kor_count = len(re.findall(r"[가-힣]", text))
    total_count = len(re.findall(r"[가-힣a-zA-Z]", text))
    if total_count == 0:
        return False
    return kor_count / total_count >= threshold

# 不要な案内・広告・おすすめ・アプリ領域のセレクター（BeautifulSoupで除去）
KNOWN_TRASH_SELECTORS = [
    ".txt-copyright", ".adrs", ".sns-box", ".relate_news", ".copy",
    ".recommend", ".app-down", ".guide", ".comment", ".news_app_banner",
    ".article-ad", "#recommend", "#comment", "#reply", ".promotion"
]

# 本文に頻出する削除対象キーワード
UNWANTED_KEYWORDS = [
    "이 기사の 댓글 정책을 결정합니다",
    "앱 다운", "빠르고 정확한 연합뉴스", "이 기사를 추천합니다",
    "글자 크기 변경하기", "네이버 AI 뉴스 알고리즘",
    "프리미엄콘텐츠", "본 기사와 무관한 광고", "해당 언론사에서 선정하며",
    "사고로 해발", "기사 추천은", "모두에게 보여주고 싶은 기사라면",
    "텍스트 음성 변환 서비스 사용하기", "글자로 지은 집7", "이 콘텐츠의 저작권은",
    "섹션 정보는", "댓글 정책", "해당 언론사", "관련 업계에 따르면",
    "인용된 모든 콘텐츠는", "당신의 의견을 남겨주세요", "클릭! 기사는 어떠셨나요?"
]

# 本文に繰り返し現れる案内・広告・記者情報・著作権テキストの正規表現
REMOVE_TEXT_PATTERNS = [
    r"^[가-힣]{2,4}\s?기자\s?[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    r"^[가-힣]{2,4}\s?기자$",
    r"^[가-힣]{2,4}\s?\([^)]+@[^-\s)]+\)$",
    r"^Copyright.*", r"^무단[^\n]{0,20}전재.*", r"^재배포 금지.*",
    r"^\[카카오톡\].*", r"^\[메일\].*", r"^\[전화\].*",
]
REMOVE_TEXT_PATTERNS_COMPILED = [re.compile(pat) for pat in REMOVE_TEXT_PATTERNS]

# メールアドレスと電話番号の正規表現
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\d{2,3}-\d{3,4}-\d{4}")

def clean_text_noise(text: str) -> str:
    """
    ニュース本文から不要な案内・広告・記者情報・著作権関連のテキストを削除
    """
    if not isinstance(text, str):
        return ""
    cleaned_lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # 1. 行全体削除パターン（記者、著作権、連絡先など）
        if any(pat.match(line) for pat in REMOVE_TEXT_PATTERNS_COMPILED):
            continue
        # 2. メールアドレス・電話番号を含む行は除外
        if EMAIL_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        # 3. 一般的な広告・案内キーワードを含む行は除外
        if any(kw in line for kw in UNWANTED_KEYWORDS):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)

# [方法1] BeautifulSoupによる本文抽出（失敗時は全文にフォールバック）
def extract_content_with_bs4(url: str, timeout: float = 10.0) -> str:
    """
    BeautifulSoupを使って記事本文を抽出
    - ドメインごとのセレクターを優先
    - 無ければ全文取得
    - 広告・アプリ・コメントなどの不要要素を削除
    - 最終的にテキストクリーンアップ
    """
    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT}
        )
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        # 不要なタグを削除
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        for selector in KNOWN_TRASH_SELECTORS:
            for tag in soup.select(selector):
                tag.decompose()
        # ドメインごとのセレクター適用
        domain = urlparse(url).netloc.replace("www.", "")
        selector = ARTICLE_SELECTORS.get(domain)
        if selector:
            article_tag = soup.select_one(selector)
            if article_tag:
                text = article_tag.get_text(separator="\n")
            else:
                print(f" selectorは存在するが要素が見つからない: {domain} → {selector}")
                text = soup.get_text(separator="\n")
        else:
            text = soup.get_text(separator="\n")
        # 本文のノイズ除去
        text = clean_text_noise(text)
        return text.strip()
    except httpx.TimeoutException as e:
        print(f" [タイムアウト] {url} - {e}")
        return ""
    except httpx.RequestError as e:
        print(f" [リクエストエラー] {url} - {e}")
        return ""
    except httpx.HTTPStatusError as e:
        print(f" [HTTPエラー] {url} - {e.response.status_code}")
        return ""
    except ValueError as e:
        print(f" [URLパースエラー] {url} - {e}")
        return ""
    except Exception as e:
        print(f" [本文抽出で予期しないエラー] {url} - {e}")
        return ""

# [方法2] Trafilatura + BeautifulSoup混合方式（最優先で使用）
def extract_content_flexibly(url: str, timeout: float = 10.0) -> str:
    """
    Trafilaturaを優先して本文抽出
    - 広告・アプリ・推奨セレクター/パターン削除
    - 長さ・文数・韓国語比率によるフィルタ
    - 失敗時はBeautifulSoup方式にフォールバック
    """
    try:
        html = trafilatura.fetch_url(url)
        if html:
            soup = BeautifulSoup(html, "html.parser")
            for selector in KNOWN_TRASH_SELECTORS:
                for tag in soup.select(selector):
                    tag.decompose()
            content = trafilatura.extract(str(soup))
            # 十分な長さ・文数・韓国語比率を満たす場合のみ返却
            if content and len(content) >= 300 and content.count('.') >= 5:
                content = clean_text_noise(content)
                if is_korean_text(content, threshold=0.7):
                    return content.strip()
        # Trafilatura失敗時はBeautifulSoup方式にフォールバック
        text = extract_content_with_bs4(url)
        if text and len(text) >= 300 and text.count('.') >= 5:
            text = clean_text_noise(text)
            if is_korean_text(text, threshold=0.7):
                return text
        return ""
    except ImportError as e:
        print(f" [ライブラリ未導入] trafilaturaのインストールが必要: {e}")
        return extract_content_with_bs4(url)
    except MemoryError as e:
        print(f" [メモリエラー] {url} - {e}")
        return ""
    except Exception as e:
        print(f" [混合本文抽出で予期しないエラー] {url} - {e}")
        return ""

# DeepSearch人気記事リストの取得（非同期）
async def fetch_top_articles(
    category: str,
    size: int = 30,
    section: Literal["domestic", "international"] = "domestic"
) -> List[dict]:
    """
    特定カテゴリの人気記事リストをDeepSearch APIから取得（テスト用）
    """
    url = (
        f"{DEEPSEARCH_BASE_URL}/articles/{category}"
        if section == "domestic"
        else f"{DEEPSEARCH_BASE_URL}/global-articles/{category}"
    )
    params = {"sort": "popular", "page_size": size}
    async with httpx.AsyncClient(headers=HEADERS) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data", [])

# カテゴリ別ニュースの中で本文が有効な記事のみを抽出して返す
def fetch_valid_articles_by_category(
    category: str,
    start_time: str,
    end_time: str,
    size: int = 60,
    limit: int = 30,
    sort: Literal["popular", "traffic"] = "popular",
    section: Literal["domestic", "international"] = "domestic",
    min_content_length: int = 300,
    max_try: int = 5
) -> List[dict]:
    """
    DeepSearch APIでカテゴリ別記事リストを取得し、本文が有効な記事のみを返す
    - メモリ・DBベースの重複除外
    - 韓国語ニュースのみ抽出
    """
    seen_ids = set()
    seen_urls = set()
    seen_titles = set()
    results = []
    page = 1
    while len(results) < limit and page <= max_try:
        url = (
            f"{DEEPSEARCH_BASE_URL}/articles/{category}"
            if section == "domestic"
            else f"{DEEPSEARCH_BASE_URL}/global-articles/{category}"
        )
        params = {
            "date_from": start_time,
            "date_to": end_time,
            "sort": sort,
            "page_size": size,
            "page": page
        }
        response = httpx.get(url, headers=HEADERS, params=params)
        response.raise_for_status()
        all_articles = response.json().get("data", [])
        if not all_articles:
            break
        for article in all_articles:
            news_id = article.get("id")
            article_url = article.get("content_url")
            title = article.get("title", "").strip()
            # メモリ基準の重複除外
            if not article_url or not news_id:
                continue
            if news_id in seen_ids or article_url in seen_urls:
                continue
            if title and title in seen_titles:
                continue
            # DBにすでに存在するかをチェック
            if get_news_card_by_id(news_id):
                continue
            if get_news_card_by_content_url(article_url):
                continue
            seen_ids.add(news_id)
            seen_urls.add(article_url)
            if title:
                seen_titles.add(title)
            # 本文抽出と有効性チェック
            content = extract_content_flexibly(article_url)
            if not content or len(content) < min_content_length:
                continue
            if not is_korean_text(content, threshold=0.7):
                continue
            article["content"] = content
            results.append(article)
            if len(results) >= limit:
                break
        page += 1
    return results[:limit]

# 保存されたニュースのうち content が空のものに本文を再抽出して補完する関数
def fetch_detailed_articles(category: str, date: str, limit: int = 30) -> List[dict]:
    """
    保存済みニュースのうち content が空のものに本文を再抽出して補完する
    """
    all_items = get_news_by_category_and_date(category, date)
    results = []
    for item in all_items:
        if "content" in item and item["content"]:
            results.append(item)
            continue
        content_url = item.get("content_url")
        if not content_url:
            continue
        # 本文再抽出
        content = extract_content_flexibly(content_url)
        if content and len(content) >= 300:
            item["content"] = content
            results.append(item)
        if len(results) >= limit:
            break
    return results
