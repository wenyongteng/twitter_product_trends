"""
信号检测模块
检测推文中的产品发布/讨论信号
"""

import re
from config.config import RELEASE_SIGNALS


class SignalDetector:
    """
    产品发布/讨论信号检测器
    """

    def __init__(self):
        self.signals = RELEASE_SIGNALS

    def detect_signals(self, tweet_text):
        """
        检测推文中的信号词

        Args:
            tweet_text: 推文文本

        Returns:
            list: 检测到的信号列表
            [
                {
                    'category': 'launch',
                    'signal': 'just released',
                    'position': 10
                },
                ...
            ]
        """
        text_lower = tweet_text.lower()
        detected = []

        for category, signal_list in self.signals.items():
            for signal in signal_list:
                # 查找信号词位置
                pos = text_lower.find(signal.lower())
                if pos != -1:
                    detected.append({
                        'category': category,
                        'signal': signal,
                        'position': pos,
                    })

        return detected

    def find_tweets_with_signals(self, tweets):
        """
        找出包含信号的推文

        Args:
            tweets: 推文列表

        Returns:
            list: [(tweet, signals), ...]
        """
        signaled_tweets = []

        for tweet in tweets:
            text = tweet.get('text', '')
            signals = self.detect_signals(text)

            if signals:
                signaled_tweets.append((tweet, signals))

        return signaled_tweets

    def get_signal_statistics(self, tweets):
        """
        统计信号词出现频率

        Args:
            tweets: 推文列表

        Returns:
            dict: 统计信息
        """
        signal_counts = {}
        category_counts = {}

        for tweet in tweets:
            text = tweet.get('text', '')
            signals = self.detect_signals(text)

            for sig in signals:
                # 统计具体信号词
                signal_word = sig['signal']
                signal_counts[signal_word] = signal_counts.get(signal_word, 0) + 1

                # 统计信号类别
                category = sig['category']
                category_counts[category] = category_counts.get(category, 0) + 1

        # 排序
        sorted_signals = sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            'signal_counts': dict(sorted_signals),
            'category_counts': dict(sorted_categories),
            'total_signaled_tweets': len([t for t in tweets if self.detect_signals(t.get('text', ''))]),
        }

    def get_context_window(self, text, signal_position, window_size=50):
        """
        获取信号词的上下文窗口

        Args:
            text: 文本
            signal_position: 信号词位置
            window_size: 窗口大小

        Returns:
            str: 上下文文本
        """
        start = max(0, signal_position - window_size)
        end = min(len(text), signal_position + window_size)
        return text[start:end]


if __name__ == '__main__':
    # 测试
    detector = SignalDetector()

    test_tweets = [
        {
            'text': 'OpenAI just released GPT-5, and it\'s amazing! Better than Claude in many ways.'
        },
        {
            'text': 'Google announced new Gemini 2.0 model today'
        },
        {
            'text': 'Tried the new Claude Code - it\'s incredible!'
        },
        {
            'text': 'Random tweet about AI without any signals'
        }
    ]

    print("🔍 信号检测测试:\n")

    for tweet in test_tweets:
        text = tweet['text']
        signals = detector.detect_signals(text)

        print(f"推文: {text}")
        if signals:
            print(f"信号: {signals}")
        else:
            print("无信号")
        print()

    # 统计
    print("\n📊 信号统计:")
    stats = detector.get_signal_statistics(test_tweets)
    print(f"信号类别分布: {stats['category_counts']}")
    print(f"Top信号词: {list(stats['signal_counts'].items())[:5]}")
