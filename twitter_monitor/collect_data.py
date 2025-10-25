"""
KOL推文数据采集工具

功能：采集Top N KOL在过去N天的推文数据

用法:
    python3 collect_data.py --days 7 --kol-count 200

输出:
    weekly_reports/week_YYYY-MM-DD_to_YYYY-MM-DD/raw_data.json

说明:
    - 只采集数据，不做任何分析
    - 输出标准的JSON格式
    - 可用于后续的任何分析工具
"""

import sys
import os
import json
import argparse
from datetime import datetime

# 添加当前目录到路径
sys.path.append(os.path.dirname(__file__))

from core.data_collector import KOLWeeklyDataCollector


def main():
    parser = argparse.ArgumentParser(
        description='KOL推文数据采集工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 采集Top 200 KOL过去7天的推文
    python3 collect_data.py --days 7 --kol-count 200

    # 采集Top 300 KOL过去30天的推文
    python3 collect_data.py --days 30 --kol-count 300
        """
    )

    parser.add_argument('--days', type=int, default=7,
                       help='采集过去N天的推文（默认7天）')
    parser.add_argument('--kol-count', type=int, default=200,
                       choices=[100, 200, 300],
                       help='采集Top N个KOL（默认200）')

    args = parser.parse_args()

    print("\n" + "="*80)
    print("📊 KOL推文数据采集工具")
    print("="*80)
    print(f"\n配置:")
    print(f"   - KOL范围: Top {args.kol_count}")
    print(f"   - 时间范围: 过去 {args.days} 天")

    # 初始化采集器
    print(f"\n🔍 开始采集推文...")
    collector = KOLWeeklyDataCollector()

    # 采集数据
    data = collector.collect_weekly_tweets(
        days=args.days,
        kol_count=args.kol_count
    )

    # 创建输出目录
    date_range = data['metadata']['date_range']
    output_dir = os.path.join(
        'weekly_reports',
        f"week_{date_range['start']}_to_{date_range['end']}"
    )
    os.makedirs(output_dir, exist_ok=True)

    # 保存数据
    output_file = os.path.join(output_dir, 'raw_data.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 输出统计信息
    print(f"\n✅ 数据采集完成!")
    print(f"   - 采集推文: {data['metadata']['total_tweets']} 条")
    print(f"   - 监控KOL: {data['metadata']['kol_count']} 个")
    if 'active_kol_count' in data['metadata']:
        print(f"   - 有推文的KOL: {data['metadata']['active_kol_count']} 个")
    print(f"   - 时间范围: {date_range['start']} 至 {date_range['end']}")
    print(f"\n📁 输出文件: {output_file}")

    # API成本统计
    if 'api_stats' in data['metadata']:
        api_stats = data['metadata']['api_stats']
        print(f"\n💰 API成本:")
        print(f"   - API调用次数: {api_stats['total_calls']}")
        print(f"   - 消耗Credits: {api_stats['total_credits']:,}")
        print(f"   - 总成本: ${api_stats['total_cost']:.4f} USD")

    print("\n" + "="*80)


if __name__ == '__main__':
    main()
