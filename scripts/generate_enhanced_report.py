#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版 Twitter 产品趋势报告生成器
- 添加目录导航
- 新产品全部展示（121个）
- 热门老产品 Top 30 详细展示
- 其他老产品用表格汇总
- 每个产品评价下都有可折叠的详细推文
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any


def load_analysis_data(json_path: str) -> Dict:
    """加载分析数据"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_collapsible_tweets(tweets: List, product_name: str) -> str:
    """创建可折叠的推文详情区域"""
    if not tweets:
        return ""

    content = f"\n<details>\n<summary>📱 查看 {len(tweets)} 条相关推文详情</summary>\n\n"

    for i, tweet in enumerate(tweets, 1):
        # 处理字符串类型的推文（new_products）
        if isinstance(tweet, str):
            content += f"""
#### 推文 {i}

**内容**:
> {tweet}

---
"""
        # 处理字典类型的推文（products）
        elif isinstance(tweet, dict):
            kol = tweet.get('kol', 'Unknown')
            rank = tweet.get('rank', 'N/A')
            followers = tweet.get('followers', 0)
            likes = tweet.get('likes', 0)
            retweets = tweet.get('retweets', 0)
            text = tweet.get('text', '')
            created_at = tweet.get('created_at', '')
            sentiment = tweet.get('sentiment', 'neutral')

            # 情感标签
            sentiment_emoji = {
                'positive': '🟢',
                'negative': '🔴',
                'neutral': '⚪'
            }.get(sentiment, '⚪')

            content += f"""
#### 推文 {i} {sentiment_emoji}

**KOL**: @{kol} (Rank #{rank}, {followers:,} 粉丝)
**发布时间**: {created_at}
**互动**: 👍 {likes:,} | 🔄 {retweets:,}

**内容**:
> {text}

---
"""

    content += "\n</details>\n\n"
    return content


def generate_product_section(product_name: str, data: Dict, rank: int = None) -> str:
    """生成单个产品的详细分析章节"""
    mention_count = data.get('mention_count', 0)
    sentiment = data.get('sentiment', {})
    total_engagement = data.get('total_engagement', 0)
    sample_tweets = data.get('sample_tweets', [])

    # 计算热度星级
    if mention_count >= 50:
        heat = "⭐⭐⭐⭐⭐"
    elif mention_count >= 30:
        heat = "⭐⭐⭐⭐"
    elif mention_count >= 15:
        heat = "⭐⭐⭐"
    elif mention_count >= 5:
        heat = "⭐⭐"
    else:
        heat = "⭐"

    # 排名标题
    rank_text = f"#### {rank}. " if rank else "#### "

    section = f"""{rank_text}{product_name} {heat}

**基本信息**
- 提及次数: **{mention_count}次**
- 讨论热度: {heat}
- 总互动数: {total_engagement:,} (likes + retweets)

**观点分布**
"""

    # 情感分析
    positive = sentiment.get('positive', 0)
    negative = sentiment.get('negative', 0)
    neutral = sentiment.get('neutral', 0)

    if positive > 0:
        section += f"- 🟢 正面评价: {positive}条\n"
    if negative > 0:
        section += f"- 🔴 负面评价: {negative}条\n"
    if neutral > 0:
        section += f"- ⚪中性/功能介绍: {neutral}条\n"

    # 添加可折叠的推文详情
    section += create_collapsible_tweets(sample_tweets, product_name)

    section += "---\n\n"
    return section


def generate_product_table(products: Dict[str, Dict], start_rank: int) -> str:
    """生成产品汇总表格"""
    table = """
| 排名 | 产品名称 | 提及次数 | 主要评价 |
|------|----------|----------|----------|
"""

    sorted_products = sorted(products.items(), key=lambda x: x[1].get('mention_count', 0), reverse=True)

    for i, (product_name, data) in enumerate(sorted_products, start_rank):
        mention_count = data.get('mention_count', 0)
        sentiment = data.get('sentiment', {})

        # 简要评价
        positive = sentiment.get('positive', 0)
        negative = sentiment.get('negative', 0)

        if positive > negative and positive > 0:
            评价 = "🟢 正面为主"
        elif negative > positive and negative > 0:
            评价 = "🔴 负面关注"
        else:
            评价 = "⚪ 中性讨论"

        table += f"| {i} | {product_name} | {mention_count} | {评价} |\n"

    return table + "\n"


def generate_enhanced_report(analysis_json_path: str, output_path: str):
    """生成改进版完整报告"""

    # 加载数据
    data = load_analysis_data(analysis_json_path)
    summary = data.get('summary', {})
    products = data.get('products', {})
    new_products = data.get('new_products', {})

    # 按提及次数排序产品
    sorted_products = sorted(products.items(), key=lambda x: x[1].get('mention_count', 0), reverse=True)
    top_30_products = dict(sorted_products[:30])
    other_products = dict(sorted_products[30:])

    # 开始生成报告
    report = f"""# Twitter Weekly Report - 完整版（改进版）
## {summary.get('date_range', {}).get('start')} 至 {summary.get('date_range', {}).get('end')}

生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Powered by: Claude Code - Twitter Weekly Monitor Skill

---

## 📊 数据概览

- **监控KOL**: 300个
- **分析推文**: {summary.get('total_tweets', 0):,}条
- **识别产品**: {summary.get('unique_products', 0)}个
- **发现新产品**: {summary.get('new_products', 0)}个

---

## 📑 目录

### 一、新产品发现（{len(new_products)}个）
"""

    # 生成新产品目录
    sorted_new_products = sorted(new_products.items(), key=lambda x: x[1].get('mention_count', 0), reverse=True)
    for i, (product_name, _) in enumerate(sorted_new_products, 1):
        report += f"{i}. [{product_name}](#新产品-{i}-{product_name.lower().replace(' ', '-')})\n"

    report += f"""
### 二、热门产品 Top 30（详细分析）
"""

    for i in range(1, min(31, len(top_30_products) + 1)):
        product_name = sorted_products[i-1][0]
        report += f"{i}. [{product_name}](#热门产品-{i}-{product_name.lower().replace(' ', '-')})\n"

    report += f"""
### 三、其他产品汇总（{len(other_products)}个）
- [产品列表表格](#其他产品汇总表格)

---

## 📦 一、新产品发现

本周共发现 **{len(new_products)}个** 新产品/新功能发布。

"""

    # 生成新产品详细内容
    for i, (product_name, product_data) in enumerate(sorted_new_products, 1):
        report += f"### 新产品 {i}. {product_name}\n\n"
        report += generate_product_section(product_name, product_data)

    report += """
---

## 🏆 二、热门产品 Top 30（详细分析）

以下是本周讨论最热烈的30个产品，包含详细的KOL观点和推文内容。

"""

    # 生成 Top 30 产品详细内容
    for i, (product_name, product_data) in enumerate(sorted_products[:30], 1):
        report += f"### 热门产品 {i}. {product_name}\n\n"
        report += generate_product_section(product_name, product_data, rank=i)

    report += """
---

## 📋 三、其他产品汇总表格

以下是第31名之后的产品汇总，按提及次数排序：

"""

    # 生成其他产品表格
    report += generate_product_table(other_products, start_rank=31)

    report += f"""
---

## 📊 统计摘要

### 话题热度 Top 10
"""

    top_topics = summary.get('top_topics', {})
    for topic, count in sorted(top_topics.items(), key=lambda x: x[1], reverse=True):
        report += f"- **{topic}**: {count}次\n"

    report += f"""

---

## 🔗 数据来源

- **原始数据**: `raw_data.json`
- **分析摘要**: `analysis_summary.json`
- **数据采集日期**: {summary.get('date_range', {}).get('end')}
- **报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

**报告说明**:
- 本报告基于 Top 300 KOL 的 {summary.get('total_tweets', 0):,} 条推文深度分析
- 每个产品评价下都可以展开查看详细推文内容
- 新产品全部展示，热门老产品 Top 30 详细分析，其他产品表格汇总

**生成工具**: Claude Code + Twitter Weekly Monitor Skill
"""

    # 写入文件
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 改进版报告已生成: {output_path}")
    print(f"📊 包含:")
    print(f"   - {len(new_products)} 个新产品（全部详细展示）")
    print(f"   - Top 30 热门产品（详细分析）")
    print(f"   - {len(other_products)} 个其他产品（表格汇总）")
    print(f"   - 所有产品评价都可展开查看详细推文")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("用法: python3 generate_enhanced_report.py <analysis_summary.json路径> <输出报告路径>")
        sys.exit(1)

    analysis_json = sys.argv[1]
    output_md = sys.argv[2]

    generate_enhanced_report(analysis_json, output_md)
