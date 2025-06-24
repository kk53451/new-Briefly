# app/tasks/scheduler.py

import logging
import traceback
from app.utils.date import get_today_kst

# ログ設定
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS EventBridge → Lambdaトリガー関数（毎朝6時に自動実行）
    - 本日のニュース収集（collect_today_news）
    - カテゴリ別の総合要約 + TTS生成（generate_all_frequencies）
    - 結果ログおよび要約を返却
    """

    logger.info(" Lambda 트리거 시작")  # Lambdaトリガー開始
    today = get_today_kst()
    logger.info(f" 기준 날짜: {today}")  # 基準日付ログ出力

    # 結果サマリー用ディクショナリ初期化
    result_summary = {
        "news": " 실패",       # 失敗
        "frequency": " 실패"   # 失敗
    }

    # 第1段階：本日のニュース収集
    try:
        logger.info("뉴스 수집 시작")  # ニュース収集開始
        from app.tasks.collect_news import collect_today_news
        collect_today_news()
        result_summary["news"] = " 완료"  # 完了
        logger.info(" 뉴스 수집 완료")  # ニュース収集完了
    except ImportError as e:
        logger.error(f"[뉴스 수집 모듈 오류] {e}")  # ニュース収集モジュールエラー
        logger.error(traceback.format_exc())
    except MemoryError as e:
        logger.error(f"[뉴스 수집 메모리 부족] {e}")  # メモリ不足
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"[뉴스 수집 예상치 못한 오류] {e}")  # 予期せぬエラー
        logger.error(traceback.format_exc())

    # 第2段階：カテゴリー別要約（TTS含む）生成
    try:
        logger.info("🎧 주파수 요약 생성 시작")  # 周波数要約生成開始
        from app.tasks.generate_frequency import generate_all_frequencies
        generate_all_frequencies()
        result_summary["frequency"] = " 완료"  # 完了
        logger.info(" 주파수 요약 생성 완료")  # 要約生成完了
    except ImportError as e:
        logger.error(f"[주파수 생성 모듈 오류] {e}")  # モジュールエラー
        logger.error(traceback.format_exc())
    except MemoryError as e:
        logger.error(f"[주파수 생성 메모리 부족] {e}")  # メモリ不足
        logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"[주파수 생성 예상치 못한 오류] {e}")  # 予期せぬエラー
        logger.error(traceback.format_exc())

    logger.info(f"📦 작업 결과 요약: {result_summary}")  # 処理結果の要約ログ出力

    return {
        "statusCode": 200,
        "body": {
            "message": f"Lambda 작업 완료: {today}",  # Lambda処理完了
            "result": result_summary
        }
    }
