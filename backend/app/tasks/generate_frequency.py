import logging
from datetime import datetime
import concurrent.futures
import time

from app.utils.date import get_today_kst
from app.utils.dynamo import (
    save_frequency_summary,
    get_frequency_by_category_and_date,
    get_news_by_category_and_date,
    update_news_card_content,
)
from app.services.openai_service import summarize_articles, cluster_similar_texts, summarize_group
from app.services.tts_service import text_to_speech
from app.utils.s3 import upload_audio_to_s3_presigned
from app.constants.category_map import CATEGORY_MAP
from app.services.deepsearch_service import extract_content_flexibly

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def process_single_category(category_ko: str, date: str) -> dict:
    """
    単一カテゴリ処理関数（並列処理用）
    """
    category_en = CATEGORY_MAP[category_ko]["api_name"]
    freq_id = f"{category_en}#{date}"
    start_time = time.time()
    
    try:
        # 重複防止：既に生成済みの場合はスキップ
        if get_frequency_by_category_and_date(category_en, date):
            logger.info(f"🚫 이미 생성됨 → 스킵: {freq_id}")
            return {"category": category_en, "status": "skipped", "reason": "already_exists"}

        logger.info(f"[{category_en}] 대본/음성 생성 시작")
        # 該当カテゴリの本日の記事を取得
        articles = get_news_by_category_and_date(category_en, date)
        logger.info(f"[{category_en}] 수집된 기사 수: {len(articles)}")

        full_contents = []
        processed_count = 0
        target_count = 30  # 正確に30件に制限

        # 記事本文を正確に30件まで収集
        for i, article in enumerate(articles):
            if len(full_contents) >= target_count:
                logger.info(f"[{category_en}] 목표 달성: {target_count}개 수집 완료")
                break
                
            processed_count += 1
            news_id = article.get("news_id")
            url = article.get("content_url")
            content = article.get("content", "").strip()

            if not news_id or not url:
                logger.warning(f"[{category_en}] #{processed_count} URL 또는 ID 없음 → 스킵")
                continue

            # 本文が短いまたは存在しない場合は再抽出を試みる
            if not content or len(content) < 300:
                try:
                    content = extract_content_flexibly(url)
                    if content and len(content) >= 300:
                        update_news_card_content(news_id, content)
                        logger.info(f"[{category_en}] #{processed_count} 본문 보완 저장 완료 ({len(content)}자)")
                    else:
                        logger.warning(f"[{category_en}] #{processed_count} 본문 추출 실패 또는 너무 짧음 → 스킵")
                        continue
                except Exception as e:
                    logger.warning(f"[{category_en}] #{processed_count} 본문 재추출 중 오류: {e}")
                    continue

            # トークン最適化：3000文字から1500文字へ短縮
            trimmed = content[:1500]
            full_contents.append(trimmed)
            logger.info(f"[{category_en}] #{len(full_contents)} 본문 사용 완료 ({len(trimmed)}자)")

        logger.info(f"[{category_en}] 최종 수집된 기사 수: {len(full_contents)}개 (목표: {target_count}개)")

        # 本文数が少なすぎる場合はスキップ
        if len(full_contents) < 5:
            logger.warning(f"[{category_en}] 유효 본문 부족 ({len(full_contents)}개) → 스킵")
            return {"category": category_en, "status": "failed", "reason": "insufficient_content"}

        # 一次クラスタリング：重複記事の除去
        logger.info(f"[{category_en}] 1차 클러스터링 시작: {len(full_contents)}개 기사")
        try:
            groups = cluster_similar_texts(full_contents, threshold=0.80)
            group_summaries = []
            
            for group_idx, group in enumerate(groups):
                if len(group) == 1:
                    # 単一記事はそのまま使用
                    group_summaries.append(group[0])
                    logger.info(f"[{category_en}] 그룹 #{group_idx+1}: 단일 기사 ({len(group[0])}자)")
                else:
                    # 複数の類似記事 → 代表要約文を生成
                    try:
                        summary = summarize_group(group, category_en)
                        group_summaries.append(summary)
                        logger.info(f"[{category_en}] 그룹 #{group_idx+1}: {len(group)}개 기사 → 통합 요약 ({len(summary)}자)")
                    except Exception as e:
                        logger.warning(f"[{category_en}] 그룹 #{group_idx+1} 요약 실패, 첫 번째 기사 사용: {e}")
                        group_summaries.append(group[0])
            
            logger.info(f"[{category_en}] 1차 클러스터링 완료: {len(full_contents)}개 → {len(group_summaries)}개 그룹")
            final_contents = group_summaries
            
        except Exception as e:
            logger.warning(f"[{category_en}] 1차 클러스터링 실패, 원본 기사 사용: {e}")
            final_contents = full_contents

        # GPTで最終スクリプト生成
        logger.info(f"[{category_en}] 대본 생성 시작: {len(final_contents)}개 기사")
        script = summarize_articles(final_contents, category_en)
        if not script or len(script) < 500:
            logger.warning(f"[{category_en}] 요약 길이 부족 → 스킵")
            return {"category": category_en, "status": "failed", "reason": "summary_too_short"}

        logger.info(f"[{category_en}] 요약 완료: {len(script)}자")

        # ElevenLabsでTTS変換後、S3のPresigned URLを生成
        try:
            audio_bytes = text_to_speech(script)
            audio_url = upload_audio_to_s3_presigned(
                file_bytes=audio_bytes,
                user_id="shared",
                category=category_en,
                date=date,
                expires_in_seconds=604800  # 有効期間：7日間
            )
            logger.info(f"[{category_en}] TTS Presigned URL 생성 완료")
        except Exception as e:
            logger.warning(f"[{category_en}] TTS 업로드 실패: {str(e)}")
            return {"category": category_en, "status": "failed", "reason": f"tts_failed: {str(e)}"}

        # 結果をDynamoDBに保存
        item = {
            "frequency_id": freq_id,
            "category": category_en,
            "date": date,
            "script": script,
            "audio_url": audio_url,
            "created_at": datetime.utcnow().isoformat()
        }

        save_frequency_summary(item)
        
        elapsed_time = time.time() - start_time
        logger.info(f"[{category_en}] DynamoDB 저장 완료 (소요시간: {elapsed_time:.1f}초)")
        
        return {
            "category": category_en, 
            "status": "success", 
            "script_length": len(script),
            "elapsed_time": elapsed_time
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.exception(f"[{category_en}] 처리 실패 (소요시간: {elapsed_time:.1f}초): {str(e)}")
        return {
            "category": category_en, 
            "status": "failed", 
            "reason": f"exception: {str(e)}",
            "elapsed_time": elapsed_time
        }

def generate_all_frequencies():
    """
    毎朝6時に自動実行：カテゴリ別のニュース本文をもとに共通台本・音声を生成（並列処理）
    - ニュースカードDBからカテゴリごとに正確に30件の記事を使用（トークン最適化）
    - 不足している本文は再抽出
    - GPTで要約し、スクリプトを生成（クラスタリング含む）
    - ElevenLabsのTTSで音声変換し、S3にアップロード
    - Frequenciesテーブルに保存（スクリプト＋Presigned MP3リンク）
    """
    date = get_today_kst()
    all_categories = list(CATEGORY_MAP.keys())
    total_start_time = time.time()
    
    logger.info(f"병렬 처리 시작: {len(all_categories)}개 카테고리 동시 처리")
    # 並列処理開始：{len(all_categories)}件のカテゴリを同時処理
    logger.info(f"카테고리 목록: {all_categories}")
    # カテゴリ一覧の出力

    # 並列処理：ThreadPoolExecutorを使用
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:  # 6カテゴリを同時に処理
        # 各カテゴリを並列で処理するFutureオブジェクトを生成
        future_to_category = {
            executor.submit(process_single_category, category_ko, date): category_ko 
            for category_ko in all_categories
        }
        
        # 完了した順に結果を収集
        for future in concurrent.futures.as_completed(future_to_category):
            category_ko = future_to_category[future]
            try:
                result = future.result()
                results.append(result)
                
                if result["status"] == "success":
                    logger.info(f"[{result['category']}] 성공 완료 - 대본: {result['script_length']}자, 소요시간: {result['elapsed_time']:.1f}초")
                    # 成功完了 - 台本：{文字数}文字、所要時間：{秒数}秒
                elif result["status"] == "skipped":
                    logger.info(f"[{result['category']}] 스킵됨 - 사유: {result['reason']}")
                    # スキップ - 理由：{reason}
                else:
                    logger.warning(f"[{result['category']}] 실패 - 사유: {result['reason']}")
                    # 失敗 - 理由：{reason}
                    
            except Exception as exc:
                logger.exception(f"[{category_ko}] 예상치 못한 오류: {exc}")
                # 想定外のエラー発生
                results.append({
                    "category": CATEGORY_MAP[category_ko]["api_name"], 
                    "status": "failed", 
                    "reason": f"executor_exception: {str(exc)}"
                })

    # 全体の結果を要約
    total_elapsed_time = time.time() - total_start_time
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    skipped_count = sum(1 for r in results if r["status"] == "skipped")
    
    logger.info("병렬 처리 완료!")
    # 並列処理完了！
    logger.info(f"총 소요시간: {total_elapsed_time:.1f}초")
    # 総所要時間
    logger.info(f"결과 요약: 성공 {success_count}개, 실패 {failed_count}개, 스킵 {skipped_count}개")
    # 成功件数、失敗件数、スキップ件数の要約
    
    # 各カテゴリごとの詳細結果ログ
    for result in results:
        status_text = {"success": "SUCCESS", "failed": "FAILED", "skipped": "SKIPPED"}.get(result["status"], "UNKNOWN")
        logger.info(f"{status_text} {result['category']}: {result['status']}")
        if "reason" in result:
            logger.info(f"   └─ 사유: {result['reason']}")
            # 理由の出力

    return results
