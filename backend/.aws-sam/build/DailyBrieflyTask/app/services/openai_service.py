# app/services/openai_service.py

import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

def summarize_articles(texts: list[str], category: str) -> str:
    """
    GPT-4o-mini를 사용하여 요약된 기사들을 종합하여 팟캐스트 대본 형태로 생성
    """
    prompt = (
        f"당신은 지적이고 친절한 팟캐스트 진행자입니다. "
        f"다음은 '{category}' 카테고리의 주요 뉴스 기사 요약입니다.\n\n"
        "각 기사들의 내용을 기반으로, 청취자에게 쉽고 흥미롭게 전달할 수 있도록 "
        "하나의 흐름을 가진 약 1800~2000자 분량의 대본을 작성해주세요.\n\n"
        "조건:\n"
        "- 너무 딱딱한 뉴스톤이 아니라 자연스럽고 전달력 있는 말투\n"
        "- 중복 표현 없이 핵심 내용만 간결하게 구성\n"
        "- '오늘 {category} 분야에서는 이런 이슈들이 있었습니다.'와 같은 도입부 및 마무리 멘트 포함\n"
        "- 청취자가 실제로 듣는 팟캐스트처럼 읽기 좋게 구성"
    )

    context = prompt + "\n\n기사 요약 목록:\n" + "\n\n".join(texts)

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": context}],
        temperature=0.7,
    )

    return response.choices[0].message.content.strip()