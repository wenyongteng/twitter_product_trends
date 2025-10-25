#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter 原始数据集成工具
遍历所有周报目录，提取所有 raw_data.json 中的推文数据
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


def find_all_raw_data_files(base_dir: str) -> List[Dict]:
    """查找所有包含 raw_data.json 的周报目录"""
    reports_dir = Path(base_dir)

    if not reports_dir.exists():
        print(f"❌ 目录不存在: {base_dir}")
        return []

    raw_data_files = []

    for item in reports_dir.iterdir():
        if item.is_dir() and item.name.startswith('week_'):
            raw_data_path = item / 'raw_data.json'

            if raw_data_path.exists():
                file_size = raw_data_path.stat().st_size / (1024 * 1024)  # MB

                report_info = {
                    'directory': str(item),
                    'week_name': item.name,
                    'raw_data_path': str(raw_data_path),
                    'file_size_mb': round(file_size, 2),
                }

                # 提取日期范围
                if '_to_' in item.name:
                    parts = item.name.replace('week_', '').split('_to_')
                    if len(parts) >= 2:
                        report_info['start_date'] = parts[0]
                        report_info['end_date'] = parts[1].split('_')[0]  # 去掉模型后缀

                raw_data_files.append(report_info)

    # 按日期排序
    raw_data_files.sort(key=lambda x: x.get('start_date', ''))

    return raw_data_files


def load_raw_tweets(file_path: str) -> List[Dict]:
    """加载原始推文数据"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # raw_data.json 的结构可能是 {'tweets': [...]} 或直接是列表
        if isinstance(data, dict):
            tweets = data.get('tweets', [])
            metadata = data.get('metadata', {})
        else:
            tweets = data
            metadata = {}

        return tweets, metadata

    except Exception as e:
        print(f"⚠️  加载失败 {file_path}: {e}")
        return [], {}


def integrate_all_raw_data(raw_data_files: List[Dict]) -> Dict:
    """集成所有原始推文数据"""

    integrated_data = {
        'metadata': {
            'integration_date': datetime.now().isoformat(),
            'total_weeks': len(raw_data_files),
            'data_sources': [],
        },
        'all_tweets': [],  # 所有推文的集合
        'tweets_by_week': {},  # 按周分组的推文
        'statistics': {
            'total_tweets': 0,
            'total_kols': 0,
            'date_range': {
                'earliest': None,
                'latest': None,
            },
        },
        'kol_activity': {},  # KOL 活跃度统计
        'weekly_summaries': [],  # 每周摘要
    }

    all_kols = set()
    kol_tweets = defaultdict(list)
    kol_stats = defaultdict(lambda: {'tweet_count': 0, 'total_likes': 0, 'total_retweets': 0, 'weeks': []})

    for report in raw_data_files:
        print(f"📊 处理: {report['week_name']} ({report['file_size_mb']} MB)")

        # 加载推文数据
        tweets, metadata = load_raw_tweets(report['raw_data_path'])

        if not tweets:
            print(f"  ⚠️  没有推文数据")
            continue

        week_name = report['week_name']

        # 记录数据源
        integrated_data['metadata']['data_sources'].append({
            'week': week_name,
            'date_range': f"{report.get('start_date', 'N/A')} to {report.get('end_date', 'N/A')}",
            'tweet_count': len(tweets),
            'file_size_mb': report['file_size_mb'],
        })

        # 为每条推文添加周信息
        week_tweets = []
        for tweet in tweets:
            # 添加元数据
            tweet_with_meta = tweet.copy()
            tweet_with_meta['source_week'] = week_name
            tweet_with_meta['source_date_range'] = {
                'start': report.get('start_date'),
                'end': report.get('end_date'),
            }

            week_tweets.append(tweet_with_meta)
            integrated_data['all_tweets'].append(tweet_with_meta)

            # 统计 KOL 活跃度
            kol_info = tweet.get('kol_info', {})
            if kol_info:
                username = kol_info.get('username', 'unknown')
                all_kols.add(username)
                kol_tweets[username].append(tweet_with_meta)

                # 更新统计
                kol_stats[username]['tweet_count'] += 1
                kol_stats[username]['total_likes'] += tweet.get('public_metrics', {}).get('like_count', 0)
                kol_stats[username]['total_retweets'] += tweet.get('public_metrics', {}).get('retweet_count', 0)
                if week_name not in kol_stats[username]['weeks']:
                    kol_stats[username]['weeks'].append(week_name)

                # 保存 KOL 详细信息
                if username not in integrated_data['kol_activity']:
                    integrated_data['kol_activity'][username] = {
                        'username': username,
                        'rank': kol_info.get('rank'),
                        'followers': kol_info.get('followers'),
                        'verified': kol_info.get('verified', False),
                        'score': kol_info.get('score'),
                    }

        # 保存按周分组的推文
        integrated_data['tweets_by_week'][week_name] = week_tweets

        # 周摘要
        week_summary = {
            'week_name': week_name,
            'date_range': {
                'start': report.get('start_date'),
                'end': report.get('end_date'),
            },
            'tweet_count': len(week_tweets),
            'unique_kols': len(set(t.get('kol_info', {}).get('username') for t in week_tweets if t.get('kol_info'))),
        }

        integrated_data['weekly_summaries'].append(week_summary)
        integrated_data['statistics']['total_tweets'] += len(week_tweets)

        # 更新日期范围
        start_date = report.get('start_date')
        end_date = report.get('end_date')

        if start_date:
            if not integrated_data['statistics']['date_range']['earliest'] or \
               start_date < integrated_data['statistics']['date_range']['earliest']:
                integrated_data['statistics']['date_range']['earliest'] = start_date

        if end_date:
            if not integrated_data['statistics']['date_range']['latest'] or \
               end_date > integrated_data['statistics']['date_range']['latest']:
                integrated_data['statistics']['date_range']['latest'] = end_date

    # 更新 KOL 统计
    for username, stats in kol_stats.items():
        if username in integrated_data['kol_activity']:
            integrated_data['kol_activity'][username].update({
                'total_tweets': stats['tweet_count'],
                'total_likes': stats['total_likes'],
                'total_retweets': stats['total_retweets'],
                'weeks_active': stats['weeks'],
                'avg_likes_per_tweet': round(stats['total_likes'] / stats['tweet_count'], 1) if stats['tweet_count'] > 0 else 0,
            })

    integrated_data['statistics']['total_kols'] = len(all_kols)

    return integrated_data


def generate_integration_report(integrated_data: Dict, output_path: str):
    """生成集成报告"""

    metadata = integrated_data['metadata']
    stats = integrated_data['statistics']

    report = f"""# Twitter 原始数据集成报告

**生成时间**: {metadata['integration_date']}
**数据来源**: {metadata['total_weeks']} 个周报

---

## 📊 总体统计

- **推文总数**: {stats['total_tweets']:,} 条
- **KOL 总数**: {stats['total_kols']} 位
- **数据时间范围**: {stats['date_range']['earliest']} 至 {stats['date_range']['latest']}

---

## 📅 周报数据详情

"""

    for week in integrated_data['weekly_summaries']:
        report += f"""### {week['week_name']}
**时间**: {week['date_range']['start']} 至 {week['date_range']['end']}
- 推文数: {week['tweet_count']:,} 条
- KOL 数: {week['unique_kols']} 位

"""

    report += """
---

## 👥 最活跃 KOL Top 30

"""

    # 按推文数排序
    sorted_kols = sorted(
        integrated_data['kol_activity'].items(),
        key=lambda x: x[1].get('total_tweets', 0),
        reverse=True
    )[:30]

    report += "| 排名 | KOL | 推文数 | 活跃周数 | 总赞数 | 总转发数 | 平均赞/推文 | 粉丝数 |\n"
    report += "|------|-----|--------|----------|--------|----------|-------------|--------|\n"

    for i, (username, data) in enumerate(sorted_kols, 1):
        report += f"| {i} | @{username} | {data.get('total_tweets', 0)} | {len(data.get('weeks_active', []))} | {data.get('total_likes', 0):,} | {data.get('total_retweets', 0):,} | {data.get('avg_likes_per_tweet', 0)} | {data.get('followers', 0):,} |\n"

    report += f"""
---

## 📂 数据源详情

"""

    for source in metadata['data_sources']:
        report += f"- **{source['week']}** ({source['date_range']})\n"
        report += f"  - 推文: {source['tweet_count']:,} 条\n"
        report += f"  - 文件大小: {source['file_size_mb']} MB\n\n"

    report += """
---

**生成工具**: Claude Code - Twitter Raw Data Integration Script
**完整数据**: 见 `integrated_all_tweets.json`

**数据结构说明**:
- `all_tweets`: 所有推文的完整列表（包含推文内容、KOL 信息、互动数据）
- `tweets_by_week`: 按周分组的推文数据
- `kol_activity`: 每位 KOL 的详细活跃度统计
- `weekly_summaries`: 每周数据摘要
"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ 集成报告已生成: {output_path}")


def main():
    # 配置路径
    base_dir = "/Users/wenyongteng/twitter hot news/weekly_monitor/weekly_reports"
    output_dir = "/Users/wenyongteng/vibe_coding/twitter_product_trends-20251022/data_sources"

    # 确保输出目录存在
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print("🔍 开始扫描所有周报目录...")

    # 查找所有 raw_data.json
    raw_data_files = find_all_raw_data_files(base_dir)

    print(f"\n📊 找到 {len(raw_data_files)} 个包含原始数据的周报:")
    for f in raw_data_files:
        print(f"  - {f['week_name']}: {f['file_size_mb']} MB")
    print()

    # 集成数据
    print("🔄 开始集成所有原始推文数据...\n")
    integrated_data = integrate_all_raw_data(raw_data_files)

    # 保存完整 JSON（包含所有推文）
    json_output_path = os.path.join(output_dir, "integrated_all_tweets.json")
    print(f"\n💾 保存完整数据...")
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(integrated_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 完整数据已保存: {json_output_path}")
    file_size = Path(json_output_path).stat().st_size / (1024 * 1024)
    print(f"   文件大小: {file_size:.2f} MB")

    # 生成报告
    print("\n📝 生成集成报告...")
    report_output_path = os.path.join(output_dir, "all_tweets_integration_report.md")
    generate_integration_report(integrated_data, report_output_path)

    # 打印统计摘要
    print("\n" + "="*70)
    print("📊 数据集成完成！")
    print("="*70)
    print(f"总推文数: {integrated_data['statistics']['total_tweets']:,} 条")
    print(f"总 KOL 数: {integrated_data['statistics']['total_kols']} 位")
    print(f"数据周数: {integrated_data['metadata']['total_weeks']} 周")
    print(f"时间范围: {integrated_data['statistics']['date_range']['earliest']} "
          f"至 {integrated_data['statistics']['date_range']['latest']}")
    print(f"\n输出文件:")
    print(f"  - 完整推文 JSON: {json_output_path} ({file_size:.2f} MB)")
    print(f"  - 集成报告: {report_output_path}")
    print("="*70)


if __name__ == "__main__":
    main()
