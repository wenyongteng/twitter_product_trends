#!/usr/bin/env python3
"""
Twitter Weekly Monitor - 统一入口脚本

功能：采集 + 分析 + Product Knowledge 集成的完整工作流

用法:
    python3 weekly_monitor.py --days 7 --kol-count 300
    python3 weekly_monitor.py --days 7 --kol-count 300 --model deepseek-v3.1-terminus

输出:
    weekly_reports/week_YYYY-MM-DD_to_YYYY-MM-DD/
    ├── raw_data.json                    # 原始推文数据
    ├── analysis_summary.json            # 分析摘要
    ├── product_classification_v3.json   # 产品分类结果
    └── enhanced_report_v3.md            # 增强报告
"""

import sys
import os
import json
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(
        description='Twitter Weekly Monitor - 完整工作流',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 采集 Top 300 KOL 过去7天的推文并分析
    python3 weekly_monitor.py --days 7 --kol-count 300

    # 指定分析模型
    python3 weekly_monitor.py --days 7 --kol-count 300 --model deepseek-v3.1-terminus
        """
    )

    parser.add_argument('--days', type=int, default=7,
                       help='采集过去N天的推文（默认7天）')
    parser.add_argument('--kol-count', type=int, default=200,
                       choices=[100, 200, 300],
                       help='采集Top N个KOL（默认200）')
    parser.add_argument('--model', type=str, default=None,
                       help='分析使用的AI模型（可选）')
    parser.add_argument('--skip-collection', action='store_true',
                       help='跳过数据采集，仅运行分析（假设数据已存在）')
    parser.add_argument('--skip-analysis', action='store_true',
                       help='跳过 analyze_tweets，仅采集数据')
    parser.add_argument('--skip-pk-integration', action='store_true',
                       help='跳过 Product Knowledge 集成')

    args = parser.parse_args()

    print("\n" + "="*80)
    print("🚀 Twitter Weekly Monitor - 完整工作流")
    print("="*80)
    print(f"\n配置:")
    print(f"   - KOL范围: Top {args.kol_count}")
    print(f"   - 时间范围: 过去 {args.days} 天")
    if args.model:
        print(f"   - 分析模型: {args.model}")
    print()

    # ============ 步骤 1: 数据采集 ============
    if not args.skip_collection:
        print("=" * 80)
        print("📊 步骤 1: 数据采集")
        print("=" * 80)

        collect_cmd = [
            sys.executable,
            str(PROJECT_ROOT / "twitter_monitor" / "collect_data.py"),
            "--days", str(args.days),
            "--kol-count", str(args.kol_count)
        ]

        try:
            result = subprocess.run(collect_cmd, check=True, cwd=str(PROJECT_ROOT))
            print("\n✅ 数据采集完成")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 数据采集失败: {e}")
            sys.exit(1)
    else:
        print("⏭️  跳过数据采集\n")

    # 查找最新的数据目录
    weekly_reports_dir = PROJECT_ROOT / "weekly_reports"
    latest_week_dir = None

    if weekly_reports_dir.exists():
        week_dirs = sorted([d for d in weekly_reports_dir.iterdir() if d.is_dir()],
                          key=lambda x: x.name, reverse=True)
        if week_dirs:
            latest_week_dir = week_dirs[0]
            print(f"📂 使用数据目录: {latest_week_dir.name}\n")

    if not latest_week_dir:
        print("❌ 错误: 未找到数据目录")
        sys.exit(1)

    raw_data_file = latest_week_dir / "raw_data.json"
    if not raw_data_file.exists():
        print(f"❌ 错误: 未找到数据文件 {raw_data_file}")
        sys.exit(1)

    # ============ 步骤 2: 推文分析 ============
    if not args.skip_analysis:
        print("=" * 80)
        print("📈 步骤 2: 推文分析")
        print("=" * 80)

        analyze_cmd = [
            sys.executable,
            str(PROJECT_ROOT / "twitter_monitor" / "analyze_tweets.py"),
            str(raw_data_file)
        ]

        try:
            result = subprocess.run(analyze_cmd, check=True, cwd=str(PROJECT_ROOT))
            print("\n✅ 推文分析完成")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ 推文分析失败: {e}")
            sys.exit(1)
    else:
        print("⏭️  跳过推文分析\n")

    # ============ 步骤 3: Product Knowledge 集成 ============
    if not args.skip_pk_integration:
        print("\n" + "=" * 80)
        print("🔗 步骤 3: Product Knowledge 集成")
        print("=" * 80)

        pk_script = PROJECT_ROOT / "scripts" / "integrate_product_knowledge_v3.py"

        if not pk_script.exists():
            print(f"⚠️  警告: Product Knowledge 脚本不存在: {pk_script}")
            print("    跳过 Product Knowledge 集成")
        else:
            pk_cmd = [
                sys.executable,
                str(pk_script),
                str(raw_data_file)
            ]

            try:
                # 自动输入 'n' 跳过更新 Product Knowledge 数据库的提示
                result = subprocess.run(
                    pk_cmd,
                    input=b'n\n',
                    check=True,
                    cwd=str(PROJECT_ROOT)
                )
                print("\n✅ Product Knowledge 集成完成")
            except subprocess.CalledProcessError as e:
                print(f"\n❌ Product Knowledge 集成失败: {e}")
                print("    继续执行后续步骤...")
    else:
        print("\n⏭️  跳过 Product Knowledge 集成\n")

    # ============ 完成 ============
    print("\n" + "=" * 80)
    print("✅ 所有步骤完成！")
    print("=" * 80)

    print(f"\n📁 输出目录: {latest_week_dir}")
    print("\n生成的文件:")

    files_to_check = [
        ("raw_data.json", "原始推文数据"),
        ("analysis_summary.json", "分析摘要"),
        ("product_classification_v3.json", "产品分类结果"),
        ("enhanced_report_v3.md", "增强报告")
    ]

    for filename, description in files_to_check:
        filepath = latest_week_dir / filename
        if filepath.exists():
            print(f"   ✅ {filename} - {description}")
        else:
            print(f"   ⚠️  {filename} - 未生成")

    print("\n" + "=" * 80)


if __name__ == '__main__':
    main()
