from datetime import datetime
import pytz

def get_today_kst():
    kst = pytz.timezone("Asia/Seoul")                  # KSTタイムゾーンを設定
    now_kst = datetime.now(kst)                        # 現在時刻をKST基準で取得
    return now_kst.strftime("%Y-%m-%d")                # "2025-05-23"形式で返す
