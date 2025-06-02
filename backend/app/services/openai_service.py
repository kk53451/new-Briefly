# app/services/openai_service.py

import os
import openai
import numpy as np   # 추가!

openai.api_key = os.getenv("OPENAI_API_KEY")

def get_embedding(text: str) -> list:
    res = openai.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return res.data[0].embedding

def cosine_similarity(vec1, vec2):
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def cluster_similar_texts(texts, threshold=0.8):
    embeddings = [get_embedding(t) for t in texts]
    clusters = []
    for idx, emb in enumerate(embeddings):
        added = False
        for cluster in clusters:
            if cosine_similarity(emb, cluster['embedding']) > threshold:
                cluster['indices'].append(idx)
                added = True
                break
        if not added:
            clusters.append({'embedding': emb, 'indices': [idx]})
    grouped = [[texts[i] for i in c['indices']] for c in clusters]
    return grouped

def summarize_group(texts: list, category: str) -> str:
    prompt = (
        f"다음은 '{category}' 분야에서 비슷한 뉴스 기사들입니다. "
        f"중복 내용을 합치고, 하나의 자연스러운 요약(600자~800자)으로 써주세요. "
        f"핵심 이슈와 내용만 간결하게 담아주세요.\n\n"
        + "\n\n".join(texts)
    )
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=900
    )
    return response.choices[0].message.content.strip()

def summarize_articles(texts: list[str], category: str) -> str:
    prompt = (
        f"당신은 지적이고 친절한 팟캐스트 진행자입니다. "
        f"다음은 '{category}' 카테고리의 주요 뉴스 기사 요약입니다.\n\n"
        "각 기사들의 내용을 기반으로, 청취자에게 쉽고 흥미롭게 전달할 수 있도록 "
        "하나의 흐름을 가진 1800자 이상 2000자 이하 분량의 대본을 작성해주세요.\n\n"
        "조건:\n"
        "- 반드시 1800자 이상이 되어야 합니다.\n"
        "- 너무 딱딱한 뉴스톤이 아니라 자연스럽고 전달력 있는 말투\n"
        "- 중복 표현 없이 핵심 내용만 간결하게 구성\n"
        "-'오늘 {category} 분야에서는 이런 이슈들이 있었습니다.'와 같은 도입부 및 마무리 멘트 포함\n"
        "- 청취자가 실제로 듣는 팟캐스트처럼 읽기 좋게 구성"
    )
    context = prompt + "\n\n기사 요약 목록:\n" + "\n\n".join(texts)
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": context}],
        temperature=0.7,
        max_tokens=2200
    )
    return response.choices[0].message.content.strip()
