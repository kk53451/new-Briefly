from fastapi import APIRouter, Depends, HTTPException, Query
from app.utils.dynamo import (
    get_news_by_category_and_date,
    get_news_card_by_id,
    get_today_news_grouped,
    add_bookmark,
    remove_bookmark
)
from app.utils.jwt_service import get_current_user
from typing import List
from datetime import datetime
import pytz

# ✅ /api/news 하위 엔드포인트 그룹
router = APIRouter(prefix="/api/news", tags=["News"])

# ✅ [GET] /api/news?category=xxx
@router.get("/")
def get_news(category: str = Query(..., description="뉴스 카테고리")):
    """
    특정 카테고리의 오늘 뉴스 목록 조회 (최대 10개)

    - 파라미터: category (예: "politics", "tech")
    - 정렬 기준: 인기순 or 수집순 (현재는 상위 10개 슬라이싱)
    - 사용 예시: '내 뉴스' 탭 등에서 사용자 관심 카테고리별 뉴스 보기
    """
    kst = pytz.timezone("Asia/Seoul")
    today = datetime.now(kst).strftime("%Y-%m-%d")
    items = get_news_by_category_and_date(category, today)
    return items[:10]

# ✅ [GET] /api/news/today
@router.get("/today")
def get_today_news():
    """
    오늘의 뉴스 탭: 카테고리별 대표 뉴스 6개씩 그룹핑하여 반환

    - 내부적으로 DynamoDB에서 각 카테고리별 뉴스 6개씩 가져옴
    - 사용 예시: '오늘의 뉴스' 탭에서 전체 카테고리 뉴스 카드 슬라이드 출력
    - 리턴 예시: { "정치": [...6개], "경제": [...6개], ... }
    """
    return get_today_news_grouped()

# ✅ [GET] /api/news/{news_id}
@router.get("/{news_id}")
def get_news_detail(news_id: str):
    """
    개별 뉴스 카드 상세 내용 조회

    - 뉴스 ID를 기준으로 뉴스 상세 데이터 반환
    - content, publisher, summary 등 포함
    - 예외 처리: 존재하지 않으면 404 반환
    """
    item =  get_news_card_by_id(news_id)
    if not item:
        raise HTTPException(status_code=404, detail="뉴스를 찾을 수 없습니다.")
    return item

# ✅ [POST] /api/news/bookmark
@router.post("/bookmark")
def bookmark_news(news_id: str, user=Depends(get_current_user)):
    """
    뉴스 북마크 추가

    - 인증 필요
    - 북마크된 뉴스는 사용자 북마크 목록에서 확인 가능
    - 사용 예시: 뉴스 카드의 북마크 버튼 클릭 시
    """
    add_bookmark(user_id=user["user_id"], news_id=news_id)
    return {"message": "북마크 완료"}

# ✅ [DELETE] /api/news/bookmark/{news_id}
@router.delete("/bookmark/{news_id}")
def delete_bookmark(news_id: str, user=Depends(get_current_user)):
    """
    뉴스 북마크 삭제

    - 인증 필요
    - 사용 예시: 북마크 탭 또는 뉴스 카드에서 북마크 해제 버튼 클릭 시
    """
    remove_bookmark(user_id=user["user_id"], news_id=news_id)
    return {"message": "북마크 삭제됨"}
