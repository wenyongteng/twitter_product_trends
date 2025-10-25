#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter 数据集成工具
将所有历史周报数据集成到一个统一的 JSON 文件中
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List


def find_all_weekly_reports(base_dir: str) -> List[Dict]:
    """查找所有周报目录"""
    reports_dir = Path(base_dir)

    if not reports_dir.exists():
        print(f"❌ 目录不存在: {base_dir}")
        return []

    weekly_reports = []

    for item in reports_dir.iterdir():
        if item.is_dir() and item.name.startswith('week_'):
            # 检查是否有数据文件
            raw_data = item / 'raw_data.json'
            summary_data = item / 'analysis_summary.json'

            report_info = {
                'directory': str(item),
                'week_name': item.name,
                'has_raw_data': raw_data.exists(),
                'has_summary': summary_data.exists(),
                'raw_data_path': str(raw_data) if raw_data.exists() else None,
                'summary_path': str(summary_data) if summary_data.exists() else None,
            }

            # 提取日期范围
            if '_to_' in item.name:
                parts = item.name.replace('week_', '').split('_to_')
                if len(parts) == 2:
                    report_info['start_date'] = parts[0].split('_')[0]  # 去掉可能的模型后缀
                    report_info['end_date'] = parts[1].split('_')[0]

            weekly_reports.append(report_info)

    # 按日期排序
    weekly_reports.sort(key=lambda x: x.get('start_date', ''), reverse=True)

    return weekly_reports


def load_json_safe(file_path: str) -> Dict:
    """安全加载 JSON 文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️  加载失败 {file_path}: {e}")
        return {}


def integrate_all_data(weekly_reports: List[Dict]) -> Dict:
    """集成所有数据"""

    integrated_data = {
        'metadata': {
            'integration_date': datetime.now().isoformat(),
            'total_weeks': len(weekly_reports),
            'data_sources': [],
        },
        'weekly_reports': [],
        'aggregated_statistics': {
            'total_tweets_analyzed': 0,
            'total_products_identified': 0,
            'total_new_products': 0,
            'date_range': {
                'earliest': None,
                'latest': None,
            }
        },
        'all_products': {},  # 跨周期汇总的产品数据
        'all_kols': {},  # 跨周期汇总的 KOL 数据
    }

    all_products_mentions = {}
    all_kols_activity = {}

    for report in weekly_reports:
        if not report['has_summary']:
            continue

        print(f"📊 处理: {report['week_name']}")

        # 加载摘要数据
        summary = load_json_safe(report['summary_path'])

        if not summary:
            continue

        # 记录数据源
        integrated_data['metadata']['data_sources'].append({
            'week': report['week_name'],
            'date_range': f"{report.get('start_date', 'N/A')} to {report.get('end_date', 'N/A')}",
            'has_raw_data': report['has_raw_data'],
        })

        # 提取周报摘要
        week_summary = summary.get('summary', {})
        products = summary.get('products', {})
        new_products = summary.get('new_products', {})

        # 添加到周报列表
        week_data = {
            'week_name': report['week_name'],
            'date_range': {
                'start': report.get('start_date'),
                'end': report.get('end_date'),
            },
            'statistics': {
                'total_tweets': week_summary.get('total_tweets', 0),
                'unique_products': week_summary.get('unique_products', 0),
                'new_products': week_summary.get('new_products', 0),
            },
            'top_topics': week_summary.get('top_topics', {}),
            'top_products': {},
            'new_products_list': list(new_products.keys()) if new_products else [],
        }

        # 提取 Top 10 产品
        sorted_products = sorted(
            products.items(),
            key=lambda x: x[1].get('mention_count', 0),
            reverse=True
        )
        week_data['top_products'] = {
            name: data.get('mention_count', 0)
            for name, data in sorted_products[:10]
        }

        integrated_data['weekly_reports'].append(week_data)

        # 更新统计
        integrated_data['aggregated_statistics']['total_tweets_analyzed'] += week_summary.get('total_tweets', 0)

        # 汇总产品数据
        for product_name, product_data in products.items():
            if product_name not in all_products_mentions:
                all_products_mentions[product_name] = {
                    'total_mentions': 0,
                    'weeks_mentioned': [],
                    'total_engagement': 0,
                }

            all_products_mentions[product_name]['total_mentions'] += product_data.get('mention_count', 0)
            all_products_mentions[product_name]['weeks_mentioned'].append(report['week_name'])
            all_products_mentions[product_name]['total_engagement'] += product_data.get('total_engagement', 0)

        # 汇总 KOL 数据
        top_kols = summary.get('top_kols', {})
        for kol_name, kol_data in top_kols.items():
            if kol_name not in all_kols_activity:
                all_kols_activity[kol_name] = {
                    'total_tweets': 0,
                    'weeks_active': [],
                }

            # kol_data 可能是整数（推文数）或字典（详细数据）
            if isinstance(kol_data, int):
                all_kols_activity[kol_name]['total_tweets'] += kol_data
            elif isinstance(kol_data, dict):
                all_kols_activity[kol_name]['total_tweets'] += kol_data.get('tweet_count', 0)

            all_kols_activity[kol_name]['weeks_active'].append(report['week_name'])

        # 更新日期范围
        start_date = report.get('start_date')
        end_date = report.get('end_date')

        if start_date:
            if not integrated_data['aggregated_statistics']['date_range']['earliest'] or \
               start_date < integrated_data['aggregated_statistics']['date_range']['earliest']:
                integrated_data['aggregated_statistics']['date_range']['earliest'] = start_date

        if end_date:
            if not integrated_data['aggregated_statistics']['date_range']['latest'] or \
               end_date > integrated_data['aggregated_statistics']['date_range']['latest']:
                integrated_data['aggregated_statistics']['date_range']['latest'] = end_date

    # 排序并添加汇总数据
    integrated_data['all_products'] = dict(
        sorted(all_products_mentions.items(), key=lambda x: x[1]['total_mentions'], reverse=True)
    )

    integrated_data['all_kols'] = dict(
        sorted(all_kols_activity.items(), key=lambda x: x[1]['total_tweets'], reverse=True)
    )

    # 更新统计
    integrated_data['aggregated_statistics']['total_products_identified'] = len(all_products_mentions)

    return integrated_data


def generate_integration_report(integrated_data: Dict, output_path: str):
    """生成集成报告（Markdown 格式）"""

    metadata = integrated_data['metadata']
    stats = integrated_data['aggregated_statistics']

    report = f"""# Twitter 数据集成报告

**生成时间**: {metadata['integration_date']}
**数据来源**: {metadata['total_weeks']} 个周报

---

## 📊 总体统计

- **分析推文总数**: {stats['total_tweets_analyzed']:,} 条
- **识别产品总数**: {stats['total_products_identified']} 个
- **数据时间范围**: {stats['date_range']['earliest']} 至 {stats['date_range']['latest']}

---

## 📅 周报列表

"""

    for week in integrated_data['weekly_reports']:
        report += f"""### {week['week_name']}
**时间**: {week['date_range']['start']} 至 {week['date_range']['end']}
- 推文数: {week['statistics']['total_tweets']:,}
- 产品数: {week['statistics']['unique_products']}
- 新产品: {week['statistics']['new_products']}

**Top 5 产品**:
"""
        top_5 = list(week['top_products'].items())[:5]
        for i, (product, count) in enumerate(top_5, 1):
            report += f"{i}. {product}: {count}次\n"

        report += "\n"

    report += f"""
---

## 🏆 跨周期热门产品 Top 20

"""

    top_products = list(integrated_data['all_products'].items())[:20]
    report += "| 排名 | 产品名称 | 总提及次数 | 出现周数 | 总互动数 |\n"
    report += "|------|----------|------------|----------|----------|\n"

    for i, (product_name, data) in enumerate(top_products, 1):
        report += f"| {i} | {product_name} | {data['total_mentions']} | {len(data['weeks_mentioned'])} | {data['total_engagement']:,} |\n"

    report += f"""
---

## 👥 跨周期活跃 KOL Top 20

"""

    top_kols = list(integrated_data['all_kols'].items())[:20]
    report += "| 排名 | KOL | 总推文数 | 活跃周数 |\n"
    report += "|------|-----|----------|----------|\n"

    for i, (kol_name, data) in enumerate(top_kols, 1):
        report += f"| {i} | @{kol_name} | {data['total_tweets']} | {len(data['weeks_active'])} |\n"

    report += f"""
---

## 📂 数据源

"""

    for source in metadata['data_sources']:
        has_raw = "✅" if source['has_raw_data'] else "❌"
        report += f"- {source['week']} ({source['date_range']}) - 原始数据: {has_raw}\n"

    report += """
---

**生成工具**: Claude Code - Twitter Data Integration Script
**完整数据**: 见 `integrated_twitter_data.json`
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

    print("🔍 开始扫描周报数据...")

    # 查找所有周报
    weekly_reports = find_all_weekly_reports(base_dir)

    print(f"📊 找到 {len(weekly_reports)} 个周报目录")
    print(f"   - 有摘要数据: {sum(1 for r in weekly_reports if r['has_summary'])} 个")
    print(f"   - 有原始数据: {sum(1 for r in weekly_reports if r['has_raw_data'])} 个")
    print()

    # 集成数据
    print("🔄 开始集成数据...")
    integrated_data = integrate_all_data(weekly_reports)

    # 保存 JSON
    json_output_path = os.path.join(output_dir, "integrated_twitter_data.json")
    with open(json_output_path, 'w', encoding='utf-8') as f:
        json.dump(integrated_data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 集成数据已保存: {json_output_path}")

    # 生成报告
    print("\n📝 生成集成报告...")
    report_output_path = os.path.join(output_dir, "integration_report.md")
    generate_integration_report(integrated_data, report_output_path)

    # 打印统计摘要
    print("\n" + "="*60)
    print("📊 数据集成完成！")
    print("="*60)
    print(f"总推文数: {integrated_data['aggregated_statistics']['total_tweets_analyzed']:,}")
    print(f"总产品数: {integrated_data['aggregated_statistics']['total_products_identified']}")
    print(f"时间范围: {integrated_data['aggregated_statistics']['date_range']['earliest']} "
          f"至 {integrated_data['aggregated_statistics']['date_range']['latest']}")
    print(f"\n输出文件:")
    print(f"  - JSON 数据: {json_output_path}")
    print(f"  - Markdown 报告: {report_output_path}")
    print("="*60)


if __name__ == "__main__":
    main()
