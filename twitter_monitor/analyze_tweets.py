#!/usr/bin/env python3
"""
推文分析脚本
提取产品、趋势和关键信息
"""

import json
import re
from collections import defaultdict, Counter
from typing import List, Dict, Set
from datetime import datetime

def load_data(file_path: str) -> Dict:
    """加载推文数据"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def extract_products(text: str) -> List[str]:
    """提取产品/工具名称"""
    # 常见产品关键词模式
    product_patterns = [
        # AI工具
        r'\b(ChatGPT|GPT-?[0-9o]+|Claude|Gemini|Copilot|Cursor|Codeium|V0|Bolt|Windsurf|Lovable|Replit|Midjourney|DALL-E|Stable Diffusion|RunwayML|Suno|Udio)\b',
        # 开发工具
        r'\b(VS Code|WebStorm|IntelliJ|Xcode|Figma|Framer|Webflow|Notion|Linear|Slack|Discord|Telegram)\b',
        # AI模型
        r'\b(Llama ?[0-9.]+|DeepSeek|Qwen|GLM-?[0-9.]+|Mistral|Falcon|Mixtral|Grok)\b',
        # AI平台
        r'\b(HuggingFace|Replicate|Together AI|Anthropic|OpenAI|Google AI|Perplexity|Poe|Character\.AI)\b',
        # 新产品关键词
        r'(launched|releasing|introduced|unveils?|announces?|debuts?|drops?)\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)?)',
        # @mentions of products
        r'@([a-zA-Z0-9_]+)',
    ]

    products = set()
    text_lower = text.lower()

    for pattern in product_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match.groups()) > 0:
                products.add(match.group(1) if match.group(1) else match.group(0))
            else:
                products.add(match.group(0))

    return list(products)

def is_new_product_mention(text: str) -> bool:
    """判断是否提到新产品"""
    new_product_keywords = [
        'launch', 'just released', 'announcing', 'new', 'released',
        'unveil', 'debut', 'introduce', 'coming soon', 'now available',
        '刚发布', '新推出', '新功能', '即将发布', '今天发布'
    ]

    text_lower = text.lower()
    return any(keyword in text_lower for keyword in new_product_keywords)

def get_sentiment(text: str) -> str:
    """简单情感分析"""
    positive_words = ['love', 'amazing', 'great', 'awesome', 'excellent', 'fantastic', 'incredible', 'best']
    negative_words = ['hate', 'terrible', 'awful', 'bad', 'poor', 'disappointed', 'worst', 'sucks']

    text_lower = text.lower()
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)

    if pos_count > neg_count:
        return 'positive'
    elif neg_count > pos_count:
        return 'negative'
    else:
        return 'neutral'

def analyze_tweets(data_file: str) -> Dict:
    """分析推文"""
    print("📊 开始分析推文...")

    data = load_data(data_file)
    tweets = data['tweets']

    print(f"总推文数: {len(tweets)}")

    # 产品统计
    product_mentions = defaultdict(list)  # product -> [tweets]
    new_products = defaultdict(list)

    # 话题统计
    topics = Counter()

    # KOL活跃度
    top_kol_tweets = defaultdict(int)

    # 按日期统计
    daily_tweets = defaultdict(int)

    print("处理推文中...")
    for i, tweet in enumerate(tweets, 1):
        if i % 200 == 0:
            print(f"  进度: {i}/{len(tweets)}")

        text = tweet.get('text', '')
        kol = tweet.get('kol_info', {})
        created_at = tweet.get('created_at', '')

        # 提取产品
        products = extract_products(text)
        for product in products:
            product_mentions[product].append({
                'text': text,
                'kol': kol.get('username'),
                'rank': kol.get('rank'),
                'followers': kol.get('followers'),
                'likes': tweet.get('likeCount', 0),
                'retweets': tweet.get('retweetCount', 0),
                'created_at': created_at,
                'sentiment': get_sentiment(text),
                'is_new': is_new_product_mention(text)
            })

            if is_new_product_mention(text):
                new_products[product].append({
                    'text': text,
                    'kol': kol.get('username'),
                    'rank': kol.get('rank'),
                    'created_at': created_at
                })

        # 提取话题（简单的关键词统计）
        keywords = ['AI', 'AGI', 'LLM', 'ML', 'agent', 'model', 'open source',
                   'coding', 'development', 'design', 'startup', 'funding']
        for keyword in keywords:
            if keyword.lower() in text.lower():
                topics[keyword] += 1

        # KOL活跃度（仅Top 100）
        if kol.get('is_top_100'):
            top_kol_tweets[kol.get('username')] += 1

        # 日期统计
        try:
            date = created_at.split()[2:4]  # Mon Oct 14
            date_str = ' '.join(date)
            daily_tweets[date_str] += 1
        except:
            pass

    print("\n生成统计报告...")

    # 按提及次数排序产品
    sorted_products = sorted(
        product_mentions.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    # 按提及次数排序新产品
    sorted_new_products = sorted(
        new_products.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )

    # 按推文数排序Top KOL
    sorted_top_kols = sorted(
        top_kol_tweets.items(),
        key=lambda x: x[1],
        reverse=True
    )[:20]  # Top 20

    result = {
        'summary': {
            'total_tweets': len(tweets),
            'unique_products': len(product_mentions),
            'new_products': len(new_products),
            'top_topics': dict(topics.most_common(10)),
            'date_range': data['metadata']['date_range'],
        },
        'products': {
            product: {
                'mention_count': len(mentions),
                'top_kols': sorted([m['kol'] for m in mentions if m['rank'] and m['rank'] <= 20])[:5],
                'sentiment': Counter([m['sentiment'] for m in mentions]),
                'total_engagement': sum(m['likes'] + m['retweets'] for m in mentions),
                'sample_tweets': mentions[:3]  # 前3条
            }
            for product, mentions in sorted_products[:30]  # Top 30产品
        },
        'new_products': {
            product: {
                'mention_count': len(mentions),
                'first_mentioned': min([m['created_at'] for m in mentions]),
                'discoverers': [{'kol': m['kol'], 'rank': m['rank']} for m in mentions],
                'sample_tweets': [m['text'] for m in mentions[:2]]
            }
            for product, mentions in sorted_new_products[:20]  # Top 20新产品
        },
        'top_kols': dict(sorted_top_kols),
        'daily_distribution': dict(daily_tweets)
    }

    return result

if __name__ == '__main__':
    import sys

    data_file = sys.argv[1] if len(sys.argv) > 1 else 'weekly_reports/week_2025-10-10_to_2025-10-17/raw_data.json'

    result = analyze_tweets(data_file)

    # 保存结果
    output_file = data_file.replace('raw_data.json', 'analysis_summary.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析完成！")
    print(f"📁 结果已保存: {output_file}")

    # 打印摘要
    print(f"\n📋 摘要:")
    print(f"  - 总推文数: {result['summary']['total_tweets']}")
    print(f"  - 识别产品: {result['summary']['unique_products']}个")
    print(f"  - 新产品: {result['summary']['new_products']}个")
    print(f"\nTop 10 提及最多的产品:")
    for i, (product, info) in enumerate(list(result['products'].items())[:10], 1):
        print(f"  {i}. {product}: {info['mention_count']}次提及")
