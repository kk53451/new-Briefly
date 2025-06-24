import logging
from datetime import datetime
import pytz
import concurrent.futures
import time

from app.services.deepsearch_service import fetch_valid_articles_by_category
from app.utils.dynamo import save_news_card, get_news_card_by_id, get_news_card_by_content_url
from app.constants.category_map import CATEGORY_MAP

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def collect_category_news(category_ko: str, config: dict, start_time: str, end_time: str, date_str: str) -> dict:
    """
    単一カテゴリのニュース収集関数（並列処理用）
    """
    category_en = config["api_name"]
    section = config["section"]
    collection_start_time = time.time()
    
    try:
        logger.info(f"[{category_ko}] 뉴스 수집 시작 ({section})")  # ニュース収集開始

        # ニュースAPI呼び出し
        try:
            articles = fetch_valid_articles_by_category(
                category=category_en,
                start_time=start_time,
                end_time=end_time,
                size=60,                # 多めに取得してフィルタリング
                sort="popular",
                section=section,
                min_content_length=300,
                limit=30               # 最終的に保存する件数
            )
            logger.info(f"[{category_ko}] 유효 기사 수: {len(articles)}")  # 有効な記事数
        except Exception as e:
            logger.error(f" [{category_ko}] API 호출 실패: {e}")  # API呼び出し失敗
            return {
                "category": category_ko,
                "status": "failed",
                "reason": f"api_error: {str(e)}",
                "saved_count": 0,
                "elapsed_time": time.time() - collection_start_time
            }

        saved_count = 0

        # 記事を順に保存
        for rank, article in enumerate(articles, start=1):
            news_id = article.get("id")
            if not news_id:
                logger.warning(f" [{category_ko}] ID 누락 → 스킵")  # IDがないためスキップ
                continue

            # 重複チェック
            if get_news_card_by_id(news_id):
                logger.info(f"🚫 [{category_ko}] [ID중복] 뉴스 스킵: {news_id}")  # ID重複によりスキップ
                continue
            if get_news_card_by_content_url(article.get("content_url")):
                logger.info(f"🚫 [{category_ko}] [URL중복] 뉴스 스킵: {article.get('content_url')}")  # URL重複
                continue

            content = article.get("content", "")
            if not content or len(content) < 300:
                logger.warning(f" [{category_ko}] 본문 누락/부족 → 스킵: {news_id}")  # 本文不足でスキップ
                continue

            # 保存するニュースアイテムの構成
            news_item = {
                "id": news_id,
                "sections": article.get("sections", []),
                "rank": rank,
                "title": article.get("title"),
                "title_ko": None,
                "summary": article.get("summary"),
                "summary_ko": None,
                "image_url": article.get("image_url"),
                "thumbnail_url": article.get("thumbnail_url") or article.get("thumbnail"),
                "content_url": article.get("content_url"),
                "publisher": article.get("publisher"),
                "author": article.get("author"),
                "published_at": article.get("published_at"),
                "companies": article.get("companies", []),
                "esg": article.get("esg", []),
                "content": content  # 本文を含む（セレクタベース）
            }

            # DynamoDB保存処理
            try:
                save_news_card(category_en, news_item, date_str)
                saved_count += 1
                logger.info(f" [{category_ko}] 저장 완료 #{rank} - {news_item['title']}")  # 保存完了
            except Exception as e:
                logger.error(f" [{category_ko}] 저장 실패 #{rank}: {e}")  # 保存失敗

        elapsed_time = time.time() - collection_start_time
        logger.info(f" [{category_ko}] 최종 저장 수: {saved_count} (소요시간: {elapsed_time:.1f}초)")  # 最終保存数
        
        return {
            "category": category_ko,
            "status": "success",
            "saved_count": saved_count,
            "elapsed_time": elapsed_time
        }
        
    except Exception as e:
        elapsed_time = time.time() - collection_start_time
        logger.exception(f" [{category_ko}] 예상치 못한 오류 (소요시간: {elapsed_time:.1f}초): {str(e)}")  # 予期せぬエラー
        return {
            "category": category_ko,
            "status": "failed",
            "reason": f"exception: {str(e)}",
            "saved_count": 0,
            "elapsed_time": elapsed_time
        }

def collect_today_news():
    """
    毎朝6時に自動実行：0時～6時のニュースを収集・保存（並列処理）
    - CATEGORY_MAPで定義されたカテゴリごとに人気ニュースを取得
    - 本文が300文字以上のニュースのみ保存
    - 本文はセレクタベースで抽出（フォールバックあり）
    - 保存時に本文もDynamoDBへ保存（要約とTTS生成のため）
    """
    total_start_time = time.time()

    # 韓国時間での当日範囲設定
    kst = pytz.timezone("Asia/Seoul")
    now = datetime.now(kst)
    date_str = now.strftime("%Y-%m-%d")
    start_time = f"{date_str}T00:00:00"
    end_time = f"{date_str}T06:00:00"

    logger.info(f" 병렬 뉴스 수집 시작: {len(CATEGORY_MAP)}개 카테고리 동시 처리")  # 並列収集開始
    logger.info(f" 수집 범위: {start_time} ~ {end_time}")  # 収集範囲
    logger.info(f" 카테고리 목록: {list(CATEGORY_MAP.keys())}")  # カテゴリ一覧

    # 並列処理：ThreadPoolExecutor使用
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:  # 6カテゴリ同時処理
        # 各カテゴリの処理を並列実行
        future_to_category = {
            executor.submit(collect_category_news, category_ko, config, start_time, end_time, date_str): category_ko 
            for category_ko, config in CATEGORY_MAP.items()
        }
        
        # 完了順に結果を取得
        for future in concurrent.futures.as_completed(future_to_category):
            category_ko = future_to_category[future]
            try:
                result = future.result()
                results.append(result)
                
                if result["status"] == "success":
                    logger.info(f" [{result['category']}] 뉴스 수집 완료 - 저장: {result['saved_count']}개, 소요시간: {result['elapsed_time']:.1f}초")  # 収集完了
                else:
                    logger.warning(f" [{result['category']}] 뉴스 수집 실패 - 사유: {result['reason']}")  # 収集失敗
                
            except Exception as exc:
                logger.exception(f" [{category_ko}] 예상치 못한 오류: {exc}")  # 予期せぬ例外
                results.append({
                    "category": category_ko, 
                    "status": "failed", 
                    "reason": f"executor_exception: {str(exc)}",
                    "saved_count": 0
                })

    # 全体結果のまとめ
    total_elapsed_time = time.time() - total_start_time
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    total_saved = sum(r["saved_count"] for r in results)
    
    logger.info(f" 병렬 뉴스 수집 완료!")  # 並列収集完了
    logger.info(f" 총 소요시간: {total_elapsed_time:.1f}초")  # 総処理時間
    logger.info(f" 결과 요약: 성공 {success_count}개, 실패 {failed_count}개")  # 成功・失敗件数
    logger.info(f"💾 총 저장된 뉴스: {total_saved}개")  # 保存件数
    
    # カテゴリごとの詳細結果
    for result in results:
        status_emoji = {"success": "", "failed": ""}.get(result["status"], "❓") 
        logger.info(f"{status_emoji} {result['category']}: {result['saved_count']}개 저장")
        if "reason" in result:
            logger.info(f"   └─ 사유: {result['reason']}")  # 失敗理由

    return results
