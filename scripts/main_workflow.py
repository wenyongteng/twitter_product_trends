#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Product Trends - 主工作流
整合采集、提取、分类和报告生成
"""

import sys
from pathlib import Path
from datetime import datetime

# 导入各模块
from twitter_collector import TwitterCollector
from product_processor import ProductProcessor


def main_workflow(days=7, kol_count=300, test_mode=False):
    """
    主工作流

    Args:
        days: 时间范围
        kol_count: KOL 数量
        test_mode: 测试模式(使用已有数据)
    """

    start_time = datetime.now()

    print("=" * 80)
    print("🚀 Twitter 产品趋势分析 - 完整流程")
    print("=" * 80)
    print(f"⏰ 开始时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📅 时间范围: 过去 {days} 天")
    print(f"👥 KOL 数量: {kol_count}")
    print(f"🧪 测试模式: {'是' if test_mode else '否'}")
    print("=" * 80)

    try:
        # === Step 1: 采集 Twitter 数据 ===
        print("\n[1/3] 📱 采集 Twitter 数据...")
        print("-" * 80)

        if test_mode:
            # 测试模式: 使用已有数据
            print("   🧪 测试模式: 使用已有数据")
            data_file = Path(__file__).parent.parent / "data_sources" / "integrated_all_tweets.json"

            if not data_file.exists():
                print(f"   ❌ 测试数据不存在: {data_file}")
                return None

            import json
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            raw_tweets = data.get('all_tweets', [])[:200]  # 只用前200条测试
            print(f"   ✅ 加载测试数据: {len(raw_tweets)} 条推文")

        else:
            collector = TwitterCollector()
            raw_tweets = collector.collect(days=days, kol_count=kol_count)

        print(f"\n   ✅ Step 1 完成: {len(raw_tweets)} 条推文")

        # === Step 2: 提取和匹配产品 ===
        print("\n[2/3] 🔍 提取和匹配产品...")
        print("-" * 80)

        processor = ProductProcessor()
        extraction_result = processor.process(raw_tweets)

        print(f"\n   ✅ Step 2 完成:")
        print(f"      - 提取产品: {extraction_result['summary']['total_products_extracted']} 个")
        print(f"      - 新产品: {extraction_result['summary']['new_products']} 个")
        print(f"      - 已有产品: {extraction_result['summary']['matched_existing']} 个")
        print(f"      - 新版本: {extraction_result['summary']['new_releases']} 个")

        # === Step 3: 更新 Product Knowledge 数据库 ===
        print("\n[3/3] 💾 更新 Product Knowledge 数据库...")
        print("-" * 80)

        if extraction_result['summary']['new_products'] > 0:
            processor.update_knowledge_db()
            print(f"\n   ✅ Step 3 完成: 数据库已更新")
        else:
            print(f"\n   ℹ️  Step 3 跳过: 没有新产品")

        # === 总结 ===
        elapsed = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 80)
        print("✅ 完整流程执行成功!")
        print("=" * 80)
        print(f"⏱️  总耗时: {elapsed:.1f} 秒 ({elapsed/60:.1f} 分钟)")
        print(f"📊 处理推文: {len(raw_tweets)} 条")
        print(f"🔍 识别产品: {extraction_result['summary']['total_products_extracted']} 个")
        print(f"🆕 新产品: {extraction_result['summary']['new_products']} 个")
        print(f"📦 已有产品: {extraction_result['summary']['matched_existing']} 个")
        print(f"🚀 新版本: {extraction_result['summary']['new_releases']} 个")
        print("=" * 80)

        # 返回结果摘要
        return {
            'success': True,
            'tweets_processed': len(raw_tweets),
            'extraction_result': extraction_result,
            'elapsed_time': elapsed
        }

    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断执行")
        return None

    except Exception as e:
        print(f"\n\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Twitter 产品趋势分析 - 完整流程')
    parser.add_argument('--days', type=int, default=7, help='时间范围(天)')
    parser.add_argument('--kol-count', type=int, default=300, help='KOL数量')
    parser.add_argument('--test', action='store_true', help='测试模式(使用已有数据)')

    args = parser.parse_args()

    result = main_workflow(
        days=args.days,
        kol_count=args.kol_count,
        test_mode=args.test
    )

    if result and result['success']:
        print("\n🎉 流程完成!")
        sys.exit(0)
    else:
        print("\n💥 流程失败!")
        sys.exit(1)
