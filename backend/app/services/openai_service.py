# app/services/openai_service.py

import os
import openai
import numpy as np 
import logging

openai.api_key = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini") 

logger = logging.getLogger(__name__)

# Few-shot例（カテゴリごとの入力・出力例）
FEW_SHOT_EXAMPLES = {
    "경제": {
        "input": [
            "[기사 1] 삼성전자가 3분기 영업이익 10조원을 기록했다고 28일 발표했다. 이는 전년 동기 대비 30% 증가한 수치다.",
            "[기사 2] 삼성전자 3분기 실적 발표 후 주가가 3% 상승했다. 시장 예상치 9.5조원을 크게 상회한 결과다.",
            "[기사 3] 반도체 업황 회복으로 삼성전자 실적이 개선됐다. 메모리 반도체 가격 상승이 주요 요인으로 분석된다."
        ],
        "output": "삼성전자가 28일 3분기 영업이익 10조원을 기록했다고 발표했다. 이는 전년 동기 대비 30% 증가한 수치로 시장 예상치 9.5조원을 크게 상회했다. 실적 발표 직후 삼성전자 주가는 전일 대비 3% 상승하며 투자자들의 긍정적 반응을 보였다. 반도체 업황 회복과 메모리 반도체 가격 상승이 이번 실적 개선의 주요 동력으로 분석되고 있어, 4분기에도 이런 상승세가 이어질지 주목된다."
    },
    "정치": {
        "input": [
            "[기사 1] 정부가 부동산 정책 개편안을 29일 발표할 예정이다. 주택 공급 확대가 핵심 내용으로 알려졌다.",
            "[기사 2] 야당은 정부 부동산 정책이 서민 주거 안정에 도움이 되지 않는다고 비판했다.",
            "[기사 3] 부동산업계는 새 정책이 시장 안정화에 기여할 것으로 기대한다고 밝혔다."
        ],
        "output": "정부가 29일 부동산 정책 개편안을 발표할 예정이다. 주택 공급 확대를 핵심으로 하는 이번 정책에 대해 여야와 업계의 반응이 엇갈리고 있다. 정부는 주택 공급 확대를 통한 시장 안정화를 목표로 한다고 밝혔으나, 야당은 서민 주거 안정에 실질적 도움이 되지 않을 것이라고 비판했다. 반면 부동산업계는 새 정책이 시장 안정화에 긍정적 영향을 미칠 것으로 기대한다고 입장을 표했다."
    },
    "사회": {
        "input": [
            "[기사 1] 서울시가 청년 주거 지원을 위해 월세 보조금을 30만원으로 확대한다고 발표했다.",
            "[기사 2] 청년들은 월세 보조금 확대에 환영 의사를 표했지만 여전히 부족하다는 반응이다.",
            "[기사 3] 시민단체는 근본적인 주거비 해결책이 필요하다고 지적했다."
        ],
        "output": "서울시가 청년 주거 부담 완화를 위해 월세 보조금을 기존보다 확대해 30만원으로 지원한다고 발표했다. 이번 정책에 대해 청년들은 환영 의사를 표했지만, 여전히 높은 주거비에 비해 부족하다는 반응을 보이고 있다. 시민단체들은 일시적 보조금보다는 주거비 상승의 근본적 원인을 해결하는 정책이 필요하다고 지적하며, 보다 체계적인 청년 주거 정책 마련을 촉구했다."
    },
    "IT": {
        "input": [
            "[기사 1] 네이버가 새로운 AI 검색 서비스 '하이퍼클로바X'를 공개했다. 생성형 AI 기술을 활용한 것이 특징이다.",
            "[기사 2] 하이퍼클로바X는 기존 검색과 달리 대화형으로 답변을 제공한다고 네이버가 설명했다.",
            "[기사 3] IT업계는 네이버의 AI 검색이 구글과의 경쟁에서 차별화 요소가 될 것으로 전망했다."
        ],
        "output": "네이버가 생성형 AI 기술을 활용한 새로운 검색 서비스 '하이퍼클로바X'를 공개했다. 기존 키워드 검색과 달리 사용자와 대화하듯 자연스럽게 답변을 제공하는 것이 핵심 특징이다. IT업계에서는 이번 서비스가 구글 등 글로벌 검색 엔진과의 경쟁에서 네이버만의 차별화 요소로 작용할 것으로 분석하고 있어, 국내 검색 시장에 새로운 변화를 가져올지 주목된다."
    },
    "문화": {
        "input": [
            "[기사 1] BTS 멤버 지민의 솔로 앨범이 빌보드 200 차트 2위에 올랐다.",
            "[기사 2] 지민은 한국 솔로 가수 최초로 빌보드 200 톱3에 진입하는 기록을 세웠다.",
            "[기사 3] 팬들은 SNS를 통해 지민의 성과를 축하하며 응원 메시지를 전했다."
        ],
        "output": "BTS 멤버 지민의 솔로 앨범이 빌보드 200 차트 2위에 오르며 한국 솔로 가수 최초로 톱3 진입이라는 역사적 기록을 달성했다. 이는 K-팝 솔로 아티스트로서는 전례 없는 성과로, 지민의 글로벌 영향력을 다시 한번 입증했다. 전 세계 팬들은 SNS를 통해 축하와 응원 메시지를 쏟아내며 이번 성과를 함께 기뻐하고 있어, K-팝의 글로벌 위상을 더욱 높이는 계기가 되고 있다."
    },
    "스포츠": {
        "input": [
            "[기사 1] 손흥민이 토트넘과의 경기에서 2골을 넣으며 팀 승리를 이끌었다.",
            "[기사 2] 이번 경기로 손흥민은 시즌 15골을 기록하며 개인 최고 기록에 근접했다.",
            "[기사 3] 토트넘 팬들은 손흥민의 활약에 열광하며 'Son is the King'이라고 외쳤다."
        ],
        "output": "손흥민이 토트넘 경기에서 멀티골을 터뜨리며 팀 승리의 주역으로 나섰다. 이번 2골로 시즌 15골을 기록한 손흥민은 개인 최고 기록 경신을 눈앞에 두고 있어 더욱 의미가 크다. 경기장을 가득 메운 토트넘 팬들은 'Son is the King'을 연호하며 손흥민의 환상적인 활약에 열광했고, 그의 꾸준한 득점 행진이 팀의 상위권 도약에 핵심 동력이 되고 있다."
    }
}

def get_embedding(text: str) -> list:
    """
    テキストの埋め込みベクトルを生成します。
    """
    try:
        res = openai.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        return res.data[0].embedding
    except openai.RateLimitError as e:
        logger.warning(f" OpenAI Rate Limit 초과: {e}")
        # OpenAIのレート制限を超過
        return []
    except openai.APIError as e:
        logger.warning(f" OpenAI API 오류: {e}")
        # OpenAI APIエラー
        return []
    except openai.AuthenticationError as e:
        logger.warning(f" OpenAI 인증 오류: {e}")
        # OpenAI認証エラー
        return []
    except Exception as e:
        logger.warning(f" 임베딩 생성 예상치 못한 오류: {e}")
        # 埋め込み生成中の予期しないエラー
        return []


def cosine_similarity(vec1, vec2):
    """
    2つのベクトル間のコサイン類似度を計算します。
    """
    try:
        if not vec1 or not vec2:
            return 0.0
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    except (ValueError, ZeroDivisionError, np.linalg.LinAlgError) as e:
        logger.warning(f" コサイン類似度の計算エラー: {e}")
        # コサイン類似度の計算エラー
        return 0.0
    except Exception as e:
        logger.warning(f" コサイン類似度の予期しないエラー: {e}")
        # コサイン類似度の予期しないエラー
        return 0.0

def cluster_similar_texts(texts, threshold=0.75):
    """
    類似するテキストをクラスタリングし、重複する内容をグループ化します。
    """
    if len(texts) <= 1:
        return [texts]
    try:
        logger.info(f"{len(texts)}個のテキスト クラスタリングを開始...")
        # テキストのクラスタリングを開始
        embeddings = []
        valid_texts = []
        # 埋め込み生成（失敗したものは除外）
        for i, text in enumerate(texts):
            emb = get_embedding(text[:1000])  # トークン制限：最大1000文字
            if emb:
                embeddings.append(emb)
                valid_texts.append(text)
        if len(embeddings) <= 1:
            return [valid_texts]
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
        # 各クラスタごとにテキストをグループ化
        grouped = [[valid_texts[i] for i in c['indices']] for c in clusters]
        logger.info(f"{len(texts)}個のテキストを {len(grouped)}個のクラスタにグループ化しました")
        # クラスタリングの完了ログ
        return grouped
    except MemoryError as e:
        logger.warning(f" メモリ不足によるクラスタリング失敗: {e}")
        # メモリ不足によるクラスタリング失敗
        return [texts]
    except (ValueError, TypeError) as e:
        logger.warning(f" データ型のエラーによる失敗: {e}")
        # データ型のエラーによる失敗
        return [texts]
    except Exception as e:
        logger.warning(f" クラスタリング中の予期しないエラー, 元のリストを返す: {e}")
        # 予期しないエラーが発生した場合は元のリストを返す
        return [texts]

def summarize_group(texts: list, category: str) -> str:
    """
    クラスタリングされた類似記事を1つの要約に統合します。
    Few-shot学習と品質検証を含みます。
    """
    if len(texts) == 1:
        return texts[0]
    # 各記事を800文字に制限
    limited_texts = [text[:800] for text in texts]
    # カテゴリごとの特化スタイル
    category_context = {
        "정치": "정책の背景と影響、さまざまな視点をバランスよく",
        "경제": "経済指標の意味と一般人への影響に注目",
        "사회": "社会問題の原因と影響、市民の反応を含めて",
        "문화": "文化的な意味やトレンド、大衆の関心を含めて",
        "IT": "技術の革新性と実生活への応用可能性",
        "스포츠": "試合結果と選手のストーリー、ファンの反応"
    }.get(category, "核心の事実とその意味を")
    # Few-shotの例を追加
    few_shot_example = ""
    if category in FEW_SHOT_EXAMPLES:
        example = FEW_SHOT_EXAMPLES[category]
        few_shot_example = (
            f"**よい統合要約の例 ({category}分野):**\n"
            + "\n".join(example["input"]) + "\n\n"
            f"→ **統合要約**: {example['output']}\n\n"
            "上記の例のように、重複を除去し、重要な情報を論理的につなげて作成してください。\n\n"
        )
    prompt = (
        f"あなたはニュース要約の専門家です。「{category}」分野の類似記事を、"
        f"完成度の高い1つの要約に統合してください。\n\n"
        f"{few_shot_example}"
        f"**統合要約作成ガイド:**\n"
        f"1. **重要事実の抽出**: 最も重要な事実を優先順位で整理\n"
        f"2. **重複排除**: 繰り返される内容は一度だけ言及し、重要性に応じて強調\n"
        f"3. **文脈提供**: {category_context} を含める\n"
        f"4. **論理的構成**: 時系列や重要度に基づいて自然につなぐ\n"
        f"5. **具体的情報の保持**: 日付、数値、人名などの具体的情報を保持\n"
        f"6. **バランスの取れた視点**: 複数の視点がある場合は公平に提示\n\n"
        f"**品質基準:**\n"
        f"- 独立して読んでも理解できる完成された要約\n"
        f"- 重要な情報を漏らさず簡潔に\n"
        f"- 自然な韓国語の文体\n"
        f"- 500-700文字（音声変換に最適化)\n\n"
        f"**統合する記事:**\n"
        + "\n\n".join([f"[記事 {i+1}]\n{text}" for i, text in enumerate(limited_texts)])
        + "\n\n上記の記事をもとに統合要約を作成してください:"
    )
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            temp = 0.3 + (attempt * 0.2)
            response = openai.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                max_tokens=700
            )
            summary = response.choices[0].message.content.strip()
            logger.info(f"試行 {attempt + 1}: 温度={temp:.1f}, 要約生成完了 ({len(summary)}文字)")
            return summary
        except openai.RateLimitError as e:
            logger.warning(f" OpenAI Rate Limit 超過 (グループ要約, 試行 {attempt + 1}): {e}")
            # OpenAIレート制限超過
            if attempt == max_attempts - 1:
                return texts[0]
            continue
        except openai.APIError as e:
            logger.warning(f" OpenAI API エラー (グループ要約, 試行 {attempt + 1}): {e}")
            # OpenAI APIエラー
            if attempt == max_attempts - 1:
                return texts[0]
            continue
        except openai.AuthenticationError as e:
            logger.warning(f" OpenAI 認証エラー (グループ要約): {e}")
            # OpenAI認証エラー
            return texts[0]
        except Exception as e:
            logger.warning(f" グループ要約中の予期しないエラー (試行 {attempt + 1}): {e}")
            # 予期しないエラー
            if attempt == max_attempts - 1:
                return texts[0]
            continue
    logger.warning("すべての要約試行に失敗したため、元のテキストを返します。")
    # すべての要約試行に失敗したため、元のテキストを返します。
    return texts[0]

def get_category_specific_style(category: str) -> str:
    """
    カテゴリごとの特化した進行スタイルとトーンを返す
    """
    category_styles = {
        "정치": {
            "tone": "慎重でバランスの取れた",
            "style": "複雑な政治状況を簡単に説明し、さまざまな視点を提示",
            "examples": "'この政策が私たちの生活にどのような影響を与えるか', '両方の見解を整理してみましょう'"
        },
        "경제": {
            "tone": "専門的で親しみやすい",
            "style": "経済用語を日常言語に翻訳し、実生活との関連性を強調",
            "examples": "'簡単に言うと', '私たちの財布にはどのような意味があるでしょうか', '例を挙げて'"
        },
        "사회": {
            "tone": "温かく共感する",
            "style": "人々の話に集中し、感情的な共感を形成",
            "examples": "'本当に悲しいことですね', '多くの人が共感すると思いますが', '私たち全員の関心が必要です'"
        },
        "문화": {
            "tone": "明るく楽しく",
            "style": "面白く生き生きして、文化的な意味とトレンドを説明",
            "examples": "'本当に面白いですね', '最近ホットな', '文化的に見て'"
        },
        "IT": {
            "tone": "好奇心が満ちた",
            "style": "技術を簡単に説明し、将来の展望と日常との関連性を強調",
            "examples": "'技術的には', '将来はどうなるでしょうか', '私たちの生活がどうなるか'"
        },
        "스포츠": {
            "tone": "熱心で生き生きした",
            "style": "現場感を持って伝え、選手とチームのストーリーを強調",
            "examples": "'本当に素晴らしい', '感動した瞬間でしたが', 'ファンはそれほど熱心でしたように見えます'"
        }
    }

    if category in category_styles:
        style_info = category_styles[category]
        return (
            f"**{category}分野の特化スタイル:**\n"
            f"- トーン: {style_info['tone']} の雰囲気で\n"
            f"- アプローチ: {style_info['style']}\n"
            f"- よく使う表現: {style_info['examples']}\n\n"
        )
    else:
        return "**一般的なニュースブリーフィングスタイル:**\n- トーン: 親しみやすく信頼感のある\n- アプローチ: バランスの取れた視点で情報を伝える\n\n"


def summarize_articles(texts: list[str], category: str) -> str:
    """
    GPT-4o-miniを使用して複数のニュース要約をもとに、
    一貫した流れのあるポッドキャスト原稿を生成します。
    """
    # 2次クラスタリング: GPT要約文を元に意味的な重複を除去
    try:
        if len(texts) > 5:  # 5個以上のときのみクラスタリングを実行
            # 5件以上のときのみクラスタリングを実行
            logger.info(f"2次クラスタリングを開始: {len(texts)}個の要約文")
            # 2次クラスタリング開始：{len(texts)}件の要約文
            clustered_groups = cluster_similar_texts(texts, threshold=0.75)

            # 各クラスタを1つの要約に統合
            # 各クラスタを1つの要約に統合
            consolidated_texts = []
            for group_idx, group in enumerate(clustered_groups):
                if len(group) > 1:
                    # 複数の類似要約を一つに統合
                    # 複数の類似要約を一つに統合
                    try:
                        summary = summarize_group(group, category)
                        consolidated_texts.append(summary)
                        logger.info(f"2次グループ #{group_idx+1}: {len(group)}個の要約を統合 ({len(summary)}文字)")
                        # 第2グループ #{group_idx+1}：{len(group)}件の要約を統合（{len(summary)}文字）
                    except Exception as e:
                        logger.warning(f" 2次グループ #{group_idx+1} 要約失敗、最初の要約を使用")
                        # 第2グループ #{group_idx+1} の要約失敗、最初の要約を使用
                        consolidated_texts.append(group[0][:1000])  # 長さ制限
                        # 長さ制限
                else:
                    # 単一の要約はそのまま使用（長さ制限）
                    # 単一の要約はそのまま使用（長さ制限）
                    consolidated_texts.append(group[0][:1000])
                    logger.info(f"2次グループ #{group_idx+1}: 単一要約 ({len(group[0][:1000])}文字)")
                    # 第2グループ #{group_idx+1}：単一要約（{len(group[0][:1000])}文字）

            final_texts = consolidated_texts
            logger.info(f"2次クラスタリング完了: {len(texts)}個を{len(final_texts)}個に集約")
            # 2次クラスタリング完了：{len(texts)}件を{len(final_texts)}件に集約
        else:
            # クラスタリングを行わない場合も長さを制限
            # クラスタリングを行わない場合も長さを制限
            final_texts = [text[:1000] for text in texts]
            logger.info(f"2次クラスタリング省略、元の要約数：{len(final_texts)}")
            # クラスタリング省略、元の要約数：{len(final_texts)}

    except Exception as e:
        logger.warning(f" 2次クラスタリング中に失敗、元の要約を使用: {e}")
        # 2次クラスタリング中に失敗、元の要約を使用
        final_texts = [text[:1000] for text in texts]  # 失敗時でも長さを制限
        # 失敗時でも長さを制限

    # 最終的なポッドキャスト原稿の生成
    # 最終的なポッドキャスト原稿の生成
    category_style = get_category_specific_style(category)
    
    prompt = (
        f"あなたは親しみやすく信頼できるニュース進行役です。 "
        f"今日の重要なニュースを友人に伝えるように、自然で温かいトーンで話してください。\n\n"
        
        f"**リスナー:** '{category}'分野に関心のある一般人\n"
        f"**目標:** 複雑なニュースを分かりやすく、楽しく伝えること\n"
        f"**スタイル:** 会話のように自然に、時には感嘆詞や相槌も含めて\n\n"
        f"{category_style}"
        
        "**本日のニュース要約:**\n"
        "{{ニュース要約リスト}}\n\n"
        f"**原稿作成ガイド:**\n"
        "1. **自然な始まり**: 'こんにちは、今日も一緒にいてくれてありがとうございます' のような挨拶\n"
        f"2. **カテゴリ紹介**: '今日は{category}分野に本当に興味深いニュースが多いですね'\n"
        f"3. **ニュース紹介**: 各ニュースに「ところで」「本当に驚いたのは」「なぜ重要かというと」など自然なつなぎ言葉を使用\n"
        f"4. **感情表現**: 'わぁ、これは本当に...', 'うーん、考えてみると...', 'アッ、それともう一つ...' など自然な反応\n"
        f"5. **分かりやすい説明**: 難しい用語は「簡単に言うと」「つまり」「言い換えれば」で補足\n"
        f"6. **個人的な意見**: '個人的には', '私はこの部分が印象的でした' など進行役の視点も含める\n"
        f"7. **自然な締めくくり**: '今日のブリーフィングはここまでです。また明日良いニュースでお会いしましょう'\n\n"

        "**TTS最適化のポイント:**\n"
        "- 文章を長くしすぎず、自然な息継ぎポイントで区切ってください\n"
        "- 強調したい部分には「本当に」「まさに」「特に」などの副詞を使う\n"
        "- 数字や専門用語の前後に少し間を置く\n"
        "- 感嘆詞の活用：「あ」「お」「うーん」「ところで」「でも」など\n\n"

        "**長さの要件:**\n"
        "- 最小1800文字以上（音声で約3～4分相当）\n"
        "- 最大2200文字以下\n"
        "- 各ニュースごとに十分な説明と背景情報を含む\n\n"

        "**重要:** 実際に人が話すように自然で親しみやすく書いてください。 "
        "ニュースアナウンサーではなく、友達が面白い話をしてくれるような雰囲気で！"
    )

    # ニュース要約リストを文字列に変換
    # ニュース要約リストを文字列に変換
    article_list = "\n".join([f"- {text}" for text in final_texts])
    context = prompt.replace("{{ニュース要約リスト}}", article_list)

    try:
        response = openai.chat.completions.create(
            model=MODEL_NAME,  # モデルは環境変数から取得
            messages=[{"role": "user", "content": context}],
            temperature=0.7,
            max_tokens=2000  # トークン制限：2200から2000に短縮
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"生成された原稿の長さ: {len(result)}文字 (モデル: {MODEL_NAME})")  # 使用モデルログ追加
        # 生成された原稿の長さをログに記録
        return result
        
    except openai.RateLimitError as e:
        logger.warning(f" OpenAI Rate Limit 超過 (ポッドキャスト原稿生成): {e}")
        # OpenAIレート制限超過
        return f"今日は{category}分野の重要なニュースをお伝えしました。"
    except openai.APIError as e:
        logger.warning(f" OpenAI API エラー (ポッドキャスト原稿生成): {e}")
        # OpenAI APIエラー
        return f"今日は{category}分野の重要なニュースをお伝えしました。"
    except openai.AuthenticationError as e:
        logger.warning(f" OpenAI 認証エラー (ポッドキャスト原稿生成): {e}")
        # OpenAI認証エラー
        return f"今日は{category}分野の重要なニュースをお伝えしました。"
    except Exception as e:
        logger.warning(f" ポッドキャスト原稿生成中の予期せぬエラー: {e}")
        # 台本生成中の予期せぬエラー
        return f"今日は{category}分野の重要なニュースをお伝えしました。"
