import os
import httpx
from typing import List, Literal
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from app.utils.dynamo import get_news_by_category_and_date
from app.constants.category_map import CATEGORY_MAP

# 환경 변수에서 API 키 및 기본 설정 로드
DEEPSEARCH_API_KEY = os.getenv("DEEPSEARCH_API_KEY")
DEEPSEARCH_BASE_URL = "https://api-v2.deepsearch.com/v1"
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36")

# HTTP 요청 헤더 (API 인증 + User-Agent 포함)
HEADERS = {
    "Authorization": f"Bearer {DEEPSEARCH_API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": USER_AGENT
}

# ✅ 주요 언론사 도메인별 기사 본문 selector 정의
ARTICLE_SELECTORS = {
    "newsis.com": "div.view_text",
    "news1.kr": "div#articleBody",
    "yna.co.kr": "div#articleWrap",
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

def extract_content_with_bs4(url: str, timeout: float = 10.0) -> str:
    """
    주어진 뉴스 URL에서 본문 텍스트를 추출 (도메인별 selector → fallback 방식)

    Args:
        url (str): 뉴스 기사 URL
        timeout (float): 요청 제한 시간 (기본값 10초)

    Returns:
        str: 정제된 본문 텍스트 (실패 시 빈 문자열)
    """
    try:
        response = httpx.get(
            url,
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT}
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # 광고 및 불필요한 태그 제거
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        # 도메인에 따라 selector 사용
        domain = urlparse(url).netloc.replace("www.", "")
        selector = ARTICLE_SELECTORS.get(domain)

        if selector:
            article_tag = soup.select_one(selector)
            if article_tag:
                text = article_tag.get_text(separator="\n")
            else:
                print(f"⚠️ selector 존재하나 해당 요소 없음: {domain} → {selector}")
                text = soup.get_text(separator="\n")
        else:
            # fallback: 페이지 전체 텍스트
            text = soup.get_text(separator="\n")

        # 공백 줄 제거 및 정제
        clean_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        return clean_text

    except Exception as e:
        print(f"❌ 본문 추출 실패: {url} → {e}")
        return ""

async def fetch_top_articles(
    category: str,
    size: int = 30,
    section: Literal["domestic", "international"] = "domestic"
) -> List[dict]:
    """
    (테스트용) 특정 카테고리의 인기 기사 리스트 조회

    Args:
        category (str): 카테고리 영문명 (예: "politics")
        size (int): 기사 수 (기본 30)
        section (str): 국내 or 해외 기사 구분

    Returns:
        List[dict]: 기사 목록 (딥서치 응답 그대로)
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

def fetch_valid_articles_by_category(
    category: str,
    start_time: str,
    end_time: str,
    size: int = 60,
    sort: Literal["popular", "traffic"] = "popular",
    section: Literal["domestic", "international"] = "domestic",
    min_content_length: int = 300,
    limit: int = 30
) -> List[dict]:
    """
    카테고리별 뉴스 중 본문이 존재하고 길이 제한을 넘는 기사만 필터링하여 반환

    Args:
        category (str): 카테고리 영문명
        start_time (str): ISO 8601 형식 시작 시각
        end_time (str): ISO 8601 형식 종료 시각
        size (int): API 조회 수 (오버페치용)
        sort (str): 정렬 기준 ("popular" 또는 "traffic")
        section (str): 기사 섹션 (국내/해외)
        min_content_length (int): 본문 최소 길이
        limit (int): 최종 반환 기사 수 제한

    Returns:
        List[dict]: 본문이 유효한 뉴스 기사 리스트
    """
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
    }

    response = httpx.get(url, headers=HEADERS, params=params)
    response.raise_for_status()
    all_articles = response.json().get("data", [])

    results = []
    for article in all_articles:
        url = article.get("content_url")
        if not url:
            continue
        content = extract_content_with_bs4(url)
        if content and len(content) >= min_content_length:
            article["content"] = content
            results.append(article)
        if len(results) >= limit:
            break

    return results

def fetch_detailed_articles(category: str, date: str, limit: int = 30) -> List[dict]:
    """
    저장된 뉴스 중 content 필드가 비어 있는 기사에 대해 본문을 재추출하여 채워주는 함수

    Args:
        category (str): 카테고리 영문명
        date (str): 날짜 (YYYY-MM-DD)
        limit (int): 최대 기사 수

    Returns:
        List[dict]: 본문이 보완된 뉴스 리스트
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

        content = extract_content_with_bs4(content_url)
        if content and len(content) >= 300:
            item["content"] = content
            results.append(item)

        if len(results) >= limit:
            break

    return results
