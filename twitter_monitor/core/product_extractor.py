"""
产品提取模块
从包含信号的推文中提取产品名称
"""

import re
from config.config import EXCLUDE_TERMS


class ProductExtractor:
    """
    产品名称提取器（基于信号词）
    """

    def __init__(self):
        self.exclude_terms = EXCLUDE_TERMS

    def extract_products_from_signaled_tweet(self, tweet, signals):
        """
        从包含信号的推文中提取产品名

        Args:
            tweet: 推文数据
            signals: 检测到的信号列表

        Returns:
            list: 提取的产品候选
        """
        text = tweet.get('text', '')
        products = []

        for signal_info in signals:
            signal = signal_info['signal']
            category = signal_info['category']

            # 根据信号类别选择提取策略
            if category in ['launch', 'announcement']:
                candidates = self._extract_near_signal(text, signal)

            elif category == 'new':
                candidates = self._extract_after_new(text, signal)

            elif category == 'comparison':
                candidates = self._extract_comparison_products(text, signal)

            elif category in ['testing', 'availability']:
                candidates = self._extract_action_target(text, signal)

            else:
                # 通用提取：信号词附近的大写词组
                candidates = self._extract_capitalized_near(text, signal)

            # 记录候选产品
            for name in candidates:
                # 过滤排除词
                if name in self.exclude_terms:
                    continue

                # 过滤太短的词
                if len(name) < 2:
                    continue

                products.append({
                    'product_name': name.strip(),
                    'tweet_id': tweet.get('id', ''),
                    'tweet_text': text,
                    'author': tweet.get('author_id', ''),
                    'signal_category': category,
                    'signal_word': signal,
                    'confidence': self._calculate_initial_confidence(category, name),
                })

        return products

    def _extract_near_signal(self, text, signal):
        """
        提取信号词附近的产品名

        例如:
        - "Google just released Gemini 2.0" → ["Gemini 2.0"]
        - "Anthropic announced Claude 3.5" → ["Claude 3.5"]
        """
        pattern = re.escape(signal)
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            return []

        signal_pos = match.start()
        products = []

        # 策略1: 信号词之后的词组
        after_text = text[signal_pos + len(signal):].strip()
        # 匹配大写开头的词组，直到遇到特定词或标点
        after_match = re.match(
            r'^[,\s]*([A-Z][A-Za-z0-9\s\.\-]+?)(?:\s+(?:is|has|can|will|for|with|by|and|or|,|\.|!|\?|:|;))',
            after_text
        )

        # 策略2: 信号词之前的词组
        before_text = text[:signal_pos].strip()
        before_match = re.search(r'([A-Z][A-Za-z0-9\s\.\-]+?)\s*$', before_text)

        if after_match:
            products.append(after_match.group(1).strip())
        if before_match:
            products.append(before_match.group(1).strip())

        return products

    def _extract_after_new(self, text, signal='new'):
        """
        提取 "new X" 中的X

        例如:
        - "the new Claude model" → ["Claude"]
        - "introducing new Gemini" → ["Gemini"]
        """
        pattern = rf'\b{re.escape(signal)}\s+([A-Z][A-Za-z0-9\s\-\.]+?)(?:\s+(?:is|has|can|model|tool|AI|from|by|,|\.|!|\?))'
        matches = re.finditer(pattern, text, re.IGNORECASE)

        products = []
        for match in matches:
            product_phrase = match.group(1).strip()

            # 提取首个大写词（可能就是产品名）
            first_word_match = re.match(r'^([A-Z][A-Za-z0-9\-\.]+)', product_phrase)
            if first_word_match:
                products.append(first_word_match.group(1))

            # 如果是多个词，也保留完整短语
            if len(product_phrase.split()) > 1:
                products.append(product_phrase)

        return products

    def _extract_comparison_products(self, text, signal):
        """
        从对比句中提取产品

        例如:
        - "X vs Y" → [X, Y]
        - "better than X" → [X]
        """
        products = []

        if signal.lower() == 'vs':
            # "X vs Y" 模式
            pattern = r'([A-Z][A-Za-z0-9\s\-\.]+?)\s+vs\.?\s+([A-Z][A-Za-z0-9\s\-\.]+?)(?:\s|,|\.|\?|!|$)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                products.extend([match.group(1).strip(), match.group(2).strip()])

        elif 'better than' in signal.lower() or 'beats' in signal.lower():
            # "better than X" 模式
            pattern = rf'{re.escape(signal)}\s+([A-Z][A-Za-z0-9\s\-\.]+?)(?:\s|,|\.|\?|!|$)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                products.append(match.group(1).strip())

        elif 'alternative to' in signal.lower() or 'competitor to' in signal.lower():
            # "alternative to X" 模式
            pattern = rf'{re.escape(signal)}\s+([A-Z][A-Za-z0-9\s\-\.]+?)(?:\s|,|\.|\?|!|$)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                products.append(match.group(1).strip())

        return products

    def _extract_action_target(self, text, signal):
        """
        提取动作的目标产品

        例如:
        - "tried X" → [X]
        - "using X" → [X]
        """
        pattern = rf'{re.escape(signal)}\s+([A-Z][A-Za-z0-9\s\-\.]+?)(?:\s+(?:and|or|,|\.|!|\?|:|;)|$)'
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            return [match.group(1).strip()]

        return []

    def _extract_capitalized_near(self, text, signal, window=100):
        """
        提取信号词附近的大写词组（通用方法）

        Args:
            text: 文本
            signal: 信号词
            window: 窗口大小

        Returns:
            list: 产品候选
        """
        match = re.search(re.escape(signal), text, re.IGNORECASE)
        if not match:
            return []

        pos = match.start()
        start = max(0, pos - window)
        end = min(len(text), pos + len(signal) + window)
        context = text[start:end]

        # 提取所有大写开头的词组
        pattern = r'\b([A-Z][A-Za-z0-9\-\.]+(?:\s+[A-Z][A-Za-z0-9\-\.]+)*)\b'
        matches = re.finditer(pattern, context)

        products = []
        for match in matches:
            product = match.group(1).strip()
            if product and len(product) > 1:
                products.append(product)

        return products

    def _calculate_initial_confidence(self, category, product_name):
        """
        计算初始置信度

        Args:
            category: 信号类别
            product_name: 产品名

        Returns:
            float: 置信度 (0-1)
        """
        # 不同信号类别的基础置信度
        category_confidence = {
            'launch': 0.9,      # 发布信号最可靠
            'announcement': 0.9,
            'new': 0.7,
            'comparison': 0.6,  # 对比可能提到已知产品
            'testing': 0.6,
            'availability': 0.7,
            'excitement': 0.3,  # 情绪词不太可靠
        }

        base_confidence = category_confidence.get(category, 0.5)

        # 根据产品名特征调整
        # 包含版本号（更可靠）
        if re.search(r'\d+\.?\d*', product_name):
            base_confidence += 0.1

        # 包含常见后缀（更可靠）
        if any(suffix in product_name.lower() for suffix in [' ai', '-ai', ' model', ' tool']):
            base_confidence += 0.1

        return min(base_confidence, 1.0)

    def deduplicate_candidates(self, candidates):
        """
        去重候选产品

        Args:
            candidates: 候选列表

        Returns:
            list: 去重后的候选
        """
        seen = set()
        unique_candidates = []

        for candidate in candidates:
            # 标准化产品名（忽略大小写和空格）
            normalized = candidate['product_name'].lower().replace(' ', '')

            if normalized not in seen:
                seen.add(normalized)
                unique_candidates.append(candidate)

        return unique_candidates


if __name__ == '__main__':
    # 测试
    extractor = ProductExtractor()

    test_cases = [
        {
            'text': 'OpenAI just released GPT-5, and it\'s amazing!',
            'signals': [{'category': 'launch', 'signal': 'just released', 'position': 7}]
        },
        {
            'text': 'Google announced new Gemini 2.0 model today',
            'signals': [
                {'category': 'announcement', 'signal': 'announced', 'position': 7},
                {'category': 'new', 'signal': 'new', 'position': 17}
            ]
        },
        {
            'text': 'Claude Code vs Cursor - which one is better?',
            'signals': [{'category': 'comparison', 'signal': 'vs', 'position': 12}]
        },
    ]

    print("🔬 产品提取测试:\n")

    for i, case in enumerate(test_cases, 1):
        tweet = {'text': case['text'], 'id': f'test_{i}'}
        signals = case['signals']

        print(f"测试 {i}:")
        print(f"  推文: {case['text']}")
        print(f"  信号: {[s['signal'] for s in signals]}")

        products = extractor.extract_products_from_signaled_tweet(tweet, signals)

        print(f"  提取结果:")
        for p in products:
            print(f"    - {p['product_name']} (信号: {p['signal_word']}, 置信度: {p['confidence']})")
        print()
