"""
数据采集模块
负责收集Top N KOL过去N天的推文数据
"""

import sys
import os
from datetime import datetime, timedelta
import json

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from twitter_collector import TwitterCollector
from config.config import DATA_COLLECTION


class KOLWeeklyDataCollector:
    """
    KOL周度数据采集器
    """

    def __init__(self, api_key=None):
        """
        初始化采集器

        Args:
            api_key: Twitter API密钥
        """
        # 使用Twitter API密钥（不是Claude API密钥）
        self.api_key = api_key or 'e734db59d601492e9406f6b6d30c22aa'
        self.collector = TwitterCollector(self.api_key)

        # 加载KOL数据
        self.kol_data = self._load_kol_data()

    def _load_kol_data(self):
        """加载KOL数据"""
        import csv

        # 优先使用weekly_monitor目录下的product kol_ranking_weighted.csv
        kol_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'product kol_ranking_weighted.csv'
        )

        # 如果不存在，尝试旧路径
        if not os.path.exists(kol_file):
            kol_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'kol_analysis/kol_ranking_weighted.csv'
            )

        kols = []
        with open(kol_file, 'r', encoding='utf-8-sig') as f:  # utf-8-sig 自动去除BOM
            reader = csv.DictReader(f)
            for row in reader:
                kols.append({
                    'username': row['Twitter用户名'],
                    'rank': int(row['加权排名']),
                    'score': float(row['加权总分']),
                    'followers': int(row['粉丝数']) if row.get('粉丝数') else 0,
                    'verified': row.get('官方认证', '') == '✓' or row.get('蓝V认证', '') == '✓',
                })

        return kols

    def _filter_by_date(self, tweets, start_date, end_date):
        """
        按日期过滤推文

        Args:
            tweets: 推文列表
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            list: 过滤后的推文
        """
        from dateutil import parser

        filtered = []
        for tweet in tweets:
            created_at = tweet.get('created_at') or tweet.get('createdAt')
            if not created_at:
                continue

            try:
                # 解析推文时间
                tweet_date = parser.parse(created_at)
                # 移除时区信息进行比较
                tweet_date = tweet_date.replace(tzinfo=None)

                # 检查是否在范围内
                if start_date <= tweet_date <= end_date:
                    filtered.append(tweet)
            except Exception as e:
                # 解析失败，跳过该推文
                continue

        return filtered

    def get_top_kols(self, n=300):
        """
        获取Top N KOL

        Args:
            n: 数量

        Returns:
            list: Top N KOL列表
        """
        return sorted(self.kol_data, key=lambda x: x['rank'])[:n]

    def collect_weekly_tweets(self, days=7, kol_count=300):
        """
        收集KOL周度推文

        Args:
            days: 过去N天
            kol_count: KOL数量

        Returns:
            dict: {
                'tweets': [...],
                'metadata': {...}
            }
        """
        print(f"📊 开始收集数据...")
        print(f"   - KOL范围: Top {kol_count}")
        print(f"   - 时间范围: 过去{days}天")

        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 获取Top KOL
        top_kols = self.get_top_kols(kol_count)
        print(f"   - 已加载 {len(top_kols)} 个KOL")

        # API成本跟踪
        api_calls = 0  # API调用次数

        # 收集推文
        all_tweets = []
        kol_tweet_count = {}

        for i, kol in enumerate(top_kols, 1):
            username = kol['username']

            try:
                # 使用新的用户推文收集方法
                tweets, calls = self.collector.collect_user_tweets(
                    username=username,
                    max_tweets=50,  # 每个KOL最多50条
                    include_replies=False  # 不包含回复
                )
                api_calls += calls  # 累加API调用次数

                # 过滤时间范围
                tweets = self._filter_by_date(tweets, start_date, end_date)

                # 过滤转发（如果配置要求）
                if DATA_COLLECTION['exclude_retweets']:
                    tweets = [t for t in tweets if not t.get('text', '').startswith('RT @')]

                # 过滤低互动（如果配置要求）
                min_engagement = DATA_COLLECTION.get('min_engagement', 0)
                if min_engagement > 0:
                    tweets = [
                        t for t in tweets
                        if (t.get('public_metrics', {}).get('like_count', 0) +
                            t.get('public_metrics', {}).get('retweet_count', 0)) >= min_engagement
                    ]

                # 添加KOL信息到每条推文
                for tweet in tweets:
                    tweet['kol_info'] = {
                        'username': username,
                        'rank': kol['rank'],
                        'score': kol['score'],
                        'is_top_100': kol['rank'] <= 100,
                        'followers': kol['followers'],
                        'verified': kol['verified'],
                    }

                all_tweets.extend(tweets)
                kol_tweet_count[username] = len(tweets)

                if i % 10 == 0:
                    print(f"   进度: {i}/{len(top_kols)} KOL, 已收集 {len(all_tweets)} 条推文")

            except Exception as e:
                print(f"   ⚠️ 收集 {username} 的推文失败: {e}")
                continue

        # 计算API成本
        # 每次调用 /twitter/user/last_tweets 消耗 300 credits
        # $20 可以买 2,000,000 credits
        credits_per_call = 300
        credits_per_dollar = 2000000 / 20  # 100,000 credits per dollar

        total_credits = api_calls * credits_per_call
        total_cost_usd = total_credits / credits_per_dollar

        # 构建元数据
        metadata = {
            'total_tweets': len(all_tweets),
            'kol_count': len(top_kols),
            'kol_with_tweets': len([k for k in kol_tweet_count.values() if k > 0]),
            'date_range': {
                'start': start_date.strftime('%Y-%m-%d'),
                'end': end_date.strftime('%Y-%m-%d'),
            },
            'collection_time': datetime.now().isoformat(),
            'kol_tweet_distribution': kol_tweet_count,
            'api_usage': {
                'api_calls': api_calls,
                'total_credits': total_credits,
                'cost_usd': round(total_cost_usd, 4),
            }
        }

        print(f"\n✅ 数据收集完成!")
        print(f"   - 总推文数: {metadata['total_tweets']}")
        print(f"   - 有推文的KOL: {metadata['kol_with_tweets']}/{metadata['kol_count']}")
        print(f"\n💰 API成本:")
        print(f"   - API调用次数: {api_calls}")
        print(f"   - 消耗Credits: {total_credits:,}")
        print(f"   - 成本: ${total_cost_usd:.4f} USD")

        return {
            'tweets': all_tweets,
            'metadata': metadata,
        }

    def build_indexes(self, data):
        """
        构建数据索引（加速后续查询）

        Args:
            data: 采集的数据

        Returns:
            dict: 索引数据
        """
        tweets = data['tweets']

        # KOL索引
        kol_index = {}
        for tweet in tweets:
            username = tweet['kol_info']['username']
            if username not in kol_index:
                kol_index[username] = []
            kol_index[username].append(tweet)

        # 日期索引
        date_index = {}
        for tweet in tweets:
            date = tweet.get('created_at', '')[:10]  # YYYY-MM-DD
            if date not in date_index:
                date_index[date] = []
            date_index[date].append(tweet)

        # Top100 KOL的推文
        top100_tweets = [t for t in tweets if t['kol_info']['is_top_100']]

        return {
            'kol_index': kol_index,
            'date_index': date_index,
            'top100_tweets': top100_tweets,
            'all_tweets': tweets,
        }

    def save_raw_data(self, data, output_dir):
        """
        保存原始数据

        Args:
            data: 数据
            output_dir: 输出目录
        """
        os.makedirs(output_dir, exist_ok=True)

        # 保存为JSON
        output_file = os.path.join(output_dir, 'raw_data.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"💾 原始数据已保存: {output_file}")

        return output_file


if __name__ == '__main__':
    # 测试
    collector = KOLWeeklyDataCollector()

    # 收集数据
    data = collector.collect_weekly_tweets(days=7, kol_count=10)  # 测试用10个KOL

    # 构建索引
    indexes = collector.build_indexes(data)

    print(f"\n索引统计:")
    print(f"  - KOL数量: {len(indexes['kol_index'])}")
    print(f"  - 日期数量: {len(indexes['date_index'])}")
    print(f"  - Top100推文: {len(indexes['top100_tweets'])}")
