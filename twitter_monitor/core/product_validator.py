"""
产品验证模块
使用LLM验证提取的产品候选
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from utils.llm_helper import LLMHelper
from config.config import PRODUCT_DISCOVERY


class ProductValidator:
    """
    产品验证器（基于LLM）
    """

    def __init__(self, model='deepseek-v3.1-terminus'):
        self.llm = LLMHelper(model=model)
        self.confidence_threshold = PRODUCT_DISCOVERY['confidence_threshold']

    def validate_candidates(self, candidates, tweets_map, batch_size=50):
        """
        验证候选产品

        Args:
            candidates: 候选产品列表
            tweets_map: 推文映射 {tweet_id: tweet}
            batch_size: 批处理大小

        Returns:
            list: 验证通过的产品
        """
        print(f"\n🤖 LLM验证产品候选...")
        print(f"   - 候选数量: {len(candidates)}")
        print(f"   - 批处理大小: {batch_size}")

        # 按推文ID分组（同一推文的候选一起验证）
        grouped = self._group_by_tweet(candidates)
        print(f"   - 涉及推文: {len(grouped)}")

        validated = []
        total_tweets = len(grouped)

        for i, (tweet_id, tweet_candidates) in enumerate(grouped.items(), 1):
            try:
                tweet = tweets_map.get(tweet_id, {})
                result = self._validate_tweet_products(tweet, tweet_candidates)

                if result and result.get('is_about_product'):
                    validated.extend(result['products'])

                if i % 10 == 0:
                    print(f"   进度: {i}/{total_tweets} 推文")

            except Exception as e:
                print(f"   ⚠️ 验证推文 {tweet_id} 失败: {e}")
                continue

        # 过滤低置信度
        validated = [
            p for p in validated
            if p.get('confidence', 0) >= self.confidence_threshold
        ]

        print(f"   ✅ 验证完成: {len(validated)} 个产品通过")

        return validated

    def _group_by_tweet(self, candidates):
        """按推文ID分组"""
        grouped = {}
        for candidate in candidates:
            tweet_id = candidate['tweet_id']
            if tweet_id not in grouped:
                grouped[tweet_id] = []
            grouped[tweet_id].append(candidate)
        return grouped

    def _validate_tweet_products(self, tweet, candidates):
        """
        验证单条推文中的产品候选

        Args:
            tweet: 推文数据
            candidates: 该推文的候选列表

        Returns:
            dict: 验证结果
        """
        text = tweet.get('text', '')

        # 构建prompt
        prompt = self._build_validation_prompt(text, candidates)

        # 调用LLM
        result = self.llm.call_claude_json(prompt)

        # 添加原始信息
        if result.get('is_about_product') and result.get('products'):
            for product in result['products']:
                product['tweet_id'] = tweet.get('id', '')
                product['tweet_text'] = text
                product['author'] = tweet.get('author_id', '')

        return result

    def _build_validation_prompt(self, tweet_text, candidates):
        """
        构建验证prompt

        Args:
            tweet_text: 推文文本
            candidates: 候选列表

        Returns:
            str: prompt
        """
        # 格式化候选
        candidate_list = "\n".join([
            f"- {c['product_name']} (信号: {c['signal_word']}, 类别: {c['signal_category']})"
            for c in candidates
        ])

        prompt = f"""
你是一个AI产品识别专家。我从这条推文中检测到一些可能的产品名称，请帮我验证。

【推文内容】
"{tweet_text}"

【候选产品】
{candidate_list}

【任务】
请分析：
1. 这条推文是否真的在讨论AI产品/模型/工具？
2. 如果是，提取出准确的产品名称（可能有多个）
3. 判断每个产品的类型
4. 判断是否是新发布的产品

【判断标准】
- ✅ 是产品: Claude, GPT-4, Midjourney, Cursor（具体的AI产品/模型/工具）
- ❌ 不是产品: AI, ChatGPT(太通用), Google(公司名), OpenAI(公司名)
- ❌ 不是产品: 人名、地名、通用词汇

【返回格式】
请严格按照以下JSON格式返回：

{{
  "is_about_product": true/false,
  "products": [
    {{
      "name": "准确的产品名（首字母大写）",
      "type": "model/tool/platform/other",
      "is_new_release": true/false,
      "confidence": 0.0-1.0,
      "reasoning": "简短的判断理由"
    }}
  ]
}}

注意：
- 如果不是在讨论产品，返回 {{"is_about_product": false, "products": []}}
- 产品名要准确，去除多余词汇（如"the new"等）
- 置信度要诚实，不确定的给低分
- is_new_release: 只有明确说"发布/released/announced"才是true
"""

        return prompt

    def merge_similar_products(self, products):
        """
        合并相似的产品名（简单版本）

        Args:
            products: 产品列表

        Returns:
            list: 合并后的产品
        """
        from difflib import SequenceMatcher

        if len(products) <= 1:
            return products

        # 计算相似度矩阵
        n = len(products)
        merged_indices = set()
        final_products = []

        for i in range(n):
            if i in merged_indices:
                continue

            current = products[i]
            similar_group = [current]

            for j in range(i + 1, n):
                if j in merged_indices:
                    continue

                # 计算名称相似度
                name1 = current['name'].lower()
                name2 = products[j]['name'].lower()

                similarity = SequenceMatcher(None, name1, name2).ratio()

                # 包含关系也认为相似
                if name1 in name2 or name2 in name1:
                    similarity = max(similarity, 0.8)

                # 相似度阈值
                if similarity > 0.7:
                    similar_group.append(products[j])
                    merged_indices.add(j)

            # 选择置信度最高的作为代表
            representative = max(similar_group, key=lambda x: x.get('confidence', 0))
            final_products.append(representative)

            merged_indices.add(i)

        return final_products


if __name__ == '__main__':
    # 测试
    validator = ProductValidator()

    test_candidates = [
        {
            'product_name': 'GPT-5',
            'tweet_id': 'test_1',
            'signal_word': 'just released',
            'signal_category': 'launch',
        }
    ]

    test_tweets = {
        'test_1': {
            'id': 'test_1',
            'text': 'OpenAI just released GPT-5 and it\'s amazing!',
            'author_id': 'user123',
        }
    }

    result = validator.validate_candidates(test_candidates, test_tweets)
    print("\n验证结果:", json.dumps(result, indent=2, ensure_ascii=False))
