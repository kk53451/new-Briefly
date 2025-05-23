# app/utils/date.py

from datetime import datetime
import pytz

def get_today_kst():
    kst = pytz.timezone("Asia/Seoul")                  # KST 시간대 설정
    now_kst = datetime.now(kst)                        # 현재 시간을 KST 기준으로 가져옴
    return now_kst.strftime("%Y-%m-%d")                # "2025-05-23" 형식으로 반환
