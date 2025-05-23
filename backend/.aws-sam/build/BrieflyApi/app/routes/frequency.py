from fastapi import APIRouter, Depends, HTTPException
from app.utils.jwt_service import get_current_user
from app.utils.dynamo import get_frequency_by_category_and_date
from app.utils.date import get_today_kst

# ✅ /api/frequencies 엔드포인트 그룹
router = APIRouter(prefix="/api/frequencies", tags=["Frequency"])

# ✅ [GET] /api/frequencies
@router.get("")
def get_frequencies(user: dict = Depends(get_current_user)):
    """
    오늘 날짜 기준으로 사용자의 관심 카테고리별 공유 요약(TTS 스크립트 및 오디오)을 반환합니다.
    
    - 각 카테고리에 대해, 시스템이 사전에 생성해둔 공유 주파수를 DynamoDB에서 가져옵니다.
    - 프론트에서는 사용자 관심사 기반의 오디오 목록 뷰에 사용됩니다.
    - 리턴: [{category, script, audio_url, ...}, ...]
    """
    date = get_today_kst()
    results = []

    for category in user.get("interests", []):
        item = get_frequency_by_category_and_date(category, date)
        if item:
            results.append(item)

    return results

# ✅ [GET] /api/frequencies/{category}
@router.get("/{category}")
def get_frequency_detail(category: str, user: dict = Depends(get_current_user)):
    """
    특정 카테고리에 대한 공유 주파수 상세 정보를 조회합니다.
    
    - 사용자는 관심 카테고리에 상관없이 직접 카테고리 detail 접근 가능
    - 공유된 script (요약 텍스트) 및 audio_url (MP3) 정보를 반환
    - 예외 처리: 해당 카테고리에 오늘자 데이터가 없을 경우 404 반환
    """
    date = get_today_kst()
    result = get_frequency_by_category_and_date(category, date)
    if not result:
        raise HTTPException(status_code=404, detail="해당 주파수가 없습니다.")
    return result
